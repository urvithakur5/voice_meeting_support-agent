"""Deterministic Bluetooth / audio headset diagnostic for Windows.

Separately checks:
  1. Whether the Bluetooth subsystem is available.
  2. Whether a Bluetooth audio device is connected.
  3. Whether that device appears as an active audio endpoint.

"Bluetooth enabled" and "Bluetooth headset connected" are kept as
separate facts — the tool never conflates the two.
No values are invented.
"""

from __future__ import annotations

from typing import Any

from ._common import (
    STATUS_OK,
    STATUS_WARNING,
    STATUS_FAILED,
    STATUS_UNKNOWN,
    area_result,
    observation,
    unknown_result,
    worst_status,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_bluetooth_audio"
_TITLE = "Bluetooth audio diagnostic"

# Strings that indicate a Bluetooth audio endpoint in Windows device names.
_BT_AUDIO_KEYWORDS = (
    "bluetooth",
    "headset",
    "headphone",
    "earphone",
    "airpod",
    "jabra",
    "plantronics",
    "poly ",
    "bose ",
    "sony ",
    "sennheiser",
    "jbl ",
    "beats",
    "anker",
    "soundcore",
    "samsung galaxy buds",
    "pixel buds",
)


def _looks_bt_audio(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in _BT_AUDIO_KEYWORDS)


def check_bluetooth_audio() -> dict[str, Any]:
    """Return observed Bluetooth / audio headset state.

    Checks: Bluetooth radio availability, connected Bluetooth audio device,
    and whether that device presents as an active audio endpoint.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    obs: list[dict] = []

    # ── 1. Bluetooth radio / subsystem ────────────────────────────────────
    # Query PnP devices with class "Bluetooth" to detect the radio.
    radio_result = powershell_json(
        "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status "
        "| ConvertTo-Json -Compress"
    )
    bt_radios = radio_result.get("records", [])
    bt_available = len(bt_radios) > 0

    obs.append(observation(
        "Bluetooth subsystem available" if bt_available
        else "Bluetooth subsystem not detected",
        STATE_OK if bt_available else STATE_FAILED,
    ))

    if not bt_available:
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_FAILED,
            "No active Bluetooth radio was found on this machine",
            obs,
            bluetooth_available=False,
            audio_device_connected=False,
            device_name="unknown",
        )

    # ── 2. Enumerate Bluetooth audio devices via PnP ─────────────────────
    bt_audio_result = powershell_json(
        "Get-PnpDevice -Class 'AudioEndpoint' -ErrorAction SilentlyContinue "
        "| Where-Object { $_.InstanceId -match 'BTHENUM|BTH' -or $_.FriendlyName -match 'bluetooth' } "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status,InstanceId "
        "| ConvertTo-Json -Compress"
    )
    bt_audio_pnp = bt_audio_result.get("records", [])

    # ── 3. Check audio endpoints via pycaw ────────────────────────────────
    # pycaw gives us the rendered (output) endpoint list.
    pycaw_bt_name: str | None = None
    pycaw_bt_active = False
    try:
        from pycaw.pycaw import AudioUtilities
        from pycaw.constants import DEVICE_STATE, EDataFlow

        all_output = AudioUtilities.GetAllDevices(
            data_flow=EDataFlow.eRender.value,
            device_state=DEVICE_STATE.ACTIVE.value,
        )
        for dev in all_output:
            name = getattr(dev, "FriendlyName", None) or str(dev)
            if _looks_bt_audio(name):
                pycaw_bt_name = name
                pycaw_bt_active = True
                break
    except ImportError:
        pass  # pycaw unavailable; fall back to PnP results only
    except Exception:
        pass

    # Determine observed device name from either source.
    device_name: str = "unknown"
    if pycaw_bt_name:
        device_name = pycaw_bt_name
    elif bt_audio_pnp:
        device_name = as_text(pick(bt_audio_pnp[0], "FriendlyName")) or "unknown"

    audio_device_connected = bool(bt_audio_pnp) or pycaw_bt_active

    obs.append(observation(
        f"Bluetooth audio device connected: {device_name}" if audio_device_connected
        else "No Bluetooth audio device connected",
        STATE_OK if audio_device_connected else STATE_WARNING,
    ))

    if audio_device_connected:
        obs.append(observation(
            "Device appears as active audio endpoint" if pycaw_bt_active
            else "Device found via PnP but not confirmed as active audio endpoint",
            STATE_OK if pycaw_bt_active else STATE_WARNING,
        ))

    # ── 4. Overall status ─────────────────────────────────────────────────
    if not audio_device_connected:
        overall = STATUS_WARNING
        reason = "Bluetooth is available but no Bluetooth audio device is connected"
    elif not pycaw_bt_active and bt_audio_pnp:
        overall = STATUS_WARNING
        reason = (
            f"Bluetooth audio device '{device_name}' detected via PnP "
            "but was not confirmed as an active audio output endpoint"
        )
    else:
        overall = STATUS_OK
        reason = f"Bluetooth audio device '{device_name}' is connected and active"

    return area_result(
        _TOOL,
        _TITLE,
        overall,
        reason,
        obs,
        bluetooth_available=bt_available,
        audio_device_connected=audio_device_connected,
        audio_endpoint_active=pycaw_bt_active,
        device_name=device_name,
    )

"""Deterministic docking station diagnostic for Windows.

Detects observable docking / port-replicator state via USB device
enumeration and peripheral counting.  Does NOT claim a dock is faulty
unless there is actual evidence (e.g. no hub devices at all).
Does NOT make destructive changes.
"""

from __future__ import annotations

from typing import Any

from ._common import (
    STATUS_OK,
    STATUS_WARNING,
    STATUS_UNKNOWN,
    area_result,
    observation,
    unknown_result,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_dock"
_TITLE = "Docking station diagnostic"

# PnP class names typically associated with dock hubs / port replicators.
_DOCK_HUB_CLASSES = ("USB", "HIDClass")

# Description keywords that suggest a dock or port replicator.
_DOCK_KEYWORDS = (
    "dock",
    "docking",
    "port replicator",
    "universal adapter",
    "thunderbolt",
    "usb hub",
    "usb-c hub",
    "usb type-c",
    "displaylink",
    "dell wd",
    "lenovo hybrid dock",
    "hp thunderbolt",
    "kensington sd",
    "targus dock",
    "anker dock",
    "caldigit",
    "belkin dock",
    "plugable dock",
)


def _looks_like_dock(name: str, description: str = "") -> bool:
    text = (name + " " + description).lower()
    return any(kw in text for kw in _DOCK_KEYWORDS)


def check_dock() -> dict[str, Any]:
    """Return observed docking station state.

    Detects dock/hub devices, counts USB and display peripherals attached
    to them, and reports any recognisable dock model/vendor string.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    obs: list[dict] = []

    # ── 1. Look for USB hub / dock devices ───────────────────────────────
    usb_result = powershell_json(
        "Get-PnpDevice -Class USB -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status,InstanceId "
        "| ConvertTo-Json -Compress"
    )
    usb_devices = usb_result.get("records", [])

    dock_devices = [
        d for d in usb_devices
        if _looks_like_dock(
            as_text(pick(d, "FriendlyName")) or "",
            as_text(pick(d, "InstanceId")) or "",
        )
    ]

    dock_model = "unknown"
    dock_detected = len(dock_devices) > 0

    if dock_devices:
        dock_model = as_text(pick(dock_devices[0], "FriendlyName")) or "unknown"
        obs.append(observation(f"Dock / hub device: {dock_model}", STATE_OK))
    else:
        obs.append(observation(
            "No dock device recognised by name; checking USB hub count",
            STATE_UNKNOWN,
        ))

    # ── 2. Count USB hubs (generic dock proxy) ───────────────────────────
    hub_result = powershell_json(
        "Get-PnpDevice -Class USB -ErrorAction SilentlyContinue "
        "| Where-Object { $_.FriendlyName -match 'Hub' -and $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status "
        "| ConvertTo-Json -Compress"
    )
    hub_devices = hub_result.get("records", [])
    hub_count = len(hub_devices)

    obs.append(observation(
        f"{hub_count} USB hub(s) detected",
        STATE_OK if hub_count > 0 else STATE_UNKNOWN,
    ))

    # ── 3. Monitor devices (dock output evidence) ────────────────────────
    monitor_result = powershell_json(
        "Get-PnpDevice -Class Monitor -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status "
        "| ConvertTo-Json -Compress"
    )
    monitors = monitor_result.get("records", [])
    monitor_count = len(monitors)

    obs.append(observation(
        f"{monitor_count} monitor(s) detected via PnP",
        STATE_OK if monitor_count > 0 else STATE_WARNING,
    ))

    # ── 4. Count HID devices (keyboards, mice) that suggest peripherals ──
    hid_result = powershell_json(
        "Get-PnpDevice -Class HIDClass -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName "
        "| ConvertTo-Json -Compress"
    )
    hid_devices = hid_result.get("records", [])
    hid_count = len(hid_devices)

    # ── 5. Overall status ─────────────────────────────────────────────────
    if dock_detected:
        overall = STATUS_OK
        reason = (
            f"Dock device '{dock_model}' detected. "
            f"{hub_count} USB hub(s), {monitor_count} monitor(s), "
            f"{hid_count} HID device(s) observed."
        )
    elif hub_count > 0:
        overall = STATUS_OK
        reason = (
            f"No named dock recognised, but {hub_count} USB hub(s) and "
            f"{monitor_count} monitor(s) detected — dock may be connected."
        )
    else:
        overall = STATUS_UNKNOWN
        reason = (
            "No dock device or USB hub detected. "
            "If you expect a dock to be connected, check the physical connection."
        )

    return area_result(
        _TOOL,
        _TITLE,
        overall,
        reason,
        obs,
        dock_detected=dock_detected,
        dock_model=dock_model,
        usb_hub_count=hub_count,
        monitor_count=monitor_count,
        hid_device_count=hid_count,
    )

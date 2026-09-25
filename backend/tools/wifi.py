"""Deterministic Wi-Fi diagnostic for Windows.

Reports only what Windows can actually observe.  When a property cannot
be reliably read the value is ``"unknown"`` with a truthful reason.
No values are invented.
"""

from __future__ import annotations

import platform
import socket
import time
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
    tcp_probe,
    as_int,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_wifi"
_TITLE = "Wi-Fi diagnostic"


def check_wifi() -> dict[str, Any]:
    """Return observed Wi-Fi state on this Windows machine.

    Collects: adapter presence, enabled state, connection state, SSID,
    signal strength, local IP, and basic internet reachability.
    All values originate from real Windows API / netsh queries.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    # ── 1. Query adapters via PowerShell Get-NetAdapter ──────────────────
    adapter_result = powershell_json(
        "Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'Wi.?Fi|Wireless|802\\.11|WLAN' } "
        "| Select-Object Name,Status,InterfaceDescription,MacAddress "
        "| ConvertTo-Json -Compress"
    )

    adapters = adapter_result.get("records", [])
    obs: list[dict] = []

    if not adapters:
        obs.append(observation("Wi-Fi adapter", STATE_FAILED))
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_FAILED,
            "No Wi-Fi adapter was detected on this machine",
            obs,
            wifi_adapter_detected=False,
            connected=False,
            ssid="unknown",
            signal_strength="unknown",
        )

    adapter = adapters[0]
    adapter_name = as_text(pick(adapter, "Name")) or "unknown"
    adapter_status = as_text(pick(adapter, "Status")) or "unknown"
    adapter_up = adapter_status.lower() == "up"

    obs.append(observation(
        f"Wi-Fi adapter: {adapter_name}",
        STATE_OK if adapter_up else STATE_WARNING,
    ))

    if not adapter_up:
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_WARNING,
            f"Wi-Fi adapter '{adapter_name}' is present but not up (status: {adapter_status})",
            obs,
            wifi_adapter_detected=True,
            adapter_name=adapter_name,
            adapter_status=adapter_status,
            connected=False,
            ssid="unknown",
            signal_strength="unknown",
        )

    # ── 2. Query connection details via netsh ─────────────────────────────
    netsh_result = powershell_script(
        "netsh wlan show interfaces",
        timeout_seconds=8.0,
    )
    netsh_out = netsh_result.get("stdout", "")

    ssid = "unknown"
    signal_raw = "unknown"
    connected = False

    if netsh_out:
        for line in netsh_out.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key_clean = key.strip().lower()
            value_clean = value.strip()
            if "ssid" in key_clean and "bssid" not in key_clean and value_clean:
                ssid = value_clean
            if "signal" in key_clean and value_clean:
                signal_raw = value_clean.replace("%", "").strip()
            if "state" in key_clean and "connected" in value_clean.lower():
                connected = True

    signal_int = as_int(signal_raw)

    obs.append(observation(
        "Connected to network" if connected else "Not connected to a network",
        STATE_OK if connected else STATE_FAILED,
    ))

    if connected and ssid != "unknown":
        obs.append(observation(f"SSID: {ssid}", STATE_OK))

    if signal_int is not None:
        if signal_int >= 70:
            sig_state = STATE_OK
        elif signal_int >= 40:
            sig_state = STATE_WARNING
        else:
            sig_state = STATE_FAILED
        obs.append(observation(f"Signal strength: {signal_int}%", sig_state))

    if not connected:
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_WARNING,
            "Wi-Fi adapter is up but no active network connection was detected",
            obs,
            wifi_adapter_detected=True,
            adapter_name=adapter_name,
            adapter_status=adapter_status,
            connected=False,
            ssid="unknown",
            signal_strength=signal_int if signal_int is not None else "unknown",
        )

    # ── 3. Internet reachability ──────────────────────────────────────────
    probe = tcp_probe("8.8.8.8", 53, timeout_seconds=2.0)
    internet_ok = probe.get("reachable", False)
    latency_ms = probe.get("latency_ms")

    obs.append(observation(
        "Internet reachable" if internet_ok else "Internet not reachable",
        STATE_OK if internet_ok else STATE_FAILED,
    ))

    # ── 4. Overall status ─────────────────────────────────────────────────
    if signal_int is not None and signal_int < 40:
        overall = STATUS_WARNING
    elif not internet_ok:
        overall = STATUS_WARNING
    else:
        overall = STATUS_OK

    reason = (
        f"Connected to '{ssid}'"
        + (f", signal {signal_int}%" if signal_int is not None else "")
        + (f", latency {latency_ms}ms" if latency_ms else "")
        + (", internet reachable" if internet_ok else ", internet not reachable")
    )

    result: dict[str, Any] = {
        "wifi_adapter_detected": True,
        "adapter_name": adapter_name,
        "adapter_status": adapter_status,
        "connected": connected,
        "ssid": ssid,
        "internet": internet_ok,
    }
    if signal_int is not None:
        result["signal_strength"] = signal_int
    else:
        result["signal_strength"] = "unknown"
    if latency_ms is not None:
        result["latency_ms"] = latency_ms

    return area_result(_TOOL, _TITLE, overall, reason, obs, **result)

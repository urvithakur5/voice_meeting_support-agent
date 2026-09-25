"""Deterministic display / monitor diagnostic for Windows.

Reports only what Windows can observe via Get-CimInstance Win32_VideoController
and Get-PnpDevice.  When a monitor's state cannot be determined the result
carries status ``"unknown"`` with a truthful reason.
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
    as_int,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_display"
_TITLE = "Display / monitor diagnostic"


def check_display() -> dict[str, Any]:
    """Return observed display state: adapters, monitors, resolution, active state.

    Collects display adapters from Win32_VideoController and connected
    monitors from Win32_DesktopMonitor.  Reports actual screen resolutions
    and active state where Windows exposes them.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    obs: list[dict] = []

    # ── 1. Video adapters via WMI ─────────────────────────────────────────
    adapter_result = powershell_json(
        "Get-CimInstance Win32_VideoController "
        "| Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution,"
        "CurrentRefreshRate,AdapterRAM,VideoProcessor,Status "
        "| ConvertTo-Json -Compress"
    )
    adapters = adapter_result.get("records", [])

    if not adapters:
        obs.append(observation("Display adapter", STATE_FAILED))
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_FAILED,
            "No display adapter was found via WMI",
            obs,
            display_adapter_count=0,
            monitors=[],
        )

    adapter_summaries = []
    for adapter in adapters:
        name = as_text(pick(adapter, "Name")) or "unknown"
        h_res = as_int(pick(adapter, "CurrentHorizontalResolution"))
        v_res = as_int(pick(adapter, "CurrentVerticalResolution"))
        refresh = as_int(pick(adapter, "CurrentRefreshRate"))
        status = as_text(pick(adapter, "Status")) or "unknown"

        if h_res and v_res:
            res_str = f"{h_res}×{v_res}"
            if refresh:
                res_str += f" @{refresh}Hz"
        else:
            res_str = "unknown"

        adapter_summaries.append({
            "name": name,
            "resolution": res_str,
            "status": status,
        })
        obs.append(observation(
            f"Display adapter: {name} ({res_str})",
            STATE_OK if status.lower() == "ok" else STATE_UNKNOWN,
        ))

    # ── 2. Connected monitors via WMI Win32_DesktopMonitor ────────────────
    monitor_result = powershell_json(
        "Get-CimInstance Win32_DesktopMonitor "
        "| Select-Object Name,ScreenWidth,ScreenHeight,Availability,DeviceID "
        "| ConvertTo-Json -Compress"
    )
    monitors = monitor_result.get("records", [])

    # WMI Win32_DesktopMonitor is often sparse — also try Get-PnpDevice
    pnp_monitor_result = powershell_json(
        "Get-PnpDevice -Class Monitor -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -eq 'OK' } "
        "| Select-Object FriendlyName,Status,InstanceId "
        "| ConvertTo-Json -Compress"
    )
    pnp_monitors = pnp_monitor_result.get("records", [])

    monitor_summaries = []
    for mon in monitors:
        name = as_text(pick(mon, "Name")) or "Monitor"
        width = as_int(pick(mon, "ScreenWidth"))
        height = as_int(pick(mon, "ScreenHeight"))
        avail = as_int(pick(mon, "Availability"))
        res_str = f"{width}×{height}" if width and height else "unknown"
        # Availability 3 = Running/Full power
        active = avail == 3 if avail is not None else None
        monitor_summaries.append({
            "name": name,
            "resolution": res_str,
            "active": active,
        })

    for mon in pnp_monitors:
        name = as_text(pick(mon, "FriendlyName")) or "Monitor"
        # Avoid duplicating entries that appeared in WMI list
        if not any(m["name"] == name for m in monitor_summaries):
            monitor_summaries.append({
                "name": name,
                "resolution": "unknown",
                "active": True,  # PnP status is 'OK'
            })

    active_count = sum(1 for m in monitor_summaries if m.get("active") is not False)
    total_count = len(monitor_summaries) if monitor_summaries else len(pnp_monitors)

    if total_count == 0:
        # Fallback: count adapters as a proxy
        total_count = len(adapters)
        obs.append(observation(
            "Connected monitor count: could not be determined (WMI returned no monitor records)",
            STATE_UNKNOWN,
        ))
    else:
        obs.append(observation(
            f"{total_count} display(s) detected",
            STATE_OK,
        ))

    for mon in monitor_summaries:
        active_label = "active" if mon.get("active") else ("inactive" if mon.get("active") is False else "unknown state")
        obs.append(observation(
            f"{mon['name']} — {mon['resolution']} — {active_label}",
            STATE_OK if mon.get("active") else STATE_UNKNOWN,
        ))

    # ── 3. Overall status ─────────────────────────────────────────────────
    if not monitor_summaries and not pnp_monitors:
        overall = STATUS_UNKNOWN
        reason = (
            f"{len(adapters)} display adapter(s) detected but no monitor records "
            "could be read; monitor connection state is unknown"
        )
    else:
        overall = STATUS_OK
        reason = (
            f"{total_count} display(s) detected, "
            f"{active_count} active via Windows"
        )

    return area_result(
        _TOOL,
        _TITLE,
        overall,
        reason,
        obs,
        display_adapter_count=len(adapters),
        adapters=adapter_summaries,
        monitor_count=total_count,
        monitors=monitor_summaries,
    )

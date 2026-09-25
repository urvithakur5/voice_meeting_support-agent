"""Deterministic system performance diagnostic for Windows.

Collects CPU usage, memory usage, disk free space, and uptime.
Returns structured measurements — does NOT diagnose a root cause.
High CPU is evidence, not automatic proof of a cause.
All values come from real Windows queries via PowerShell / WMI.
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
    as_float,
    as_int,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_performance"
_TITLE = "System performance diagnostic"

# Thresholds — these drive the status flags only, never root-cause claims.
_CPU_WARN = 80      # % — above this is "elevated"
_CPU_CRIT = 95      # % — above this is "critical"
_MEM_WARN = 80
_MEM_CRIT = 95
_DISK_WARN = 20     # % free below this is a warning
_DISK_CRIT = 5      # % free below this is critical


def _threshold_state(value: float, warn: float, crit: float, high_is_bad: bool = True) -> str:
    """Map a metric value to a UI state using the supplied thresholds."""
    if high_is_bad:
        if value >= crit:
            return STATE_FAILED
        if value >= warn:
            return STATE_WARNING
        return STATE_OK
    else:
        # Low is bad (e.g. disk free percent)
        if value <= crit:
            return STATE_FAILED
        if value <= warn:
            return STATE_WARNING
        return STATE_OK


def check_performance() -> dict[str, Any]:
    """Return actual CPU, memory, disk, and uptime measurements.

    Values come from real Windows performance counters and WMI.
    No root-cause conclusions are drawn from a single metric.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    obs: list[dict] = []
    statuses: list[str] = []

    # ── 1. CPU usage ──────────────────────────────────────────────────────
    cpu_result = powershell_json(
        "[PSCustomObject]@{ cpu_percent = "
        "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average "
        "} | ConvertTo-Json -Compress"
    )
    cpu_raw = pick(cpu_result.get("raw") or {}, "cpu_percent")
    cpu_percent = as_float(cpu_raw)

    if cpu_percent is not None:
        cpu_state = _threshold_state(cpu_percent, _CPU_WARN, _CPU_CRIT)
        obs.append(observation(f"CPU usage: {cpu_percent:.1f}%", cpu_state))
        if cpu_percent >= _CPU_CRIT:
            statuses.append(STATUS_FAILED)
        elif cpu_percent >= _CPU_WARN:
            statuses.append(STATUS_WARNING)
        else:
            statuses.append(STATUS_OK)
    else:
        obs.append(observation("CPU usage: could not be read", STATE_UNKNOWN))
        statuses.append(STATUS_UNKNOWN)

    # ── 2. Memory usage ───────────────────────────────────────────────────
    mem_result = powershell_json(
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "[PSCustomObject]@{ "
        "  total_mb = [math]::Round($os.TotalVisibleMemorySize / 1024, 1); "
        "  free_mb  = [math]::Round($os.FreePhysicalMemory    / 1024, 1) "
        "} | ConvertTo-Json -Compress"
    )
    mem_raw = mem_result.get("raw") or {}
    total_mb = as_float(pick(mem_raw, "total_mb"))
    free_mb  = as_float(pick(mem_raw, "free_mb"))

    if total_mb and total_mb > 0 and free_mb is not None:
        used_mb = total_mb - free_mb
        mem_percent = round((used_mb / total_mb) * 100, 1)
        mem_state = _threshold_state(mem_percent, _MEM_WARN, _MEM_CRIT)
        obs.append(observation(
            f"Memory usage: {mem_percent:.1f}% "
            f"({used_mb:.0f} MB used / {total_mb:.0f} MB total)",
            mem_state,
        ))
        if mem_percent >= _MEM_CRIT:
            statuses.append(STATUS_FAILED)
        elif mem_percent >= _MEM_WARN:
            statuses.append(STATUS_WARNING)
        else:
            statuses.append(STATUS_OK)
    else:
        mem_percent = None
        free_mb = None
        obs.append(observation("Memory usage: could not be read", STATE_UNKNOWN))
        statuses.append(STATUS_UNKNOWN)

    # ── 3. Disk free space (C: drive) ─────────────────────────────────────
    disk_result = powershell_json(
        "$d = Get-PSDrive C; "
        "[PSCustomObject]@{ "
        "  free_gb = [math]::Round($d.Free  / 1GB, 2); "
        "  used_gb = [math]::Round($d.Used  / 1GB, 2) "
        "} | ConvertTo-Json -Compress"
    )
    disk_raw = disk_result.get("raw") or {}
    free_gb  = as_float(pick(disk_raw, "free_gb"))
    used_gb  = as_float(pick(disk_raw, "used_gb"))

    if free_gb is not None and used_gb is not None:
        total_gb = free_gb + used_gb
        disk_free_pct = round((free_gb / total_gb) * 100, 1) if total_gb > 0 else 0.0
        disk_state = _threshold_state(disk_free_pct, _DISK_WARN, _DISK_CRIT, high_is_bad=False)
        obs.append(observation(
            f"Disk C: {disk_free_pct:.1f}% free "
            f"({free_gb:.1f} GB free / {total_gb:.1f} GB total)",
            disk_state,
        ))
        if disk_free_pct <= _DISK_CRIT:
            statuses.append(STATUS_FAILED)
        elif disk_free_pct <= _DISK_WARN:
            statuses.append(STATUS_WARNING)
        else:
            statuses.append(STATUS_OK)
    else:
        disk_free_pct = None
        obs.append(observation("Disk usage: could not be read", STATE_UNKNOWN))
        statuses.append(STATUS_UNKNOWN)

    # ── 4. System uptime ──────────────────────────────────────────────────
    uptime_result = powershell_json(
        "$uptime = (Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime; "
        "[PSCustomObject]@{ "
        "  days    = $uptime.Days; "
        "  hours   = $uptime.Hours; "
        "  minutes = $uptime.Minutes "
        "} | ConvertTo-Json -Compress"
    )
    uptime_raw = uptime_result.get("raw") or {}
    uptime_days    = as_int(pick(uptime_raw, "days"))
    uptime_hours   = as_int(pick(uptime_raw, "hours"))
    uptime_minutes = as_int(pick(uptime_raw, "minutes"))

    uptime_str: str
    if uptime_days is not None:
        uptime_str = f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
        obs.append(observation(f"System uptime: {uptime_str}", STATE_OK))
    else:
        uptime_str = "unknown"
        obs.append(observation("System uptime: could not be read", STATE_UNKNOWN))

    # ── 5. Overall status ─────────────────────────────────────────────────
    overall = worst_status(*statuses) if statuses else STATUS_UNKNOWN

    parts = []
    if cpu_percent is not None:
        parts.append(f"CPU {cpu_percent:.1f}%")
    if mem_percent is not None:
        parts.append(f"memory {mem_percent:.1f}%")
    if disk_free_pct is not None:
        parts.append(f"disk {disk_free_pct:.1f}% free")
    reason = ", ".join(parts) if parts else "Performance metrics could not be fully read"

    result: dict[str, Any] = {"uptime": uptime_str}
    if cpu_percent is not None:
        result["cpu_percent"] = round(cpu_percent, 1)
    if mem_percent is not None:
        result["memory_percent"] = round(mem_percent, 1)
    if free_mb is not None:
        result["memory_free_mb"] = round(free_mb, 1)
    if disk_free_pct is not None:
        result["disk_free_percent"] = round(disk_free_pct, 1)

    return area_result(_TOOL, _TITLE, overall, reason, obs, **result)

"""Deterministic browser diagnostic for Windows.

Inspects only safe, observable state:
  - Which supported browsers have a running process.
  - Browser executable path / version where available.
  - Whether the browser process is present (not a deep health check).
  - Optional network reachability test for a target URL hostname.

Does NOT read:
  - Browsing history
  - Cookies
  - Saved passwords or credential stores
  - Authentication tokens
  - Private page contents
"""

from __future__ import annotations

import platform
import subprocess
from typing import Any

from ._common import (
    STATUS_OK,
    STATUS_WARNING,
    STATUS_FAILED,
    STATUS_UNKNOWN,
    area_result,
    observation,
    unknown_result,
    tcp_probe,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_FAILED,
    STATE_UNKNOWN,
)
from .win_shell import is_windows, powershell_json, run_fixed


_TOOL = "check_browser_state"
_TITLE = "Browser diagnostic"

# Process names for supported browsers (exe name without extension).
KNOWN_BROWSERS: list[tuple[str, str]] = [
    ("chrome", "Google Chrome"),
    ("msedge", "Microsoft Edge"),
    ("firefox", "Mozilla Firefox"),
    ("brave", "Brave"),
    ("opera", "Opera"),
    ("iexplore", "Internet Explorer"),
]


def _running_browsers() -> list[dict[str, Any]]:
    """Return observed browser processes from Windows tasklist."""
    if not is_windows():
        return []
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        running_exes = set()
        for line in result.stdout.splitlines():
            parts = line.strip('"').split('","')
            if parts:
                running_exes.add(parts[0].lower().replace(".exe", ""))

        found = []
        for exe, friendly_name in KNOWN_BROWSERS:
            if exe in running_exes:
                found.append({"exe": exe, "name": friendly_name})
        return found
    except Exception:
        return []


def _browser_version(exe_name: str) -> str:
    """Read the file version of a browser executable where available."""
    if not is_windows():
        return "unknown"
    script = (
        f"$path = (Get-Command {exe_name} -ErrorAction SilentlyContinue).Source; "
        "if ($path) { (Get-Item $path).VersionInfo.ProductVersion } else { '' }"
    )
    result = powershell_json(
        f"$path = (Get-Command {exe_name} -ErrorAction SilentlyContinue).Source; "
        "if ($path) { "
        "  [PSCustomObject]@{ version = (Get-Item $path).VersionInfo.ProductVersion } "
        "} else { [PSCustomObject]@{ version = '' } } "
        "| ConvertTo-Json -Compress"
    )
    version = as_text(pick(result.get("raw") or {}, "version"))
    return version or "unknown"


def check_browser_state(target_host: str = "") -> dict[str, Any]:
    """Return observed browser state.

    Args:
        target_host: Optional hostname to probe for network reachability
                     (e.g. ``"intranet.company.com"``).  Pass an empty string
                     to skip the network probe.  Port 443 is used.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    obs: list[dict] = []

    # ── 1. Detect running browsers ────────────────────────────────────────
    running = _running_browsers()

    if running:
        names = ", ".join(b["name"] for b in running)
        obs.append(observation(f"Browser(s) running: {names}", STATE_OK))
    else:
        obs.append(observation("No supported browser process is running", STATE_WARNING))

    # ── 2. Try to read version for the first running browser ──────────────
    version = "unknown"
    primary_browser = running[0]["name"] if running else "unknown"
    if running:
        version = _browser_version(running[0]["exe"])
        if version != "unknown":
            obs.append(observation(f"Version: {version}", STATE_OK))

    # ── 3. Optional network reachability probe ────────────────────────────
    network_reachable: bool | None = None
    probe_host = target_host.strip().lstrip("https://").lstrip("http://").split("/")[0] if target_host else ""

    if probe_host:
        probe = tcp_probe(probe_host, 443, timeout_seconds=3.0)
        network_reachable = probe.get("reachable", False)
        latency = probe.get("latency_ms")
        obs.append(observation(
            f"Network reachability to {probe_host}: "
            + ("reachable" if network_reachable else "not reachable")
            + (f" ({latency}ms)" if latency else ""),
            STATE_OK if network_reachable else STATE_FAILED,
        ))

    # ── 4. Overall status ─────────────────────────────────────────────────
    if running and (network_reachable is None or network_reachable):
        overall = STATUS_OK
        reason = f"{primary_browser} is running"
        if probe_host and network_reachable:
            reason += f" and {probe_host} is reachable"
    elif running and network_reachable is False:
        overall = STATUS_WARNING
        reason = f"{primary_browser} is running but {probe_host} could not be reached"
    elif not running:
        overall = STATUS_WARNING
        reason = "No supported browser process is currently running"
    else:
        overall = STATUS_UNKNOWN
        reason = "Browser state could not be fully determined"

    result: dict[str, Any] = {
        "running_browsers": running,
        "primary_browser": primary_browser,
        "version": version,
    }
    if probe_host:
        result["probe_host"] = probe_host
        result["network_reachable"] = network_reachable if network_reachable is not None else "unknown"

    return area_result(_TOOL, _TITLE, overall, reason, obs, **result)

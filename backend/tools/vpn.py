"""Deterministic VPN / secure-connectivity diagnostic for Windows.

Reports only observable adapter state.  Does NOT claim a specific
corporate VPN is healthy merely because an interface exists.
Does NOT extract credentials, private keys, or VPN configuration.
Unknown is returned whenever the exact condition cannot be verified.
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
    worst_status,
    tcp_probe,
    as_text,
    pick,
    STATE_OK,
    STATE_WARNING,
    STATE_UNKNOWN,
    STATE_FAILED,
)
from .win_shell import is_windows, powershell_json, powershell_script


_TOOL = "check_vpn"
_TITLE = "VPN / secure connectivity diagnostic"

# Adapter description keywords that suggest a VPN tunnel interface.
_VPN_KEYWORDS = (
    "vpn",
    "tunnel",
    "tap",
    "tun",
    "wireguard",
    "openconnect",
    "cisco",
    "pulse",
    "globalprotect",
    "fortinet",
    "checkpoint",
    "zscaler",
    "anyconnect",
    "nordvpn",
    "expressvpn",
    "protonvpn",
)


def _looks_like_vpn(description: str) -> bool:
    lower = description.lower()
    return any(kw in lower for kw in _VPN_KEYWORDS)


def check_vpn() -> dict[str, Any]:
    """Return observed VPN adapter and connectivity state.

    Detects whether a VPN-like network interface is present and up.
    Does NOT verify that VPN authentication succeeded — that cannot
    be determined from interface state alone.
    Credentials and VPN configuration are never read or returned.
    """
    if not is_windows():
        return unknown_result(
            _TOOL,
            _TITLE,
            "Windows-only diagnostic unavailable on this platform",
        )

    # ── 1. Enumerate network adapters ─────────────────────────────────────
    adapter_result = powershell_json(
        "Get-NetAdapter | Select-Object Name,Status,InterfaceDescription "
        "| ConvertTo-Json -Compress"
    )

    adapters = adapter_result.get("records", [])
    obs: list[dict] = []

    if not adapters:
        return unknown_result(
            _TOOL,
            _TITLE,
            "Network adapter list could not be retrieved",
            obs,
            vpn_detected=False,
        )

    vpn_adapters = [
        a for a in adapters
        if _looks_like_vpn(as_text(pick(a, "InterfaceDescription")) or "")
        or _looks_like_vpn(as_text(pick(a, "Name")) or "")
    ]

    if not vpn_adapters:
        obs.append(observation("VPN interface", STATE_UNKNOWN))
        return area_result(
            _TOOL,
            _TITLE,
            STATUS_UNKNOWN,
            "No VPN-like network adapter was detected; VPN may be disconnected or use an unrecognised driver",
            obs,
            vpn_detected=False,
            connection_name="unknown",
        )

    # Use the first matching adapter as the representative.
    vpn = vpn_adapters[0]
    vpn_name = as_text(pick(vpn, "Name")) or "unknown"
    vpn_desc = as_text(pick(vpn, "InterfaceDescription")) or "unknown"
    vpn_status = (as_text(pick(vpn, "Status")) or "unknown").lower()
    adapter_up = vpn_status == "up"

    obs.append(observation(
        f"VPN adapter detected: {vpn_name}",
        STATE_OK if adapter_up else STATE_WARNING,
    ))
    obs.append(observation(
        f"Adapter status: {vpn_status}",
        STATE_OK if adapter_up else STATE_WARNING,
    ))

    # ── 2. Basic internet reachability while VPN is active ────────────────
    probe = tcp_probe("8.8.8.8", 53, timeout_seconds=3.0)
    internet_ok = probe.get("reachable", False)
    latency_ms = probe.get("latency_ms")

    obs.append(observation(
        "Internet reachable via active adapters" if internet_ok
        else "Internet not reachable (may be expected when VPN routes all traffic)",
        STATE_OK if internet_ok else STATE_WARNING,
    ))

    # ── 3. Determine overall status ───────────────────────────────────────
    # We know the adapter exists and its up/down state.
    # We deliberately do NOT claim "VPN is authenticated" — that is unknown.
    if adapter_up:
        overall = STATUS_OK
        reason = (
            f"VPN adapter '{vpn_name}' ({vpn_desc}) is up. "
            "Authentication state cannot be confirmed from adapter presence alone."
        )
    else:
        overall = STATUS_WARNING
        reason = (
            f"VPN adapter '{vpn_name}' ({vpn_desc}) was detected "
            f"but its status is '{vpn_status}'."
        )

    result: dict[str, Any] = {
        "vpn_detected": True,
        "connection_name": vpn_name,
        "adapter_description": vpn_desc,
        "adapter_status": vpn_status,
        "internet": internet_ok,
    }
    if latency_ms is not None:
        result["latency_ms"] = latency_ms

    return area_result(_TOOL, _TITLE, overall, reason, obs, **result)

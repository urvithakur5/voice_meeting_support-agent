"""Shared result helpers for deterministic Windows diagnostics.

Every diagnostic in this package reports only what was actually observed.
When a property cannot be read reliably the result carries ``status``
``"unknown"`` plus a truthful ``reason``; it is never reported as a failure
or a success.
"""

from __future__ import annotations

import socket
import time
from typing import Any, Iterable

# Overall status vocabulary used by every area diagnostic.
STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"

VALID_STATUSES = (STATUS_OK, STATUS_WARNING, STATUS_FAILED, STATUS_UNKNOWN)

# Per-observation states rendered as ✓ / ⚠ / ✕ / ○ in the UI.
STATE_OK = "ok"
STATE_WARNING = "warning"
STATE_FAILED = "failed"
STATE_UNKNOWN = "unknown"

# Ranking used when rolling several observations into one overall status.
# A definite failure always wins; a definite warning beats incomplete
# evidence; incomplete evidence beats a clean result.
_STATUS_RANK = {
    STATUS_OK: 0,
    STATUS_UNKNOWN: 1,
    STATUS_WARNING: 2,
    STATUS_FAILED: 3,
}

CONNECTIVITY_HOST = "8.8.8.8"
CONNECTIVITY_PORT = 53
DEFAULT_COMMAND_TIMEOUT = 15.0

# Repeated UI wording kept in one place so every tool reads the same way.
UNKNOWN_REASON = "The value could not be reliably observed"


def unknown_status(reason: str = UNKNOWN_REASON) -> str:
    return STATUS_UNKNOWN


def worst_status(*statuses: str) -> str:
    """Return the most significant status from the supplied values."""
    relevant = [status for status in statuses if status in _STATUS_RANK]
    if not relevant:
        return STATUS_UNKNOWN
    return max(relevant, key=lambda status: _STATUS_RANK[status])


def observation(label: str, state: str) -> dict[str, str]:
    """Describe one observed fact so the UI can render evidence lines."""
    return {"label": label, "state": state if state in _STATUS_RANK else STATE_UNKNOWN}


def observed(observations: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return list(observations)


def area_result(
    tool: str,
    title: str,
    status: str,
    reason: str,
    observations: Iterable[dict[str, str]] | None = None,
    **facts: Any,
) -> dict[str, Any]:
    """Build the structured result shared by every area diagnostic."""
    return {
        "tool": tool,
        "title": title,
        "status": status if status in VALID_STATUSES else STATUS_UNKNOWN,
        "reason": reason,
        "details": reason,
        "observations": observed(observations or []),
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **facts,
    }


def unknown_result(
    tool: str,
    title: str,
    reason: str,
    observations: Iterable[dict[str, str]] | None = None,
    **facts: Any,
) -> dict[str, Any]:
    """Return an explicit unknown result with the reason that blocked it."""
    return area_result(tool, title, STATUS_UNKNOWN, reason, observations, **facts)


def as_int(value: Any) -> int | None:
    """Convert an observed value to int, or None when it is not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip().replace("%", "")
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace("%", ""))
        except ValueError:
            return None
    return None


def as_text(value: Any) -> str | None:
    """Return a trimmed non-empty string, or None when nothing was observed."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def pick(mapping: dict[str, Any], *keys: str) -> Any:
    """Return the first key that holds a non-empty value."""
    for key in keys:
        if key in mapping:
            found = mapping.get(key)
            if found is not None and str(found).strip() != "":
                return found
    return None


def tcp_probe(host: str, port: int = CONNECTIVITY_PORT, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Attempt a TCP connection and report the observed outcome."""
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {"reachable": True, "latency_ms": latency_ms}
    except socket.timeout:
        return {
            "reachable": False,
            "reason": "The connection attempt timed out",
        }
    except OSError as error:
        return {
            "reachable": False,
            "reason": "The connection attempt failed",
            "error_code": type(error).__name__,
        }


def ping_host(host: str = CONNECTIVITY_HOST, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Measure reachability and latency to a host using a TCP connect."""
    result = tcp_probe(host, CONNECTIVITY_PORT, timeout_seconds)
    return {"host": host, **result}

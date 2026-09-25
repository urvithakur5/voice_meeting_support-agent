"""Fixed-command execution helpers.

Only the module-level commands defined in this package are ever executed.
No tool accepts a command, script, or flag from the caller or from the AI:
the arguments come from constant tuples, and free-text inputs are never
interpolated into a command. ``shell`` is always disabled.
"""

from __future__ import annotations

import json
import platform
import subprocess
from typing import Any, Sequence

POWERSHELL_EXECUTABLE = "powershell.exe"
POWERSHELL_FLAGS = (
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
)

WINDOWS_ONLY_REASON = "This diagnostic requires Windows and could not run on this platform"


def is_windows() -> bool:
    return platform.system() == "Windows"


def run_fixed(argv: Sequence[str], timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Run a fixed argument vector and report the observed outcome."""
    if not argv:
        return {"ok": False, "error": "No command was provided", "stdout": "", "stderr": ""}

    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"The command timed out after {timeout_seconds:g}s",
            "stdout": "",
            "stderr": "",
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "error": f"{argv[0]} is not available on this system",
            "stdout": "",
            "stderr": "",
        }
    except OSError as error:
        return {
            "ok": False,
            "error": f"The command could not be executed ({type(error).__name__})",
            "stdout": "",
            "stderr": "",
        }

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "error": None if completed.returncode == 0 else f"The command exited with code {completed.returncode}",
    }


def powershell_script(script: str, timeout_seconds: float = 20.0) -> dict[str, Any]:
    """Run a module-defined PowerShell script with the standard flags."""
    return run_fixed(
        [POWERSHELL_EXECUTABLE, *POWERSHELL_FLAGS, script],
        timeout_seconds,
    )


def normalize_json_list(data: Any) -> list[Any]:
    """Normalize PowerShell ConvertTo-Json output into a list of records."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def powershell_json(script: str, timeout_seconds: float = 20.0) -> dict[str, Any]:
    """Run a PowerShell script that emits compact JSON and parse the result.

    The returned mapping always contains ``records`` (a list), ``raw`` (the
    decoded payload), ``error`` (a truthful reason or ``None``) and ``ok``.
    """
    outcome = powershell_script(script, timeout_seconds)
    stdout = (outcome.get("stdout") or "").strip()

    if not stdout:
        reason = outcome.get("error") or "The query returned no data"
        return {"ok": False, "records": [], "raw": None, "error": reason}

    try:
        decoded = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "records": [],
            "raw": None,
            "error": "The query result could not be parsed",
        }

    return {
        "ok": True,
        "records": normalize_json_list(decoded),
        "raw": decoded,
        "error": None,
    }


def parse_key_value_output(output: str, separator: str = ":") -> dict[str, str]:
    """Parse localized Windows text output into lower-cased key/value pairs."""
    parsed: dict[str, str] = {}
    for line in (output or "").splitlines():
        if separator not in line:
            continue
        key, _, value = line.partition(separator)
        cleaned_key = key.strip().lower()
        cleaned_value = value.strip()
        if cleaned_key and cleaned_value:
            parsed[cleaned_key] = cleaned_value
    return parsed

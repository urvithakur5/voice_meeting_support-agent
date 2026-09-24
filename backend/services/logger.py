from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"


def log_event(
    event: str,
    details: str,
    input_data: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details
    }
    if input_data is not None:
        entry["input"] = input_data
    if result is not None:
        entry["result"] = result
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")
    return entry
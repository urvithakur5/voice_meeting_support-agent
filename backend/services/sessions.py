from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock


_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.json"
_sessions_lock = Lock()


def _load_sessions() -> dict[str, dict]:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_sessions: dict[str, dict] = _load_sessions()


def _save_sessions() -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _DATA_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(_sessions, indent=2), encoding="utf-8")
    temporary_path.replace(_DATA_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_session(session_id: str, payload: dict) -> dict:
    if not session_id:
        raise ValueError("session_id is required")

    with _sessions_lock:
        existing = _sessions.get(session_id, {})
        created_at = existing.get("created_at") or payload.get("created_at") or _now()
        session = {
            **existing,
            **payload,
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": _now(),
        }
        _sessions[session_id] = session
        _save_sessions()
        return session


def list_sessions() -> list[dict]:
    with _sessions_lock:
        return list(reversed(list(_sessions.values())))


def get_session(session_id: str) -> dict | None:
    with _sessions_lock:
        return _sessions.get(session_id)

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from uuid import uuid4


_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "incidents.json"
_incidents_lock = Lock()


def _load_incidents() -> dict[str, dict]:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_incidents: dict[str, dict] = _load_incidents()


def _save_incidents() -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _DATA_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(_incidents, indent=2), encoding="utf-8")
    temporary_path.replace(_DATA_PATH)


def create_incident(payload: dict) -> dict:
    incident_id = f"INC-{uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    employee = payload.get("employee") or {}
    issue = payload.get("issue") or {}
    incident = {
        "incident_id": incident_id,
        "employee": employee,
        "employee_id": payload.get("employee_id", employee.get("id", "DEMO-EMPLOYEE")),
        "employee_name": payload.get("employee_name", employee.get("name", "Demo Employee")),
        "status": payload.get("status", "needs_technician"),
        "issue": issue,
        "issue_type": payload.get("issue_type", issue.get("type", "meeting_support")),
        "user_report": payload.get("user_report") or payload.get("user_statement") or payload.get("symptom", ""),
        "questions_answered": payload.get("questions_answered", []),
        "diagnostics": payload.get("diagnostics") or payload.get("diagnostics_run", []),
        "knowledge_used": payload.get("knowledge_used", []),
        "actions_attempted": payload.get("actions_attempted", []),
        "approval_history": payload.get("approval_history", []),
        "verification": payload.get("verification", {}),
        "final_outcome": payload.get("final_outcome", "needs_technician"),
        "likely_area": payload.get("likely_area", "unknown"),
        "recommended_team": payload.get(
            "recommended_team", payload.get("routing_team", "IT Helpdesk")
        ),
        "created_at": created_at,
        "updated_at": created_at,
    }

    with _incidents_lock:
        _incidents[incident_id] = incident
        _save_incidents()

    return incident


def list_incidents() -> list[dict]:
    with _incidents_lock:
        return list(reversed(list(_incidents.values())))


def get_incident(incident_id: str) -> dict | None:
    with _incidents_lock:
        return _incidents.get(incident_id)


def update_incident_status(incident_id: str, status: str) -> dict | None:
    with _incidents_lock:
        incident = _incidents.get(incident_id)
        if incident is None:
            return None
        incident["status"] = status
        incident["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_incidents()
        return incident
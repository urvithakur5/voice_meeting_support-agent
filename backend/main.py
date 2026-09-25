from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.scenario import (
    apply_fix,
    get_tool_result,
    set_scenario,
    get_current_scenario
)
from services.scenario_library import all_scenarios, get_scenario as get_library_scenario
from services.logger import log_event
from services.incidents import (
    create_incident,
    get_incident,
    list_incidents,
    update_incident_status,
)
from services.sessions import (
    get_session,
    list_sessions,
    upsert_session,
)
from tools.diagnostics import (
    check_app_state,
    check_application_state,
    check_camera,
    check_connectivity,
    check_microphone,
    check_speaker,
    run_test,
)
from tools.wifi import check_wifi
from tools.vpn import check_vpn
from tools.bluetooth_audio import check_bluetooth_audio
from tools.display import check_display
from tools.dock import check_dock
from tools.browser import check_browser_state
from tools.performance import check_performance


# Create the FastAPI application
app = FastAPI(title="Voice Meeting Support Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# Request model for selecting a test scenario
class ScenarioRequest(BaseModel):
    id: str


class ActionRequest(BaseModel):
    session_id: str
    action_name: str
    user_approved: bool


class TicketRequest(BaseModel):
    symptom: str
    diagnostics_run: list[dict] = Field(default_factory=list)
    actions_attempted: list[dict] = Field(default_factory=list)
    routing_team: str = "IT Helpdesk"
    employee_id: str = "DEMO-EMPLOYEE"
    employee_name: str = "Demo Employee"
    issue_type: str = "meeting_support"
    questions_answered: list[dict] = Field(default_factory=list)
    knowledge_used: list[dict] = Field(default_factory=list)
    approval_history: list[dict] = Field(default_factory=list)
    verification: dict = Field(default_factory=dict)
    likely_area: str = "unknown"
    final_outcome: str = "needs_technician"


class IncidentStatusRequest(BaseModel):
    status: str


class IncidentRequest(BaseModel):
    employee: dict = Field(default_factory=dict)
    issue: dict = Field(default_factory=dict)
    user_statement: str
    diagnostics: list[dict] = Field(default_factory=list)
    questions_answered: list[dict] = Field(default_factory=list)
    knowledge_used: list[dict] = Field(default_factory=list)
    actions_attempted: list[dict] = Field(default_factory=list)
    verification: dict = Field(default_factory=dict)
    likely_area: str = "unknown"
    recommended_team: str = "IT Helpdesk"
    status: str = "needs_human"


class IncidentPatchRequest(BaseModel):
    status: str


class SessionRequest(BaseModel):
    session_id: str | None = None
    title: str = ""
    status: str = "idle"
    employee_name: str = "Demo Employee"
    transcript: list[dict] = Field(default_factory=list)
    diagnostics: list[dict] = Field(default_factory=list)
    questions_answered: list[dict] = Field(default_factory=list)
    knowledge_used: list[dict] = Field(default_factory=list)
    actions_attempted: list[dict] = Field(default_factory=list)
    verification: dict = Field(default_factory=dict)
    finding: str = ""
    issue: dict = Field(default_factory=dict)
    incident_id: str | None = None
    ui_state: dict = Field(default_factory=dict)


@app.get("/api/scenario-library")
def scenario_library():
    """Return all structured scenarios for frontend/demo use."""
    return all_scenarios()


@app.get("/api/scenario-library/{scenario_id}")
def scenario_library_item(scenario_id: str):
    scenario = get_library_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@app.get("/")
def home():
    # Return a message to confirm that the backend is running
    return {
        "message": "Voice Meeting Support Backend is running"
    }


@app.post("/scenario")
def change_scenario(request: ScenarioRequest):
    # Switch the backend to the requested testing scenario
    if not set_scenario(request.id):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario: {request.id}"
        )

    return {
        "scenario_id": get_current_scenario(),
        "message": "Scenario selected successfully."
    }


def _diagnostic(tool: str, device: str | None = None):
    result = get_tool_result(tool)
    if device is not None:
        result = {**result, "device": device}

    return {
        "status": result.get("status", "error"),
        "error_code": result.get("error_code", "tool_error"),
        "message": result.get("message", "Diagnostic failed."),
    }


@app.get("/api/check_mic")
def microphone_diagnostic(device: str = Query(default="default")):
    return _diagnostic("mic", device)


@app.get("/api/check_camera")
def camera_diagnostic(device: str = Query(default="default")):
    return _diagnostic("camera", device)


@app.get("/api/check_speaker")
def speaker_diagnostic(device: str = Query(default="default")):
    return _diagnostic("speaker", device)


@app.get("/api/check_connectivity")
def connectivity_diagnostic():
    return _diagnostic("connectivity")


def _real_diagnostic(tool_name: str, input_data: dict, diagnostic):
    result = diagnostic(**input_data)
    log_event("tool_called", tool_name, input_data=input_data, result=result)
    return result


@app.get("/api/diagnostics/check_microphone")
def real_microphone_diagnostic(device: str = Query(default="default")):
    return _real_diagnostic("check_microphone", {"device": device}, check_microphone)


@app.get("/api/diagnostics/check_camera")
def real_camera_diagnostic(device: str = Query(default="default")):
    return _real_diagnostic("check_camera", {"device": device}, check_camera)


@app.get("/api/diagnostics/check_speaker")
def real_speaker_diagnostic(device: str = Query(default="default")):
    return _real_diagnostic("check_speaker", {"device": device}, check_speaker)


@app.get("/api/diagnostics/check_connectivity")
def real_connectivity_diagnostic(
    host: str = Query(default="8.8.8.8"),
    timeout_seconds: float = Query(default=2.0, gt=0, le=10),
):
    return _real_diagnostic(
        "check_connectivity",
        {"host": host, "timeout_seconds": timeout_seconds},
        check_connectivity,
    )


@app.get("/api/diagnostics/check_app_state")
def application_state_diagnostic(application: str = Query(default="Teams")):
    return _real_diagnostic("check_app_state", {"application": application}, check_app_state)


@app.get("/api/diagnostics/check_application_state")
def extended_application_state_diagnostic(application: str = Query(default="Teams")):
    return _real_diagnostic("check_application_state", {"application": application}, check_application_state)


@app.get("/api/diagnostics/check_wifi")
def wifi_diagnostic():
    return _real_diagnostic("check_wifi", {}, check_wifi)


@app.get("/api/diagnostics/check_vpn")
def vpn_diagnostic():
    return _real_diagnostic("check_vpn", {}, check_vpn)


@app.get("/api/diagnostics/check_bluetooth_audio")
def bluetooth_audio_diagnostic():
    return _real_diagnostic("check_bluetooth_audio", {}, check_bluetooth_audio)


@app.get("/api/diagnostics/check_display")
def display_diagnostic():
    return _real_diagnostic("check_display", {}, check_display)


@app.get("/api/diagnostics/check_dock")
def dock_diagnostic():
    return _real_diagnostic("check_dock", {}, check_dock)


@app.get("/api/diagnostics/check_browser_state")
def browser_state_diagnostic(target_host: str = Query(default="")):
    return _real_diagnostic("check_browser_state", {"target_host": target_host}, check_browser_state)


@app.get("/api/diagnostics/check_performance")
def performance_diagnostic():
    return _real_diagnostic("check_performance", {}, check_performance)


@app.get("/api/diagnostics/run_test")
def diagnostic_test(test_type: str = Query(...)):
    return _real_diagnostic("run_test", {"test_type": test_type}, run_test)


@app.post("/api/actions")
def execute_action(request: ActionRequest):
    if not request.user_approved:
        return {
            "status": "blocked",
            "error_code": "approval_required",
            "message": "User approval is required before this action.",
        }

    action_tools = {
        "fix_microphone_permissions": "mic",
        "unmute_microphone": "mic",
        "restart_camera": "camera",
        "restart_speaker": "speaker",
        "restart_network": "connectivity",
    }
    tool = action_tools.get(request.action_name)
    if tool is None:
        return {
            "status": "error",
            "error_code": "unsupported_action",
            "message": f"Unsupported action: {request.action_name}",
        }

    apply_fix(tool)
    return {
        "status": "working",
        "error_code": "none",
        "message": f"Action '{request.action_name}' applied for session {request.session_id}.",
    }


@app.post("/api/tickets")
def ticket_creation(request: TicketRequest):
    incident = create_incident(request.model_dump())
    return {
        "ticket_id": incident["incident_id"],
        "incident_id": incident["incident_id"],
        "symptom": incident["user_report"],
        "diagnostics": incident["diagnostics"],
        "actions": incident["actions_attempted"],
        "routing_team": incident["recommended_team"],
        "status": "open",
        "incident": incident,
    }


@app.post("/api/incidents", status_code=201)
def create_incident_endpoint(request: IncidentRequest):
    incident = create_incident(request.model_dump())
    log_event("incident_created", incident["incident_id"], result=incident)
    return incident


@app.get("/api/incidents")
def incidents_endpoint():
    return list_incidents()


@app.get("/api/incidents/{incident_id}")
def incident_endpoint(incident_id: str):
    incident = get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.patch("/api/incidents/{incident_id}")
def update_incident_endpoint(incident_id: str, request: IncidentPatchRequest):
    allowed_statuses = {"open", "investigating", "resolved", "closed", "needs_human"}
    if request.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported incident status")
    incident = update_incident_status(incident_id, request.status)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    log_event("incident_status_changed", incident_id, input_data={"status": request.status}, result=incident)
    return incident


@app.get("/api/tickets")
def incident_list():
    return {"incidents": list_incidents()}


@app.get("/api/tickets/{incident_id}")
def incident_detail(incident_id: str):
    incident = get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.patch("/api/tickets/{incident_id}/status")
def incident_status(incident_id: str, request: IncidentStatusRequest):
    incident = update_incident_status(incident_id, request.status)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/api/sessions", status_code=201)
def create_session_endpoint(request: SessionRequest):
    from uuid import uuid4

    session_id = request.session_id or str(uuid4())
    return upsert_session(session_id, request.model_dump(exclude_none=True))


@app.get("/api/sessions")
def sessions_endpoint():
    return list_sessions()


@app.get("/api/sessions/{session_id}")
def session_endpoint(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.patch("/api/sessions/{session_id}")
def update_session_endpoint(session_id: str, request: SessionRequest):
    payload = request.model_dump(exclude_unset=True)
    payload.pop("session_id", None)
    return upsert_session(session_id, payload)


@app.post("/logs")
def create_log():
    # Record a backend event in the log
    return log_event(
        event="backend_event",
        details="Backend event logged"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5673)
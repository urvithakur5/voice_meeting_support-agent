from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from services.scenario import (
    apply_fix,
    get_tool_result,
    set_scenario,
    get_current_scenario
)
from services.logger import log_event


# Create the FastAPI application
app = FastAPI(title="Voice Meeting Support Backend")


# Request model for selecting a test scenario
class ScenarioRequest(BaseModel):
    id: str


class ActionRequest(BaseModel):
    session_id: str
    action_name: str
    user_approved: bool


class TicketRequest(BaseModel):
    issue: str
    diagnostics_run: list[dict]
    actions_attempted: list[dict]
    result: str


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
    return {
        "ticket_id": f"INC-{uuid4().hex[:8].upper()}",
        "issue": request.issue,
        "diagnostics": request.diagnostics_run,
        "actions": request.actions_attempted,
        "result": request.result,
        "status": "open",
    }


@app.post("/logs")
def create_log():
    # Record a backend event in the log
    return log_event(
        event="backend_event",
        details="Backend event logged"
    )
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tools.microphone import check_mic
from tools.camera import check_camera
from tools.speaker import check_speaker
from tools.connectivity import check_connection

from actions.actions import (
    fix_microphone,
    fix_camera,
    fix_speaker,
    check_approval
)

from services.scenario import (
    set_scenario,
    get_current_scenario
)

from services.ticket import create_ticket
from services.logger import log_event


# Create the FastAPI application
app = FastAPI(title="Voice Meeting Support Backend")


# Request model for approved actions
class ActionRequest(BaseModel):
    approved: bool


# Request model for selecting a test scenario
class ScenarioRequest(BaseModel):
    id: str


# Request model for creating an IT support ticket
class TicketRequest(BaseModel):
    issue: str
    diagnostics: list[str]
    actions: list[str]
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


@app.get("/diagnostics/mic")
def microphone_diagnostic():
    # Run the microphone diagnostic
    return check_mic()


@app.get("/diagnostics/camera")
def camera_diagnostic():
    # Run the camera diagnostic
    return check_camera()


@app.get("/diagnostics/speaker")
def speaker_diagnostic():
    # Run the speaker diagnostic
    return check_speaker()


@app.get("/diagnostics/connection")
def connection_diagnostic():
    # Run the network connection diagnostic
    return check_connection()


@app.post("/approval")
def approval(approved: bool):
    # Check whether the user approved an action
    return check_approval(approved)


@app.post("/actions/microphone")
def microphone_action(request: ActionRequest):
    # Only perform the microphone action after user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    return fix_microphone()


@app.post("/actions/camera")
def camera_action(request: ActionRequest):
    # Only perform the camera action after user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    return fix_camera()


@app.post("/actions/speaker")
def speaker_action(request: ActionRequest):
    # Only perform the speaker action after user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    return fix_speaker()


@app.post("/tickets")
def ticket_creation(request: TicketRequest):
    # Create the ticket using the data received in the request
    return create_ticket(
        issue=request.issue,
        diagnostics=request.diagnostics,
        actions=request.actions,
        result=request.result
    )


@app.post("/logs")
def create_log():
    # Record a backend event in the log
    return log_event(
        event="backend_event",
        details="Backend event logged"
    )
# Import FastAPI to create the backend application
from fastapi import FastAPI

# Import BaseModel to validate request data
from pydantic import BaseModel

# Import diagnostic functions for different meeting devices
from tools.microphone import check_mic
from tools.camera import check_camera
from tools.speaker import check_speaker
from tools.connectivity import check_connectivity

# Import functions used to perform approved actions
from actions.actions import (
    fix_microphone,
    fix_camera,
    fix_speaker,
    check_approval
)

# Import functions used to verify whether the action fixed the issue
from services.verification import (
    verify_microphone,
    verify_camera,
    verify_speaker
)

# Import ticket creation and logging services
from services.ticket import create_ticket
from services.logger import log_event


# Create the FastAPI application
app = FastAPI(title="Voice Meeting Support Backend")


# Request model used for actions that require user approval
class ActionRequest(BaseModel):
    approved: bool


# Root endpoint to check whether the backend is running
@app.get("/")
def home():
    return {
        "message": "Voice Meeting Support Backend is running"
    }


# Diagnostic endpoint for checking microphone status
@app.get("/diagnostics/mic")
def microphone_diagnostic():
    return check_mic()


# Diagnostic endpoint for checking camera status
@app.get("/diagnostics/camera")
def camera_diagnostic():
    return check_camera()


# Diagnostic endpoint for checking speaker status
@app.get("/diagnostics/speaker")
def speaker_diagnostic():
    return check_speaker()


# Diagnostic endpoint for checking network/connectivity status
@app.get("/diagnostics/connectivity")
def connectivity_diagnostic():
    return check_connectivity()


# Endpoint for checking whether the user approved an action
@app.post("/approval")
def approval(approved: bool):
    return check_approval(approved)


# Endpoint for performing the microphone fix
@app.post("/actions/microphone")
def microphone_action(request: ActionRequest):

    # Do not perform the action without user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    # Perform the approved microphone action
    return fix_microphone()


# Endpoint for performing the camera fix
@app.post("/actions/camera")
def camera_action(request: ActionRequest):

    # Do not perform the action without user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    # Perform the approved camera action
    return fix_camera()


# Endpoint for performing the speaker fix
@app.post("/actions/speaker")
def speaker_action(request: ActionRequest):

    # Do not perform the action without user approval
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }

    # Perform the approved speaker action
    return fix_speaker()


# Endpoint for verifying whether the microphone is working after the fix
@app.get("/verification/microphone")
def microphone_verification():
    return verify_microphone()


# Endpoint for verifying whether the camera is working after the fix
@app.get("/verification/camera")
def camera_verification():
    return verify_camera()


# Endpoint for verifying whether the speaker is working after the fix
@app.get("/verification/speaker")
def speaker_verification():
    return verify_speaker()


# Endpoint for creating an IT helpdesk ticket
@app.post("/tickets")
def ticket_creation():

    # Store the issue, diagnostics, actions and final result
    return create_ticket(
        issue="Microphone not working",
        diagnostics=[
            "Microphone connected",
            "Microphone muted"
        ],
        actions=[
            "Unmute microphone attempted"
        ],
        result="Unresolved"
    )


# Endpoint for recording backend events
@app.post("/logs")
def create_log():

    # Record the action and its details
    return log_event(
        event="microphone_action",
        details="Microphone unmute action executed"
    )
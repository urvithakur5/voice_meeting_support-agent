from fastapi import FastAPI
from pydantic import BaseModel

from tools.microphone import check_mic
from tools.camera import check_camera
from tools.speaker import check_speaker
from tools.connectivity import check_connectivity

from actions.actions import (
    fix_microphone,
    fix_camera,
    fix_speaker,
    check_approval
)

from services.verification import (
    verify_microphone,
    verify_camera,
    verify_speaker
)

from services.ticket import create_ticket
from services.logger import log_event


app = FastAPI(title="Voice Meeting Support Backend")


class ActionRequest(BaseModel):
    approved: bool


@app.get("/")
def home():
    return {
        "message": "Voice Meeting Support Backend is running"
    }


@app.get("/diagnostics/mic")
def microphone_diagnostic():
    return check_mic()


@app.get("/diagnostics/camera")
def camera_diagnostic():
    return check_camera()


@app.get("/diagnostics/speaker")
def speaker_diagnostic():
    return check_speaker()


@app.get("/diagnostics/connectivity")
def connectivity_diagnostic():
    return check_connectivity()


@app.post("/approval")
def approval(approved: bool):
    return check_approval(approved)


@app.post("/actions/microphone")
def microphone_action(request: ActionRequest):
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }
    return fix_microphone()


@app.post("/actions/camera")
def camera_action(request: ActionRequest):
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }
    return fix_camera()


@app.post("/actions/speaker")
def speaker_action(request: ActionRequest):
    if not request.approved:
        return {
            "success": False,
            "message": "User approval is required before this action."
        }
    return fix_speaker()


@app.get("/verification/microphone")
def microphone_verification():
    return verify_microphone()


@app.get("/verification/camera")
def camera_verification():
    return verify_camera()


@app.get("/verification/speaker")
def speaker_verification():
    return verify_speaker()


@app.post("/tickets")
def ticket_creation():
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


@app.post("/logs")
def create_log():
    return log_event(
        event="microphone_action",
        details="Microphone unmute action executed"
    )

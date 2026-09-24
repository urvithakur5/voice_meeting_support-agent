# Import Flask tools:
# Flask = creates the web application
# render_template = loads HTML pages
# jsonify = sends JSON responses
# request = receives data from the frontend
from flask import Flask, render_template, jsonify, request
import requests
import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

speech_config = speechsdk.SpeechConfig(
    subscription=SPEECH_KEY,
    region=SPEECH_REGION
)

speech_config.speech_recognition_language = "en-IN"

recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config
)
# Create the Flask application
app = Flask(__name__)
BACKEND_URL = "http://127.0.0.1:5673"
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8001"))

# Predefined IT support scenarios
# Each scenario contains:
# title, description, severity, icon, and example user complaint
SCENARIOS = {
    "microphone": (
        "Microphone not working",
        "The agent is diagnosing your Microsoft Teams meeting issue.",
        "URGENT",
        "🎙️",
        "My microphone stopped working and my meeting starts in two minutes."
    ),

    "camera": (
        "Camera not working",
        "Checking camera availability and meeting permissions.",
        "HIGH",
        "📷",
        "Teams can't see my camera."
    ),

    "audio": (
        "Speaker / audio issue",
        "Checking output device and meeting audio.",
        "HIGH",
        "🔊",
        "I can join the meeting but I can't hear anyone."
    ),

    "connectivity": (
        "Meeting join / connectivity",
        "Checking connection and meeting join conditions.",
        "URGENT",
        "↗",
        "I can't join my Teams meeting."
    )
}


# Home page route
@app.route("/")
def index():

    # Open index.html and pass the scenarios to it
    return render_template(
        "index.html",
        scenarios=SCENARIOS
    )


# API endpoint for getting a selected scenario
@app.get("/api/scenario/<name>")
def get_scenario(name):
    if name not in SCENARIOS:
        return jsonify({"error": "Unknown scenario"}), 404

    title, subtitle, severity, icon, user = SCENARIOS[name]

    scenario_ids = {
        "microphone": "MIC-001",
        "camera": "CAM-001",
        "audio": "SPK-001",
        "connectivity": "CON-001"
    }

    requests.post(
        f"{BACKEND_URL}/scenario",
        json={"id": scenario_ids[name]}
    )

    backend_result = None

    if name == "microphone":
        backend_result = requests.get(
            f"{BACKEND_URL}/diagnostics/mic"
        ).json()
    elif name == "camera":
        backend_result = requests.get(
            f"{BACKEND_URL}/diagnostics/camera"
        ).json()
    elif name == "audio":
        backend_result = requests.get(
            f"{BACKEND_URL}/diagnostics/speaker"
        ).json()
    elif name == "connectivity":
        backend_result = requests.get(
            f"{BACKEND_URL}/diagnostics/connection"
        ).json()

    check = {
        "microphone": "Check microphone",
        "camera": "Check camera",
        "audio": "Check speaker",
        "connectivity": "Check connection"
    }[name]

    return jsonify({
        "title": title,
        "subtitle": subtitle,
        "severity": severity,
        "icon": icon,
        "user": user,
        "steps": [
            {
                "title": "Capture complaint",
                "detail": "Natural language issue received.",
                "state": "done"
            },
            {
                "title": check,
                "detail": f"Backend result: {backend_result.get('status', 'unknown')}",
                "state": "done"
            },
            {
                "title": "Check permissions",
                "detail": "A setting needs attention.",
                "state": "current"
            },
            {
                "title": "Verify fix",
                "detail": "Run a final test.",
                "state": "pending"
            }
        ]
    })
@app.post("/api/voice")
def voice():

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:

        user_text = result.text
        text = user_text.lower()

        if "microphone" in text or "mic" in text:

            backend_response = requests.get(
                f"{BACKEND_URL}/api/check_mic",
                params={"device": "default"}
            )

            data = backend_response.json()

            return jsonify({
                "success": True,
                "user_text": user_text,
                "message": (
                    f"Microphone status: {data.get('status')}. "
                    f"{data.get('message')}"
                )
            })

        return jsonify({
            "success": True,
            "user_text": user_text,
            "message": "I understood your request. Please give me more details."
        })

    return jsonify({
        "success": False,
        "message": "I could not understand the speech."
    })
# API endpoint called when the user approves or denies an action
@app.post("/api/action")
def action():

    data = request.get_json(silent=True) or {}

    # User denied the action
    if not data.get("approved"):
        return jsonify({
            "status": "escalated",
            "message": (
                "No changes were made. "
                "Diagnostic evidence is ready for escalation."
            )
        })

    # Get the selected scenario
    scenario = data.get("scenario", "CAM-001")

    action_endpoints = {
        "MIC-001": "/actions/microphone",
        "CAM-001": "/actions/camera",
        "SPK-001": "/actions/speaker"
    }

    endpoint = action_endpoints.get(scenario)

    if not endpoint:
        return jsonify({
            "status": "error",
            "message": "No supported action is available for this scenario."
        }), 400

    # Call the real backend action
        # Call the real backend action
    action_names = {
        "MIC-001": "fix_microphone_permissions",
        "CAM-001": "restart_camera",
        "SPK-001": "restart_speaker"
    }

    backend_response = requests.post(
        f"{BACKEND_URL}/api/actions",
        json={
            "session_id": "MS-2048",
            "action_name": action_names[scenario],
            "user_approved": True
        }
    )

    result = backend_response.json()

    if result.get("success"):

        verify_endpoints = {
            "MIC-001": "/diagnostics/mic",
            "CAM-001": "/diagnostics/camera",
            "SPK-001": "/diagnostics/speaker"
        }

        verify_endpoint = verify_endpoints.get(scenario)

        if verify_endpoint:
            verification = requests.get(
                f"{BACKEND_URL}{verify_endpoint}"
            ).json()

            if verification.get("status") == "working":
                return jsonify({
                    "status": "verified",
                    "message": (
                        "The fix has been applied and "
                        "verified successfully."
                    )
                })

            return jsonify({
                "status": "verification_failed",
                "message": (
                    "The action was applied, but the issue "
                    "is still blocked after verification."
                )
            })

        return jsonify({
            "status": "verified",
            "message": result.get(
                "message",
                "The fix has been applied successfully."
            )
        })

    return jsonify({
        "status": "error",
        "message": result.get(
            "message",
            "The backend could not apply the fix."
        )
    }), 400


# API endpoint for creating a support ticket
@app.post("/api/ticket")
def ticket():

    # Return a mock ticket ID
    return jsonify({
        "status": "created",
        "ticket_id": "MS-2048"
    })


# API endpoint for receiving text messages
@app.post("/api/message")
def message():

    # Read JSON sent by the frontend
    data = request.get_json(silent=True) or {}


    # Check whether the message is empty
    if not data.get("text", "").strip():

        return jsonify({
            "error": "Message is empty"
        }), 400


    # Send acknowledgement to the frontend
    return jsonify({
        "message": (
            "Thanks. I'll use that information "
            "to continue the diagnosis."
        )
    })


# Start the Flask server
if __name__ == "__main__":

    # debug=True automatically reloads the server
    # when code changes during development
    app.run(host="0.0.0.0", port=FRONTEND_PORT, debug=False)
# Import Flask tools:
# Flask = creates the web application
# render_template = loads HTML pages
# jsonify = sends JSON responses
# request = receives data from the frontend
from flask import Flask, render_template, jsonify, request


# Create the Flask application
app = Flask(__name__)


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

    # Check whether the requested scenario exists
    if name not in SCENARIOS:
        return jsonify({
            "error": "Unknown scenario"
        }), 404

    # Get information about the selected scenario
    title, subtitle, severity, icon, user = SCENARIOS[name]


    # Select the diagnostic check according to the issue
    check = {
        "microphone": "Check microphone",
        "camera": "Check camera",
        "audio": "Check speaker",
        "connectivity": "Check connection"
    }[name]


    # Send the scenario information back to JavaScript as JSON
    return jsonify({

        "title": title,
        "subtitle": subtitle,
        "severity": severity,
        "icon": icon,
        "user": user,

        # Diagnostic timeline
        "steps": [

            {
                "title": "Capture complaint",
                "detail": "Natural language issue received.",
                "state": "done"
            },

            {
                "title": check,
                "detail": "Diagnostic device/status check completed.",
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


# API endpoint called when the user approves or denies an action
@app.post("/api/action")
def action():

    # Get JSON data sent by the frontend
    data = request.get_json(silent=True) or {}


    # If the user approved the action
    if data.get("approved"):

        return jsonify({
            "status": "verified",
            "message": (
                "The fix has been applied and verified. "
                "Your issue is resolved."
            )
        })


    # If the user denied the action
    return jsonify({
        "status": "escalated",
        "message": (
            "No changes were made. "
            "Diagnostic evidence is ready for escalation."
        )
    })


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
    app.run(debug=True)
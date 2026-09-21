from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

SCENARIOS = {
    "microphone": ("Microphone not working", "The agent is diagnosing your Microsoft Teams meeting issue.", "URGENT", "🎙️", "My microphone stopped working and my meeting starts in two minutes."),
    "camera": ("Camera not working", "Checking camera availability and meeting permissions.", "HIGH", "📷", "Teams can't see my camera."),
    "audio": ("Speaker / audio issue", "Checking output device and meeting audio.", "HIGH", "🔊", "I can join the meeting but I can't hear anyone."),
    "connectivity": ("Meeting join / connectivity", "Checking connection and meeting join conditions.", "URGENT", "↗", "I can't join my Teams meeting.")
}

@app.route("/")
def index():
    return render_template("index.html", scenarios=SCENARIOS)

@app.get("/api/scenario/<name>")
def get_scenario(name):
    if name not in SCENARIOS:
        return jsonify({"error": "Unknown scenario"}), 404
    title, subtitle, severity, icon, user = SCENARIOS[name]
    check = {
        "microphone": "Check microphone",
        "camera": "Check camera",
        "audio": "Check speaker",
        "connectivity": "Check connection"
    }[name]
    return jsonify({
        "title": title, "subtitle": subtitle, "severity": severity,
        "icon": icon, "user": user,
        "steps": [
            {"title": "Capture complaint", "detail": "Natural language issue received.", "state": "done"},
            {"title": check, "detail": "Diagnostic device/status check completed.", "state": "done"},
            {"title": "Check permissions", "detail": "A setting needs attention.", "state": "current"},
            {"title": "Verify fix", "detail": "Run a final test.", "state": "pending"}
        ]
    })

@app.post("/api/action")
def action():
    data = request.get_json(silent=True) or {}
    if data.get("approved"):
        return jsonify({"status": "verified", "message": "The fix has been applied and verified. Your issue is resolved."})
    return jsonify({"status": "escalated", "message": "No changes were made. Diagnostic evidence is ready for escalation."})

@app.post("/api/ticket")
def ticket():
    return jsonify({"status": "created", "ticket_id": "MS-2048"})

@app.post("/api/message")
def message():
    data = request.get_json(silent=True) or {}
    if not data.get("text", "").strip():
        return jsonify({"error": "Message is empty"}), 400
    return jsonify({"message": "Thanks. I'll use that information to continue the diagnosis."})

if __name__ == "__main__":
    app.run(debug=True)

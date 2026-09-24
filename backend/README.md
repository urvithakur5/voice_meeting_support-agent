# Voice Meeting Support Backend

A FastAPI backend for a voice-first IT helpdesk agent that helps diagnose and resolve common meeting issues.

## Features

- Microphone diagnostics
- Camera diagnostics
- Speaker diagnostics
- Connectivity diagnostics
- User approval before actions
- Microphone action
- Camera action
- Speaker action
- Post-action verification
- IT helpdesk ticket generation
- Event logging

## Project Structure

voice-meeting-backend/

├── main.py
├── requirements.txt
├── README.md
├── tools/
│   ├── microphone.py
│   ├── camera.py
│   ├── speaker.py
│   └── connectivity.py
├── actions/
│   └── actions.py
└── services/
    ├── verification.py
    ├── ticket.py
    └── logger.py

## Setup

Create a virtual environment:

python -m venv venv

Activate the virtual environment on Windows PowerShell:

venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

## Run the Backend

python main.py

The backend will run at:

http://127.0.0.1:5673

## API Documentation

Open the following URL in a browser:

http://127.0.0.1:5673/docs

## API Flow

Diagnostic

↓

User Approval

↓

Approved Action

↓

Verification

↓

Resolve or Escalate

## Diagnostic Endpoints

The real machine diagnostics are separate from the legacy scenario endpoints.
They report observed values or `status: "unknown"` when Windows or a dependency
cannot expose the requested state.

GET /api/diagnostics/check_microphone?device=default

GET /api/diagnostics/check_camera?device=default

GET /api/diagnostics/check_speaker?device=default

GET /api/diagnostics/check_connectivity?host=8.8.8.8&timeout_seconds=2

GET /api/diagnostics/check_app_state?application=Teams

GET /api/diagnostics/run_test?test_type=audio_test

Supported test types are `audio_test`, `camera_test`, and
`connectivity_test`.

## Action Endpoints

POST /actions/microphone

POST /actions/camera

POST /actions/speaker

Actions require user approval.

Example request:

{
  "approved": true
}

## Verification Endpoints

GET /verification/microphone

GET /verification/camera

GET /verification/speaker

## Ticket and Logging

POST /tickets

POST /logs

The prototype ticket route is `POST /api/tickets`. It accepts the original
Foundry payload (`symptom`, `diagnostics_run`, `actions_attempted`, and
`routing_team`) and also stores the structured incident handoff fields.

Technician endpoints:

GET /api/tickets

GET /api/tickets/{incident_id}

PATCH /api/tickets/{incident_id}/status

Incidents are stored in `backend/data/incidents.json` and survive a backend
restart during the demo. The response retains `ticket_id`, `diagnostics`,
`actions`, and `routing_team` for compatibility with the existing voice/Foundry
loop.

## Microsoft Foundry Tool Schemas

Expose these HTTP GET operations as function tools. The backend is the source
of diagnostic values; the model must pass through the returned JSON unchanged.

```json
[
  {"name":"check_microphone","method":"GET","path":"/api/diagnostics/check_microphone","parameters":{"device":{"type":"string","default":"default"}}},
  {"name":"check_camera","method":"GET","path":"/api/diagnostics/check_camera","parameters":{"device":{"type":"string","default":"default"}}},
  {"name":"check_speaker","method":"GET","path":"/api/diagnostics/check_speaker","parameters":{"device":{"type":"string","default":"default"}}},
  {"name":"check_connectivity","method":"GET","path":"/api/diagnostics/check_connectivity","parameters":{"host":{"type":"string","default":"8.8.8.8"},"timeout_seconds":{"type":"number","minimum":0.1,"maximum":10,"default":2}}},
  {"name":"check_app_state","method":"GET","path":"/api/diagnostics/check_app_state","parameters":{"application":{"type":"string","default":"Teams"}}},
  {"name":"run_test","method":"GET","path":"/api/diagnostics/run_test","parameters":{"test_type":{"type":"string","enum":["audio_test","camera_test","connectivity_test"]}}}
]
```

## Testing

The diagnostic, approval, action, verification, ticket, and logging endpoints were tested successfully using FastAPI Swagger UI.

## Note

The current backend uses deterministic mock responses for device diagnostics, actions, and verification. This allows the agent workflow to be developed and tested without requiring direct access to the user's operating system or meeting platform.
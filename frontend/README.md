# AI IT Incident Triage — Frontend

Product shell around the existing Foundry/voice troubleshooting session.

## Run

Start the backend and agent first, then:

```bash
pip install flask
python app.py
```

Open http://127.0.0.1:8001

Required local services:

- Backend: http://127.0.0.1:5673
- Agent / Foundry loop: http://127.0.0.1:3002/agent/message

## Screens

- Welcome / role selection (`#/`)
- Employee support home (`#/employee`)
- Active troubleshooting (`#/employee/session`)
- Incident created (`#/employee/incident-created`)
- My Sessions (`#/employee/sessions`)
- Session detail (`#/employee/sessions/:id`)
- Technician dashboard (`#/technician`)
- Incident detail (`#/technician/incident/:id` or `#/incident/:id`)

Voice, transcript, diagnostic timeline, approval, and verification stay on the troubleshooting screen and still call the existing agent API.

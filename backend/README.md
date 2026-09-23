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

GET /diagnostics/mic

GET /diagnostics/camera

GET /diagnostics/speaker

GET /diagnostics/connectivity

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

## Testing

The diagnostic, approval, action, verification, ticket, and logging endpoints were tested successfully using FastAPI Swagger UI.

## Note

The current backend uses deterministic mock responses for device diagnostics, actions, and verification. This allows the agent workflow to be developed and tested without requiring direct access to the user's operating system or meeting platform.
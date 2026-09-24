## Local MCP Demo

The local MCP server runs the existing Windows diagnostics on this laptop and
exposes exactly seven tools at `http://127.0.0.1:8000/mcp`:

- `check_microphone`
- `check_camera`
- `check_speaker`
- `check_connectivity`
- `check_app_state`
- `run_test`
- `create_incident`

Set `MCP_AUTH_TOKEN` in `.env`, then start it with the project interpreter:

```powershell
& .\microsoftVenv\Scripts\python.exe mcp_server.py
```

Check readiness at `http://127.0.0.1:8000/health`. The MCP endpoint requires
the bearer token. To expose it to Foundry for a local demo, run:

```powershell
devtunnel user login
devtunnel host -p 8000 --allow-anonymous
```

Use the printed HTTPS URL with `/mcp` as the Foundry remote MCP endpoint. Keep
the local server running while Foundry uses the tunnel.
# Voice Meeting Support Agent

A voice-based support agent that helps diagnose common meeting problems such as microphone, camera, speaker, and connectivity issues.

## Project Purpose

The system allows a user to describe a meeting problem using voice. The agent identifies the issue, runs the appropriate diagnostic tool, asks for approval before system-changing actions, verifies the result, and escalates when the issue cannot be resolved.

## Prototype role selection

The frontend currently uses local browser role selection rather than real authentication. Selecting **Employee** opens the existing AI troubleshooting experience, including voice, Foundry conversation, diagnostics, session history, and incident results. Selecting **Technician** opens the incident dashboard backed by the existing incident APIs.

The selected role is stored locally so a refresh keeps the same prototype experience. Use **Switch Role** to return to the welcome screen. This is not secure login, identity verification, or access control. A production deployment can replace this prototype role selection with enterprise authentication later.

## Team Structure

| Person | Responsibility |
|---|---|
| Sachleen | AI Agent / Reasoning |
| Gunika | Backend / Diagnostic Tools |
| Kanishka | Voice Interface |
| Pranav Sharma | Frontend / UI |
| Urvi Thakur | Integration, Testing & QA |

## Repository Structure

```text
voice_meeting_support_agent/
│
├── agent/
├── backend/
├── voice/
├── frontend/
├── contracts/
├── scenarios/
├── tests/
├── docs/
├── .env.example
├── .gitignore
└── README.md

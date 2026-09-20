# Voice Meeting Support Agent

A voice-based support agent that helps diagnose common meeting problems such as microphone, camera, speaker, and connectivity issues.

## Project Purpose

The system allows a user to describe a meeting problem using voice. The agent identifies the issue, runs the appropriate diagnostic tool, asks for approval before system-changing actions, verifies the result, and escalates when the issue cannot be resolved.

## Team Structure

| Person | Responsibility |
|---|---|
| A | AI Agent / Reasoning |
| B | Backend / Diagnostic Tools |
| C | Voice Interface |
| D | Frontend / UI |
| E | Integration, Testing & QA |

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

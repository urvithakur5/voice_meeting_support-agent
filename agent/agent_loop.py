"""Azure AI Foundry Agent Service loop with local approval and HTTP tools."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from dotenv import load_dotenv
from openai import BadRequestError

try:
    from .real_diagnostics import (
        check_camera,
        check_connectivity,
        check_mic,
        check_speaker,
        approved_action as approve_mock_action,
        fix_camera,
        fix_connectivity,
        fix_mic,
        fix_speaker,
    )
except ImportError:
    from real_diagnostics import (
        check_camera,
        check_connectivity,
        check_mic,
        check_speaker,
        approved_action as approve_mock_action,
        fix_camera,
        fix_connectivity,
        fix_mic,
        fix_speaker,
    )

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BACKEND_URL = (
    os.environ.get("BACKEND_URL") or "http://localhost:5673"
).rstrip("/")
TICKET_BACKEND_URL = (
    os.environ.get("TICKET_BACKEND_URL") or BACKEND_URL
).rstrip("/")
PROJECT_ENDPOINT = (
    os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    or os.environ.get("FOUNDRY_ENDPOINT")
    or os.environ["FOUNDRY_MODEL_ENDPOINT"]
)
AGENT_NAME = os.environ.get("FOUNDRY_AGENT_NAME", "voice-it-helpdesk-agent")
if "/api/projects/" not in PROJECT_ENDPOINT:
    PROJECT_ENDPOINT = (
        f"{PROJECT_ENDPOINT}/api/projects/"
        f"{os.environ.get('FOUNDRY_PROJECT_NAME', 'meeting-support-brain')}"
    )
POLL_INTERVAL_SECONDS = 1
SYSTEM_PROMPT = (
    "You are a Tier-1 IT diagnostic agent. Your job is to triage IT problems "
    "reported in natural language by employees. "
    "\n\nWhen an employee describes a problem, immediately select the most appropriate "
    "deterministic diagnostic tool and call it — do NOT ask them to choose a category. "
    "The employee will never say 'run check_wifi'; they will say 'my Wi-Fi keeps dropping'. "
    "\n\nAvailable diagnostic areas: "
    "microphone, camera, speaker, connectivity, Wi-Fi, VPN, Bluetooth audio, "
    "display/monitor, docking station, browser, application, system performance. "
    "\n\nRules: "
    "1. Call the diagnostic tool first. Read its JSON output carefully. "
    "2. Only ask follow-up questions if the answer changes which tool to call. "
    "3. Never invent diagnostic evidence. If the tool returns unknown, say so. "
    "4. Explain what the tool actually found in 1-2 sentences. "
    "5. Recommend only approved actions. Gate write actions behind user approval. "
    "6. After an action, verify with the appropriate tool. "
    "7. Resolve when verification passes. Escalate with create_incident when it does not. "
    "8. Use RAG knowledge only after a tool reports an issue requiring human guidance. "
    "9. Do not ask for OS details, driver versions, or other information "
    "the diagnostic tools can observe directly."
)

TOOL_NAMES = {
    "check_mic",
    "check_camera",
    "check_speaker",
    "check_connectivity",
    # Extended diagnostic tools
    "check_wifi",
    "check_vpn",
    "check_bluetooth_audio",
    "check_display",
    "check_dock",
    "check_browser_state",
    "check_application_state",
    "check_performance",
}

FIX_TO_DIAGNOSTIC = {
    "fix_mic": "check_mic",
    "fix_camera": "check_camera",
    "fix_speaker": "check_speaker",
    "fix_connectivity": "check_connectivity",
}

diagnostic_tools = [
    {
        "type": "function",
        "name": "check_mic",
        "description": "Check whether the default Windows microphone is connected, enabled, and muted.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_camera",
        "description": "Check whether a webcam is connected and available for use.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_speaker",
        "description": "Check the default Windows output device volume and mute status.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_connectivity",
        "description": "Ping 8.8.8.8 and report internet availability and packet loss.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "fix_mic",
        "description": "Attempt to repair the microphone by restarting its service.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "fix_camera",
        "description": "Attempt to repair the camera by restarting its service.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "fix_speaker",
        "description": "Attempt to repair the speaker by restarting its service.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "fix_connectivity",
        "description": "Attempt to repair connectivity by restarting its service.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "escalate_ticket",
        "description": "Create an IT helpdesk ticket when the issue cannot be resolved.",
        "parameters": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string"},
                "diagnostics_run": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "actions_attempted": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "routing_team": {"type": "string"},
            },
            "required": [
                "symptom",
                "diagnostics_run",
                "actions_attempted",
                "routing_team",
            ],
            "additionalProperties": False,
        },
    },
    # ── Extended diagnostic tools ────────────────────────────────────────
    {
        "type": "function",
        "name": "check_wifi",
        "description": (
            "Check Wi-Fi adapter state, SSID, signal strength, and internet reachability. "
            "Use when the user reports Wi-Fi disconnects, slow wireless, or can't connect to Wi-Fi."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_vpn",
        "description": (
            "Detect whether a VPN adapter is present and up. "
            "Use when the user reports VPN connection failures or cannot access corporate resources. "
            "Does NOT verify VPN authentication — reports adapter state only."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_bluetooth_audio",
        "description": (
            "Check Bluetooth subsystem availability and whether a Bluetooth audio headset is connected "
            "and appears as an active audio endpoint. "
            "Use when the user reports Bluetooth headset or audio problems."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_display",
        "description": (
            "Check display adapters, connected monitors, resolutions, and active state. "
            "Use when the user reports a black screen, missing monitor, or display issues."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_dock",
        "description": (
            "Check whether a docking station or USB hub is detected, and count connected peripherals. "
            "Use when the user reports that their dock stopped working or isn't detecting monitors."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_browser_state",
        "description": (
            "Check which browsers are running and optionally test network reachability to a target host. "
            "Use when the user reports browser problems or company portal issues. "
            "Does NOT read browsing history, cookies, passwords, or private data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Optional hostname to test reachability (e.g. 'portal.company.com'). Leave empty if not needed.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_application_state",
        "description": (
            "Check whether a specific application process is running and read its version. "
            "Use when the user reports that an application is freezing, crashing, or won't start. "
            "Does NOT terminate processes or read private application data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "description": "The application name without .exe (e.g. 'Teams', 'Zoom', 'Outlook').",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_performance",
        "description": (
            "Measure CPU usage, memory usage, disk free space, and system uptime. "
            "Use when the user reports that their computer is extremely slow or unresponsive. "
            "Returns measurements only — does NOT diagnose the root cause."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]


def print_environment_diagnostic() -> None:
    """Report configuration presence without exposing credentials or values."""
    checks = {
        "FOUNDRY_PROJECT_ENDPOINT": bool(os.environ.get("FOUNDRY_PROJECT_ENDPOINT")),
        "FOUNDRY_AGENT_NAME": bool(os.environ.get("FOUNDRY_AGENT_NAME")),
        "AZURE_CLIENT_ID": bool(os.environ.get("AZURE_CLIENT_ID")),
    }
    summary = ", ".join(
        f"{name}={'detected' if detected else 'missing'}"
        for name, detected in checks.items()
    )
    print(f"[startup] Environment configuration: {summary}")


def build_azure_credential():
    """Prefer the configured service principal over a cached developer login."""
    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")

    if client_id and tenant_id and client_secret:
        print("[startup] Azure credential: configured service principal")
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    print("[startup] Azure credential: DefaultAzureCredential chain")
    return DefaultAzureCredential()


def request_backend(method: str, path: str, **kwargs: Any) -> dict:
    """Call a local backend contract endpoint and return its JSON response."""
    response = requests.request(
        method,
        f"{BACKEND_URL}{path}",
        timeout=15,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def request_ticket(payload: dict) -> dict:
    """Send an escalation ticket to the ticketing backend."""
    response = requests.post(
        f"{TICKET_BACKEND_URL}/api/tickets",
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def is_approval(user_input: str) -> bool:
    normalized = user_input.lower()
    return any(
        phrase in normalized
        for phrase in ("yes", "sure", "fix", "please", "do it", "approve")
    )


def is_decline(user_input: str) -> bool:
    normalized = user_input.lower()
    return any(
        phrase in normalized
        for phrase in ("no", "cancel", "stop", "deny", "don't")
    )


def is_exit_request(user_input: str) -> bool:
    normalized = user_input.lower()
    return any(
        phrase in normalized
        for phrase in ("bye", "goodbye", "exit", "thanks", "thank you")
    )


def action_for_tool(tool_name: str) -> str:
    return {
        "check_mic": "fix_microphone_permissions",
        "check_camera": "restart_camera",
        "check_speaker": "restart_speaker",
        "check_connectivity": "restart_network",
    }[tool_name]


def tool_for_action(action_name: str) -> str:
    return {
        "fix_microphone_permissions": "check_mic",
        "unmute_microphone": "check_mic",
        "restart_camera": "check_camera",
        "restart_speaker": "check_speaker",
        "restart_network": "check_connectivity",
    }[action_name]


def extract_function_call(tool_call: Any) -> tuple[str, dict]:
    function = tool_call.function
    arguments = function.arguments or "{}"
    return function.name, json.loads(arguments)


def tool_result(tool_call_id: str, output: Any) -> dict:
    return {"tool_call_id": tool_call_id, "output": json.dumps(output)}


DIAGNOSTIC_ENDPOINTS = {
    "check_mic": "/api/diagnostics/check_microphone",
    "check_camera": "/api/diagnostics/check_camera",
    "check_speaker": "/api/diagnostics/check_speaker",
    "check_connectivity": "/api/diagnostics/check_connectivity",
    # Extended diagnostic areas
    "check_wifi": "/api/diagnostics/check_wifi",
    "check_vpn": "/api/diagnostics/check_vpn",
    "check_bluetooth_audio": "/api/diagnostics/check_bluetooth_audio",
    "check_display": "/api/diagnostics/check_display",
    "check_dock": "/api/diagnostics/check_dock",
    "check_browser_state": "/api/diagnostics/check_browser_state",
    "check_application_state": "/api/diagnostics/check_application_state",
    "check_performance": "/api/diagnostics/check_performance",
}

REAL_FIXES = {
    "fix_mic": fix_mic,
    "fix_camera": fix_camera,
    "fix_speaker": fix_speaker,
    "fix_connectivity": fix_connectivity,
}

SESSIONS: dict[str, dict[str, Any]] = {}


def run_diagnostic(tool_name: str, state: dict) -> dict:
    print(f"[tool] {tool_name}")
    diagnostic = request_backend("GET", DIAGNOSTIC_ENDPOINTS[tool_name])
    state["current_intent"] = tool_name.removeprefix("check_")
    state["diagnosis"].append(diagnostic)
    return diagnostic


def fallback_reply(tool_name: str, diagnostic: dict) -> str:
    status = diagnostic.get("status", "unknown")
    message = diagnostic.get("message") or diagnostic.get("reason")
    label = tool_name.removeprefix("check_").replace("_", " ")
    if message:
        return f"I checked your {label}. {message}"
    return f"I checked your {label}; the backend reported {status}."


def fallback_diagnostic_tool(user_text: str) -> str | None:
    normalized = user_text.lower()
    # ── Original patterns (unchanged) ─────────────────────────────────────
    if (
        "nobody can hear me" in normalized
        or "no one can hear me" in normalized
        or "can't hear me" in normalized
        or "cannot hear me" in normalized
    ):
        return "check_mic"
    if any(term in normalized for term in ("microphone", "mic")):
        return "check_mic"
    if "camera" in normalized or "webcam" in normalized:
        return "check_camera"
    if "speaker" in normalized or ("audio" in normalized and "bluetooth" not in normalized):
        return "check_speaker"
    # ── Extended patterns ──────────────────────────────────────────────────
    if any(term in normalized for term in ("wi-fi", "wifi", "wireless", "wlan")):
        return "check_wifi"
    if any(term in normalized for term in ("vpn", "secure connect", "corporate network", "remote access")):
        return "check_vpn"
    if any(term in normalized for term in ("bluetooth", "headset", "bt headphone", "bt audio")):
        return "check_bluetooth_audio"
    if any(term in normalized for term in ("monitor", "display", "screen", "second screen", "external screen", "hdmi")):
        return "check_display"
    if any(term in normalized for term in ("dock", "docking", "port replicator")):
        return "check_dock"
    if any(term in normalized for term in ("browser", "chrome", "edge", "firefox", "portal", "website", "web page", "webpage")):
        return "check_browser_state"
    if any(term in normalized for term in ("slow", "lagging", "performance", "cpu", "memory", "ram", "disk space", "freezing", "frozen")):
        return "check_performance"
    if any(term in normalized for term in ("application", "app ", "teams", "zoom", "outlook", "crashing", "won't start", "not opening")):
        return "check_application_state"
    if any(term in normalized for term in ("internet", "connection", "network")):
        return "check_connectivity"
    return None


def enforce_voice_brevity(text: str) -> str:
    """Return a concise spoken response with no list formatting."""
    cleaned = re.sub(r"【.*?】", "", text or "")
    cleaned = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return " ".join(sentences[:2]).strip()


def create_escalation(
    state: dict,
    issue: str,
    result: str,
    actions: list[dict],
) -> dict:
    ticket = request_ticket(
        {
            "symptom": issue,
            "diagnostics_run": state["diagnosis"],
            "actions_attempted": actions,
            "routing_team": "IT Helpdesk",
        }
    )
    state["stage"] = "escalated"
    state["escalation"] = {
        "required": True,
        "reason": result,
        "ticket_id": ticket["ticket_id"],
    }
    state["escalation_card"] = {
        **ticket,
        "symptom": issue,
        "diagnostics_run": state["diagnosis"],
        "actions_attempted": actions,
        "routing_team": "IT Helpdesk",
        "reason": result,
    }
    return ticket


def escalate_ticket(
    arguments: dict,
    state: dict,
    actions: list[dict],
) -> dict:
    """Create a ticket from the LLM's explicit escalation request."""
    ticket = request_ticket(
        {
            "symptom": arguments["symptom"],
            "diagnostics_run": arguments["diagnostics_run"],
            "actions_attempted": arguments["actions_attempted"],
            "routing_team": arguments["routing_team"],
        }
    )
    state["stage"] = "escalated"
    state["escalation"] = {
        "required": True,
        "reason": "llm_escalation",
        "ticket_id": ticket.get("ticket_id"),
    }
    state["escalation_card"] = {
        **ticket,
        **arguments,
    }
    return ticket


def handle_requires_action(
    client: Any,
    run: Any,
    thread_id: str,
    session_id: str,
    state: dict,
    actions: list[dict],
) -> Any:
    """Execute read-only tools and gate every write action before POSTing."""
    required = run.required_action.submit_tool_outputs
    outputs: list[Any] = []

    for tool_call in required.tool_calls:
        tool_name, arguments = extract_function_call(tool_call)

        if tool_name in TOOL_NAMES:
            diagnostic = run_diagnostic(tool_name, state)
            outputs.append(tool_result(tool_call.id, diagnostic))
            continue

        if tool_name != "execute_action":
            outputs.append(
                tool_result(
                    tool_call.id,
                    {
                        "status": "error",
                        "error_code": "unsupported_tool",
                        "message": f"Unsupported tool: {tool_name}",
                    },
                )
            )
            continue

        action_name = arguments.get("action_name") or "fix_microphone_permissions"
        state["stage"] = "approval_required"
        state["recommended_action"] = action_name
        print(
            "Agent: I need your approval before changing a meeting setting. "
            "Please answer yes or no."
        )
        approval = input("You: ").strip()
        client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=approval,
        )

        if is_decline(approval) or not is_approval(approval):
            ticket = create_escalation(
                state,
                state.get("current_intent") or "meeting_support",
                "user_declined_action",
                actions,
            )
            outputs.append(
                tool_result(
                    tool_call.id,
                    {
                        "status": "blocked",
                        "error_code": "user_declined_action",
                        "message": "User declined the approved action.",
                        "ticket_id": ticket["ticket_id"],
                    },
                )
            )
            continue

        state["stage"] = "acting"
        action_result = request_backend(
            "POST",
            "/api/actions",
            json={
                "session_id": session_id,
                "action_name": action_name,
                "user_approved": True,
            },
        )
        actions.append(action_result)
        if action_result.get("status") != "working":
            outputs.append(tool_result(tool_call.id, action_result))
            continue

        state["stage"] = "verifying"
        verification_tool = tool_for_action(action_name)
        verification = request_backend(
            "GET",
            f"/api/{verification_tool}",
        )
        state["diagnosis"].append(verification)
        action_output = {
            "action": action_result,
            "verification": verification,
        }
        if verification.get("status") != "working":
            create_escalation(
                state,
                state.get("current_intent") or verification_tool,
                verification.get("error_code", "verification_failed"),
                actions,
            )
        else:
            state["stage"] = "resolved"
            state["recommended_action"] = None
        outputs.append(tool_result(tool_call.id, action_output))

    return client.agents.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=outputs,
    )


def process_run(
    client: Any,
    thread_id: str,
    run: Any,
    session_id: str,
    state: dict,
    actions: list[dict],
) -> Any:
    """Poll a run and service every requires_action request until terminal."""
    while run.status in {"queued", "in_progress", "requires_action"}:
        if run.status == "requires_action":
            run = handle_requires_action(
                client,
                run,
                thread_id,
                session_id,
                state,
                actions,
            )
            continue

        time.sleep(POLL_INTERVAL_SECONDS)
        run = client.agents.runs.get(thread_id=thread_id, run_id=run.id)

    if run.status == "failed":
        state["stage"] = "escalated"
        state["escalation"] = {
            "required": True,
            "reason": getattr(run.last_error, "message", "agent_run_failed"),
        }
    return run


def execute_response_tool(
    tool_name: str,
    arguments: dict,
    session_id: str,
    state: dict,
    actions: list[dict],
    user_approved: bool,
) -> dict:
    if tool_name in TOOL_NAMES:
        return run_diagnostic(tool_name, state)

    if tool_name in FIX_TO_DIAGNOSTIC:
        if not user_approved:
            state["stage"] = "approval_required"
            state["recommended_action"] = action_for_tool(tool_name)
            return {
                "status": "approval_required",
                "error_code": "approval_required",
                "message": "User approval is required before attempting a repair.",
            }
        state["stage"] = "acting"
        action_result = json.loads(REAL_FIXES[tool_name]())
        actions.append(action_result)
        state["stage"] = "verifying"
        verification = run_diagnostic(FIX_TO_DIAGNOSTIC[tool_name], state)
        result = {"action": action_result, "verification": verification}
        if verification.get("status") == "working":
            state["stage"] = "resolved"
            state["recommended_action"] = None
        else:
            create_escalation(
                state,
                state.get("current_intent") or FIX_TO_DIAGNOSTIC[tool_name],
                verification.get("error_code", "verification_failed"),
                actions,
            )
        return result

    if tool_name == "escalate_ticket":
        return escalate_ticket(arguments, state, actions)

    if tool_name != "execute_action":
        return {"status": "error", "error_code": "unsupported_tool"}

    action_name = arguments.get("action_name") or "fix_microphone_permissions"
    state["stage"] = "approval_required"
    state["recommended_action"] = action_name
    if not user_approved:
        return {
            "status": "approval_required",
            "error_code": "approval_required",
            "message": "User approval is required before attempting a repair.",
        }

    state["stage"] = "acting"
    action_result = request_backend(
        "POST",
        "/api/actions",
        json={
            "session_id": session_id,
            "action_name": action_name,
            "user_approved": True,
        },
    )
    actions.append(action_result)
    if action_result.get("status") != "working":
        return action_result

    state["stage"] = "verifying"
    verification_tool = tool_for_action(action_name)
    verification = request_backend("GET", f"/api/{verification_tool}")
    state["diagnosis"].append(verification)
    if verification.get("status") != "working":
        create_escalation(
            state,
            state.get("current_intent") or verification_tool,
            verification.get("error_code", "verification_failed"),
            actions,
        )
    else:
        state["stage"] = "resolved"
        state["recommended_action"] = None
    return {"action": action_result, "verification": verification}


def approved_action(
    action_name: str,
    session_id: str,
    state: dict,
    actions: list[dict],
) -> dict:
    """Apply an approved action, verify it, and escalate if it still fails."""
    state["stage"] = "acting"
    if action_name == "fix_mic_permission":
        action_result = approve_mock_action(action_name)
        actions.append(action_result)
        if not action_result.get("success"):
            state["stage"] = "escalated"
            return {"action": action_result}
        state["stage"] = "verifying"
        verification = run_diagnostic("check_mic", state)
        state["stage"] = "resolved" if verification.get("permission") else "escalated"
        if state["stage"] == "resolved":
            state["recommended_action"] = None
        return {"action": action_result, "verification": verification}

    action_result = request_backend(
        "POST",
        "/api/actions",
        json={
            "session_id": session_id,
            "action_name": action_name,
            "user_approved": True,
        },
    )
    actions.append(action_result)
    if action_result.get("status") != "working":
        create_escalation(
            state,
            state.get("current_intent") or action_name,
            action_result.get("error_code", "action_failed"),
            actions,
        )
        return {"action": action_result}

    state["stage"] = "verifying"
    verification_tool = tool_for_action(action_name)
    verification = run_diagnostic(verification_tool, state)
    result = {"action": action_result, "verification": verification}
    if verification.get("status") == "working":
        state["stage"] = "resolved"
        state["recommended_action"] = None
    else:
        create_escalation(
            state,
            state.get("current_intent") or verification_tool,
            verification.get("error_code", "verification_failed"),
            actions,
        )
    return result


def complete_response(
    openai_client: Any,
    conversation_id: str,
    response: Any,
    session_id: str,
    state: dict,
    actions: list[dict],
    user_approved: bool,
) -> Any:
    while True:
        calls = [
            item for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        if not calls:
            return response
        outputs = []
        for call in calls:
            result = execute_response_tool(
                call.name,
                json.loads(call.arguments or "{}"),
                session_id,
                state,
                actions,
                user_approved,
            )
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                }
            )
        response = openai_client.responses.create(
            conversation=conversation_id,
            previous_response_id=response.id,
            input=outputs,
            tools=diagnostic_tools,
            tool_choice="auto",
            temperature=0.2,
            max_output_tokens=100,
        )


def _checklist_from_diagnostics(diagnosis: list[dict]) -> list[dict]:
    """Pass through observed tool results without inventing failures.

    Handles both legacy tool results (status/message/error_code) and
    new-area results (title/reason/observations from area_result).
    """
    checklist = []
    for item in diagnosis:
        if not isinstance(item, dict):
            checklist.append({"title": str(item), "state": "unknown"})
            continue
        permission = item.get("permission")
        status = str(item.get("status") or "unknown").lower()
        observations = item.get("observations") or []
        if permission in (False, "blocked", "denied"):
            perm_state = "failed"
            perm_detail = "Application microphone permission blocked"
        elif permission in (True, "granted", "allowed"):
            perm_state = "completed"
            perm_detail = "Application microphone permission granted"
        else:
            perm_state = "unknown"
            perm_detail = "Application permission: Not observable"
        checklist.append(
            {
                "title": item.get("title")
                or item.get("name")
                or item.get("tool")
                or "Diagnostic check",
                "detail": item.get("reason") or item.get("message") or item.get("details") or status,
                "state": status,
                "detected": item.get("detected"),
                "connected": item.get("connected"),
                "permission": permission,
                "permission_state": perm_state,
                "permission_detail": perm_detail,
                "observations": observations,
                **{key: value for key, value in item.items() if key not in {"title"}},
            }
        )
    return checklist


def ui_state_for(state: dict) -> dict:
    """Expose the conversation state in the shape expected by the UI."""
    escalation = state.get("escalation", {"required": False, "reason": None})
    diagnosis = state.get("diagnosis", [])
    latest_diagnostic = diagnosis[-1] if diagnosis else {}
    recommended_action = state.get("recommended_action")
    pending_action_id = state.get("pending_action_id")
    finding = (
        latest_diagnostic.get("reason")
        or latest_diagnostic.get("message")
        or state.get("finding")
        or ""
    )
    return {
        "issue": state.get("current_intent") or state.get("issue"),
        "diagnosis_checklist": _checklist_from_diagnostics(diagnosis),
        "pending_action": recommended_action,
        "pending_action_id": pending_action_id,
        "finding": finding,
        "escalation_card": state.get("escalation_card")
        if escalation.get("required")
        else None,
        **state,
        "recommended_action": recommended_action,
        "verification": state.get("verification", {}),
        "agent_status": state.get("stage", "diagnosing"),
    }


def run_agent_turn(
    session_id: str,
    user_text: str,
    user_approved: bool,
) -> tuple[str, dict]:
    """Process one user message and return the reply plus current UI state."""
    if not user_text.strip():
        raise ValueError("user_text must not be empty")

    session = SESSIONS.get(session_id)
    if session is None:
        print_environment_diagnostic()
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=build_azure_credential(),
        )
        try:
            client.agents.get(AGENT_NAME)
            openai_client = client.get_openai_client(agent_name=AGENT_NAME)
            conversation = openai_client.conversations.create()
        except HttpResponseError as error:
            client.close()
            raise RuntimeError(
                f"Unable to access Foundry agent '{AGENT_NAME}'. Check "
                "FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_AGENT_NAME."
            ) from error
        session = {
            "client": client,
            "openai_client": openai_client,
            "conversation_id": conversation.id,
            "state": {
                "current_intent": None,
                "stage": "diagnosing",
                "diagnosis": [],
                "recommended_action": None,
                "escalation": {"required": False, "reason": None},
            },
            "actions": [],
        }
        SESSIONS[session_id] = session

    if user_approved:
        action_name = session["state"].get("pending_action_id")
        latest_diagnostic = session["state"].get("diagnosis", [])[-1:]
        if (
            not action_name
            and session["state"].get("current_intent") == "mic"
            and latest_diagnostic
            and latest_diagnostic[0].get("permission") is False
        ):
            action_name = "fix_mic_permission"
        if not action_name:
            action_name = session["state"].get("recommended_action")
        if not action_name:
            current_intent = session["state"].get("current_intent")
            if current_intent:
                action_name = action_for_tool(f"check_{current_intent}")
        if not action_name:
            raise ValueError("No pending action is available for approval")
        action_result = approved_action(
            action_name,
            session_id,
            session["state"],
            session["actions"],
        )
        if session["state"].get("stage") == "escalated":
            reply_text = "The fix didn't work, so I have escalated this and opened a high-priority ticket with all our diagnostic data."
        else:
            reply_text = "I applied the fix and verified your hardware is now working."
        return (
            reply_text,
            ui_state_for(session["state"]),
        )

    tool_name = fallback_diagnostic_tool(user_text)
    tool_choice = (
        {"type": "function", "name": tool_name}
        if tool_name
        else "auto"
    )

    response_arguments = {
        "conversation": session["conversation_id"],
        "instructions": SYSTEM_PROMPT,
        "input": user_text,
        "tools": diagnostic_tools,
        "tool_choice": tool_choice,
        "temperature": 0.2,
        "max_output_tokens": 100,
    }
    try:
        response = session["openai_client"].responses.create(**response_arguments)
    except BadRequestError as error:
        if "Not allowed when agent is specified" not in str(error):
            raise
        response = session["openai_client"].responses.create(
            conversation=session["conversation_id"],
            input=user_text,
            max_output_tokens=100,
        )
    response = complete_response(
        session["openai_client"],
        session["conversation_id"],
        response,
        session_id,
        session["state"],
        session["actions"],
        user_approved,
    )
    reply_text = enforce_voice_brevity(response.output_text)
    if tool_name and not session["state"].get("diagnosis"):
        diagnostic = run_diagnostic(tool_name, session["state"])
        reply_text = fallback_reply(tool_name, diagnostic)
    elif not reply_text and session["state"].get("diagnosis"):
        reply_text = fallback_reply(tool_name or "meeting support", session["state"]["diagnosis"][-1])
    return reply_text, ui_state_for(session["state"])

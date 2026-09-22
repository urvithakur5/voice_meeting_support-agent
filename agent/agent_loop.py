"""Azure AI Foundry Agent Service loop with local approval and HTTP tools."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import MessageRole, ToolOutput
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BACKEND_URL = (
    os.environ.get("BACKEND_URL") or "http://localhost:8000"
).rstrip("/")
PROJECT_ENDPOINT = (
    os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    or os.environ.get("FOUNDRY_ENDPOINT")
    or os.environ["FOUNDRY_MODEL_ENDPOINT"]
)
AGENT_ID = os.environ["FOUNDRY_AGENT_ID"]
POLL_INTERVAL_SECONDS = 1

TOOL_NAMES = {
    "check_mic",
    "check_camera",
    "check_speaker",
    "check_connectivity",
}


def print_environment_diagnostic() -> None:
    """Report configuration presence without exposing credentials or values."""
    checks = {
        "FOUNDRY_PROJECT_ENDPOINT": bool(os.environ.get("FOUNDRY_PROJECT_ENDPOINT")),
        "FOUNDRY_AGENT_ID": bool(os.environ.get("FOUNDRY_AGENT_ID")),
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


def tool_result(tool_call_id: str, output: Any) -> ToolOutput:
    return ToolOutput(
        tool_call_id=tool_call_id,
        output=json.dumps(output),
    )


def get_assistant_text(client: AIProjectClient, thread_id: str, run_id: str) -> str:
    """Read the newest assistant message from the completed run."""
    message = client.agents.messages.get_last_message_text_by_role(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
    )
    if message is None:
        return ""
    return getattr(message, "value", str(message))


def create_escalation(
    state: dict,
    issue: str,
    result: str,
    actions: list[dict],
) -> dict:
    ticket = request_backend(
        "POST",
        "/api/tickets",
        json={
            "issue": issue,
            "diagnostics_run": state["diagnosis"],
            "actions_attempted": actions,
            "result": result,
        },
    )
    state["stage"] = "escalated"
    state["escalation"] = {
        "required": True,
        "reason": result,
        "ticket_id": ticket["ticket_id"],
    }
    return ticket


def handle_requires_action(
    client: AIProjectClient,
    run: Any,
    thread_id: str,
    session_id: str,
    state: dict,
    actions: list[dict],
) -> Any:
    """Execute read-only tools and gate every write action before POSTing."""
    required = run.required_action.submit_tool_outputs
    outputs: list[ToolOutput] = []

    for tool_call in required.tool_calls:
        tool_name, arguments = extract_function_call(tool_call)

        if tool_name in TOOL_NAMES:
            state["current_intent"] = tool_name.removeprefix("check_")
            diagnostic = request_backend(
                "GET",
                f"/api/{tool_name}",
            )
            state["diagnosis"].append(diagnostic)
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
    client: AIProjectClient,
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


def run_agent() -> None:
    print_environment_diagnostic()
    session_id = str(uuid.uuid4())
    request_backend("POST", "/scenario", json={"id": "MIC-007"})

    client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=build_azure_credential(),
    )
    agent = client.agents.get_agent(AGENT_ID)
    thread = client.agents.threads.create()
    state = {
        "current_intent": None,
        "stage": "diagnosing",
        "diagnosis": [],
        "recommended_action": None,
        "escalation": {"required": False, "reason": None},
    }
    actions: list[dict] = []

    print("Agent: Hello. How can I help with your meeting today?")
    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input,
            )
            run = client.agents.runs.create(
                thread_id=thread.id,
                agent_id=agent.id,
            )
            run = process_run(
                client,
                thread.id,
                run,
                session_id,
                state,
                actions,
            )

            response_text = get_assistant_text(client, thread.id, run.id)
            if response_text:
                print(f"Agent: {response_text}")

            if is_exit_request(user_input):
                break

            if run.status == "completed" and state["diagnosis"]:
                latest = state["diagnosis"][-1]
                if latest.get("status") == "working":
                    state["stage"] = "resolved"
                elif latest.get("status") == "blocked":
                    state["stage"] = "approval_required"

    finally:
        client.close()


if __name__ == "__main__":
    run_agent()

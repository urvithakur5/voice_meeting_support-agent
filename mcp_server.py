"""Local MCP bridge for Windows diagnostics and incident handoff."""

from __future__ import annotations

import hmac
import os
import time
from functools import wraps
from typing import Any, Literal

import uvicorn
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.services.incidents import create_incident as persist_incident
from backend.services.logger import log_event
from backend.tools.diagnostics import (
    check_app_state as read_app_state,
    check_camera as read_camera,
    check_connectivity as read_connectivity,
    check_microphone as read_microphone,
    check_speaker as read_speaker,
    run_test as execute_test,
)


load_dotenv()

MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")
MCP_TOOL_NAMES = (
    "check_microphone",
    "check_camera",
    "check_speaker",
    "check_connectivity",
    "check_app_state",
    "run_test",
    "create_incident",
)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Require bearer authentication for the remote MCP endpoint."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        if not MCP_AUTH_TOKEN:
            return JSONResponse(
                {"detail": "MCP_AUTH_TOKEN is not configured"},
                status_code=503,
            )

        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(token, MCP_AUTH_TOKEN):
            return JSONResponse({"detail": "Bearer authentication required"}, status_code=401)

        return await call_next(request)


def logged_tool(function):
    """Record tool execution without recording credentials or full payloads."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            result = function(*args, **kwargs)
            log_event(
                "mcp_tool_completed",
                function.__name__,
                result={
                    "success": True,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            return result
        except Exception as error:
            log_event(
                "mcp_tool_failed",
                function.__name__,
                result={
                    "success": False,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error_code": type(error).__name__,
                },
            )
            raise

    return wrapper


server = MCPServer(
    name="it-incident-local-diagnostics",
    title="AI IT Incident Triage Local Diagnostics",
    description="Runs approved diagnostics on the local Windows machine and creates evidence-rich incidents.",
    version="1.0.0",
)


@server.tool(
    name="check_microphone",
    description="Use when the user reports microphone or audio-input problems. Returns actual local machine microphone information. Never fabricate results.",
    structured_output=True,
)
@logged_tool
def check_microphone(device: str = "default") -> dict[str, Any]:
    return read_microphone(device)


@server.tool(
    name="check_camera",
    description="Use when the user reports camera or video problems. Returns actual local camera information where available. Never fabricate results.",
    structured_output=True,
)
@logged_tool
def check_camera(device: str = "default") -> dict[str, Any]:
    return read_camera(device)


@server.tool(
    name="check_speaker",
    description="Use when the user reports speaker or audio-output problems. Returns actual local output-device information where available. Never fabricate results.",
    structured_output=True,
)
@logged_tool
def check_speaker(device: str = "default") -> dict[str, Any]:
    return read_speaker(device)


@server.tool(
    name="check_connectivity",
    description="Use when the user reports connectivity, meeting-joining, or network problems. Returns actual local connectivity test results.",
    structured_output=True,
)
@logged_tool
def check_connectivity(host: str = "8.8.8.8", timeout_seconds: float = 2.0) -> dict[str, Any]:
    return read_connectivity(host, timeout_seconds)


@server.tool(
    name="check_app_state",
    description="Use when the agent needs to determine whether a relevant application is running or whether observable local state is available. The result is unknown when it cannot be reliably observed.",
    structured_output=True,
)
@logged_tool
def check_app_state(application: str = "Teams") -> dict[str, Any]:
    return read_app_state(application)


@server.tool(
    name="run_test",
    description="Use for concrete verification after troubleshooting. Accepts microphone, speaker, camera, or connectivity and returns a structured result.",
    structured_output=True,
)
@logged_tool
def run_test(test_type: Literal["microphone", "speaker", "camera", "connectivity"]) -> dict[str, Any]:
    legacy_test_type = {
        "microphone": "microphone_test",
        "speaker": "speaker_test",
        "camera": "camera_test",
        "connectivity": "connectivity_test",
    }[test_type]
    result = execute_test(legacy_test_type)
    return {**result, "test_type": test_type}


@server.tool(
    name="create_incident",
    description="Use only after troubleshooting was attempted and the issue remains unresolved. Include the diagnostic evidence already collected; do not invent evidence.",
    structured_output=True,
)
@logged_tool
def create_incident(
    user_statement: str,
    employee: dict[str, Any] | None = None,
    issue: dict[str, Any] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    questions_answered: list[dict[str, Any]] | None = None,
    knowledge_used: list[dict[str, Any]] | None = None,
    actions_attempted: list[dict[str, Any]] | None = None,
    verification: dict[str, Any] | None = None,
    likely_area: str = "unknown",
    recommended_team: str = "IT Helpdesk",
    status: str = "needs_human",
) -> dict[str, Any]:
    return persist_incident(
        {
            "user_statement": user_statement,
            "user_report": user_statement,
            "employee": employee or {},
            "issue": issue or {},
            "diagnostics": diagnostics or [],
            "questions_answered": questions_answered or [],
            "knowledge_used": knowledge_used or [],
            "actions_attempted": actions_attempted or [],
            "verification": verification or {},
            "likely_area": likely_area,
            "recommended_team": recommended_team,
            "status": status,
        }
    )


app = server.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    host=MCP_HOST,
)
async def health(request: Request):
    return JSONResponse(
        {
            "status": "ok",
            "service": "local-mcp",
            "mcp_path": "/mcp",
            "tool_count": len(MCP_TOOL_NAMES),
            "authentication_configured": bool(MCP_AUTH_TOKEN),
        }
    )


app.add_route("/health", health, methods=["GET"])
app.add_middleware(BearerTokenMiddleware)


if __name__ == "__main__":
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
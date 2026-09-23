from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from .agent_loop import run_agent_turn
except ImportError:
    from agent_loop import run_agent_turn


class AgentMessageRequest(BaseModel):
    session_id: str
    user_text: str
    user_approved: bool


class AgentMessageResponse(BaseModel):
    reply_text: str
    ui_state: dict[str, Any]


app = FastAPI(title="Voice Meeting Support Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:6000",
        "http://127.0.0.1:6000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/agent/message", response_model=AgentMessageResponse)
def agent_message(request: AgentMessageRequest) -> AgentMessageResponse:
    reply_text, ui_state = run_agent_turn(
        session_id=request.session_id,
        user_text=request.user_text,
        user_approved=request.user_approved,
    )
    return AgentMessageResponse(reply_text=reply_text, ui_state=ui_state)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3002)
import json

import requests


response = requests.post(
    "http://localhost:3002/agent/message",
    json={
        "session_id": "test_001",
        "user_text": "My camera is just showing a black screen.",
        "user_approved": False,
    },
    timeout=60,
)

print(f"Status code: {response.status_code}")
response.raise_for_status()

payload = response.json()
print(json.dumps({
    "reply_text": payload["reply_text"],
    "ui_state": payload["ui_state"],
}, indent=2))
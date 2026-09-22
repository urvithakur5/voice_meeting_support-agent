"""Shared state and tool contracts for the voice meeting support agent.

These dictionaries are the source of truth for the agent, backend, and
frontend integration. They describe the exact JSON keys exchanged between
components; runtime validation should be performed at each API boundary.
"""


DEFAULT_UI_STATE = {
    "current_intent": None,
    "stage": "diagnosing",
    "diagnosis": [],
    "recommended_action": None,
    "escalation": {
        "required": False,
        "reason": None,
    },
}


EXPECTED_TOOL_SCHEMAS = {
    "check_mic": {
        "type": "read_only_diagnostic",
        "input": {
            "required_keys": ["device"],
            "properties": {
                "device": {"type": "string"},
            },
        },
        "output": {
            "required_keys": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["working", "blocked", "error"],
                },
                "error_code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
    "check_camera": {
        "type": "read_only_diagnostic",
        "input": {
            "required_keys": ["device"],
            "properties": {
                "device": {"type": "string"},
            },
        },
        "output": {
            "required_keys": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["working", "blocked", "error"],
                },
                "error_code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
    "check_speaker": {
        "type": "read_only_diagnostic",
        "input": {
            "required_keys": ["device"],
            "properties": {
                "device": {"type": "string"},
            },
        },
        "output": {
            "required_keys": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["working", "blocked", "error"],
                },
                "error_code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
    "check_connectivity": {
        "type": "read_only_diagnostic",
        "input": {
            "required_keys": [],
            "properties": {},
        },
        "output": {
            "required_keys": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["working", "blocked", "error"],
                },
                "error_code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
    "execute_action": {
        "type": "write_action",
        "input": {
            "required_keys": [
                "action_name",
                "session_id",
                "user_approved",
            ],
            "properties": {
                "action_name": {"type": "string"},
                "session_id": {"type": "string"},
                "user_approved": {"type": "boolean"},
            },
        },
        "output": {
            "required_keys": ["status", "error_code", "message"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["working", "blocked", "error"],
                },
                "error_code": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    },
    "create_ticket": {
        "type": "ticketing",
        "input": {
            "required_keys": [
                "issue",
                "diagnostics",
                "actions",
                "result",
            ],
            "properties": {
                "issue": {"type": "string"},
                "diagnostics": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "actions": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "result": {"type": "string"},
            },
        },
        "output": {
            "required_keys": [
                "ticket_id",
                "issue",
                "diagnostics",
                "actions",
                "result",
                "status",
            ],
            "properties": {
                "ticket_id": {"type": "string"},
                "issue": {"type": "string"},
                "diagnostics": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "actions": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "result": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["open", "error"],
                },
            },
        },
    },
}

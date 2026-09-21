# Store all predefined testing scenarios
SCENARIOS = {
    "MIC-007": {
        "tool": "mic",
        "before": {
            "status": "blocked",
            "error_code": "permission_denied",
            "message": "Microphone permission is denied."
        },
        "after": {
            "status": "working",
            "error_code": "none",
            "message": "Microphone is working correctly after the fix."
        }
    },

    "MIC-008": {
        "tool": "mic",
        "before": {
            "status": "blocked",
            "error_code": "permission_denied",
            "message": "Microphone permission is denied."
        },
        "after": {
            "status": "blocked",
            "error_code": "permission_denied",
            "message": "Microphone permission is still denied after the fix."
        }
    },

    "MIC-003": {
        "tool": "mic",
        "before": {
            "status": "error",
            "error_code": "timeout",
            "message": "Microphone diagnostic timed out."
        },
        "after": {
            "status": "error",
            "error_code": "timeout",
            "message": "Microphone diagnostic timed out."
        }
    },

    "MIC-001": {
        "tool": "mic",
        "before": {
            "status": "working",
            "error_code": "none",
            "message": "Microphone is working correctly."
        },
        "after": {
            "status": "working",
            "error_code": "none",
            "message": "Microphone is working correctly."
        }
    },

    "MIC-006": {
        "tool": "mic",
        "before": {
            "status": "working",
            "error_code": "none",
            "message": "Microphone is working correctly."
        },
        "after": {
            "status": "working",
            "error_code": "none",
            "message": "Microphone is working correctly."
        }
    },

    "CAM-001": {
        "tool": "camera",
        "before": {
            "status": "blocked",
            "error_code": "permission_denied",
            "message": "Camera permission is denied."
        },
        "after": {
            "status": "working",
            "error_code": "none",
            "message": "Camera is working correctly after the fix."
        }
    },

    "SPK-001": {
        "tool": "speaker",
        "before": {
            "status": "blocked",
            "error_code": "permission_denied",
            "message": "Speaker access is blocked."
        },
        "after": {
            "status": "working",
            "error_code": "none",
            "message": "Speaker is working correctly after the fix."
        }
    },

    "CON-001": {
        "tool": "connection",
        "before": {
            "status": "unstable",
            "error_code": "none",
            "message": "Network connection is unstable."
        },
        "after": {
            "status": "unstable",
            "error_code": "none",
            "message": "Network connection is unstable."
        }
    }
}


# Store the currently selected scenario
current_scenario = "MIC-007"

# Track whether an approved fix has been applied
fix_applied = False


def set_scenario(scenario_id):
    # Change the active scenario
    global current_scenario, fix_applied

    if scenario_id not in SCENARIOS:
        return False

    current_scenario = scenario_id
    fix_applied = False

    return True


def get_current_scenario():
    # Return the currently selected scenario
    return current_scenario


def get_tool_result(tool):
    # Return the diagnostic result for the active scenario
    scenario = SCENARIOS[current_scenario]

    if scenario["tool"] != tool:
        return {
            "status": "error",
            "error_code": "tool_error",
            "message": f"Scenario {current_scenario} does not belong to {tool}."
        }

    # After an approved fix, return the scenario's after state
    if fix_applied:
        return scenario["after"]

    # Before a fix, return the scenario's initial state
    return scenario["before"]


def apply_fix(tool):
    # Mark the approved fix as applied for the active scenario
    global fix_applied

    scenario = SCENARIOS[current_scenario]

    if scenario["tool"] == tool:
        fix_applied = True
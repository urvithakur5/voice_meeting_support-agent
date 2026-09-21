def fix_microphone():
    return {
        "action": "unmute_microphone",
        "success": True,
        "message": "Microphone has been unmuted."
    }


def fix_camera():
    return {
        "action": "restart_camera",
        "success": True,
        "message": "Camera has been restarted."
    }


def fix_speaker():
    return {
        "action": "restart_speaker",
        "success": True,
        "message": "Speaker has been restarted."
    }


def check_approval(approved):
    if approved:
        return {
            "approved": True,
            "message": "User approved the action."
        }

    return {
        "approved": False,
        "message": "User did not approve the action."
    }
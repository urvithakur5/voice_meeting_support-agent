def fix_microphone():
    # Unmute the microphone
    return {
        "action": "unmute_microphone",
        "success": True,
        "message": "Microphone has been unmuted."
    }


def fix_camera():
    # Restart the camera
    return {
        "action": "restart_camera",
        "success": True,
        "message": "Camera has been restarted."
    }


def fix_speaker():
    # Restart the speaker
    return {
        "action": "restart_speaker",
        "success": True,
        "message": "Speaker has been restarted."
    }


def check_approval(approved):
    # Check whether the user approved the action
    if approved:
        return {
            "approved": True,
            "message": "User approved the action."
        }

    return {
        "approved": False,
        "message": "User did not approve the action."
    }
from services.scenario import apply_fix


def fix_microphone():
    # Apply the approved microphone fix
    apply_fix("mic")

    return {
        "action": "unmute_microphone",
        "success": True,
        "message": "Microphone fix has been applied."
    }


def fix_camera():
    # Apply the approved camera fix
    apply_fix("camera")

    return {
        "action": "restart_camera",
        "success": True,
        "message": "Camera fix has been applied."
    }


def fix_speaker():
    # Apply the approved speaker fix
    apply_fix("speaker")

    return {
        "action": "restart_speaker",
        "success": True,
        "message": "Speaker fix has been applied."
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
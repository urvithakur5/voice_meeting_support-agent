def check_mic():
    return {
        "tool": "check_mic",
        "status": "failure",
        "device": "Default Microphone",
        "device_connected": True,
        "permission": True,
        "muted": True,
        "message": "Microphone is connected but muted."
    }
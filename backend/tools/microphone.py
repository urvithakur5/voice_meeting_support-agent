def check_mic():
    # Return microphone diagnostic result
    return {
        "tool": "check_mic",
        "status": "failure",
        "device": "Default Microphone",
        "device_connected": True,
        "permission": True,
        "muted": True,

        # Explain the microphone issue
        "message": "Microphone is connected but muted."
    }
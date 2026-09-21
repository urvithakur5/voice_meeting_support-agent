def check_speaker():
    # Return speaker diagnostic result
    return {
        "tool": "check_speaker",
        "status": "failure",
        "device": "Default Speaker",
        "device_connected": True,
        "working": False,

        # Explain the speaker issue
        "message": "Speaker is connected but no audio output was detected."
    }
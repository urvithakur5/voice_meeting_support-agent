def check_camera():
    # Return camera diagnostic result
    return {
        "tool": "check_camera",
        "status": "failure",
        "device": "Default Camera",
        "device_connected": True,
        "permission": True,
        "working": False,

        # Explain the camera issue
        "message": "Camera is connected but not working."
    }
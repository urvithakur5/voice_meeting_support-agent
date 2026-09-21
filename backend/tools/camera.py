from services.scenario import get_tool_result


def check_camera():
    # Return the current camera diagnostic result
    return get_tool_result("camera")
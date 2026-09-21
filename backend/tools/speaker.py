from services.scenario import get_tool_result


def check_speaker():
    # Return the current speaker diagnostic result
    return get_tool_result("speaker")
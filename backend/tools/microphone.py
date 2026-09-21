from services.scenario import get_tool_result


def check_mic():
    # Return the current microphone diagnostic result
    return get_tool_result("mic")
from services.scenario import get_tool_result


def check_connection():
    # Return the current network connection diagnostic result
    return get_tool_result("connection")
from datetime import datetime


def log_event(event, details):
    # Return event log with timestamp and details
    return {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "details": details
    }
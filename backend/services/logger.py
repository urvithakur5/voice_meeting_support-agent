from datetime import datetime


def log_event(event, details):
    return {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "details": details
    }
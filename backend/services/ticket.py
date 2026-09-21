def create_ticket(issue, diagnostics, actions, result):
    # Return ticket details for the IT Helpdesk
    return {
        "ticket_id": "INC-1001",
        "issue": issue,
        "diagnostics": diagnostics,
        "actions_taken": actions,
        "result": result,
        "route": "IT Helpdesk",
        "status": "Open"
    }
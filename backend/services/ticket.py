def create_ticket(issue, diagnostics, actions, result):
    return {
        "ticket_id": "INC-1001",
        "issue": issue,
        "diagnostics": diagnostics,
        "actions_taken": actions,
        "result": result,
        "route": "IT Helpdesk",
        "status": "Open"
    }
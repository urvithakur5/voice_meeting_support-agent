# Tool Contract

## check_mic

### Input

{
  "device": "default"
}

### Output

{
  "status": "working | blocked | missing | error",
  "message": "string"
}

### Possible Errors

- device_not_found
- permission_denied
- timeout
- tool_error

### Read/Write

Read system microphone state.

### Approval Required

No for diagnosis.
Yes if an action changes system settings.

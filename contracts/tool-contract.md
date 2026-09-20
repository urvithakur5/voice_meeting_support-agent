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


## Status values per tool

| Tool | Status values |
|---|---|
| check_mic | working, blocked, missing, error |
| check_camera | working, blocked, missing, error |
| check_speaker | working, blocked, missing, error |
| check_connection | stable, unstable, disconnected, error |

## Status vs error code

Status is the main result. Error code explains why.

| Status | Error code |
|---|---|
| working / stable | none |
| blocked | permission_denied |
| missing | device_not_found |
| unstable / disconnected | none |
| error | timeout or tool_error |

## Standard output format

```json
{ "status": "blocked", "error_code": "permission_denied", "message": "string" }
```

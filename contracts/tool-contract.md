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


## Extended tool status vocabulary (new diagnostic areas)

New-area tools (check_wifi, check_vpn, check_bluetooth_audio, check_display,
check_dock, check_browser_state, check_application_state, check_performance)
use the _common.py area_result format:

```json
{
  "tool": "check_wifi",
  "title": "Wi-Fi diagnostic",
  "status": "ok | warning | failed | unknown",
  "reason": "string — truthful, observable description",
  "details": "string — same as reason",
  "observations": [
    { "label": "Wi-Fi adapter: Intel Wi-Fi 6", "state": "ok" },
    { "label": "Signal strength: 72%", "state": "ok" }
  ],
  "observed_at": "ISO-8601 timestamp"
}
```

### Status vocabulary for new tools

| Status  | Meaning                                                  |
|---------|----------------------------------------------------------|
| ok      | All observed facts are healthy                           |
| warning | At least one observed fact is suboptimal but not failed  |
| failed  | A definite failure was observed                          |
| unknown | The property could not be reliably observed              |

### UNKNOWN rule (critical)

The system must never convert "could not determine" into "failed" or "ok".
If a property cannot be reliably read, status MUST be "unknown" with a
truthful reason. This applies to every new and existing tool.

### run_test extended test_type values

microphone | speaker | camera | connectivity |
wifi | vpn | bluetooth_audio | display | performance | application | browser

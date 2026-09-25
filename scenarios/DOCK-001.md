# DOCK-001 — Dock Stopped Detecting Monitor

## User Input
"My dock stopped detecting my monitor."

## Expected Intent
dock_display_failure

## Expected Tool
check_dock, check_display

## Expected Result
```json
{
  "status": "ok|unknown",
  "dock_detected": true,
  "usb_hub_count": 2,
  "monitor_count": 1
}
```

## Expected Behavior
Agent runs check_dock to observe USB hub count and dock presence.
Agent runs check_display to observe how many monitors Windows sees.
Agent reports actual evidence before suggesting action.
If dock is detected but monitor_count is 1, agent guides reconnect/cable check.

## Final State
diagnosing → action_required → verifying → resolved or escalated

## Failure Condition
Agent claims dock is faulty without any evidence from check_dock.

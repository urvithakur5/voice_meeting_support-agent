# DISP-001 — Second Monitor Not Showing

## User Input
"My second monitor isn't showing."

## Expected Intent
external_display_missing

## Expected Tool
check_display

## Expected Result
```json
{
  "status": "ok|unknown|warning",
  "display_adapter_count": 1,
  "monitor_count": 1,
  "adapters": [{"name": "<observed>", "resolution": "<observed>"}]
}
```

## Expected Behavior
Agent runs check_display.
Reports how many monitors Windows can see (actual value from tool).
If monitor_count is 1 and employee expects 2, agent explains Windows only detects one.
Agent guides employee to use Windows+P and check physical cable.

## Final State
diagnosing → action_required → verifying → resolved or escalated

## Failure Condition
Agent tells employee to "restart Windows" without first reporting what check_display found.
Agent invents monitor count.

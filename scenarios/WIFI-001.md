# WIFI-001 — Wi-Fi Keeps Disconnecting

## User Input
"My Wi-Fi keeps disconnecting."

## Expected Intent
wifi_instability

## Expected Tool
check_wifi

## Expected Result
```json
{
  "status": "warning",
  "connected": true,
  "ssid": "<observed_ssid>",
  "signal_strength": "<observed_value>",
  "internet": true
}
```

## Expected Behavior
Agent runs check_wifi immediately.
Agent reads signal_strength from the result and describes what was observed.
If signal < 40%, agent explains the signal is weak.
Agent does NOT claim a fix worked without running verification.

## Final State
diagnosing → action_required (move closer to AP or reconnect) → verifying → resolved or escalated

## Failure Condition
Agent invents a signal strength value or claims "Wi-Fi is fine" when check_wifi returned a warning.

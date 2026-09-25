# PERF-001 — Laptop Extremely Slow

## User Input
"My laptop has become extremely slow."

## Expected Intent
performance_degradation

## Expected Tool
check_performance

## Expected Result
```json
{
  "status": "warning",
  "cpu_percent": "<observed>",
  "memory_percent": "<observed>",
  "disk_free_percent": "<observed>",
  "uptime": "<observed>"
}
```

## Expected Behavior
Agent runs check_performance immediately.
Reports the actual CPU, memory, and disk values from the tool.
Does NOT claim "high CPU is caused by X" without further evidence.
If disk_free_percent < 10%, mentions this as a likely contributing factor.
If uptime > 7 days, suggests a restart.

## Final State
diagnosing → action_required → verifying → resolved or escalated

## Failure Condition
Agent diagnoses root cause from a single metric without asking about specific applications.
Agent invents CPU or memory values.

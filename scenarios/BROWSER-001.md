# BROWSER-001 — Company Website Won't Open in Browser

## User Input
"The company website won't open in my browser."

## Expected Intent
browser_site_unreachable

## Expected Tool
check_browser_state

## Expected Result
```json
{
  "status": "ok|warning",
  "running_browsers": [{"name": "Microsoft Edge"}],
  "network_reachable": false,
  "probe_host": "<target>"
}
```

## Expected Behavior
Agent runs check_browser_state (with target_host if hostname is known).
Distinguishes between: browser not running, network unreachable, or site-specific issue.
If network_reachable is false, agent also checks connectivity.
Does NOT declare the website is broken without a specific reachability test.

## Final State
diagnosing → action_required → verifying → resolved or escalated

## Failure Condition
Agent claims "website is down" without running check_browser_state.
Agent reads browsing history or any private data.

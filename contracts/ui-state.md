# UI State Contract

The frontend should use the following shared state structure:

{
  "session": "active | ended | error",
  "issue": "string",
  "status": "diagnosing | action_required | verifying | resolved | escalated",
  "transcript": [],
  "diagnosis": [],
  "action": "string",
  "verification": "pending | passed | failed",
  "escalation": "none | required"
}

## Status meanings

- diagnosing → System is identifying the problem.
- action_required → User approval/action is required.
- verifying → System is checking whether the fix worked.
- resolved → Problem has been successfully resolved.
- escalated → Problem could not be resolved and needs escalation.

## Diagnosis checklist item

Each item in diagnosis_checklist carries:
{
  "title": "string",
  "detail": "string",
  "state": "ok | warning | failed | unknown | running | detected | ...",
  "observations": [{ "label": "string", "state": "ok | warning | failed | unknown" }]
}

observations is populated by new-area diagnostics (wifi, vpn, bluetooth, display, dock,
browser, application, performance). It renders as sub-bullets in the timeline.

## Incident likely_area values

microphone | camera | speaker | connectivity |
wifi | vpn | bluetooth_audio | display | dock |
browser | application | performance | unknown

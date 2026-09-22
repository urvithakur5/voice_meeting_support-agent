# Test Matrix

This matrix tracks the scenarios used to evaluate the voice meeting support agent.
| ID | Scenario | Expected Tool | Expected Result | Expected Final State | Status |
|---|---|---|---|---|---|
| MIC-001 | Mic working, issue elsewhere | check_mic | working | diagnosing | ☑ |
| MIC-002 | Microphone permission blocked | check_mic | blocked | action_required | ☑ |
| MIC-003 | Microphone diagnostic timeout | check_mic | error (timeout) | escalated | ☑ |
| MIC-004 | User refuses approval | check_mic | blocked | action_required | ☑ |
| MIC-005 | Vague Teams problem | None initially | not applicable | diagnosing |  |
| MIC-006 | Repeated microphone information | check_mic | working | diagnosing | ☑ |
| MIC-007 | Approved fix, verified | check_mic (x2) | blocked, then working | resolved | ☑ |
| MIC-008 | Approved fix, verification fails | check_mic (x2) | blocked, then blocked | escalated | ☑ |
| CAM-001 | Camera problem | check_camera | blocked | action_required | ☑ |
| SPK-001 | Speaker problem | check_speaker | blocked | action_required | ☑ |
| CON-001 | Connection problem | check_connection | unstable | diagnosing | ☑ |

## Failure Cases

The system should also be tested for:

- Tool timeout
- Tool error
- Permission denial
- User refusal
- Vague user input
- Repeated information
- Voice failure
- Backend failure
- Incorrect tool selection
- Incorrect final state

## End-to-End Checks

- [ ] Voice session starts
- [ ] User speech becomes transcript
- [ ] Agent receives transcript
- [ ] Agent selects correct diagnostic tool
- [ ] Tool response reaches agent
- [ ] Agent response reaches frontend
- [ ] Approval flow works
- [ ] Verification flow works
- [ ] Escalation flow works
- [ ] Voice failure fallback works

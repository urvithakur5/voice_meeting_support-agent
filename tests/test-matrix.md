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

## Extended Diagnostic Areas — Verified on Windows Machine (2026-09-24)

| ID | Scenario | Tool | Result on this machine | Verified |
|---|---|---|---|---|
| WIFI-001 | Wi-Fi keeps disconnecting | check_wifi | ok — SSID "Saini", signal 84%, latency 13.2ms | ✅ |
| VPN-001 | VPN won't connect | check_vpn | warning — ProtonVPN TAP adapter disconnected | ✅ |
| BT-001 | Bluetooth headset won't connect | check_bluetooth_audio | ok — "Headphones (Infinity SPIN 150)" active | ✅ |
| BT-002 | Headphones connected, no sound | check_bluetooth_audio | ok — endpoint active (same device) | ✅ |
| DISP-001 | Second monitor not showing | check_display | ok — 2 adapters, 3 monitors (1 integrated active) | ✅ |
| DOCK-001 | Dock stopped detecting monitor | check_dock | ok — 1 USB hub, 1 monitor, 17 HID devices | ✅ |
| BROWSER-001 | Company website won't open | check_browser_state | ok — Chrome + Edge running | ✅ |
| BROWSER-002 | Browser running, page won't load | check_browser_state(host) | ok — google.com reachable 31.4ms | ✅ |
| APP-001 | Application keeps freezing | check_application_state | running — msedge detected | ✅ |
| APP-002 | Application won't start | check_application_state | not_running — notepad not running | ✅ |
| PERF-001 | Laptop extremely slow | check_performance | warning — CPU 8%, memory 94.2%, disk 20.2% | ✅ |
| PERF-002 | Running out of disk space | check_performance | ok — 84 GB free (20.2%) | ✅ |

## Extended run_test Results

| test_type | result | notes |
|---|---|---|
| wifi_test | pass | status=ok |
| vpn_test | unknown | status=warning (disconnected adapter) — correct |
| bluetooth_audio_test | pass | status=ok |
| display_test | pass | status=ok |
| performance_test | unknown | status=warning (memory 94.2%) — correct |
| browser_test | pass | status=ok |

## Diagnostics returning unknown/warning (truthful)

- **check_vpn**: returns `warning` when VPN adapter present but disconnected. Does NOT claim authentication state.
- **check_performance**: returns `warning` when memory ≥ 80%. Does NOT claim a root cause.
- **check_display** monitor resolutions: returns `unknown` for monitors where WMI cannot read resolution — truthful.
- **check_dock**: returns `dock_model: unknown` when no named dock recognised — truthful.
- **check_application_state** version: returns `unknown` when exe path not found via `where` — truthful.

## New incident schema — likely_area values confirmed working
microphone | camera | speaker | connectivity | wifi | vpn | bluetooth_audio | display | dock | browser | application | performance

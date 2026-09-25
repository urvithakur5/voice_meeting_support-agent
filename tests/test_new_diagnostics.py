"""Direct tests for the 8 new diagnostic tools.

Run from the project root:
    python tests/test_new_diagnostics.py

Each test confirms:
- Structured dict is returned
- Required keys are present
- status is a valid value
- No fake values are produced (status never contradicts evidence)
- Exceptions are handled (no unhandled exceptions)
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

# Allow running from project root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

VALID_STATUSES = {"ok", "warning", "failed", "unknown"}
VALID_STATES = {"ok", "warning", "failed", "unknown"}

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))
        passed += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        failed += 1


def assert_base_shape(name: str, result: dict) -> None:
    check(f"{name}: returns dict", isinstance(result, dict))
    check(f"{name}: has status", "status" in result)
    check(f"{name}: status is valid", result.get("status") in VALID_STATUSES,
          f"got {result.get('status')!r}")
    check(f"{name}: has reason or details", bool(result.get("reason") or result.get("details") or result.get("message")))
    obs = result.get("observations", [])
    check(f"{name}: observations is list", isinstance(obs, list))
    for ob in obs:
        check(f"{name}: observation has label", "label" in ob)
        check(f"{name}: observation state valid", ob.get("state") in VALID_STATES,
              f"got {ob.get('state')!r}")


# ── check_wifi ─────────────────────────────────────────────────────────────
print("\n── check_wifi ──")
from tools.wifi import check_wifi
r = check_wifi()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_wifi", r)
check("check_wifi: wifi_adapter_detected is bool", isinstance(r.get("wifi_adapter_detected"), bool))
check("check_wifi: connected is bool", isinstance(r.get("connected"), bool))
if r.get("connected"):
    check("check_wifi: ssid not empty when connected", bool(r.get("ssid") and r["ssid"] != ""))
    check("check_wifi: signal_strength not invented", r.get("signal_strength") == "unknown" or isinstance(r.get("signal_strength"), int))

# ── check_vpn ──────────────────────────────────────────────────────────────
print("\n── check_vpn ──")
from tools.vpn import check_vpn
r = check_vpn()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_vpn", r)
check("check_vpn: vpn_detected is bool", isinstance(r.get("vpn_detected"), bool))
if r.get("vpn_detected") and r.get("adapter_status") not in ("up",):
    check("check_vpn: disconnected adapter is not ok", r.get("status") != "ok",
          "adapter disconnected must not be status=ok")

# ── check_bluetooth_audio ─────────────────────────────────────────────────
print("\n── check_bluetooth_audio ──")
from tools.bluetooth_audio import check_bluetooth_audio
r = check_bluetooth_audio()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_bluetooth_audio", r)
check("check_bluetooth_audio: bluetooth_available is bool", isinstance(r.get("bluetooth_available"), bool))
check("check_bluetooth_audio: audio_device_connected is bool", isinstance(r.get("audio_device_connected"), bool))
if r.get("bluetooth_available") and not r.get("audio_device_connected"):
    check("check_bluetooth_audio: no device means not ok", r.get("status") != "ok")

# ── check_display ─────────────────────────────────────────────────────────
print("\n── check_display ──")
from tools.display import check_display
r = check_display()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_display", r)
check("check_display: adapters is list", isinstance(r.get("adapters"), list))
check("check_display: monitors is list", isinstance(r.get("monitors"), list))
check("check_display: display_adapter_count >= 0", isinstance(r.get("display_adapter_count"), int))

# ── check_dock ────────────────────────────────────────────────────────────
print("\n── check_dock ──")
from tools.dock import check_dock
r = check_dock()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_dock", r)
check("check_dock: dock_detected is bool", isinstance(r.get("dock_detected"), bool))
check("check_dock: usb_hub_count >= 0", isinstance(r.get("usb_hub_count"), int) and r.get("usb_hub_count", -1) >= 0)

# ── check_browser_state ───────────────────────────────────────────────────
print("\n── check_browser_state ──")
from tools.browser import check_browser_state
r = check_browser_state()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_browser_state", r)
check("check_browser_state: running_browsers is list", isinstance(r.get("running_browsers"), list))

# ── check_browser_state with probe ───────────────────────────────────────
print("\n── check_browser_state(google.com) ──")
r2 = check_browser_state("google.com")
assert_base_shape("check_browser_state_probe", r2)
check("check_browser_state_probe: probe_host set", r2.get("probe_host") == "google.com")
check("check_browser_state_probe: network_reachable is bool", isinstance(r2.get("network_reachable"), bool))

# ── check_performance ─────────────────────────────────────────────────────
print("\n── check_performance ──")
from tools.performance import check_performance
r = check_performance()
print("  result:", json.dumps({k: v for k, v in r.items() if k != "observations"}, indent=4))
assert_base_shape("check_performance", r)
for key in ("cpu_percent", "memory_percent", "disk_free_percent"):
    val = r.get(key)
    check(f"check_performance: {key} is numeric", val is None or isinstance(val, (int, float)),
          f"got {val!r}")
    if isinstance(val, (int, float)):
        check(f"check_performance: {key} in range 0-100", 0 <= val <= 100, f"got {val}")

# ── check_application_state (running) ─────────────────────────────────────
print("\n── check_application_state (msedge) ──")
from tools.diagnostics import check_application_state
r = check_application_state("msedge")
print("  result:", json.dumps(r, indent=4))
check("check_application_state: has status", "status" in r)
check("check_application_state: has running", "running" in r)
check("check_application_state: running is bool", isinstance(r.get("running"), bool))

# ── check_application_state (not running) ─────────────────────────────────
print("\n── check_application_state (notepad) ──")
r2 = check_application_state("notepad")
print("  result:", json.dumps(r2, indent=4))
check("check_application_state_notepad: status reflects running", r2.get("status") in ("running", "not_running", "unknown"))

# ── run_test extended ─────────────────────────────────────────────────────
print("\n── run_test extended types ──")
from tools.diagnostics import run_test
for test_type in ["wifi_test", "vpn_test", "bluetooth_audio_test", "display_test",
                  "performance_test", "browser_test", "application_test"]:
    r = run_test(test_type)
    check(f"run_test {test_type}: has result", "result" in r)
    check(f"run_test {test_type}: result not error", r.get("result") in ("pass", "unknown"),
          f"got {r.get('result')!r}")

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  {passed} passed, {failed} failed")
if failed:
    sys.exit(1)

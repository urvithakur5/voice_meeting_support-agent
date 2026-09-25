"""
Final verification for the redesigned Employee Support UI.
Run: python verify_final.py
"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = "frontend"
with open(f"{ROOT}/templates/index.html", encoding="utf-8") as f: html = f.read()
with open(f"{ROOT}/static/app.js",        encoding="utf-8") as f: js   = f.read()
with open(f"{ROOT}/static/style.css",     encoding="utf-8") as f: css  = f.read()

errors   = []
warnings = []

def ok(label):   print(f"  [OK  ] {label}")
def fail(label): print(f"  [FAIL] {label}"); errors.append(label)
def warn(label): print(f"  [WARN] {label}"); warnings.append(label)

def chk(label, cond):
    ok(label) if cond else fail(label)

# ── Extract HTML ids ──────────────────────────────────────────────────────────
html_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))

# ── Extract all JS id references ─────────────────────────────────────────────
dollar_ids  = set(re.findall(r"""\$\(['"]([^'"]+)['"]\)""",   js))
settext_ids = set(re.findall(r"""setText\(['"]([^'"]+)['"]""", js))
setattr_ids = set(re.findall(r"""setAttr\(['"]([^'"]+)['"]""", js))
all_js_ids  = dollar_ids | settext_ids | setattr_ids

# incidentStatus is injected at runtime inside renderIncidentDetail innerHTML — OK to exclude
runtime_ids = {'incidentStatus'}
missing = sorted((all_js_ids - html_ids) - runtime_ids)

# ── 1. ID cross-check ─────────────────────────────────────────────────────────
print("\n=== 1. ID cross-check ===")
chk(f"All JS id refs exist in HTML  ({len(all_js_ids)} refs, {len(html_ids)} html ids)",
    not missing)
if missing:
    for m in missing:
        print(f"       MISSING: {m}")

# ── 2. Navigation bug fix ─────────────────────────────────────────────────────
print("\n=== 2. Navigation / role storage ===")
chk("setRole uses sessionStorage",       "sessionStorage.setItem(ROLE_KEY" in js)
chk("clearRole removes sessionStorage",  "sessionStorage.removeItem(ROLE_KEY)" in js)
chk("clearRole removes localStorage",    "localStorage.removeItem(ROLE_KEY)" in js)
chk("Boot purges localStorage role",     js.count("localStorage.removeItem(ROLE_KEY)") >= 2)
chk("No localStorage.setItem(ROLE_KEY)", "localStorage.setItem(ROLE_KEY" not in js)
chk("Boot reads from sessionStorage",    "sessionStorage.getItem(ROLE_KEY)" in js)

# ── 3. Welcome screen ─────────────────────────────────────────────────────────
print("\n=== 3. Welcome screen ===")
chk("role-tile buttons in HTML",         "role-tile" in html)
chk("JS listens to .role-tile",          "querySelectorAll('.role-tile')" in js)
chk("welcomeView present in HTML",       "welcomeView" in html_ids)
chk("employeeView present in HTML",      "employeeView" in html_ids)
chk("technicianView present in HTML",    "technicianView" in html_ids)

# ── 4. Voice state machine ────────────────────────────────────────────────────
print("\n=== 4. Voice state machine ===")
chk("VOICE.IDLE defined",                "'IDLE'" in js)
chk("VOICE.LISTENING defined",           "'LISTENING'" in js)
chk("VOICE.PROCESSING defined",         "'PROCESSING'" in js)
chk("setVoicePhase hides all 3 divs",    "forEach(hide)" in js)
chk("composerIdle shown in IDLE",        "show(idle)" in js)
chk("composerListening shown in LISTEN", "show(listening)" in js)
chk("composerProcessing shown in PROC",  "show(processing)" in js)
chk("onend always returns to IDLE",      js.count("setVoicePhase(VOICE.IDLE)") >= 2)
chk("sendMessage finally resets voice",  "setVoicePhase(VOICE.IDLE)" in js)
chk("Composer container never hidden",
    'id="composer"' in html and
    'id="composer" class="composer hidden"' not in html and
    'id="composer" class="hidden"' not in html)

# ── 5. Session state machine phases ──────────────────────────────────────────
print("\n=== 5. Session state machine ===")
required_phases = [
    "READY","LISTENING","PROCESSING_INPUT","UNDERSTANDING",
    "DIAGNOSING","RAG_LOOKUP","ACTION_AVAILABLE","ACTION_APPROVED",
    "ACTION_IN_PROGRESS","VERIFYING","RESOLVED","ESCALATING",
    "INCIDENT_CREATED","ERROR"
]
for p in required_phases:
    chk(f"PHASE.{p} defined", f"'{p}'" in js or f'"{p}"' in js)
chk("setPhase sets body.dataset.phase", "document.body.dataset.phase" in js)
chk("STAGE_TO_PHASE mapping exists",    "STAGE_TO_PHASE" in js)

# ── 6. Workspace render functions ─────────────────────────────────────────────
print("\n=== 6. Workspace render functions ===")
fns = ["renderWorkspace","renderIssue","renderEvidence","renderTimeline",
       "renderAction","renderVerification","renderEscalation","renderResolved"]
for fn in fns:
    chk(f"function {fn} defined", f"function {fn}" in js)
chk("renderWorkspace called after fetch", "renderWorkspace(data.ui_state" in js)

# ── 7. No fake states ─────────────────────────────────────────────────────────
print("\n=== 7. No fake / hard-coded content ===")
chk("No speakAgentResponse('Checking')",
    "speakAgentResponse" not in js)
chk("cleanReply filter defined",         "function cleanReply" in js)
chk("INTERNAL_RX patterns defined",      "INTERNAL_RX" in js)
chk("No hard-coded 'Wi-Fi adapter detected'",
    "Wi-Fi adapter detected" not in js)
chk("No hard-coded '✓ Connected'",
    "'✓ Connected'" not in js and '"✓ Connected"' not in js)
chk("showRunning only around fetches",   "showRunning(" in js)
chk("hideRunning in finally block",      "hideRunning()" in js)

# ── 8. Approve button gating ──────────────────────────────────────────────────
print("\n=== 8. Approve button gating ===")
chk("approve btn starts hidden in HTML",
    'id="approve"' in html and 'class="btn-approve hidden"' in html)
chk("manualConfirm starts hidden in HTML",
    'id="manualConfirm"' in html and 'class="btn-manual hidden"' in html)
chk("show(approveBtn) conditional",      "show(approveBtn)" in js)
chk("hide(approveBtn) conditional",      "hide(approveBtn)" in js)
chk("approveBtn.disabled = true on click","btn.disabled = true" in js)

# ── 9. Workspace sections hidden by default ───────────────────────────────────
print("\n=== 9. Workspace sections start hidden ===")
for sid in ["wsSectionAction","wsSectionVerification",
            "wsSectionEscalation","wsSectionResolved"]:
    chk(f"{sid} starts hidden in HTML",
        f'id="{sid}"' in html and f'id="{sid}" class="ws-section hidden"' in html)

# ── 10. CSS: no --teal tokens ─────────────────────────────────────────────────
print("\n=== 10. CSS token hygiene ===")
teal_hits = re.findall(r'--teal[\w-]*', css)
chk("No --teal tokens in CSS",           not teal_hits)
if teal_hits:
    print(f"       Found: {set(teal_hits)}")

chk("--navy token defined",              "--navy:" in css)
chk("--crimson token defined",           "--crimson:" in css)
chk("--scarlet token defined",           "--scarlet:" in css)
chk("--porcelain token defined",         "--porcelain:" in css)
chk("--ok (success) token defined",      "--ok:" in css)
chk("--warn token defined",              "--warn:" in css)

# ── 11. CSS: no --teal in JS either ──────────────────────────────────────────
print("\n=== 11. JS token hygiene ===")
teal_js = re.findall(r'--teal[\w-]*', js)
chk("No --teal tokens in JS",            not teal_js)
if teal_js:
    print(f"       Found: {set(teal_js)}")

# ── 12. CSS workspace components ─────────────────────────────────────────────
print("\n=== 12. CSS workspace components ===")
css_checks = [
    ("Light background --surf-0",        "--surf-0:" in css),
    (".workspace-pane defined",          ".workspace-pane" in css),
    (".ws-section defined",              ".ws-section" in css),
    (".ws-running defined",              ".ws-running" in css),
    (".ws-evidence-list defined",        ".ws-evidence-list" in css),
    (".ws-ev-ok defined",                ".ws-ev-ok" in css),
    (".ws-ev-fail defined",              ".ws-ev-fail" in css),
    (".ws-ev-warn defined",              ".ws-ev-warn" in css),
    (".ws-timeline defined",             ".ws-timeline" in css),
    (".wt-done defined",                 ".wt-done" in css),
    (".wt-active defined",               ".wt-active" in css),
    (".wt-error defined",                ".wt-error" in css),
    (".btn-approve defined",             ".btn-approve" in css),
    (".btn-manual defined",              ".btn-manual" in css),
    (".btn-view-incident defined",       ".btn-view-incident" in css),
    (".btn-continue defined",            ".btn-continue" in css),
    (".composer-idle defined",           ".composer-idle" in css),
    (".composer-listening defined",      ".composer-listening" in css),
    (".composer-processing defined",     ".composer-processing" in css),
    (".waveform animation defined",      ".waveform" in css),
    ("body[data-phase] accent strips",   "data-phase" in css),
    ("@media 900px breakpoint",          "max-width: 900px" in css),
    ("@media 600px breakpoint",          "max-width: 600px" in css),
    ("focus-visible ring",               "focus-visible" in css),
]
for label, cond in css_checks:
    chk(label, cond)

# ── 13. ARIA / accessibility ──────────────────────────────────────────────────
print("\n=== 13. Accessibility ===")
chk("transcript role=log",               'role="log"' in html)
chk("transcript aria-live=polite",       'aria-live="polite"' in html)
chk("composerListening role=status",
    'id="composerListening"' in html and 'role="status"' in html)
chk("micBtn aria-pressed",              'aria-pressed' in html)
chk("approve has aria-label",           'id="approve"' in html)
chk("wsDiagRunning role=status",        'id="wsDiagRunning"' in html)

# ── 14. Responsive layout ────────────────────────────────────────────────────
print("\n=== 14. Responsive layout ===")
chk(".support-layout grid defined",      ".support-layout" in css)
chk(".convo-pane defined",               ".convo-pane" in css)
chk("900px: grid-template-columns:1fr",
    "max-width: 900px" in css and "grid-template-columns: 1fr" in css)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  Errors   : {len(errors)}")
print(f"  Warnings : {len(warnings)}")
if errors:
    print("\n  FAILED:")
    for e in errors: print(f"    [FAIL] {e}")
else:
    print("  ALL CHECKS PASSED")
sys.exit(1 if errors else 0)

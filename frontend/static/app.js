/**
 * AI IT Incident Triage Agent — Employee Support UI
 *
 * State machine phases:
 *   READY → UNDERSTANDING → DIAGNOSING → ACTION_AVAILABLE
 *   → ACTION_IN_PROGRESS → VERIFYING → RESOLVED → ESCALATING → ERROR
 *
 * Voice input states (independent of session phase):
 *   IDLE → LISTENING → PROCESSING → IDLE  (never collapses the composer)
 *
 * Rule: UI elements are driven by explicit session/tool state only.
 *       No fake diagnostic results. No "Checking…" injected into chat.
 */

'use strict';

// ─── Constants ───────────────────────────────────────────────────────────────

const AGENT_API_URL = 'http://localhost:3002/agent/message';
const BACKEND_URL = 'http://localhost:5673';
const ROLE_STORAGE_KEY = 'ai_it_support_role';

// ─── Session identity ─────────────────────────────────────────────────────────

const sessionId = sessionStorage.getItem('meetassist-session') || crypto.randomUUID();
sessionStorage.setItem('meetassist-session', sessionId);

// ─── DOM helpers ──────────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);
const show = (el) => el && el.classList.remove('hidden');
const hide = (el) => el && el.classList.add('hidden');
const setText = (id, text) => { const el = $(id); if (el) el.textContent = text; };
const setAttr = (id, attr, value) => { const el = $(id); if (el) el.setAttribute(attr, value); };

// ─── Session phase state machine ──────────────────────────────────────────────

const PHASE = Object.freeze({
  READY: 'READY',
  UNDERSTANDING: 'UNDERSTANDING',
  DIAGNOSING: 'DIAGNOSING',
  ACTION_AVAILABLE: 'ACTION_AVAILABLE',
  ACTION_IN_PROGRESS: 'ACTION_IN_PROGRESS',
  VERIFYING: 'VERIFYING',
  RESOLVED: 'RESOLVED',
  ESCALATING: 'ESCALATING',
  ERROR: 'ERROR',
});

let sessionPhase = PHASE.READY;

// ─── Runtime flags ────────────────────────────────────────────────────────────

let isSubmitting = false;   // true while fetch is in flight
let finalVoiceText = '';
let silenceTimer = null;
let liveTranscriptRow = null;
let recognition = null;

// ─── Utility: human-friendly tool labels ─────────────────────────────────────

const TOOL_LABELS = {
  check_mic:               'Checking microphone…',
  check_camera:            'Checking camera…',
  check_speaker:           'Checking audio output…',
  check_connectivity:      'Checking internet connection…',
  check_wifi:              'Checking Wi-Fi connection…',
  check_vpn:               'Checking VPN connection…',
  check_bluetooth_audio:   'Checking Bluetooth audio devices…',
  check_display:           'Checking display setup…',
  check_dock:              'Checking docking station…',
  check_browser_state:     'Checking browser state…',
  check_application_state: 'Checking application state…',
  check_performance:       'Reviewing system performance…',
  fix_mic:                 'Applying microphone fix…',
  fix_camera:              'Applying camera fix…',
  fix_speaker:             'Applying audio fix…',
  fix_connectivity:        'Applying network fix…',
  fix_display:             'Applying display fix…',
  fix_dock:                'Applying dock fix…',
  escalate_ticket:         'Preparing IT handoff…',
  create_incident:         'Creating incident…',
  execute_action:          'Applying recommended fix…',
};

// Human-readable section titles for each tool when its result block renders
const TOOL_SECTION_TITLES = {
  check_display:           'DISPLAY',
  check_dock:              'DOCK',
  check_mic:               'MICROPHONE',
  check_camera:            'CAMERA',
  check_speaker:           'AUDIO OUTPUT',
  check_connectivity:      'CONNECTIVITY',
  check_wifi:              'WI-FI',
  check_vpn:               'VPN',
  check_bluetooth_audio:   'BLUETOOTH',
  check_browser_state:     'BROWSER',
  check_application_state: 'APPLICATION',
  check_performance:       'PERFORMANCE',
};

const STAGE_LABELS = {
  diagnosing:        'Diagnosing',
  approval_required: 'Action Required',
  acting:            'Applying Fix',
  verifying:         'Verifying',
  resolved:          'Resolved',
  escalated:         'Escalated',
};

function readable(value) {
  return String(value || '').replaceAll('_', ' ');
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]
  ));
}

function formatDate(value) {
  if (!value) return 'Unknown time';
  return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

// ─── Phase → session phase mapping ───────────────────────────────────────────

function phaseFromStage(stage) {
  switch (stage) {
    case 'diagnosing':        return PHASE.DIAGNOSING;
    case 'approval_required': return PHASE.ACTION_AVAILABLE;
    case 'acting':            return PHASE.ACTION_IN_PROGRESS;
    case 'verifying':         return PHASE.VERIFYING;
    case 'resolved':          return PHASE.RESOLVED;
    case 'escalated':         return PHASE.ESCALATING;
    default:                  return PHASE.UNDERSTANDING;
  }
}

// ─── TTS ──────────────────────────────────────────────────────────────────────

function speak(text) {
  const cleaned = String(text || '').trim();
  if (!cleaned || !('speechSynthesis' in window)) return;
  if (/failed to fetch|network error|could not reach/i.test(cleaned)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleaned);
  utterance.rate = 0.96;
  utterance.pitch = 1.02;
  window.speechSynthesis.speak(utterance);
}

// ─── Transcript ───────────────────────────────────────────────────────────────

function addTranscriptRow(role, text) {
  const container = $('transcript');
  if (!container) return;
  const empty = container.querySelector('.transcript-empty');
  if (empty) empty.remove();

  const row = document.createElement('div');
  row.className = `transcript-row transcript-${role}`;

  const label = document.createElement('span');
  label.className = 'transcript-label';
  label.textContent = role === 'user' ? 'YOU' : 'AGENT';

  const bubble = document.createElement('p');
  bubble.className = 'transcript-bubble';
  bubble.textContent = text;

  row.append(label, bubble);
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function updateLiveTranscript(text) {
  const container = $('transcript');
  if (!container) return;
  const empty = container.querySelector('.transcript-empty');
  if (empty) empty.remove();

  if (!liveTranscriptRow) {
    liveTranscriptRow = document.createElement('div');
    liveTranscriptRow.className = 'transcript-row transcript-user transcript-live';
    const label = document.createElement('span');
    label.className = 'transcript-label';
    label.textContent = 'YOU';
    const bubble = document.createElement('p');
    bubble.className = 'transcript-bubble';
    liveTranscriptRow.append(label, bubble);
    container.appendChild(liveTranscriptRow);
  }
  liveTranscriptRow.querySelector('p').textContent = text;
  container.scrollTop = container.scrollHeight;
}

function commitLiveTranscript() {
  // Kept for safety — inline logic in submitVoiceMessage handles the main path.
  if (liveTranscriptRow) {
    liveTranscriptRow.classList.remove('transcript-live');
    liveTranscriptRow = null;
  }
}

// ─── Voice state flags (replaces the VOICE state machine) ────────────────────
// Simple boolean — avoids the race condition caused by the old enum state
// machine calling setVoicePhase(IDLE) from inside sendMessage's finally block
// on EVERY message (text and voice alike).

let isListening = false;   // true while SpeechRecognition is active
let speechEnded  = false;  // set by onspeechend so onend knows to submit
let stopRequested = false; // set when Stop button / mic click stops recording

// ─── Mic UI helpers ───────────────────────────────────────────────────────────

function setListening(active) {
  isListening = active;
  document.body.dataset.voice = active ? 'listening' : 'idle';

  const micBtn    = $('micBtn');
  const listenEl  = $('composerListening');
  const idleEl    = $('composerIdle');

  if (active) {
    // Show recording panel below idle bar; mark mic button active
    show(listenEl);
    if (micBtn) {
      micBtn.setAttribute('aria-pressed', 'true');
      micBtn.setAttribute('aria-label', 'Recording — click to stop');
      micBtn.classList.add('mic-active');
    }
    setText('liveTranscriptInline', '');
    setText('voiceOrbLive', '');
    setText('listeningLabel', 'Listening');
  } else {
    // Collapse recording panel; restore mic button
    hide(listenEl);
    if (micBtn) {
      micBtn.setAttribute('aria-pressed', 'false');
      micBtn.setAttribute('aria-label', 'Start voice input');
      micBtn.classList.remove('mic-active');
    }
    setText('listeningLabel', 'Listening');
    setText('liveTranscriptInline', '');
    setText('voiceOrbLive', '');
  }

  // Always keep the idle bar (text input + send) visible
  show(idleEl);
}

// ─── Session phase ────────────────────────────────────────────────────────────

function setSessionPhase(phase) {
  sessionPhase = phase;
  document.body.dataset.phase = phase;
}

// ─── Diagnostic activity bar ──────────────────────────────────────────────────
// Shown ONLY while a real tool is running. JS calls show/hide around each fetch.

function showDiagnosticActivity(label) {
  const bar = $('diagStatusBar');
  if (!bar) return;
  show(bar);
  show($('diagSection'));
  setText('diagStatusLabel', label || 'Working…');
}

function hideDiagnosticActivity() {
  hide($('diagStatusBar'));
  setText('diagStatusLabel', '');
}

// ─── STATUS_PILL_MAP ──────────────────────────────────────────────────────────

const STATUS_PILL_MAP = {
  [PHASE.READY]:              { text: 'READY',           mod: 'ready' },
  [PHASE.UNDERSTANDING]:      { text: 'UNDERSTANDING',   mod: 'understanding' },
  [PHASE.DIAGNOSING]:         { text: 'DIAGNOSING',      mod: 'diagnosing' },
  [PHASE.ACTION_AVAILABLE]:   { text: 'ACTION REQUIRED', mod: 'action' },
  [PHASE.ACTION_IN_PROGRESS]: { text: 'APPLYING FIX',   mod: 'action' },
  [PHASE.VERIFYING]:          { text: 'VERIFYING',       mod: 'verifying' },
  [PHASE.RESOLVED]:           { text: 'RESOLVED',        mod: 'resolved' },
  [PHASE.ESCALATING]:         { text: 'ESCALATING',      mod: 'escalated' },
  [PHASE.ERROR]:              { text: 'ERROR',           mod: 'error' },
};

// ─── Workspace section helpers ────────────────────────────────────────────────

function showSection(id) {
  const el = $(id);
  if (el) { el.classList.remove('hidden'); el.classList.add('ws-section'); }
}

function hideSection(id) {
  const el = $(id);
  if (el) el.classList.add('hidden');
}

// ─── renderHeader ─────────────────────────────────────────────────────────────
// Drives: #issueName, #statusPill, #issueSymptom

function renderHeader(uiState, phase) {
  const intent   = uiState.issue || uiState.current_intent;
  const stage    = uiState.agent_status || uiState.stage || '';
  const pill     = $('statusPill');
  const nameEl   = $('issueName');
  const symptom  = $('issueSymptom');
  if (!pill || !nameEl) return;

  const pillInfo = STATUS_PILL_MAP[phase] || STATUS_PILL_MAP[PHASE.READY];
  pill.textContent  = pillInfo.text;
  pill.dataset.status = pillInfo.mod;

  if (!intent) {
    nameEl.textContent = 'Waiting for your issue';
    if (symptom) { symptom.textContent = ''; hideSection('issueSymptom'); }
    return;
  }

  const name = readable(intent);
  if (phase === PHASE.RESOLVED)        nameEl.textContent = `${name} resolved`;
  else if (phase === PHASE.ESCALATING) nameEl.textContent = `${name} — escalated`;
  else                                 nameEl.textContent = name;

  // Symptom line — only show when there's a short, human-readable phase label
  const symptomText = uiState.finding
    ? ''   // finding has its own section; don't duplicate in the header
    : (STAGE_LABELS[stage] ? STAGE_LABELS[stage] : '');

  if (symptom && symptomText) {
    symptom.textContent = symptomText;
    symptom.classList.remove('hidden');
  } else if (symptom) {
    symptom.textContent = '';
    symptom.classList.add('hidden');
  }
}

// ─── renderDiagnosisResults ───────────────────────────────────────────────────
// Renders per-tool result blocks inside #diagResultsContainer.
// Each tool gets one .diag-result-block keyed by data-tool attribute.
// When a result arrives it replaces the loading row for that tool.
// Values come 100% from the real tool result — nothing is invented.
//
// uiState.diagnosis_checklist item shape:
//   { title, name, check, label, tool,   ← label fields (any one)
//     detail, reason, message, result,   ← detail fields (any one)
//     state, status,                     ← state field
//     observations: [{ state, label }]   ← optional sub-rows
//   }

const STATE_ICON = { done: '✓', error: '✕', warning: '⚠', current: '●', pending: '○', unknown: '○' };

function normalizeCheckItem(item) {
  if (typeof item === 'string') {
    return { title: item, detail: '', state: 'current', toolKey: '', observations: [] };
  }

  const rawState = String(item.state || item.status || 'unknown').toLowerCase();
  const state =
    ['working', 'detected', 'pass', 'passed', 'connected', 'ok', 'running', 'available', 'healthy'].includes(rawState)
      ? 'done'
      : ['blocked', 'error', 'failed', 'unavailable', 'not_detected', 'timeout', 'not_running'].includes(rawState)
        ? 'error'
        : rawState === 'warning'  ? 'warning'
        : rawState === 'current'  ? 'current'
        : 'unknown';

  // Resolve toolKey for section-title lookup
  const rawTool = String(item.tool || item.name || item.check || item.label || item.title || '').toLowerCase();
  const toolKey = Object.keys(TOOL_SECTION_TITLES).find((k) => rawTool.includes(k)) || '';

  return {
    title:        readable(item.title || item.name || item.check || item.label || item.tool || 'Diagnostic check'),
    detail:       readable(item.detail || item.reason || item.message || item.result || rawState),
    state,
    toolKey,
    observations: Array.isArray(item.observations) ? item.observations : [],
  };
}

function renderDiagnosisResults(checklist) {
  const container = $('diagResultsContainer');
  if (!container) return;

  if (!Array.isArray(checklist) || !checklist.length) {
    container.replaceChildren();
    return;
  }

  // Group items by toolKey so each tool gets one expandable block.
  // Items without a toolKey fall into a generic group.
  const groups = new Map();
  checklist.forEach((raw) => {
    const item = normalizeCheckItem(raw);
    const key  = item.toolKey || '__generic__';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  // Rebuild only blocks that have changed (keyed by data-tool attribute).
  groups.forEach((items, key) => {
    const sectionTitle = TOOL_SECTION_TITLES[key] || null;

    // Find or create the block
    let block = container.querySelector(`[data-tool="${CSS.escape(key)}"]`);
    if (!block) {
      block = document.createElement('div');
      block.className   = 'diag-result-block';
      block.dataset.tool = key;
      container.appendChild(block);
    }

    block.replaceChildren();

    // Section title (e.g. "DISPLAY", "DOCK")
    if (sectionTitle) {
      const title = document.createElement('span');
      title.className   = 'diag-result-title';
      title.textContent = sectionTitle;
      block.appendChild(title);
    }

    // Observation rows
    const list = document.createElement('ul');
    list.className = 'diag-result-list';

    items.forEach((item) => {
      // Main row
      const li = document.createElement('li');
      li.className = `diag-obs diag-obs-${item.state}`;

      const icon = document.createElement('span');
      icon.className   = 'diag-obs-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = STATE_ICON[item.state] || '○';

      const text = document.createElement('span');
      text.className   = 'diag-obs-text';
      text.textContent = item.detail || item.title;

      li.append(icon, text);
      list.appendChild(li);

      // Sub-observations (e.g. individual display ports)
      if (item.observations.length) {
        item.observations.forEach((o) => {
          const subState = String(o.state || 'unknown').toLowerCase();
          const oIcon = { ok: '✓', warning: '⚠', failed: '✕' }[subState] || '○';
          const sub = document.createElement('li');
          sub.className = `diag-obs diag-obs-sub diag-obs-${subState === 'ok' ? 'done' : subState}`;

          const subIconEl = document.createElement('span');
          subIconEl.className   = 'diag-obs-icon';
          subIconEl.setAttribute('aria-hidden', 'true');
          subIconEl.textContent = oIcon;

          const subText = document.createElement('span');
          subText.className   = 'diag-obs-text';
          subText.textContent = readable(o.label || '');

          sub.append(subIconEl, subText);
          list.appendChild(sub);
        });
      }
    });

    block.appendChild(list);
  });

  showSection('diagSection');
}

// ─── renderTimeline ───────────────────────────────────────────────────────────

function renderTimeline(items) {
  const timeline = $('timeline');
  if (!timeline) return;
  timeline.replaceChildren();

  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement('div');
    empty.className   = 'timeline-empty';
    empty.textContent = 'Steps will appear here.';
    timeline.appendChild(empty);
    setText('progressPill', '–');
    hideSection('timelineSection');
    return;
  }

  const checks    = items.map(normalizeCheckItem);
  let   doneCount = 0;

  checks.forEach((check) => {
    const row = document.createElement('div');
    row.className = `tl-check tl-${check.state}`;

    const iconSpan = document.createElement('span');
    iconSpan.className = 'tl-icon';
    iconSpan.setAttribute('aria-hidden', 'true');
    iconSpan.textContent = STATE_ICON[check.state] || '○';

    const copy = document.createElement('div');
    copy.className = 'tl-copy';

    const strong = document.createElement('strong');
    strong.textContent = check.title;

    const small = document.createElement('small');
    small.textContent = check.detail;

    copy.append(strong, small);

    if (check.observations.length) {
      const obs = document.createElement('ul');
      obs.className = 'tl-obs';
      check.observations.forEach((o) => {
        const li       = document.createElement('li');
        const oState   = String(o.state || 'unknown').toLowerCase();
        li.className   = `tl-obs-${oState}`;
        const oIcon = { ok: '✓', warning: '⚠', failed: '✕' }[oState] || '○';
        li.textContent = `${oIcon} ${readable(o.label || '')}`;
        obs.appendChild(li);
      });
      copy.appendChild(obs);
    }

    row.append(iconSpan, copy);
    timeline.appendChild(row);
    if (check.state === 'done') doneCount++;
  });

  setText('progressPill', `${doneCount} / ${checks.length}`);
  showSection('timelineSection');
}

// ─── renderFinding ────────────────────────────────────────────────────────────
// Shows the FINDING section when backend provides uiState.finding.
// Hides if no finding is present.

function renderFinding(uiState) {
  const finding = uiState.finding;
  if (finding && finding.trim()) {
    setText('findingText', finding);
    showSection('findingSection');
  } else {
    hideSection('findingSection');
  }
}

// ─── renderNextStep ───────────────────────────────────────────────────────────
// Shows the NEXT STEP section when backend provides uiState.next_step
// (a human-readable guidance string without exposing RAG internals).

function renderNextStep(uiState) {
  const step = uiState.next_step;
  if (step && step.trim()) {
    setText('nextStepText', step);
    showSection('nextStepSection');
  } else {
    hideSection('nextStepSection');
  }
}

// ─── renderTroubleshootingState ───────────────────────────────────────────────
// Shows a transient "Reviewing guidance…" spinner while RAG is processing.
// The backend signals this with uiState.rag_processing === true.
// The section hides itself as soon as rag_processing is false/absent
// (the finding section takes over).

function renderTroubleshootingState(uiState) {
  const processing = uiState.rag_processing === true;
  if (processing) {
    // Allow the backend to override the label text
    const label = uiState.rag_label || 'Reviewing guidance…';
    setText('ragStateLabel', label);
    showSection('troubleshootingSection');
  } else {
    hideSection('troubleshootingSection');
  }
}

// ─── renderActionSection ──────────────────────────────────────────────────────
// Drives the ACTION section: title, description, Approve & Test, I've done this.
//
// Rules:
//  - Section is hidden until there is something to act on.
//  - "Approve & Test" appears only when stage === approval_required AND a real
//    executable action key is present (uiState.action_is_executable !== false).
//  - "I've done this" appears when stage === approval_required AND the action
//    is manual guidance only (uiState.action_is_executable === false).
//  - Neither button is shown when acting is in progress (applying…).
//  - Both buttons are hidden for all other stages.

function renderActionSection(uiState) {
  const action    = uiState.pending_action || uiState.recommended_action;
  const pendingId = uiState.pending_action_id;
  const stage     = uiState.agent_status || uiState.stage || '';
  const isExecutable = uiState.action_is_executable !== false; // default true

  const approveBtn    = $('approve');
  const manualBtn     = $('manualDone');
  const titleEl       = $('actionTitle');
  const descEl        = $('actionDescription');

  if (!titleEl || !descEl) return;

  // Nothing to act on yet — hide entire section
  if (!action && !pendingId) {
    hideSection('actionSection');
    hide(approveBtn);
    hide(manualBtn);
    return;
  }

  titleEl.textContent = readable(action || pendingId);

  if (stage === 'acting' || sessionPhase === PHASE.ACTION_IN_PROGRESS) {
    // Mid-flight: show the section but no buttons
    descEl.textContent = 'Applying the fix…';
    hide(approveBtn);
    hide(manualBtn);
    if (approveBtn) { approveBtn.textContent = 'Applying…'; approveBtn.disabled = true; }
    showSection('actionSection');
    return;
  }

  const needsApproval = stage === 'approval_required' || sessionPhase === PHASE.ACTION_AVAILABLE;

  if (needsApproval && isExecutable) {
    descEl.textContent = 'This change needs your approval before it is applied and tested.';
    if (approveBtn) {
      approveBtn.innerHTML = 'Approve &amp; Test <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';
      approveBtn.disabled = false;
      show(approveBtn);
    }
    hide(manualBtn);
  } else if (needsApproval && !isExecutable) {
    descEl.textContent = 'Complete this step, then confirm so we can verify the result.';
    hide(approveBtn);
    if (manualBtn) { manualBtn.disabled = false; show(manualBtn); }
  } else {
    // Action exists but not awaiting approval (e.g. stage = verifying / resolved)
    descEl.textContent = 'Awaiting the outcome of the applied action.';
    hide(approveBtn);
    hide(manualBtn);
  }

  showSection('actionSection');
}

// ─── renderVerificationSection ────────────────────────────────────────────────

function renderVerificationSection(uiState) {
  const verification = uiState.verification || {};
  const stage        = uiState.agent_status || uiState.stage || '';
  const titleEl      = $('verificationTitle');
  const detailEl     = $('verificationDetail');
  const verifyingEl  = $('verifyingState');

  if (!titleEl || !detailEl) return;

  // Nothing to show until we reach the acting/verifying/resolved/escalated stages
  if (!stage || ['diagnosing', 'approval_required'].includes(stage)) {
    hideSection('verificationSection');
    return;
  }

  showSection('verificationSection');

  if (stage === 'acting') {
    hide(verifyingEl);
    titleEl.textContent      = 'Pending verification';
    titleEl.dataset.vstate   = 'pending';
    detailEl.textContent     = '';
    return;
  }

  if (stage === 'verifying') {
    // Show running spinner, hide result text
    show(verifyingEl);
    titleEl.textContent    = '';
    detailEl.textContent   = '';
    titleEl.dataset.vstate = 'working';
    return;
  }

  // Result is available — hide spinner
  hide(verifyingEl);

  const status = String(verification.status || '').toLowerCase();

  if (stage === 'resolved' || status === 'passed') {
    titleEl.textContent      = '✓ Verified';
    detailEl.textContent     = verification.message || 'The fix was applied and the issue is resolved.';
    titleEl.dataset.vstate   = 'passed';
    return;
  }

  if (stage === 'escalated' || ['failed', 'unresolved', 'error'].includes(status)) {
    titleEl.textContent      = '✕ Not resolved';
    detailEl.textContent     = verification.message || verification.reason || 'The problem is still present.';
    titleEl.dataset.vstate   = 'failed';
    return;
  }

  if (status === 'unknown' || !status) {
    titleEl.textContent      = '? Unable to verify automatically';
    detailEl.textContent     = verification.message || '';
    titleEl.dataset.vstate   = 'unknown';
    return;
  }

  titleEl.textContent    = readable(status);
  detailEl.textContent   = verification.message || '';
  titleEl.dataset.vstate = status;
}

// ─── renderEscalationSection ──────────────────────────────────────────────────
// Drives: #escalationSection, #creatingIncidentState, #incidentCreatedCard,
//         #ticketId, #routingTeam, #diagnosticCount, #escalationSummary,
//         #escalationHandoff, #viewIncidentBtn

function renderEscalationSection(uiState) {
  const ec    = uiState.escalation_card || null;
  const stage = uiState.agent_status || uiState.stage || '';

  // Hide entirely when not escalating
  if (!ec && stage !== 'escalated') {
    hideSection('escalationSection');
    return;
  }

  showSection('escalationSection');

  const creatingEl = $('creatingIncidentState');
  const cardEl     = $('incidentCreatedCard');

  // Ticket not yet created — show spinner
  if (!ec || !ec.ticket_id) {
    show(creatingEl);
    hide(cardEl);
    return;
  }

  // Ticket created — hide spinner, show card
  hide(creatingEl);
  show(cardEl);

  setText('ticketId',       ec.ticket_id || '–');
  setText('routingTeam',    ec.routing_team || 'IT Helpdesk');
  setText('diagnosticCount', `${(ec.diagnostics_run || []).length} checks`);
  setText('escalationSummary', ec.reason || ec.symptom || 'The captured evidence has been routed to support.');

  // Technician handoff detail block
  const handoffEl = $('escalationHandoff');
  if (handoffEl && ec.handoff) {
    handoffEl.textContent = ec.handoff;
    handoffEl.classList.remove('hidden');
  }

  // View Incident button — links to the technician view filtered to this ticket
  const btn = $('viewIncidentBtn');
  if (btn && ec.ticket_id) {
    btn.href = `#${ec.ticket_id}`;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      // Switch to technician view and select the incident
      setRole('technician');
      selectIncident(ec.ticket_id);
    }, { once: true });
    btn.classList.remove('hidden');
  }
}

// ─── Diagnostic activity label inference ────────────────────────────────────

function inferRunningTool(diagnosisChecklist) {
  if (!Array.isArray(diagnosisChecklist) || !diagnosisChecklist.length) return null;
  const last     = diagnosisChecklist[diagnosisChecklist.length - 1];
  const rawState = String(last.state || last.status || 'unknown').toLowerCase();
  const isTerminal = ['working', 'detected', 'pass', 'passed', 'connected', 'ok',
    'running', 'blocked', 'error', 'failed', 'unavailable', 'not_detected', 'timeout'].includes(rawState);
  if (isTerminal) return null;
  const toolName = last.tool || last.name || last.title || '';
  const matched  = Object.keys(TOOL_LABELS).find((k) =>
    toolName.toLowerCase().includes(k.replace(/_/g, ' ').toLowerCase().slice(6))
  );
  return matched || null;
}

// ─── Master render ────────────────────────────────────────────────────────────
// Single entry point called after every API response.
// Drives every section of the unified workspace panel from real ui_state only.

function renderUiState(uiState) {
  if (!uiState) return;

  const stage = uiState.agent_status || uiState.stage || '';
  const phase = phaseFromStage(stage);
  setSessionPhase(phase);

  // 1. Header — issue name + status pill + symptom
  renderHeader(uiState, phase);

  // 2. Diagnosis — tool result blocks (appear as each tool result arrives)
  const checklist = uiState.diagnosis_checklist || uiState.diagnosis || [];
  renderDiagnosisResults(checklist);

  // 3. Timeline — high-level step progression
  renderTimeline(checklist);

  // 4. Troubleshooting — transient RAG spinner (while rag_processing === true)
  renderTroubleshootingState(uiState);

  // 5. Finding — plain-language summary from backend (after RAG + tool results)
  renderFinding(uiState);

  // 6. Next step — manual guidance when no executable action exists
  renderNextStep(uiState);

  // 7. Action — approval buttons driven by stage + action_is_executable flag
  renderActionSection(uiState);

  // 8. Verification — spinner while verifying, result after
  renderVerificationSection(uiState);

  // 9. Escalation — incident creation + handoff card
  renderEscalationSection(uiState);

  // Clear activity bar once terminal stages are reached
  if (['resolved', 'escalated'].includes(stage)) {
    hideDiagnosticActivity();
  }
}

// ─── Send message to agent API ───────────────────────────────────────────────

async function sendMessage(text, approved = false) {
  if (!text || isSubmitting) return null;
  isSubmitting = true;

  // Show activity bar immediately with a best-guess label (before fetch returns)
  const runningLabel = guessToolLabel(text, approved);
  if (runningLabel) showDiagnosticActivity(runningLabel);

  // Pre-emptively update status pill while waiting for the response
  if (!approved) {
    setSessionPhase(PHASE.UNDERSTANDING);
    const pill = $('statusPill');
    if (pill) { pill.textContent = 'UNDERSTANDING'; pill.dataset.status = 'understanding'; }
  } else {
    setSessionPhase(PHASE.ACTION_IN_PROGRESS);
    const pill = $('statusPill');
    if (pill) { pill.textContent = 'APPLYING FIX'; pill.dataset.status = 'action'; }
    // Also show "Applying…" on the approve button
    const approveBtn = $('approve');
    if (approveBtn) { approveBtn.innerHTML = 'Applying…'; approveBtn.disabled = true; }
  }

  try {
    const response = await fetch(AGENT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, user_text: text, user_approved: approved }),
    });

    if (!response.ok) throw new Error(`Agent API ${response.status}`);
    const data = await response.json();

    if (data.reply_text) {
      const clean = cleanAgentReply(data.reply_text);
      if (clean) { addTranscriptRow('agent', clean); speak(clean); }
    }

    renderUiState(data.ui_state || {});
    return data;
  } catch (error) {
    console.error('[agent]', error);
    setSessionPhase(PHASE.ERROR);
    addTranscriptRow('agent', 'Could not reach the support service. Please check the connection and try again.');
    return null;
  } finally {
    isSubmitting = false;
    hideDiagnosticActivity();
    // Do NOT touch voice state here — voice manages its own lifecycle
    // via setListening(). Calling setListening(false) from here would
    // close the recording panel mid-session on every text send.
  }
}

// ─── Filter internal status phrases out of conversation ──────────────────────

const INTERNAL_PATTERNS = [
  /^(checking|running|calling|executing|invoking|awaiting|let me (check|inspect|look))/i,
  /^(i['']m checking|i am checking)/i,
  /running a diagnostic/i,
  /calling (the |an? )?mcp tool/i,
  /tool invocation/i,
  /awaiting tool result/i,
];

function cleanAgentReply(text) {
  const trimmed = (text || '').trim();
  for (const pattern of INTERNAL_PATTERNS) {
    if (pattern.test(trimmed)) return null;
  }
  return trimmed || null;
}

// ─── Guess a tool label from user text for immediate activity bar ─────────────

function guessToolLabel(text, approved) {
  if (approved) return TOOL_LABELS['execute_action'];
  const lower = text.toLowerCase();
  if (/monitor|display|screen|hdmi/.test(lower))          return TOOL_LABELS['check_display'];
  if (/dock(ing)?|port replicator/.test(lower))           return TOOL_LABELS['check_dock'];
  if (/wi.fi|wireless|wlan/.test(lower))                  return TOOL_LABELS['check_wifi'];
  if (/vpn|secure connect|corporate network/.test(lower)) return TOOL_LABELS['check_vpn'];
  if (/bluetooth|headset|bt /.test(lower))                return TOOL_LABELS['check_bluetooth_audio'];
  if (/browser|chrome|edge|firefox|portal/.test(lower))   return TOOL_LABELS['check_browser_state'];
  if (/slow|lagging|performance|cpu|memory|ram/.test(lower)) return TOOL_LABELS['check_performance'];
  if (/microphone|mic|nobody can hear/.test(lower))       return TOOL_LABELS['check_mic'];
  if (/camera|webcam/.test(lower))                        return TOOL_LABELS['check_camera'];
  if (/speaker|audio/.test(lower))                        return TOOL_LABELS['check_speaker'];
  if (/internet|connection|network/.test(lower))          return TOOL_LABELS['check_connectivity'];
  if (/app|teams|zoom|outlook|crash/.test(lower))         return TOOL_LABELS['check_application_state'];
  return null;
}

// ─── Voice: submit captured transcript through shared sendMessage ─────────────
// This is the ONLY path from voice to the agent. Identical pipeline to text.

async function submitVoiceMessage() {
  clearTimeout(silenceTimer);
  const text = finalVoiceText.trim();
  finalVoiceText = '';
  if (!text || isSubmitting) {
    setListening(false);
    return;
  }
  // Commit the live preview row as a permanent user message
  if (liveTranscriptRow) {
    liveTranscriptRow.classList.remove('transcript-live');
    liveTranscriptRow = null;
  }
  addTranscriptRow('user', text);
  setListening(false);
  await sendMessage(text);
}

// ─── Voice input setup ────────────────────────────────────────────────────────

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.continuous = false;

  recognition.onstart = () => {
    finalVoiceText = '';
    speechEnded    = false;
    stopRequested  = false;
    liveTranscriptRow = null;
    setListening(true);
  };

  recognition.onerror = (event) => {
    clearTimeout(silenceTimer);
    setListening(false);
    const micBtn = $('micBtn');
    if (micBtn) micBtn.classList.add('mic-error');
    // Auto-clear error state after 3 s
    setTimeout(() => { if (micBtn) micBtn.classList.remove('mic-error'); }, 3000);
  };

  recognition.onspeechend = () => {
    speechEnded = true;
    setText('listeningLabel', 'Processing…');
  };

  // onend fires after every stop — submit only if speech was captured
  recognition.onend = () => {
    clearTimeout(silenceTimer);
    if (speechEnded || stopRequested) {
      submitVoiceMessage();
    } else {
      // No speech detected — just close the panel
      setListening(false);
    }
  };

  recognition.onresult = (event) => {
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text   = result[0].transcript.trim();
      if (!text) continue;
      if (result.isFinal) {
        finalVoiceText = `${finalVoiceText} ${text}`.trim();
        // Auto-stop after 1.5 s of silence following final result
        clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => { if (recognition) recognition.stop(); }, 1500);
      } else {
        interimText = `${interimText} ${text}`.trim();
      }
    }
    const preview = `${finalVoiceText} ${interimText}`.trim();
    if (preview) {
      // Update live transcript in the recording panel and the orb
      updateLiveTranscript(preview);
      setText('liveTranscriptInline', preview);
      setText('voiceOrbLive', preview);
    }
  };
} else {
  // Browser doesn't support SpeechRecognition — disable mic button on load
  document.addEventListener('DOMContentLoaded', () => {
    const micBtn = $('micBtn');
    if (micBtn) { micBtn.disabled = true; micBtn.title = 'Voice input unavailable in this browser'; }
  });
}

// ─── Mic button click handler ─────────────────────────────────────────────────

function handleMicClick() {
  if (!recognition) return;
  if (isSubmitting) return;   // don't start while a fetch is in flight

  if (isListening) {
    // User explicitly stops recording (same as clicking Stop)
    stopRequested = true;
    clearTimeout(silenceTimer);
    recognition.stop();
    return;
  }

  // Start fresh recording
  finalVoiceText    = '';
  liveTranscriptRow = null;
  try {
    recognition.start();
  } catch (err) {
    console.warn('[voice] start error:', err.message);
    setListening(false);
  }
}

// ─── Text input send ──────────────────────────────────────────────────────────

function handleSend() {
  const input = $('messageInput');
  if (!input) return;
  const text = input.value.trim();
  if (!text || isSubmitting) return;
  input.value = '';
  addTranscriptRow('user', text);
  sendMessage(text);
}

// ─── Approve button ───────────────────────────────────────────────────────────

async function handleApprove() {
  const approveBtn = $('approve');
  if (!approveBtn || approveBtn.disabled) return;
  approveBtn.disabled = true;
  setSessionPhase(PHASE.ACTION_IN_PROGRESS);
  showDiagnosticActivity('Applying the fix…');
  try {
    await sendMessage('Approve', true);
  } finally {
    hideDiagnosticActivity();
  }
}

// ─── Manual "I've done this" button ───────────────────────────────────────────
// Sent as an approval signal so the agent can move to verification.

async function handleManualDone() {
  const btn = $('manualDone');
  if (!btn || btn.disabled) return;
  btn.disabled = true;
  setSessionPhase(PHASE.ACTION_IN_PROGRESS);
  showDiagnosticActivity('Verifying…');
  try {
    await sendMessage('Done', true);
  } finally {
    hideDiagnosticActivity();
  }
}

// ─── Technician workspace ─────────────────────────────────────────────────────

function renderEvidenceList(value, emptyText = 'No recorded evidence.') {
  const items = Array.isArray(value) && value.length ? value : [emptyText];
  return items.map((item) => {
    const text = typeof item === 'string'
      ? item
      : Object.entries(item || {})
        .map(([k, v]) => `${readable(k)}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
        .join(' · ');
    return `<li>${escapeHtml(text || emptyText)}</li>`;
  }).join('');
}

function diagnosticState(item) {
  const status = String(item?.status || item?.state || 'unknown').toLowerCase();
  if (['working', 'detected', 'pass', 'passed', 'connected', 'ok', 'running', 'available', 'healthy'].includes(status)) return 'pass';
  if (['failed', 'error', 'blocked', 'unavailable', 'not_detected', 'timeout', 'not_running'].includes(status)) return 'fail';
  if (status === 'warning') return 'warning';
  return 'unknown';
}

function renderDiagnostics(items) {
  if (!Array.isArray(items) || !items.length)
    return '<p class="empty-detail">No diagnostic results recorded.</p>';

  return `<ul class="diagnostic-list">${items.map((item) => {
    const state = diagnosticState(item);
    const label = item.title || item.name || item.check || item.tool || item.label || 'Diagnostic check';
    const detail = item.detail || item.message || item.reason || item.status || 'unknown';
    const icon = state === 'pass' ? '✓' : state === 'fail' ? '✕' : state === 'warning' ? '⚠' : '○';
    const obsHtml = Array.isArray(item.observations) && item.observations.length
      ? `<ul class="obs-list">${item.observations.map((o) => {
        const oIcon = { ok: '✓', warning: '⚠', failed: '✕' }[o.state] || '○';
        return `<li class="obs-${escapeHtml(o.state || 'unknown')}">${oIcon} ${escapeHtml(readable(o.label || ''))}</li>`;
      }).join('')}</ul>` : '';
    return `<li class="diagnostic-${state}"><span>${icon}</span><div><strong>${escapeHtml(readable(label))}</strong><small>${escapeHtml(readable(detail))}</small>${obsHtml}</div></li>`;
  }).join('')}</ul>`;
}

function renderVerification(verification, outcome) {
  const rawStatus = String(verification?.status || outcome || 'not recorded');
  const status = rawStatus === 'needs_technician' ? 'unresolved' : rawStatus;
  const failed = ['failed', 'unresolved', 'error'].includes(status.toLowerCase());
  const icon = failed ? '✕' : (status === 'passed' || status === 'resolved') ? '✓' : '○';
  const detail = verification?.message || verification?.reason || (failed ? 'Issue persists' : 'Verification result not recorded.');
  return `<div class="verification-result ${failed ? 'failed' : ''}">
    <span>${icon}</span>
    <div><strong>${escapeHtml(readable(detail))}</strong><small>Final result: ${escapeHtml(readable(status))}</small></div>
  </div>`;
}

function renderIncidentDetail(incident) {
  const detail = $('incidentDetail');
  if (!incident) {
    detail.innerHTML = '<p class="timeline-empty">Select an incident to inspect its diagnostic handoff.</p>';
    return;
  }

  const status = readable(incident.status || 'needs_human').toUpperCase();
  const handoff = incident.ai_summary
    || (['unresolved', 'needs_technician'].includes(incident.final_outcome)
      ? 'The issue remained unresolved after the attempted troubleshooting. Human investigation is required.'
      : 'Diagnostic context is available above for continued investigation.');

  detail.innerHTML = `
    <div class="detail-top">
      <div>
        <div class="incident-title-line">
          <span class="eyebrow">${escapeHtml(incident.incident_id)}</span>
          <span class="status-badge">● ${escapeHtml(status)}</span>
        </div>
        <h2>${escapeHtml(incident.issue?.summary || readable(incident.issue_type || 'IT incident'))}</h2>
      </div>
      <select id="incidentStatus" aria-label="Update incident status">
        <option value="needs_human"   ${incident.status === 'needs_human' ? 'selected' : ''}>Needs human</option>
        <option value="investigating" ${incident.status === 'investigating' ? 'selected' : ''}>Investigating</option>
        <option value="resolved"      ${incident.status === 'resolved' ? 'selected' : ''}>Resolved</option>
        <option value="closed"        ${incident.status === 'closed' ? 'selected' : ''}>Closed</option>
      </select>
    </div>
    <section class="detail-section">
      <span class="eyebrow">EMPLOYEE</span>
      <p class="detail-strong">${escapeHtml(incident.employee_name || 'Unknown employee')}</p>
      <span class="eyebrow">ORIGINAL REPORT</span>
      <p class="quote">"${escapeHtml(incident.user_report || 'No statement recorded.')}"</p>
    </section>
    <section class="detail-section">
      <span class="eyebrow">AI DIAGNOSIS</span>
      <p class="detail-strong">${escapeHtml(readable(incident.issue_type || 'IT incident'))} issue</p>
      <div class="routing">
        <span>Likely area: <strong>${escapeHtml(readable(incident.likely_area || 'unknown'))}</strong></span>
        <span>Recommended team: <strong>${escapeHtml(incident.recommended_team || 'IT Helpdesk')}</strong></span>
      </div>
    </section>
    <section class="detail-section">
      <span class="eyebrow">DIAGNOSTICS</span>
      ${renderDiagnostics(incident.diagnostics)}
    </section>
    <section class="detail-section">
      <span class="eyebrow">QUESTIONS ANSWERED</span>
      <ul class="evidence-list">${renderEvidenceList(incident.questions_answered, 'No questions recorded.')}</ul>
    </section>
    <section class="detail-section">
      <span class="eyebrow">ACTIONS ATTEMPTED</span>
      <ul class="evidence-list">${renderEvidenceList(incident.actions_attempted)}</ul>
    </section>
    <section class="detail-section">
      <span class="eyebrow">VERIFICATION</span>
      ${renderVerification(incident.verification, incident.final_outcome)}
    </section>
    <section class="detail-section">
      <span class="eyebrow">AI HANDOFF SUMMARY</span>
      <p>${escapeHtml(handoff)}</p>
    </section>
    <section class="detail-section">
      <span class="eyebrow">KNOWLEDGE USED</span>
      <ul class="evidence-list">${renderEvidenceList(incident.knowledge_used, 'No knowledge sources recorded.')}</ul>
    </section>
    <section class="detail-section history">
      <span class="eyebrow">INCIDENT HISTORY</span>
      <p>Created ${escapeHtml(formatDate(incident.created_at))}</p>
      <p>Last updated ${escapeHtml(formatDate(incident.updated_at || incident.created_at))}</p>
    </section>
    <div class="incident-actions">
      <button data-status="investigating" type="button">Investigating</button>
      <button data-status="resolved"      type="button">Resolve</button>
      <button data-status="closed"        type="button">Close</button>
    </div>`;

  $('incidentStatus').addEventListener('change', (e) => updateIncident(incident.incident_id, e.target.value));
  detail.querySelectorAll('.incident-actions button').forEach((btn) =>
    btn.addEventListener('click', () => updateIncident(incident.incident_id, btn.dataset.status)));
}

async function loadIncidents(selectedId) {
  const response = await fetch(`${BACKEND_URL}/api/incidents`);
  if (!response.ok) throw new Error('Incident list unavailable');
  const incidents = await response.json();

  setText('incidentCount', incidents.length);
  const list = $('incidentList');
  list.replaceChildren();

  if (!incidents.length) {
    list.innerHTML = '<p class="timeline-empty">No incidents have been escalated.</p>';
    return;
  }

  incidents.forEach((incident) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `incident-row ${selectedId === incident.incident_id ? 'selected' : ''}`;
    btn.innerHTML = `
      <strong>${escapeHtml(incident.incident_id)}</strong>
      <span>${escapeHtml(incident.employee_name || 'Unknown employee')}</span>
      <span>${escapeHtml(incident.issue?.summary || readable(incident.issue_type || 'IT incident'))}</span>
      <small>${escapeHtml(incident.status)} · ${escapeHtml(formatDate(incident.created_at))}</small>`;
    btn.addEventListener('click', () => selectIncident(incident.incident_id));
    list.appendChild(btn);
  });

  if (selectedId) selectIncident(selectedId);
  else if (incidents[0]) selectIncident(incidents[0].incident_id);
}

async function selectIncident(id) {
  const response = await fetch(`${BACKEND_URL}/api/incidents/${encodeURIComponent(id)}`);
  if (response.ok) renderIncidentDetail(await response.json());
}

async function updateIncident(id, status) {
  await fetch(`${BACKEND_URL}/api/incidents/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  loadIncidents(id).catch(() => { });
}

// ─── Role / view management ───────────────────────────────────────────────────

function setView(view) {
  const isEmployee = view === 'employee';
  hide($('welcomeView'));
  show($('roleControls'));
  show($('topbarNav'));
  setText('roleLabel', isEmployee ? 'Employee' : 'Technician');
  $('employeeView').classList.toggle('hidden', !isEmployee);
  $('technicianView').classList.toggle('hidden', isEmployee);

  // Sync active pill
  document.querySelectorAll('.topbar-nav-pill').forEach((pill) => {
    pill.classList.toggle('active', pill.dataset.role === view);
  });

  if (!isEmployee) {
    loadIncidents().catch(() => {
      $('incidentList').innerHTML = '<p class="timeline-empty">Backend unavailable. Start the backend and refresh.</p>';
    });
  }
}

function setRole(role) {
  if (!['employee', 'technician'].includes(role)) return;
  // Use sessionStorage so the role only persists for this browser tab.
  // Closing the tab, refreshing, or clicking "Start new session" always
  // returns the user to the welcome screen.
  sessionStorage.setItem(ROLE_STORAGE_KEY, role);
  setView(role);
}

function clearRole() {
  // Clear both storages so the welcome screen always appears fresh.
  sessionStorage.removeItem(ROLE_STORAGE_KEY);
  localStorage.removeItem(ROLE_STORAGE_KEY);
  hide($('roleControls'));
  hide($('topbarNav'));
  hide($('employeeView'));
  hide($('technicianView'));
  show($('welcomeView'));
}

// ─── Bootstrap event listeners ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Voice
  $('micBtn')?.addEventListener('click', handleMicClick);
  $('stopListening')?.addEventListener('click', () => {
    stopRequested = true;
    clearTimeout(silenceTimer);
    if (recognition) recognition.stop();
  });

  // Text
  $('send')?.addEventListener('click', handleSend);
  $('messageInput')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleSend(); });

  // Approve
  $('approve')?.addEventListener('click', handleApprove);
  $('manualDone')?.addEventListener('click', handleManualDone);

  // New session — wipe everything and return to welcome
  $('newSession')?.addEventListener('click', () => {
    sessionStorage.removeItem('meetassist-session');
    clearRole();   // clears stored role + shows welcome screen
    window.location.reload();
  });

  // Role controls
  document.querySelectorAll('.role-button').forEach((btn) =>
    btn.addEventListener('click', () => setRole(btn.dataset.role)));
  document.querySelectorAll('.topbar-nav-pill').forEach((pill) =>
    pill.addEventListener('click', () => setRole(pill.dataset.role)));
  $('switchRole')?.addEventListener('click', clearRole);
  $('footerSwitchRole')?.addEventListener('click', clearRole);

  // Technician auto-refresh
  $('refreshIncidents')?.addEventListener('click', () => loadIncidents().catch(() => { }));
  setInterval(() => {
    if ($('technicianView') && !$('technicianView').classList.contains('hidden')) {
      loadIncidents().catch(() => { });
    }
  }, 10000);

  // Initial UI state — show idle bar, hide recording panel, set orb to idle
  setListening(false);

  // Restore role only for this tab's session — never auto-navigate past welcome
  // on a fresh page load. sessionStorage is cleared when the tab is closed.
  const savedRole = sessionStorage.getItem(ROLE_STORAGE_KEY);
  // Also purge any stale localStorage role from the old code
  localStorage.removeItem(ROLE_STORAGE_KEY);
  if (savedRole) setRole(savedRole); else clearRole();
});

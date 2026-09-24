const API_URL = "http://localhost:3002/agent/message";
const BACKEND_URL = "http://localhost:5673";
const ROLE_STORAGE_KEY = "ai_it_support_role";
const sessionId = sessionStorage.getItem("meetassist-session") || crypto.randomUUID();
sessionStorage.setItem("meetassist-session", sessionId);
const $ = (id) => document.getElementById(id);
let recognition;
let isSubmitting = false;
let finalVoiceText = "";
let silenceTimer;
let speechEnded = false;
let stopRequested = false;
let liveTranscriptRow;

function speakAgentResponse(text) {
    const speechText = String(text || "").trim();
    if (!speechText || /failed to fetch|network error|could not reach support/i.test(speechText) || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.rate = 0.96;
    utterance.pitch = 1.02;
    window.speechSynthesis.speak(utterance);
}

function addTranscript(role, text) {
    const transcript = $("transcript");
    const empty = transcript.querySelector(".empty-transcript");
    if (empty) empty.remove();
    const row = document.createElement("div");
    row.className = `transcript-line ${role}`;
    const label = document.createElement("span");
    label.className = "transcript-label";
    label.textContent = role === "user" ? "YOU" : "AGENT";
    const quote = document.createElement("p");
    quote.textContent = `“${text}”`;
    row.append(label, quote);
    transcript.appendChild(row);
}

function normalizeCheck(item) {
    if (typeof item === "string") return { title: item, detail: "", state: "current" };
    const rawState = item.state || item.status || (item.passed ? "working" : "unknown");
    const state = ["working", "detected", "pass", "passed", "connected"].includes(rawState) ? "done" : ["blocked", "error", "failed", "unavailable", "not_detected", "timeout"].includes(rawState) ? "error" : "current";
    const title = item.title || item.name || item.check || item.label || item.error_code || "Diagnostic result";
    const detail = item.detail || item.message || item.reason || item.result || rawState;
    return { title: readable(title), detail: readable(detail), state };
}

function renderChecklist(items) {
    const timeline = $("timeline");
    timeline.replaceChildren();
    const checks = items.map(normalizeCheck);
    checks.forEach((check) => {
        const row = document.createElement("div");
        row.className = `check ${check.state}`;
        const icon = document.createElement("span");
        icon.textContent = check.state === "done" ? "✓" : check.state === "error" ? "✕" : "○";
        const copy = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = check.title;
        const detail = document.createElement("small");
        detail.textContent = check.detail;
        copy.append(title, detail);
        row.append(icon, copy);
        timeline.appendChild(row);
    });
    if (!checks.length) { const empty = document.createElement("div"); empty.className = "timeline-empty"; empty.textContent = "Diagnostic checks will populate here."; timeline.appendChild(empty); }
    $("progress").textContent = `${checks.filter((check) => check.state === "done").length} / ${checks.length}`;
}

function readable(value) { return String(value || "").replaceAll("_", " "); }

function renderEscalation(card) {
    const escalation = $("escalation");
    escalation.classList.toggle("hidden", !card);
    if (!card) return;
    $("ticketId").textContent = card.ticket_id || "Pending";
    $("routingTeam").textContent = card.routing_team || "IT Helpdesk";
    $("diagnosticCount").textContent = `${(card.diagnostics_run || []).length} checks`;
    $("escalationSummary").textContent = card.reason || card.symptom || "The captured evidence has been routed to support.";
}

function renderState(uiState) {
    const intent = uiState.issue || uiState.current_intent;
    $("title").textContent = intent ? `${readable(intent)} failure` : "Waiting for your issue";
    $("subtitle").textContent = uiState.stage ? `Support stage: ${readable(uiState.stage)}.` : "Tell us what is happening in your meeting and we'll check it.";
    $("severity").textContent = uiState.stage === "resolved" ? "RESOLVED" : intent ? "INVESTIGATING" : "READY";
    $("agentStatus").textContent = readable(uiState.agent_status || uiState.stage || "listening");
    renderChecklist(uiState.diagnosis_checklist || uiState.diagnosis || []);
    const action = uiState.pending_action || uiState.recommended_action;
    $("actionTitle").textContent = action ? readable(action) : "We'll recommend the next step here.";
    $("actionDescription").textContent = action ? "This change needs your approval before we test it." : "Run a diagnostic to receive a plain-language action.";
    $("approve").disabled = !action;
    $("verify").classList.toggle("hidden", !["verifying", "resolved", "escalated"].includes(uiState.stage));
    const verification = uiState.verification || {};
    const verificationStatus = verification.status || (uiState.stage === "resolved" ? "passed" : uiState.stage === "escalated" ? "failed" : "pending");
    $("verificationTitle").textContent = readable(verificationStatus);
    $("verificationDetail").textContent = verification.message || verification.reason || (verificationStatus === "pending" ? "A result will appear after an approved action is tested." : "The backend returned a verification result.");
    renderEscalation(uiState.escalation_card || null);
}

async function sendMessage(text, approved = false) {
    if (!text || isSubmitting) return null;
    isSubmitting = true;
    speakAgentResponse("Checking...");
    try {
        const response = await fetch(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, user_text: text, user_approved: approved }) });
        if (!response.ok) throw new Error(`Agent API returned ${response.status}`);
        const data = await response.json();
        addTranscript("agent", data.reply_text);
        renderState(data.ui_state || {});
        speakAgentResponse(data.reply_text);
        return data;
    } finally {
        isSubmitting = false;
    }
}

function setListening(listening) { $("mic").classList.toggle("listening", listening); $("voiceStatus").textContent = listening ? "Listening... describe your meeting issue." : "Tap the microphone and describe what went wrong."; }
function updateLiveTranscript(text) {
    const transcript = $("transcript");
    const empty = transcript.querySelector(".empty-transcript");
    if (empty) empty.remove();
    if (!liveTranscriptRow) {
        liveTranscriptRow = document.createElement("div");
        liveTranscriptRow.className = "transcript-line user";
        const label = document.createElement("span");
        label.className = "transcript-label";
        label.textContent = "YOU";
        const quote = document.createElement("p");
        liveTranscriptRow.append(label, quote);
        transcript.appendChild(liveTranscriptRow);
    }
    liveTranscriptRow.querySelector("p").textContent = `“${text}”`;
}

async function submitVoiceMessage() {
    clearTimeout(silenceTimer);
    const text = finalVoiceText.trim();
    finalVoiceText = "";
    if (!text || isSubmitting) return;
    $("voiceStatus").textContent = "Checking your meeting setup...";
    try {
        const response = await sendMessage(text);
        if (response) $("voiceStatus").textContent = "Response ready. Tap to speak again.";
    } catch {
        $("voiceStatus").textContent = "Could not reach support.";
    }
}

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
        finalVoiceText = "";
        speechEnded = false;
        stopRequested = false;
        liveTranscriptRow = null;
        setListening(true);
    };
    recognition.onerror = (event) => { setListening(false); $("voiceStatus").textContent = event.error === "not-allowed" ? "Microphone permission is blocked." : "Voice input failed. Try typing instead."; };
    recognition.onspeechend = () => { speechEnded = true; };
    recognition.onend = () => {
        setListening(false);
        if (speechEnded || stopRequested) submitVoiceMessage();
    };
    recognition.onresult = (event) => {
        let interimText = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const result = event.results[index];
            const text = result[0].transcript.trim();
            if (!text) continue;
            if (result.isFinal) {
                finalVoiceText = `${finalVoiceText} ${text}`.trim();
                clearTimeout(silenceTimer);
                silenceTimer = setTimeout(submitVoiceMessage, 1500);
            } else {
                interimText = `${interimText} ${text}`.trim();
            }
        }
        updateLiveTranscript(`${finalVoiceText} ${interimText}`.trim());
    };
} else { $("voiceStatus").textContent = "Voice input is unavailable. Type your issue below."; }

$("mic").addEventListener("click", () => { if (!recognition) return; if ($("mic").classList.contains("listening")) { stopRequested = true; recognition.stop(); } else if (!isSubmitting) recognition.start(); });
$("approve").addEventListener("click", async () => { if ($("approve").disabled) return; $("approve").disabled = true; try { const response = await sendMessage("Approve", true); if (!response) $("approve").disabled = false; } catch { $("voiceStatus").textContent = "Could not reach support."; $("approve").disabled = false; } });
$("send").addEventListener("click", async () => { const input = $("message"); const text = input.value.trim(); if (!text || isSubmitting) return; input.value = ""; addTranscript("user", text); try { await sendMessage(text); } catch { $("voiceStatus").textContent = "Could not reach support."; } });
$("message").addEventListener("keydown", (event) => { if (event.key === "Enter") $("send").click(); });
$("new").addEventListener("click", () => { sessionStorage.removeItem("meetassist-session"); window.location.reload(); });

function formatDate(value) {
    if (!value) return "Unknown time";
    return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function displayValue(value) {
    if (Array.isArray(value)) return value.length ? value : ["No recorded evidence."];
    if (value && typeof value === "object") return Object.entries(value).map(([key, item]) => `${readable(key)}: ${typeof item === "object" ? JSON.stringify(item) : item}`);
    return [String(value || "No recorded evidence.")];
}

function renderEvidenceList(value, emptyText = "No recorded evidence.") {
    const items = Array.isArray(value) && value.length ? value : [emptyText];
    return items.map((item) => {
        const text = typeof item === "string" ? item : Object.entries(item || {}).map(([key, entry]) => `${readable(key)}: ${typeof entry === "object" ? JSON.stringify(entry) : entry}`).join(" · ");
        return `<li>${escapeHtml(text || emptyText)}</li>`;
    }).join("");
}

function diagnosticState(item) {
    const status = String(item?.status || item?.state || "unknown").toLowerCase();
    if (["working", "detected", "pass", "passed", "connected", "available", "healthy"].includes(status)) return "pass";
    if (["failed", "error", "blocked", "unavailable", "not_detected", "timeout"].includes(status)) return "fail";
    return "unknown";
}

function renderDiagnostics(items) {
    if (!Array.isArray(items) || !items.length) return '<p class="empty-detail">No diagnostic results recorded.</p>';
    return `<ul class="diagnostic-list">${items.map((item) => {
        const state = diagnosticState(item);
        const label = item.title || item.name || item.check || item.tool || item.label || "Diagnostic check";
        const detail = item.detail || item.message || item.reason || item.status || "unknown";
        const icon = state === "pass" ? "✓" : state === "fail" ? "✕" : "○";
        return `<li class="diagnostic-${state}"><span>${icon}</span><div><strong>${escapeHtml(readable(label))}</strong><small>${escapeHtml(readable(detail))}</small></div></li>`;
    }).join("")}</ul>`;
}

function renderVerification(verification, outcome) {
    const rawStatus = String(verification?.status || outcome || "not recorded");
    const status = rawStatus === "needs_technician" ? "unresolved" : rawStatus;
    const failed = ["failed", "unresolved", "error"].includes(status.toLowerCase());
    const icon = failed ? "✕" : status === "passed" || status === "resolved" ? "✓" : "○";
    const detail = verification?.message || verification?.reason || (failed ? "Microphone test failed" : "Verification result not recorded.");
    return `<div class="verification-result ${failed ? "failed" : ""}"><span>${icon}</span><div><strong>${escapeHtml(readable(detail))}</strong><small>Final result: ${escapeHtml(readable(status))}</small></div></div>`;
}

function renderIncidentDetail(incident) {
    const detail = $("incidentDetail");
    if (!incident) { detail.innerHTML = '<p class="timeline-empty">Select an incident to inspect its diagnostic handoff.</p>'; return; }
    const status = readable(incident.status || "needs_human").toUpperCase();
    const handoff = incident.ai_summary || (["unresolved", "needs_technician"].includes(incident.final_outcome) ? "The issue remained unresolved after the attempted troubleshooting. Human investigation is required." : "Diagnostic context is available above for continued investigation.");
    detail.innerHTML = `<div class="detail-top"><div><div class="incident-title-line"><span class="eyebrow">${escapeHtml(incident.incident_id)}</span><span class="status-badge">● ${escapeHtml(status)}</span></div><h2>${escapeHtml(incident.issue?.summary || readable(incident.issue_type || "IT incident"))}</h2></div><select id="incidentStatus" aria-label="Update incident status"><option value="needs_human" ${incident.status === "needs_human" ? "selected" : ""}>Needs human</option><option value="investigating" ${incident.status === "investigating" ? "selected" : ""}>Investigating</option><option value="resolved" ${incident.status === "resolved" ? "selected" : ""}>Resolved</option><option value="closed" ${incident.status === "closed" ? "selected" : ""}>Closed</option></select></div><section class="detail-section"><span class="eyebrow">EMPLOYEE</span><p class="detail-strong">${escapeHtml(incident.employee_name || "Unknown employee")}</p><span class="eyebrow">ORIGINAL REPORT</span><p class="quote">“${escapeHtml(incident.user_report || "No statement recorded.")}”</p></section><section class="detail-section"><span class="eyebrow">AI DIAGNOSIS</span><p class="detail-strong">${escapeHtml(readable(incident.issue_type || "IT incident"))} issue</p><div class="routing"><span>Likely area: <strong>${escapeHtml(readable(incident.likely_area || "unknown"))}</strong></span><span>Recommended team: <strong>${escapeHtml(incident.recommended_team || "IT Helpdesk")}</strong></span></div></section><section class="detail-section"><span class="eyebrow">DIAGNOSTICS</span>${renderDiagnostics(incident.diagnostics)}</section><section class="detail-section"><span class="eyebrow">QUESTIONS ANSWERED</span><ul class="evidence-list">${renderEvidenceList(incident.questions_answered, "No questions recorded.")}</ul></section><section class="detail-section"><span class="eyebrow">ACTIONS ATTEMPTED</span><ul class="evidence-list">${renderEvidenceList(incident.actions_attempted)}</ul></section><section class="detail-section"><span class="eyebrow">VERIFICATION</span>${renderVerification(incident.verification, incident.final_outcome)}</section><section class="detail-section"><span class="eyebrow">AI HANDOFF SUMMARY</span><p>${escapeHtml(handoff)}</p></section><section class="detail-section"><span class="eyebrow">KNOWLEDGE USED</span><ul class="evidence-list">${renderEvidenceList(incident.knowledge_used, "No knowledge sources recorded.")}</ul></section><section class="detail-section history"><span class="eyebrow">INCIDENT HISTORY</span><p>Created ${escapeHtml(formatDate(incident.created_at))}</p><p>Last updated ${escapeHtml(formatDate(incident.updated_at || incident.created_at))}</p></section><div class="incident-actions"><button data-status="investigating" type="button">Investigating</button><button data-status="resolved" type="button">Resolve</button><button data-status="closed" type="button">Close</button></div>`;
    $("incidentStatus").addEventListener("change", (event) => updateIncident(incident.incident_id, event.target.value));
    detail.querySelectorAll(".incident-actions button").forEach((button) => button.addEventListener("click", () => updateIncident(incident.incident_id, button.dataset.status)));
}

function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character])); }

async function loadIncidents(selectedId) {
    const response = await fetch(`${BACKEND_URL}/api/incidents`);
    if (!response.ok) throw new Error("Incident list unavailable");
    const incidents = await response.json();
    $("incidentCount").textContent = incidents.length;
    const list = $("incidentList");
    list.replaceChildren();
    if (!incidents.length) { list.innerHTML = '<p class="timeline-empty">No incidents have been escalated.</p>'; return; }
    incidents.forEach((incident) => {
        const button = document.createElement("button");
        button.className = `incident-row ${selectedId === incident.incident_id ? "selected" : ""}`;
        button.innerHTML = `<strong>${escapeHtml(incident.incident_id)}</strong><span>${escapeHtml(incident.employee_name || "Unknown employee")}</span><span>${escapeHtml(incident.issue?.summary || readable(incident.issue_type || "IT incident"))}</span><small>${escapeHtml(incident.status)} · ${escapeHtml(formatDate(incident.created_at))}</small>`;
        button.addEventListener("click", () => selectIncident(incident.incident_id));
        list.appendChild(button);
    });
    if (selectedId) selectIncident(selectedId); else selectIncident(incidents[0].incident_id);
}

async function selectIncident(id) {
    const response = await fetch(`${BACKEND_URL}/api/incidents/${encodeURIComponent(id)}`);
    if (response.ok) renderIncidentDetail(await response.json());
}

async function updateIncident(id, status) {
    await fetch(`${BACKEND_URL}/api/incidents/${encodeURIComponent(id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    loadIncidents(id).catch(() => {});
}

function setView(view) {
    const employee = view === "employee";
    $("welcomeView").classList.add("hidden");
    $("roleControls").classList.remove("hidden");
    $("roleLabel").textContent = employee ? "Employee mode" : "Technician mode";
    $("employeeView").classList.toggle("hidden", !employee);
    $("technicianView").classList.toggle("hidden", employee);
    if (!employee) loadIncidents().catch(() => { $("incidentList").innerHTML = '<p class="timeline-empty">Backend unavailable. Start the backend and refresh.</p>'; });
}

function setRole(role) {
    if (!["employee", "technician"].includes(role)) return;
    localStorage.setItem(ROLE_STORAGE_KEY, role);
    setView(role);
}

function clearRole() {
    localStorage.removeItem(ROLE_STORAGE_KEY);
    $("roleControls").classList.add("hidden");
    $("employeeView").classList.add("hidden");
    $("technicianView").classList.add("hidden");
    $("welcomeView").classList.remove("hidden");
}

document.querySelectorAll(".role-button").forEach((button) => button.addEventListener("click", () => setRole(button.dataset.role)));
$("switchRole").addEventListener("click", clearRole);
$("footerSwitchRole").addEventListener("click", clearRole);
$("refreshIncidents").addEventListener("click", () => loadIncidents().catch(() => {}));
setInterval(() => { if (!$("technicianView").classList.contains("hidden")) loadIncidents().catch(() => {}); }, 10000);

const savedRole = localStorage.getItem(ROLE_STORAGE_KEY);
if (savedRole) setRole(savedRole); else clearRole();
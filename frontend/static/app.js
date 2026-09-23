const API_URL = "http://localhost:3002/agent/message";
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

function speak(text) {
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
    const state = item.state || item.status || (item.passed ? "done" : "error");
    return { title: item.title || item.name || item.check || item.error_code || "Diagnostic check", detail: item.detail || item.message || item.result || "", state: state === "passed" || state === "working" ? "done" : state };
}

function renderChecklist(items) {
    const timeline = $("timeline");
    timeline.replaceChildren();
    const checks = items.map(normalizeCheck);
    checks.forEach((check) => {
        const row = document.createElement("div");
        row.className = `check ${check.state}`;
        const icon = document.createElement("span");
        icon.textContent = check.state === "done" ? "✓" : check.state === "error" || check.state === "blocked" ? "✕" : "•";
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
    renderChecklist(uiState.diagnosis_checklist || uiState.diagnosis || []);
    const action = uiState.pending_action || uiState.recommended_action;
    $("actionTitle").textContent = action ? readable(action) : "We'll recommend the next step here.";
    $("actionDescription").textContent = action ? "This change needs your approval before we test it." : "Run a diagnostic to receive a plain-language action.";
    $("approve").disabled = !action;
    $("verify").classList.toggle("hidden", uiState.stage !== "verifying");
    renderEscalation(uiState.escalation_card || null);
}

async function sendMessage(text, approved = false) {
    if (!text || isSubmitting) return null;
    isSubmitting = true;
    try {
        const response = await fetch(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, user_text: text, user_approved: approved }) });
        if (!response.ok) throw new Error(`Agent API returned ${response.status}`);
        const data = await response.json();
        addTranscript("agent", data.reply_text);
        renderState(data.ui_state || {});
        speak(data.reply_text);
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
const API_URL = "http://localhost:3002/agent/message";
const sessionId = sessionStorage.getItem("meetassist-session") || crypto.randomUUID();
sessionStorage.setItem("meetassist-session", sessionId);

const $ = (id) => document.getElementById(id);
let lastUserText = "";
let recognition;

function addMessage(role, text) {
    const item = document.createElement("div");
    item.className = `msg ${role}`;
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "YOU" : "AI";
    const content = document.createElement("div");
    const sender = document.createElement("b");
    sender.textContent = role === "user" ? "YOU" : "AGENT";
    const body = document.createElement("p");
    body.textContent = text;
    content.append(sender, body);
    item.append(avatar, content);
    $("transcript").appendChild(item);
    $("transcript").scrollTop = $("transcript").scrollHeight;
}

function speak(text) {
    if (!text || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
}

function checklistItem(item) {
    if (typeof item === "string") return { title: item, detail: "", state: "current" };
    const state = item.state || item.status || (item.passed ? "done" : "error");
    return {
        title: item.title || item.name || item.check || "Diagnostic check",
        detail: item.detail || item.message || item.result || "",
        state: state === "passed" ? "done" : state,
    };
}

function renderChecklist(items) {
    const timeline = $("timeline");
    timeline.replaceChildren();
    items.map(checklistItem).forEach((item) => {
        const row = document.createElement("div");
        row.className = `step ${item.state}`;
        const icon = document.createElement("i");
        icon.textContent = item.state === "done" ? "✓" : item.state === "error" ? "✗" : "•";
        const content = document.createElement("div");
        const title = document.createElement("b");
        title.textContent = item.title;
        const detail = document.createElement("p");
        detail.textContent = item.detail;
        content.append(title, detail);
        row.append(icon, content);
        timeline.appendChild(row);
    });
    $("diagnosis").classList.toggle("hidden", items.length === 0);
    $("progress").textContent = `${items.filter((item) => checklistItem(item).state === "done").length} / ${items.length}`;
}

function renderState(uiState) {
    const intent = uiState.issue || uiState.current_intent || "Waiting for your issue";
    $("title").textContent = intent.replaceAll("_", " ");
    $("subtitle").textContent = uiState.stage ? `Support stage: ${uiState.stage}` : "Voice support is ready.";
    renderChecklist(uiState.diagnosis_checklist || uiState.diagnosis || []);

    const pendingAction = uiState.pending_action || uiState.recommended_action;
    $("approval").classList.toggle("hidden", !pendingAction);
    if (pendingAction) {
        $("approval").querySelector("h3").textContent = "Recommended action";
        $("approval").querySelector("p").textContent = String(pendingAction).replaceAll("_", " ");
    }

    const escalation = uiState.escalation_card;
    $("escalation").classList.toggle("hidden", !escalation);
    if (escalation) {
        $("escalation h3").textContent = `Ticket ${escalation.ticket_id || "created"}`;
        $("escalation p").textContent = escalation.reason || escalation.symptom || "Diagnostics have been routed to support.";
        $("escalation .evidence").innerHTML = "";
        [
            ["Routing", escalation.routing_team || "IT Helpdesk"],
            ["Diagnostics", (escalation.diagnostics_run || []).length],
            ["Actions", (escalation.actions_attempted || []).length],
        ].forEach(([label, value]) => {
            const tag = document.createElement("span");
            tag.textContent = `${label}: ${value}`;
            $("escalation .evidence").appendChild(tag);
        });
        $("ticket").classList.add("hidden");
    }
}

async function sendMessage(text, approved = false) {
    const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user_text: text, user_approved: approved }),
    });
    if (!response.ok) throw new Error(`Agent API returned ${response.status}`);
    const data = await response.json();
    addMessage("agent", data.reply_text);
    renderState(data.ui_state || {});
    speak(data.reply_text);
    return data;
}

function setListening(listening) {
    $("mic").classList.toggle("listening", listening);
    $("voiceStatus").textContent = listening ? "Listening..." : "Tap to speak to support";
}

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onerror = (event) => {
        setListening(false);
        $("voiceStatus").textContent = event.error === "not-allowed" ? "Microphone permission is blocked" : "Voice input failed";
    };
    recognition.onend = () => setListening(false);
    recognition.onresult = async (event) => {
        const text = event.results[0][0].transcript.trim();
        if (!text) return;
        lastUserText = text;
        addMessage("user", text);
        $("voiceStatus").textContent = "Thinking...";
        try {
            await sendMessage(text);
            $("voiceStatus").textContent = "Response ready. Tap to speak again";
        } catch (error) {
            $("voiceStatus").textContent = "Could not reach support";
            addMessage("agent", error.message);
        }
    };
} else {
    $("fallback").classList.remove("hidden");
    $("voiceStatus").textContent = "Voice input is unavailable in this browser";
}

$("mic").addEventListener("click", () => {
    if (!recognition) return;
    if ($("mic").classList.contains("listening")) recognition.stop();
    else recognition.start();
});

$("approve").addEventListener("click", async () => {
    if (!lastUserText) return;
    $("approval").classList.add("hidden");
    $("verify").classList.remove("hidden");
    try {
        await sendMessage(lastUserText, true);
    } catch (error) {
        addMessage("agent", error.message);
    } finally {
        $("verify").classList.add("hidden");
    }
});

async function submitText(text) {
    if (!text.trim()) return;
    lastUserText = text.trim();
    addMessage("user", lastUserText);
    try {
        await sendMessage(lastUserText);
    } catch (error) {
        addMessage("agent", error.message);
    }
}

$("send").addEventListener("click", () => {
    const input = $("message");
    submitText(input.value);
    input.value = "";
});

$("updateIssue").addEventListener("click", () => {
    const input = $("issueInput");
    submitText(input.value);
    input.value = "";
});

$("new").addEventListener("click", () => window.location.reload());

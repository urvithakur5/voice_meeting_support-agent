# AI IT Incident Triage Agent

## 1. Product Overview

**Product Name:** AI IT Incident Triage Agent  
**Product Type:** Voice-first AI IT helpdesk / incident triage system  
**Primary Domain:** IT Helpdesk  
**Initial Scenario Focus:** Device, meeting-audio/video, connectivity, and common endpoint issues  
**Primary Interaction:** Real-time voice  
**Core Loop:** Speak → Understand → Diagnose → Act → Verify → Resolve or Escalate

### One-line product definition

> An AI agent that turns a non-technical employee's vague IT complaint into a diagnosed, verified, or technician-ready incident.

### Core value proposition

The system acts as the first diagnostic layer between an employee and human IT support. It reduces repetitive Tier-1 discovery by collecting symptoms, asking adaptive questions, performing approved diagnostics, using trusted troubleshooting knowledge, verifying results, and handing unresolved incidents to a human technician with the diagnostic context already collected.

---

## 2. Problem Statement

Employees often report IT problems in vague, non-technical terms. A human IT technician may then need to ask repetitive follow-up questions, determine the technical category, perform basic diagnosis, and repeat troubleshooting that may already have been attempted by the user or another support person.

When an issue is escalated, the next technician may receive too little diagnostic context and have to repeat the discovery process.

### Problem we are solving

> Employees need a simple way to explain what is wrong without diagnosing it themselves, while IT technicians need structured, evidence-backed incident information instead of a vague support request.

### Product response

The AI IT Incident Triage Agent converts a natural-language or spoken complaint into an adaptive diagnostic workflow, uses trusted knowledge and approved tools, verifies attempted fixes, and creates a structured incident when human IT support is required.

---

## 3. Goals

### Primary goals

1. Allow an employee to describe an IT problem naturally through voice.
2. Detect the likely issue area without forcing the employee to choose a technical category first.
3. Ask only the questions that materially change the diagnostic path.
4. Retrieve relevant troubleshooting knowledge using RAG.
5. Call deterministic diagnostic tools and interpret their structured results.
6. Guide or perform approved corrective actions.
7. Verify whether the problem was actually resolved.
8. Automatically escalate unresolved incidents.
9. Give the human technician a complete, readable incident summary.
10. Make the diagnosis visible in the frontend as it progresses.

### Success principle

The agent should reduce the gap between:

**"Something is wrong."**

and

**"Here is what happened, what we checked, what we tried, what failed, and what IT should investigate next."**

---

## 4. Users and Roles

## 4.1 Employee

The employee is the person experiencing the IT issue.

### Employee can

- Start a support session.
- Describe an issue using natural speech.
- Answer follow-up questions.
- Approve supported actions when required.
- See diagnosis progress.
- See recommended actions.
- Confirm whether the issue is fixed.
- Receive confirmation when resolved.
- Receive an incident/reference number when escalated.

### Employee should NOT need to

- Know technical terminology.
- Select the correct troubleshooting category before starting.
- Explain the root cause.
- Repeat information already provided.

---

## 4.2 IT Technician

The technician is the human support person responsible for unresolved incidents.

### Technician can

- View incoming incidents.
- Open an incident.
- Read the original employee complaint.
- View diagnostic results.
- View actions already attempted.
- View verification status.
- View the AI-generated summary.
- See the recommended support area/team.
- Change the incident status.
- Continue the investigation from the collected evidence.

### Technician should NOT need to

- Re-ask every basic diagnostic question already answered.
- Infer what the employee originally meant.
- Reconstruct which checks the AI already performed.

---

## 5. Core User Journey

```text
EMPLOYEE
   ↓
Describe IT problem
   ↓
AI understands symptom
   ↓
AI asks adaptive questions
   ↓
AI retrieves relevant knowledge
   ↓
AI calls diagnostic tools
   ↓
AI explains evidence
   ↓
AI proposes / performs approved action
   ↓
AI verifies result
   ↓
 ┌───────────────┐
 │ Problem fixed? │
 └───────┬───────┘
      YES│     │NO
         ↓     ↓
      RESOLVE  CREATE INCIDENT
                    ↓
              TECHNICIAN
                    ↓
             Human investigation
```

---

## 6. Frontend Requirements

## 6.1 Employee Dashboard

The employee experience should be a focused single-page support interface.

### Required sections

- Product/header area
- Voice input control
- Connection/session status
- Live transcript
- Current issue / detected intent
- Diagnosis timeline
- Recommended action card
- Approval control when needed
- Verification result
- Escalation result

### Example diagnosis display

```text
CURRENT INCIDENT
Microphone issue

DIAGNOSTICS
✓ Microphone detected
✓ Device connected
✗ Microphone permission blocked

NEXT STEP
Allow microphone access

[ Approve & Test ]
```

### Requirements

- Diagnosis updates must appear as the agent progresses.
- Diagnostic states must originate from tool/system results, not invented by the language model.
- The interface must show when the agent is checking something.
- Voice must have a usable text/transcript fallback.
- The employee should always know whether the case is still being diagnosed, resolved, or escalated.

---

## 6.2 Technician Dashboard

The technician view should be intentionally small and focused.

### Required views

**Incident list**

- Incident ID
- Short issue summary
- Employee
- Status
- Priority/severity indicator
- Created time

**Incident detail**

- Original employee statement
- Detected issue/category
- Questions answered
- Diagnostic results
- Knowledge/recommendation used
- Actions attempted
- Approval history where applicable
- Verification result
- Likely problem area
- Recommended team/route
- AI-generated handoff summary

### Example

```text
INCIDENT #1042

Employee: Alex Sharma
Issue: Nobody can hear me during my meeting.
Status: Needs human IT support

DIAGNOSTICS
✓ Microphone detected
✓ Device connected
✗ Application permission blocked
✓ Network available

ACTIONS ATTEMPTED
• Checked microphone state
• Checked permission state
• User approved retry
• Verification failed

AI SUMMARY
The microphone hardware is detected and connected. The
available evidence points to an application/permission issue.
The attempted recovery did not restore microphone input.

RECOMMENDED AREA
Endpoint / Application Support
```

---

## 7. Microsoft Foundry Agent Requirements

The Foundry agent is responsible for reasoning and orchestration. It must not fabricate technical state.

### Agent responsibilities

1. Understand the employee's natural-language problem.
2. Maintain conversation state.
3. Identify the likely issue area.
4. Decide which question should be asked next.
5. Decide when a diagnostic tool should be called.
6. Interpret structured tool results.
7. Retrieve relevant troubleshooting knowledge.
8. Explain findings in plain language.
9. Decide whether an action is appropriate.
10. Request approval for actions requiring user confirmation.
11. Verify the result after an action.
12. Decide whether the issue is resolved or should be escalated.
13. Generate the structured technician handoff.
14. Create an incident when escalation is required.

### Agent behavior rules

- Do not require the employee to select a technical category before speaking.
- Ask the minimum useful question needed to advance the diagnosis.
- Do not ask for information already present in the conversation state.
- Never invent diagnostic results.
- Never claim a tool was called when it was not.
- Never claim an issue is fixed without a verification step.
- Do not directly invent or execute arbitrary system changes.
- Use only approved tools and approved actions.
- Explain important findings in simple language.
- Escalate when evidence indicates the issue cannot be resolved safely or reliably.
- Preserve all relevant evidence for technician handoff.

---

## 8. Agent Automation / Orchestration

The target behavior is an automated agentic workflow rather than a question-and-answer chatbot.

### Automated flow

```text
1. Receive employee statement
2. Detect likely issue
3. Check existing conversation state
4. Decide next question OR diagnostic tool
5. Call the selected diagnostic tool
6. Receive structured result
7. Interpret result
8. Retrieve relevant RAG content if needed
9. Determine next diagnostic step
10. Propose or execute an approved action
11. Verify using a diagnostic/test tool
12. If resolved → close incident
13. If unresolved → create structured incident
14. Update technician dashboard
```

### Example

```text
Employee:
"My microphone isn't working."

Agent → check_microphone()

Tool:
{
  "detected": true,
  "connected": true,
  "permission": false,
  "device": "Bluetooth Headset"
}

Agent reasoning outcome:
- Hardware/device exists
- Device is connected
- Permission is blocked
- Permission troubleshooting is now relevant

Agent → retrieve microphone permission SOP

Agent → explain finding

Agent → request approval if required

Agent → approved_action(...)

Agent → check_microphone()

If verification passes:
    Resolve

If verification fails:
    create_incident(...)
```

### Automation requirement

The system should allow the agent to choose the next valid operation dynamically rather than hard-coding one fixed conversation script for every incident.

---

## 9. Diagnostic Tool Requirements

Diagnostic functions must return deterministic structured data.

### Required initial tools

#### `check_microphone()`

Possible fields:

```json
{
  "detected": true,
  "connected": true,
  "permission": false,
  "muted": false,
  "selected_device": "Bluetooth Headset"
}
```

#### `check_camera()`

Possible fields:

```json
{
  "detected": true,
  "connected": true,
  "permission": true,
  "in_use": false
}
```

#### `check_speaker()`

Possible fields:

```json
{
  "output_device": "Headset",
  "volume": 64,
  "muted": false,
  "detected": true
}
```

#### `check_connectivity()`

Possible fields:

```json
{
  "internet": true,
  "latency_ms": 48,
  "packet_loss_percent": 1
}
```

#### `check_app_state()`

Possible fields:

```json
{
  "application": "Teams",
  "running": true,
  "signed_in": true,
  "version": "<version>"
}
```

#### `run_test()`

Possible fields:

```json
{
  "test_type": "audio_test",
  "result": "pass"
}
```

#### `create_incident()`

Must accept structured incident data and return a unique incident ID.

Example:

```json
{
  "ticket_id": "IT-1042",
  "status": "open"
}
```

### Tool rules

- Read-only diagnostics should be callable without approval where appropriate.
- Write/action tools must use a narrow action schema.
- Sensitive actions require explicit employee approval.
- Tool errors must return structured failure states.
- Tool timeouts must be handled gracefully.
- The agent must not fabricate a tool result after a failed call.

### Real-diagnostics requirement

Where a diagnostic can be safely obtained from the actual user environment, the tool should return real system information. The frontend must not display a hard-coded success/failure result while presenting it as live detection.

For prototype environments where a specific OS/permission cannot be accessed reliably, the UI and documentation must label the limitation rather than presenting simulated values as real telemetry.

---

## 10. RAG Requirements

RAG is the knowledge layer used to support diagnosis and troubleshooting.

### Initial knowledge base

Create a small, trusted collection containing:

```text
01_microphone_troubleshooting.md
02_camera_troubleshooting.md
03_audio_output_troubleshooting.md
04_connectivity_troubleshooting.md
05_application_permission_troubleshooting.md
06_escalation_rules.md
```

### RAG behavior

- Retrieve only relevant troubleshooting information.
- Prefer approved procedures and internal SOPs where available.
- Do not use retrieved documents as proof that a diagnosis is true.
- Combine retrieved knowledge with actual diagnostic evidence.
- Do not recommend actions outside the approved troubleshooting procedures.

### Important distinction

**RAG tells the agent what should be checked or recommended.**  
**Tools tell the agent what is actually happening in the environment.**

---

## 11. Incident Creation and Escalation

The agent must create an incident when:

- The issue remains unresolved after approved troubleshooting.
- A required action is outside the agent's permissions.
- Diagnostic evidence indicates human investigation is required.
- A safe automated recovery cannot be performed.
- A tool failure prevents reliable diagnosis.

### Incident must include

- Incident ID
- Employee identity or demo identity
- Original complaint
- Detected issue
- Conversation findings
- Diagnostics and timestamps where available
- Knowledge/recommendation used
- Actions attempted
- Approval status
- Verification result
- Final outcome
- Likely problem area
- Recommended technician/team

### Handoff principle

The technician should be able to continue the investigation without restarting the entire discovery process.

---

## 12. Data Model

A minimal incident object should contain:

```json
{
  "incident_id": "IT-1042",
  "employee_id": "EMP-001",
  "employee_name": "Alex Sharma",
  "status": "needs_technician",
  "issue_type": "microphone",
  "user_report": "Nobody can hear me during my meeting.",
  "questions_answered": [],
  "diagnostics": [],
  "knowledge_used": [],
  "actions_attempted": [],
  "verification": {},
  "likely_area": "application_permission",
  "recommended_team": "Endpoint Support",
  "created_at": "<timestamp>"
}
```

A real application may later add priority, SLA, technician assignment, comments, audit events, and resolution codes.

---

## 13. Identity and Access

### Prototype

Keep identity simple and avoid building a custom enterprise authentication system unless the existing environment already provides it.

The prototype should support two logical roles:

- Employee
- Technician

### Production direction

Use Microsoft Entra ID and least-privilege access for backend and agent resources where applicable.

### Security requirements

- Never expose secrets in browser code.
- Never place credentials inside prompts.
- Restrict tool access to approved operations.
- Require explicit approval for sensitive actions.
- Log diagnostic calls and action results.
- Preserve an auditable record of approvals and outcomes.

---

## 14. Functional Requirements

### FR-01
Employee can start a voice support session.

### FR-02
Agent understands free-form descriptions of IT incidents.

### FR-03
Agent can initially handle at least four issue classes:

- Microphone/audio input
- Camera/video
- Speaker/audio output
- Connectivity/joining

### FR-04
Agent maintains conversation state.

### FR-05
Agent avoids repeating questions already answered.

### FR-06
Agent selects the next diagnostic question or tool based on current evidence.

### FR-07
Agent can call deterministic diagnostic tools.

### FR-08
Agent can retrieve relevant troubleshooting knowledge.

### FR-09
Agent explains diagnostic findings in plain language.

### FR-10
Sensitive corrective actions require explicit confirmation.

### FR-11
Agent verifies the outcome after a corrective action.

### FR-12
Agent can determine whether the incident is resolved or needs escalation.

### FR-13
Agent can create a structured incident.

### FR-14
Technician can view incidents and their diagnostic evidence.

### FR-15
Frontend visibly reflects diagnosis, action, verification, and escalation state.

### FR-16
The system provides a text/transcript fallback if live voice is unavailable.

---

## 15. Non-Functional Requirements

### Reliability

- The happy-path demo must complete reliably.
- Tool failures must degrade gracefully.
- A failed tool call must never produce fabricated diagnostic output.

### Performance

- Voice interaction should feel conversational.
- The UI should indicate when a tool or retrieval operation is in progress.

### Safety

- No arbitrary device/account changes.
- No destructive actions.
- Sensitive actions require approval.

### Auditability

Record:

- Tool called
- Tool result
- Action proposed
- Approval status
- Action result
- Verification result
- Escalation decision

---

## 16. Initial Demo Scenarios

## Scenario A: Microphone

Employee:

> "Nobody can hear me in my meeting."

Expected flow:

```text
Detect microphone issue
→ ask useful clarifying question(s)
→ check microphone
→ explain result
→ retrieve appropriate procedure
→ guide/perform approved action
→ verify
→ resolve OR escalate
```

## Scenario B: Camera

Employee:

> "My camera is just black."

Possible diagnostic areas:

- Camera detected
- Camera in use by another application
- Privacy/permission state
- Application access
- Device state

## Scenario C: Speaker

Employee:

> "I can see everyone but I can't hear anything."

Possible diagnostic areas:

- Mute
- Volume
- Selected output device
- Headset connection
- Application output device

## Scenario D: Connectivity

Employee:

> "My meeting won't let me join."

Possible diagnostic areas:

- Internet availability
- Connectivity quality
- Application state
- Sign-in/session state
- Meeting link/session symptoms

---

## 17. Acceptance Criteria

The MVP is considered successful when all of the following are true:

### Employee experience

- [ ] Employee can describe a problem naturally.
- [ ] Agent identifies the likely issue without requiring category selection.
- [ ] Agent asks adaptive questions.
- [ ] Agent does not repeat known information.

### Diagnostics

- [ ] At least one diagnostic tool returns real or explicitly documented environment data.
- [ ] Tool outputs are structured.
- [ ] Frontend displays tool-backed diagnostic results.
- [ ] Agent never invents tool results.

### RAG

- [ ] Agent can retrieve relevant troubleshooting content.
- [ ] Retrieved content influences the next recommended troubleshooting step.

### Actions

- [ ] Agent only recommends approved actions.
- [ ] Sensitive actions require approval.
- [ ] Agent performs verification afterward.

### Escalation

- [ ] Failed cases create a structured incident.
- [ ] Incident contains diagnostics and attempted actions.
- [ ] Technician dashboard displays the incident.
- [ ] Technician can understand the case without repeating the entire initial discovery.

### Demo

- [ ] One resolved scenario works end-to-end.
- [ ] One unresolved scenario works end-to-end.
- [ ] The unresolved scenario reaches the technician dashboard.

---

## 18. Implementation in Existing Environment

### Existing assets to preserve

- Existing frontend
- Existing Microsoft Foundry Agent
- Existing speech/voice integration
- Existing deployed agent/environment

### Build order

#### Step 1: Reframe existing agent

Rename/reposition it as the **AI IT Incident Triage Agent**.

#### Step 2: Update Foundry instructions

Add the role, diagnostic rules, tool-selection behavior, approval rules, verification rules, and escalation behavior defined in this document.

#### Step 3: Add RAG

Upload and index the small troubleshooting knowledge base.

#### Step 4: Add diagnostic tools

Implement the minimum deterministic tools, starting with `check_microphone()`.

#### Step 5: Wire tools into Foundry

Expose the tool schemas to the agent and allow the agent to decide when to call them.

#### Step 6: Implement verification

After any corrective action, run the relevant diagnostic/test again.

#### Step 7: Implement incident creation

Create a structured incident when resolution fails.

#### Step 8: Build the technician view

Implement incident list + incident detail view.

#### Step 9: Connect employee → incident → technician

Ensure `create_incident()` writes data that the technician dashboard can read.

#### Step 10: Polish the demo

Add diagnosis timeline, loading/tool states, clear status messages, and a reliable fallback path.

---

## 19. Recommended MVP Priority

### P0: Must work

- Voice conversation
- Agent instructions
- Adaptive diagnosis
- One real diagnostic tool
- RAG
- Verification
- Incident creation
- Technician handoff
- Employee dashboard
- Technician dashboard

### P1: Add if time permits

- Camera diagnostic
- Speaker diagnostic
- Connectivity diagnostic
- Additional issue scenarios
- Improved routing/team recommendation
- More detailed audit log

### P2: Future production integration

- ServiceNow or another real ITSM platform
- Entra-based enterprise identity and role mapping
- Real enterprise endpoint-management integrations
- Direct Teams administrator diagnostics
- Organization-wide analytics
- SLA/routing automation

---

## 20. Explicitly Out of Scope for the MVP

Do not build:

- A full ServiceNow clone
- A complete enterprise identity platform
- Direct unrestricted control of employee devices
- Automatic password/account provisioning
- Automatic destructive or high-risk changes
- A large multi-agent hierarchy
- A massive analytics portal
- Integrations with every collaboration platform

The MVP should prove the **diagnostic intelligence + evidence-rich human handoff** rather than attempt to replace an enterprise IT stack.

---

## 21. Final Product Definition

**DOMAIN:** IT Helpdesk  
**PRODUCT:** AI IT Incident Triage Agent  
**PRIMARY USER:** Company employee with an IT problem  
**SECONDARY USER:** Human IT technician  
**INTERFACE:** Voice-first employee experience + technician dashboard  
**CORE PROBLEM:** Vague complaints + repetitive diagnosis + poor escalation context  
**CORE LOOP:** Speak → Diagnose → Act → Verify → Escalate  
**CORE DIFFERENTIATOR:** Conversational diagnosis and evidence-rich technician handoff  
**AI COMPONENTS:** Microsoft Foundry Agent + voice + RAG + tool/function calling  
**HUMAN HANDOFF:** Structured incident containing symptoms, diagnostics, actions, verification, and recommended next area

### Final positioning

> **We are building the conversational diagnostic layer between a non-technical employee and human IT support.**

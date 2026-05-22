# Multi-Provider Chat Interface Follow-up

> **Purpose:** expand the first rudimentary chat panel from its
> Copilot-first proof into a multi-provider surface that can launch and
> render Claude, Codex, and Gemini through the shared adapter model,
> with normalized transcript semantics, attach/resume handling, and
> capability-aware UX.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/043-multi-provider-chat-interface-followup/`
> **Prerequisites:**
> - Set 038 (`038-claude-launch-adapter`) CLOSED.
> - Set 040 (`040-codex-launch-adapter`) CLOSED.
> - Set 041 (`041-gemini-launch-adapter`) CLOSED.
> - Set 042 (`042-rudimentary-chat-interface-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** this set broadens a UI surface across multiple CLIs with
> different capabilities and failure modes. It needs both automated IDE
> coverage and human validation of the capability-aware UX.

---

## Project Overview

- Session 1 standardizes the transcript/event/resume model across the
  now-available provider adapters.
- Sessions 2-3 add the remaining providers and capability-aware UX.
- The goal is a multi-provider rudimentary chat surface, not feature
  parity with each vendor's native TUI.
- Non-goals:
  - reproducing every vendor-specific slash command or tool inspector;
  - hiding provider limitations instead of surfacing them honestly;
  - collapsing Dabbler `chatSessionId` and native provider resume tokens
    into one field.

---

## Sessions

### Session 1 of 4: Discovery and normalization plan for multi-provider chat

**Steps:**
1. Inventory the output/event/resume differences across Claude, Codex,
   and Gemini now that their launch adapters exist.
2. Lock a normalized transcript/event model for the chat UI, including
   how unsupported features appear.
3. Decide which providers get full prompt-mode transcript rendering,
   which get attach-only first, and which require explicit capability
   banners.
4. Capture the plan in a discovery note before expanding the UI.

**Creates:**
- `docs/session-sets/043-multi-provider-chat-interface-followup/discovery-notes.md`

**Touches:**
- chat UI planning notes as needed

**Ends with:** a locked normalization plan for multi-provider chat
expansion.

**Progress keys:**
- `session-001/provider-gaps-inventoried`
- `session-001/transcript-model-frozen`
- `session-001/capability-banners-decided`
- `session-001/round-a-verification`

---

### Session 2 of 4: Add Claude and Codex integration to the chat UI

**Steps:**
1. Add Claude and Codex execution paths to the chat panel using the
   normalized transcript model.
2. Render capability-aware controls so unsupported modes or attach paths
   are shown honestly rather than silently missing.
3. Add focused unit and Layer-2 coverage for the new provider paths.
4. Keep Copilot behavior stable while the provider matrix expands.

**Creates:**
- Claude/Codex chat integration and tests

**Touches:**
- chat panel/provider integration code

**Ends with:** the chat panel can handle Claude and Codex in addition to
Copilot.

**Progress keys:**
- `session-002/claude-chat-added`
- `session-002/codex-chat-added`
- `session-002/capability-controls-rendered`
- `session-002/layer2-tests-green`

---

### Session 3 of 4: Add Gemini, attach/resume UX, and richer status rendering

**Steps:**
1. Add Gemini integration according to the locked capability model from
   Set 041.
2. Introduce attach/resume UX where supported and explicit limitation
   messaging where not.
3. Add richer but still minimal status rendering: provider, model,
   effort, and attach state.
4. Add Layer-3 coverage for a representative multi-provider flow.

**Creates:**
- Gemini chat integration and multi-provider UI tests

**Touches:**
- chat panel/provider integration code and status UI

**Ends with:** the rudimentary chat UI supports the full provider set the
launch adapters made available.

**Progress keys:**
- `session-003/gemini-chat-added`
- `session-003/attach-ux-added`
- `session-003/status-rendering-added`
- `session-003/layer3-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run regression coverage for the multi-provider chat surface.
2. Produce the ad-hoc UAT checklist for provider switching, transcript
   clarity, attach/resume behavior, and failure states.
3. Update docs and roadmap notes for any follow-on polish set that the
   UI still needs.
4. Write `change-log.md` and close the set.

**Creates:**
- `docs/session-sets/043-multi-provider-chat-interface-followup/change-log.md`
- `docs/session-sets/043-multi-provider-chat-interface-followup/043-multi-provider-chat-interface-followup-uat-checklist.json`

**Touches:**
- chat UI docs and provider integration docs as needed

**Ends with:** a multi-provider rudimentary chat surface exists with
honest capability signaling and regression coverage.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
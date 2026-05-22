# Rudimentary Chat Interface Foundations (Copilot-First)

> **Purpose:** build the first in-extension chat surface only if opening a
> vendor TUI is not sufficient, starting with a minimal Copilot-first
> panel that proves transcript persistence, prompt submission, and shared
> `beginSession()` integration before multi-provider expansion.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/042-rudimentary-chat-interface-foundations/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> - Set 039 (`039-copilot-launch-adapter`) CLOSED.
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

> **Rationale:** this set introduces a brand-new operator-visible UI
> surface inside the extension. It needs both IDE-level coverage and a
> human judgment pass on layout, transcript clarity, and error handling.

---

## Project Overview

- This set answers the product question directly: if Dabbler wants more
  than "open the vendor TUI in a terminal," then yes, a rudimentary chat
  interface is required.
- The scope is deliberately limited to a Copilot-first proof so the UI
  shape lands before multi-provider complexity arrives.
- Deliverables: a minimal chat panel/webview, transcript persistence,
  prompt composer, session picker, and prompt-mode Copilot integration.
- Non-goals:
  - multi-provider event normalization;
  - streaming/tool timeline parity with vendor TUIs;
  - replacing the vendor TUI for advanced workflows.

---

## Sessions

### Session 1 of 4: Discovery and minimal-UX boundary for the chat panel

**Steps:**
1. Inventory the extension's current webview/view surfaces and choose the
   minimal viable chat host (panel, view, or existing surface extension).
2. Lock the transcript persistence model, failure states, and what the
   first Copilot-first UX will and will not show.
3. Decide how the chat panel relates to `Launch As...` / `Attach As...`
   so the product story stays coherent.
4. Capture the UI contract in a discovery note before implementation.

**Creates:**
- `docs/session-sets/042-rudimentary-chat-interface-foundations/discovery-notes.md`

**Touches:**
- chat/UI planning notes as needed

**Ends with:** a frozen minimal UX contract for the first in-extension
chat surface.

**Progress keys:**
- `session-001/ui-host-chosen`
- `session-001/transcript-model-locked`
- `session-001/launch-chat-story-aligned`
- `session-001/round-a-verification`

---

### Session 2 of 4: Scaffold the panel/webview and transcript store

**Steps:**
1. Build the panel/webview host and minimal layout shell.
2. Add transcript persistence and session selection/state restoration.
3. Add the prompt composer and message rendering primitives.
4. Add focused tests for storage/state transitions.

**Creates:**
- chat panel/webview implementation
- transcript store/state plumbing

**Touches:**
- extension activation and webview assets as needed

**Ends with:** a local chat shell exists with persistent transcript
state, even before provider execution is wired.

**Progress keys:**
- `session-002/chat-shell-added`
- `session-002/transcript-store-added`
- `session-002/prompt-composer-added`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Wire Copilot prompt-mode execution through `beginSession()`

**Steps:**
1. Submit prompts through the shared launch boundary and the Copilot
   adapter's prompt-mode path.
2. Render user/assistant turns, loading states, and failure/refusal
   states honestly.
3. Decide whether the first UI exposes model/effort selection inline or
   reuses the launch profile picker.
4. Add Layer-2 and Layer-3 coverage for the first end-to-end chat flow.

**Creates:**
- Copilot-first chat execution wiring and tests

**Touches:**
- chat UI assets and Copilot adapter surfaces as needed

**Ends with:** a rudimentary in-extension chat can send a prompt and
render the result through the shared launch boundary.

**Progress keys:**
- `session-003/copilot-chat-wired`
- `session-003/failure-states-rendered`
- `session-003/profile-selection-decided`
- `session-003/layer3-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the first chat panel.
2. Produce the ad-hoc UAT checklist for transcript feel, prompt
   submission, restore behavior, and failure handling.
3. Update docs so the next set can expand from a stable Copilot-first
   UI rather than re-deciding the foundations.
4. Write `change-log.md`.

**Creates:**
- `docs/session-sets/042-rudimentary-chat-interface-foundations/change-log.md`
- `docs/session-sets/042-rudimentary-chat-interface-foundations/042-rudimentary-chat-interface-foundations-uat-checklist.json`

**Touches:**
- chat UI docs and extension docs as needed

**Ends with:** the first in-extension chat surface exists and is ready
for multi-provider expansion.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
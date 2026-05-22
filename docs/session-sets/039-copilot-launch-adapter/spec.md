# Copilot Launch Adapter

> **Purpose:** implement the first fully documented provider adapter for
> the shared launch boundary, using the live Copilot CLI surface to ship
> `CopilotLaunchAdapter`, attach behavior, model/effort mapping, and
> honest operator-facing launch flows.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/039-copilot-launch-adapter/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
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

> **Rationale:** Copilot is the first concrete provider launch adapter,
> with real operator-visible launch/attach behavior and CLI integration
> that needs both automated coverage and manual validation.

---

## Project Overview

- Session 1 is the pinned Copilot discovery pass: docs, local CLI help,
  auth expectations, `--session-id`, `--effort`, permission rules,
  `COPILOT_HOME`, JSONL output, and OTel model probes.
- Sessions 2-3 implement `CopilotLaunchAdapter`, attach/resume behavior,
  and actual-model capture.
- This set is the prerequisite for the first rudimentary chat-interface
  set, which is intentionally Copilot-first.
- Non-goals:
  - multi-provider chat UI;
  - undocumented Copilot env vars as contract inputs;
  - loosening `start_session` refusal semantics.

---

## Sessions

### Session 1 of 4: Discovery and local characterization for Copilot CLI

**Steps:**
1. Re-run the official-docs and local-help audit for the pinned Copilot
   CLI version in the repo environment.
2. Lock the accepted model/effort/session-id/permission/output flags and
   identify which behaviors remain doc-backed versus locally
   characterized only.
3. Capture the exact `COPILOT_HOME`, prompt-mode, attach/resume, and
   actual-model-probe strategy for implementation.

**Creates:**
- `docs/session-sets/039-copilot-launch-adapter/discovery-notes.md`

**Touches:**
- Copilot-specific planning notes as needed

**Ends with:** a pinned Copilot adapter contract that future sessions can
implement without reopening discovery.

**Progress keys:**
- `session-001/copilot-docs-confirmed`
- `session-001/local-cli-characterized`
- `session-001/otel-strategy-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `CopilotLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement the interactive and prompt-mode launch mappings for model,
   effort, session mode, permission policy, and `COPILOT_HOME`.
2. Pass Dabbler's UUID-shaped chat id through `--session-id` for new
   launches when appropriate.
3. Add focused tests for argv/env generation, especially `--allow-all`
   versus `--allow-all-tools`, attach-mode flags, and `max` effort.
4. Wire the adapter into the shared registry.

**Creates:**
- Copilot adapter implementation and focused tests

**Touches:**
- shared launch registry and command surfaces as needed

**Ends with:** a working launch-plan generator for Copilot backed by
unit tests.

**Progress keys:**
- `session-002/copilot-adapter-added`
- `session-002/session-id-passthrough-wired`
- `session-002/permission-mapping-wired`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Attach/resume, actual-model reporting, and IDE wiring

**Steps:**
1. Implement the operator attach flow for `--continue` / `--resume` or
   an explicit limitation if native attach is not stable enough.
2. Add actual-model reporting using the best documented path available
   (OTel when enabled, otherwise non-silent stdout parsing).
3. Add Layer-2 and Layer-3 coverage for the launch and attach surfaces,
   using a safe fake/stub strategy where the real CLI cannot run in CI.
4. Validate refusal and recovery UX when `start_session` or Copilot
   launch fails.

**Creates:**
- Copilot launch/attach integration tests

**Touches:**
- Copilot-facing command surfaces and status UI

**Ends with:** Copilot launch and attach behavior is wired into the
extension with honest model reporting and failure handling.

**Progress keys:**
- `session-003/attach-path-added`
- `session-003/model-reporting-wired`
- `session-003/layer3-tests-green`
- `session-003/failure-ux-verified`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the Copilot adapter and command
   flows.
2. Produce the ad-hoc UAT checklist for launch, attach, prompt mode,
   and error recovery.
3. Update docs, including any operator-facing setup instructions that
   changed after the real adapter landed.
4. Write `change-log.md` and mark this set as the chat-foundations
   prerequisite.

**Creates:**
- `docs/session-sets/039-copilot-launch-adapter/change-log.md`
- `docs/session-sets/039-copilot-launch-adapter/039-copilot-launch-adapter-uat-checklist.json`

**Touches:**
- Copilot-specific docs and shared launch docs as needed

**Ends with:** Copilot is the first end-to-end launch adapter and is
ready to support the first in-extension chat-interface set.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
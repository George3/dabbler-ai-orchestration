# Claude Launch Adapter

> **Purpose:** bring Claude Code onto the same launch-adapter contract as
> the other providers, so Claude launch and attach behavior stops being a
> special-case installer path and becomes a normal `LaunchAdapter`
> implementation backed by the shared `beginSession()` boundary.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/038-claude-launch-adapter/`
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
effort: medium
```

> **Rationale:** Claude already has hook plumbing, but this set changes
> operator-visible launch/attach behavior and needs IDE-visible regression
> coverage plus human validation of the external CLI flow.

---

## Project Overview

- Session 1 discovers the current Claude Code launch surface: model,
  effort, mode, permissions, hook payload, and any native attach/resume
  affordances.
- Sessions 2-3 implement `ClaudeLaunchAdapter` and reconcile it with the
  existing SessionStart hook installer from Set 036.
- Non-goals:
  - replacing Claude Code's own transcript UI;
  - building the Dabbler chat panel;
  - weakening the writer-side `chatSessionId` guarantees from Set 036.

---

## Sessions

### Session 1 of 4: Discover and characterize Claude Code launch surfaces

**Steps:**
1. Read the current Claude Code docs and locally characterize the CLI
   help surface for model, effort, plan/autonomous modes, permissions,
   hook payload, and any attach/resume behavior.
2. Verify how Claude's native `session_id` / hook metadata should map to
   Dabbler's `dabblerChatSessionId` and whether any reconciliation note
   is needed after Set 037.
3. Capture stable versus version-sensitive surfaces in a discovery note
   that the implementation sessions can treat as ground truth.

**Creates:**
- `docs/session-sets/038-claude-launch-adapter/discovery-notes.md`

**Touches:**
- local docs references as needed

**Ends with:** a pinned description of the Claude launch surface and its
mapping to the shared launch contract.

**Progress keys:**
- `session-001/claude-docs-read`
- `session-001/local-cli-characterized`
- `session-001/chat-id-mapping-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `ClaudeLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement `ClaudeLaunchAdapter` against the shared registry and launch
   boundary from Set 037.
2. Map Claude model, effort, and mode selections onto the shared
   `SessionProfile` and `SessionMode` contract.
3. Decide and implement Claude-specific isolation semantics (cwd,
   config-home, and any environment shaping) without reintroducing file
   watchers.
4. Add focused unit tests for argv/env generation.

**Creates:**
- Claude-specific adapter implementation and tests

**Touches:**
- shared launching registry and extension command surfaces as needed

**Ends with:** a working Claude launch-plan builder backed by tests.

**Progress keys:**
- `session-002/claude-adapter-added`
- `session-002/claude-argv-mapped`
- `session-002/isolation-policy-wired`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Unify hook installer, attach flow, and actual-model reporting

**Steps:**
1. Rework the Claude hook installer and any launch commands so they flow
   through the shared launch contract rather than parallel one-off code.
2. Add the attach story for existing Claude chats/sessions where the
   local CLI surface supports it; otherwise surface the limitation
   honestly in the UI.
3. Implement actual-model capture/reporting for Claude launch results if
   the CLI exposes a stable source.
4. Add Layer-2 coverage for the command and hook/launch integration.

**Creates:**
- integration tests for Claude launch/hook wiring

**Touches:**
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
- Claude-facing launch/attach commands

**Ends with:** Claude launch, hook install, and attach behavior all flow
through the same adapter path.

**Progress keys:**
- `session-003/hook-installer-unified`
- `session-003/attach-path-added`
- `session-003/model-reporting-wired`
- `session-003/layer2-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for Claude command, hook, and launch
   flows.
2. Produce an ad-hoc UAT checklist covering launch, attach, and failure
   states.
3. Update docs and handoff notes so the chat-interface sets can treat
   Claude as a normal adapter.
4. Write `change-log.md`.

**Creates:**
- `docs/session-sets/038-claude-launch-adapter/change-log.md`
- `docs/session-sets/038-claude-launch-adapter/038-claude-launch-adapter-uat-checklist.json`

**Touches:**
- Claude-specific docs and shared launch docs as needed

**Ends with:** Claude is fully onboarded to the shared launch-adapter
surface and documented for downstream chat UI work.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
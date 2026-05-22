# LaunchAdapter Foundations + Set 036 Reconciliation

> **Purpose:** reconcile the launch-adapter roadmap with Set 036's
> `chatSessionId` / watcher-scope plan, then land the shared
> extension-side `beginSession()` boundary, adapter registry, and
> launch-host plumbing that all provider-specific adapter sets depend
> on.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/037-launch-adapter-foundations/`
> **Prerequisites:** None. Set 036 remains an adjacent planning surface;
> Session 1 explicitly reconciles the two plans before shared code lands.
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

> **Rationale:** this set changes the VS Code extension's operator-facing
> command surface and establishes the shared launch boundary that will
> open external CLIs. Layer-3 coverage is warranted for the visible IDE
> flow, and ad-hoc UAT is warranted because the behavior crosses the IDE
> plus external terminal/CLI boundary.

---

## Project Overview

- Set 036 remains authoritative for writer-side identity,
  `chatSessionId`, and watcher-scope discipline.
- This set becomes authoritative for extension-side launch orchestration:
  `BeginSessionRequest`, `BeginSessionResult`, `LaunchPlan`,
  `LaunchAdapter`, adapter registration, and terminal-launch hosting.
- Downstream provider sets plug backend-specific argv/env rules into the
  shared contract defined here.
- Non-goals:
  - backend-specific flag mapping beyond fake/stub adapters;
  - a Dabbler-owned chat transcript UI;
  - replacing `python -m ai_router.start_session` / `close_session` as
    the lifecycle boundary.

---

## Sessions

### Session 1 of 4: Reconcile Set 036 and lock the shared launch contract

**Steps:**
1. Compare Set 036, [coding-assistant-adapter-spec.md](../../../coding-assistant-adapter-spec.md), and the existing extension command surfaces.
2. Record every overlap or conflict, especially around `chatSessionId`,
   native resume tokens, provider launch identity, and whether any Set
   036 wording needs an addendum or direct edit.
3. Freeze the shared extension-side contract for `BeginSessionRequest`,
   `BeginSessionResult`, `LaunchPlan`, `LaunchAdapter`, and provider
   capability metadata.
4. Declare the dependency DAG for the downstream Claude, Copilot,
   Codex, Gemini, and chat-interface sets.
5. Verify the reconciliation with a routed analysis review before moving
   to implementation.

**Creates:**
- `docs/session-sets/037-launch-adapter-foundations/reconciliation-notes.md`

**Touches:**
- `docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/spec.md`
- `coding-assistant-adapter-spec.md`

**Ends with:** a written reconciliation that makes Set 036 and the new
launch roadmap non-contradictory, plus a frozen shared contract for the
provider sets.

**Progress keys:**
- `session-001/036-reconciled`
- `session-001/shared-contract-frozen`
- `session-001/downstream-dag-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `beginSession()` boundary + adapter registry

**Steps:**
1. Add the TypeScript types and services for `BeginSessionRequest`,
   `BeginSessionResult`, `LaunchPlan`, `LaunchArtifacts`, and
   `LaunchAdapter`.
2. Implement the shared `beginSession()` flow: generate `new_chat_id`
   when needed, call `start_session`, stop on ownership refusal, and
   return a provider-agnostic launch plan.
3. Add an adapter registry and capability model so the extension can ask
   which providers support interactive launch, prompt mode, native
   resume, and actual-model probes.
4. Add unit tests with a fake adapter so the provider-specific sets only
   have to prove mapping logic, not the orchestration skeleton.

**Creates:**
- `tools/dabbler-ai-orchestration/src/launching/LaunchAdapter.ts`
- `tools/dabbler-ai-orchestration/src/launching/beginSession.ts`
- `tools/dabbler-ai-orchestration/src/launching/adapterRegistry.ts`
- shared test coverage for the boundary service

**Touches:**
- `tools/dabbler-ai-orchestration/src/extension.ts`
- existing command-registration surfaces that need the shared launcher

**Ends with:** a provider-agnostic launch boundary with unit tests and
no provider-specific CLI assumptions baked into the shared service.

**Progress keys:**
- `session-002/launch-types-added`
- `session-002/begin-session-boundary-wired`
- `session-002/adapter-registry-added`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Add `Launch As...` / `Attach As...` command surface + launch host

**Steps:**
1. Introduce honest operator commands for launch and attach, rather than
   overloading `Check Out As...`.
2. Add a terminal launch host that can open an interactive CLI session
   from a `LaunchPlan` and capture a prompt-mode invocation when the
   adapter requests one-shot execution.
3. Decide how the legacy checkout command degrades: retire it, bridge it,
   or keep it as a low-level recovery affordance.
4. Surface capability-aware UI copy so unsupported launch modes are
   disabled rather than implied.
5. Add Layer-2 coverage for the new commands and fake-adapter launch host.

**Creates:**
- launch-host service(s)
- capability-aware launch/attach commands

**Touches:**
- `tools/dabbler-ai-orchestration/package.json`
- `tools/dabbler-ai-orchestration/src/commands/`
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`

**Ends with:** the extension can invoke the shared launch boundary and
open a provider-specific session through a real launch/attach surface.

**Progress keys:**
- `session-003/launch-command-added`
- `session-003/attach-command-added`
- `session-003/launch-host-wired`
- `session-003/layer2-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and downstream handoff

**Steps:**
1. Run focused unit, Layer-2, and Layer-3 coverage for the shared launch
   surfaces.
2. Produce the ad-hoc UAT checklist for the operator-visible launch and
   attach flows.
3. Update roadmap/docs so the downstream provider sets inherit the final
   contract rather than stale proposal text.
4. Write `change-log.md` and explicitly hand off to the provider sets as
   the next DAG frontier.

**Creates:**
- `docs/session-sets/037-launch-adapter-foundations/change-log.md`
- `docs/session-sets/037-launch-adapter-foundations/037-launch-adapter-foundations-uat-checklist.json`

**Touches:**
- shared docs and extension docs touched by the new launch contract

**Ends with:** the shared launch foundation is documented, tested,
operator-validated, and ready for provider-specific adapters.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
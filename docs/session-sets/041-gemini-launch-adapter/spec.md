# Gemini Launch Adapter

> **Purpose:** onboard Gemini to the shared launch-adapter contract with
> an explicit discovery step that decides the target binary/surface,
> then implement a stable `GeminiLaunchAdapter` without speculative
> assumptions about soon-changing CLI behavior.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/041-gemini-launch-adapter/`
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

> **Rationale:** Gemini has the highest discovery risk because the CLI
> surface is in flux. The set still ends in operator-visible IDE launch
> behavior, so it needs both automated coverage and manual validation.

---

## Project Overview

- Session 1 is a go/no-go discovery pass: confirm whether the target is
  the current Gemini CLI, its replacement surface, or a temporarily
  gated adapter.
- Sessions 2-3 implement `GeminiLaunchAdapter` only against the locked
  discovery verdict, including model/thinking/effort mapping and prompt
  output handling.
- Non-goals:
  - shipping against undocumented or obviously sunset-only behavior;
  - treating Gemini config files as an ownership signal;
  - the in-extension chat transcript UI.

---

## Sessions

### Session 1 of 4: Discovery and target-binary decision for Gemini

**Steps:**
1. Read the current Gemini documentation and locally inspect the CLI (or
   successor) surface for model selection, prompt mode, JSON/stream
   output, thinking/effort controls, permissions, and resume behavior.
2. Decide whether the implementation target is the current Gemini CLI, a
   successor binary, or a capability-gated placeholder if the surface is
   too unstable.
3. Capture the decision and the exact adapter contract in a discovery
   note that future sessions treat as the locked source of truth.

**Creates:**
- `docs/session-sets/041-gemini-launch-adapter/discovery-notes.md`

**Touches:**
- Gemini planning notes as needed

**Ends with:** a documented target decision that prevents speculative
Gemini implementation.

**Progress keys:**
- `session-001/gemini-docs-read`
- `session-001/local-cli-characterized`
- `session-001/target-binary-locked`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `GeminiLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement the launch-plan mapping for the chosen Gemini surface,
   including model, mode, permissions, and any thinking/effort mapping.
2. Add capability gating when the chosen surface cannot yet support a
   requested feature.
3. Add focused argv/env tests so unstable CLI details stay localized to
   the adapter.
4. Register the adapter with the shared launch registry.

**Creates:**
- Gemini adapter implementation and focused tests

**Touches:**
- shared launch registry and command surfaces as needed

**Ends with:** Gemini has a working launch-plan generator for the locked
target surface.

**Progress keys:**
- `session-002/gemini-adapter-added`
- `session-002/capability-gating-wired`
- `session-002/argv-mapping-tested`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Output handling, actual-model reporting, and IDE wiring

**Steps:**
1. Implement the best stable machine-readable or text-output handling
   path for prompt-mode Gemini runs.
2. Add actual-model reporting from the most reliable surfaced signal.
3. Add Layer-2 and Layer-3 coverage for launch, failure, and any attach
   or limitation UX.
4. Confirm the operator UX honestly reflects unsupported Gemini features
   instead of implying parity where none exists.

**Creates:**
- Gemini launch integration tests

**Touches:**
- Gemini-facing command surfaces and UI messaging

**Ends with:** Gemini launch behavior is integrated into the extension
with honest capability reporting.

**Progress keys:**
- `session-003/output-path-wired`
- `session-003/model-reporting-wired`
- `session-003/layer3-tests-green`
- `session-003/capabilities-honest`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the Gemini adapter and command
   flows.
2. Produce the ad-hoc UAT checklist for launch, limitations, and error
   handling.
3. Update docs and operator guidance based on the locked target-binary
   decision.
4. Write `change-log.md` and close the set.

**Creates:**
- `docs/session-sets/041-gemini-launch-adapter/change-log.md`
- `docs/session-sets/041-gemini-launch-adapter/041-gemini-launch-adapter-uat-checklist.json`

**Touches:**
- Gemini-specific docs and shared launch docs as needed

**Ends with:** Gemini is onboarded to the shared launch path with clear
documentation of any remaining limits.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
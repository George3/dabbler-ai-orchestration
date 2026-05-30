# Verdict — Set 053 S1 (design-lock)

**Date:** 2026-05-29
**Status:** LOCKED (operator-directed reframe)

## The locked design (simple)

**Embed the schema-drift scan into the script-driven session lifecycle.**

- **`start_session`** runs the existing drift scan (`detect_drift` from
  `check_migrations.py`) after it writes its own file: scan
  `docs/session-sets/*/session-state.json`, print a terse one-line
  warning if any set is sub-current. **Non-blocking** (warn, never fail —
  honors the operator-locked "old schema is acceptable" non-goal). Reuses
  existing logic; no new detection code.
- **`close_session`** optionally emits the same scan as a soft note at
  the close boundary.
- **`check_migrations`** stays exactly as-is: an **optional, manual**
  tool anyone *may* wire into CI if they want — never required.

That's it. The session lifecycle CLI is the universal trigger: every
orchestrator (Claude, Copilot, Codex, human) runs `start_session` /
`close_session` at every boundary, on every host (GitHub, Azure, none),
independent of editor or CI. No editor hook, no CI job, no git hook, no
baseline file, no Copilot-specific anything.

## What was DROPPED and why

The CI-centric design from the proposal — **CI required-check, git
pre-commit/pre-push hooks, the baseline-allowlist file, the Azure/GitHub
wrappers, the `--fix`/`--validate-content` additions** — is **all
dropped.** Reasons:

1. **Operator steer (decisive):** "stop adding sophistication; just add
   the check to the script that writes `session-state.json`." Correct.
2. **The lifecycle CLI is already the universal trigger.** The inventory
   proved every writer already stamps `schemaVersion` from the constant,
   so a file written *through* the framework is never stale; the only
   real vector is hand-authoring that bypasses the writers. The natural
   place to catch that is the next CLI run — not external machinery.
3. **CI is an unreliable substrate** (operator: GitHub Actions "OFTEN
   FAIL"). Building a *reliability* guard on a flaky, host-specific layer
   is backwards. The CLI check has no such dependency.

## Honest record of the audit process (for the lesson)

The cross-provider consensus (gemini-pro + gpt-5-4, $0.0362, see
[`consensus-output.md`](consensus-output.md)) **confirmed CI as the
centerpiece** and both providers killed the baseline-allowlist. But the
*entire CI frame was wrong*, and the consensus could not see that —
because the orchestrator handed the models a text framing that already
presupposed CI/hooks/allowlist. The models were good critics *within* the
frame and incapable of escaping it; their "agreement" was correlated
error, not independent validation. The reframe came from the operator,
who had domain context and no anchor. Lesson banked in
[[feedback_prefer_lifecycle_simplicity_over_good_sounding_architecture]]:
prefer baking logic into the existing lifecycle over external machinery;
treat cross-provider agreement as correlated; ask "simplest thing?" not
"critique my architecture."

## Open-question dispositions (collapsed)

- **Q1/Q8 centerpiece:** the session-lifecycle CLI (`start_session`),
  not CI. Resolved.
- **Q2 hooks / Q3 CI packaging / Q6 required-for-merge / Q13 Azure
  specifics:** DROPPED (no CI, no hooks).
- **Q4 writer hardening:** already satisfied (inventory). A light
  convention test is optional, not required — left to S2's discretion.
- **Q5 advisory:** a one-line "never hand-edit `schemaVersion`" note may
  be added to `narration.py` templates if cheap; not load-bearing.
- **Q7/Q11/Q12 baseline / scan-scope / escape hatch:** MOOT — the scan
  is a non-blocking warning, so there is nothing to allowlist or escape.
  "Old schema acceptable" is honored by the warning being non-fatal.
- **Q9 `--fix` / Q10 content-validation:** DEFERRED — not needed for the
  warn-only lifecycle scan. Could be future `check_migrations` polish.

## Locked scope (collapsed 3 → 2 sessions)

- **S1 (this session):** audit + reframe + design-lock. Done.
- **S2:** implement the `start_session` drift scan (+ optional soft
  `close_session` note), reusing `detect_drift`; tests; doc note in
  `ai-led-session-workflow.md` that the guard now rides the CLI lifecycle
  (host/editor/CI-agnostic); version bump; close-out. Marketplace
  extension untouched (this is an `ai_router` change) unless the Claude
  invoker note needs trimming.

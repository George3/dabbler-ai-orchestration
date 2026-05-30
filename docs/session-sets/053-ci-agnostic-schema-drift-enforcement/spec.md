# Lifecycle-Embedded Schema-Drift Detection Spec

> **AUDIT-LOCKED 2026-05-29 (S1).** Reframed from the original
> CI-centric stub to a deliberately minimal design per operator
> direction. The verdict and audit record are at
> [`docs/proposals/2026-05-29-ci-agnostic-drift-enforcement/`](../../proposals/2026-05-29-ci-agnostic-drift-enforcement/).
>
> **Purpose:** Set 050 shipped schema-drift detection but wired its only
> automatic trigger into a **Claude Code editor hook**, so it never fires
> for the **GitHub Copilot** staff who make up most of the team. The fix
> is NOT new machinery (CI jobs, git hooks, allowlists) — it is to move
> the existing drift scan into the **script-driven session lifecycle**
> (`start_session` / `close_session`), which every orchestrator runs at
> every boundary regardless of editor, host, or CI.
>
> **Created:** 2026-05-29 · **Audit-locked:** 2026-05-29
> **Session Set:** `docs/session-sets/053-ci-agnostic-schema-drift-enforcement/`
> (slug retained from the stub; the scope is narrower than "CI-agnostic"
> implies — the point is it's *lifecycle*-embedded, which is inherently
> CI/host/editor-agnostic.)
> **Prerequisite:** Set 050 (shipped — provides `detect_drift` /
> `check_migrations` this set re-triggers).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
```

> Rationale: a small `ai_router` change (a warning printed by
> `start_session`/`close_session`) plus a doc note. No browser-visible UI;
> covered by unit tests.

---

## Project Overview

### Motivation

Set 050's guard fires from `~/.claude/settings.json` →
`claude-session-start-invoker.js` — a **Claude Code editor hook**. Most
staff use **GitHub Copilot**, which has no equivalent session-start hook,
so they get no automatic drift warning. The original instinct (this set's
stub) was to add CI enforcement + git hooks + a baseline-allowlist. That
was over-engineered:

- **The inventory proved every writer already stamps `schemaVersion` from
  the constant** (`SCHEMA_VERSION` / `SCHEMA_VERSION_V4`, Python and TS).
  A file written *through* the framework's CLI is never stale. The only
  real failure vector is **hand-authoring that bypasses the writers**
  (the harvester incident).
- **The session-lifecycle CLI is the universal trigger.**
  `start_session` and `close_session` are run by *every* orchestrator
  (Claude, Copilot, Codex, human) at *every* session boundary, on *every*
  host. They are not editor hooks and not CI — they are the commands the
  workflow already mandates. Putting the scan there reaches everyone with
  zero new infrastructure.
- **CI is an unreliable, host-specific substrate** (operator: GitHub
  Actions "OFTEN FAIL"). A reliability guard should not depend on it.

### What this set delivers

1. **`start_session` runs the drift scan after writing its file.** It
   calls the existing `detect_drift` (from `check_migrations.py`) across
   `docs/session-sets/*/session-state.json` and prints a terse one-line
   warning when any set is sub-current. **Non-blocking** — a warning,
   never a failure (honors Set 050's "old schema is acceptable" non-goal).
2. **`close_session` optionally emits the same scan as a soft note** at
   the close boundary.
3. **A doc note** in `ai-led-session-workflow.md` recording that the
   drift guard now rides the CLI lifecycle (host/editor/CI-agnostic), so
   Copilot and every other orchestrator are covered.
4. `check_migrations` is unchanged and remains an **optional, manual**
   tool anyone *may* run or wire into CI — never required.

### Non-goals

- **No CI enforcement, no git hooks, no baseline-allowlist file, no
  per-host wrappers.** Explicitly rejected as unnecessary machinery on an
  unreliable substrate (S1-locked).
- **No blocking behavior.** The scan warns; it never fails a command or
  blocks a session. "Old schema is acceptable" (Set 050) stands.
- **No new detection logic.** Reuses `detect_drift`. No new migrator, no
  schema change.
- **No coverage of full-bypass setups** (an ancient install that never
  runs the modern CLI). That is an adoption problem (use the framework),
  not an enforcement-machinery problem, and is already mitigated (the
  harvester was upgraded). Accepted residual.
- **Marketplace extension unchanged** unless the Set 050 Claude invoker
  note needs a one-line trim; this is an `ai_router` change.

---

## Sessions

### Session 1 of 2: Audit & design-lock — DONE (2026-05-29)

Inventoried every Python + TS state writer (all already stamp from the
constant) and the trigger surface. Ran a cross-provider consensus that
confirmed the CI frame — which the operator then correctly rejected in
favor of the lifecycle-embedded design. Locked the minimal scope.
Verdict + consensus record + the process lesson are in the proposal dir.

**Progress keys:** design-locked; scope collapsed 3 → 2 sessions; verdict
committed.

### Session 2 of 2: Implement + test + doc + close-out

**Steps:**
1. Add a drift-scan call to `start_session` after the state write: invoke
   `detect_drift` over `docs/session-sets/*`, print one terse warning line
   on drift, silent when clean. Non-blocking; fail-open on scan errors
   (a scan failure must never break `start_session`).
2. Add the same as a soft note in `close_session` (optional per
   implementation judgment — `start_session` is the primary trigger).
3. Tests: drift present → warning emitted; clean → silent; scan-error →
   `start_session` still succeeds. Reuse the `check_migrations` fixtures.
4. Doc note in `ai-led-session-workflow.md` (the guard rides the CLI
   lifecycle; Copilot/Codex/human all covered; `check_migrations` stays
   optional).
5. Version bump (`ai_router` PyPI), CHANGELOG, CLAUDE.md walk,
   change-log.md.
6. Cross-provider verification; close-out; publish **held** for operator
   tag-push.

**Ends with:** running `start_session` in any repo (any editor/host)
prints a drift warning when a set is sub-current; tests green; doc
updated; version bumped.
**Progress keys:** lifecycle scan shipped + tested; doc updated; version
bumped; close-out verdict recorded.

---

## End-of-set deliverables

- `start_session` emits a non-blocking drift warning via `detect_drift`
  (+ optional `close_session` soft note).
- Tests (drift / clean / scan-error-non-fatal).
- `ai-led-session-workflow.md` note that the guard rides the CLI
  lifecycle.
- Version bump + CHANGELOG + change-log; publish held for operator.
- `check_migrations` unchanged (optional manual tool).

# Set 053 Change Log

**Lifecycle-embedded schema-drift advisory — audit/reframe (S1) +
implementation (S2).**

Set 050 shipped schema-drift detection but wired its only automatic
trigger into a Claude Code `SessionStart` editor hook, so it never fired
for the GitHub Copilot staff who make up most of the team (and consumer
repos may host on Azure DevOps, not GitHub). This set moves the warning
into the **script-driven session lifecycle** — `start_session` (primary)
and `close_session` (soft note) — so it reaches every orchestrator
(Claude, Copilot, Codex, human) at every boundary on every host, with no
editor hook, CI job, or git hook required.

The S1 audit is itself part of the record: a CI-centric design (CI
required-check + git hooks + a baseline-allowlist) was proposed and run
past a cross-provider panel that *confirmed* it — then the operator
rejected the entire frame ("just add the check to the script that writes
session-state.json; CI OFTEN FAILS"), which was correct. The inventory's
load-bearing fact (every writer already stamps `schemaVersion` from the
constant, so the only real vector is hand-authoring) had pointed at the
lifecycle CLI all along. See
[`docs/proposals/2026-05-29-ci-agnostic-drift-enforcement/`](../../proposals/2026-05-29-ci-agnostic-drift-enforcement/).
Companion PyPI release: `dabbler-ai-router 0.13.0`. No Marketplace
extension release this set (`ai_router`-only).

## Session 1 — Audit & design-lock

Closed 2026-05-29 with disposition `completed`.

- Inventoried every Python + TS state writer (all already stamp
  `schemaVersion` from the constant) and the Set 050 trigger surface.
- Authored a CI-centric proposal; ran a 2-provider adversarial consensus
  (gemini-pro + gpt-5-4, $0.0362) that confirmed CI-as-centerpiece and
  rejected the baseline-allowlist.
- Operator reframe → locked the minimal lifecycle-embedded design;
  CI / git-hooks / baseline-allowlist all dropped; scope collapsed
  3 → 2 sessions. Process lesson banked to memory.
- Routed cost $0.0362 of $10 NTE.
- Commits: `820d150` (deliverables) ← `75d7503` (S1 close-out flip).

## Session 2 — Implementation

Closed 2026-05-29 with disposition `completed`.

- `check_migrations.summarize_drift(scan_root)` — terse, ASCII-only,
  non-blocking, fail-open one-line drift warning (reuses `detect_drift`);
  returns `None` when clean or on any error.
- `start_session` runs it after the boundary write and prints to stderr
  (primary lifecycle trigger; never changes the exit status).
- `close_session` emits the same as a soft note to stderr after a close.
- Tests: 6 `summarize_drift` unit tests (drift / clean / missing-version
  / ASCII-only / fail-open-on-bad-root / swallows-internal-errors) + 3
  `start_session` integration tests (emits-but-exit-OK / silent-when-clean
  / scan-error-non-fatal).
- Dogfood proof: `start_session` in this repo now warns about its 46
  sub-current sets and still exits 0.
- Doc: `ai-led-session-workflow.md` records that the guard rides the CLI
  lifecycle (Copilot/Codex/human covered; `check_migrations` stays
  optional).
- `dabbler-ai-router` 0.12.0 → 0.13.0 (`pyproject.toml` + `__init__` +
  CHANGELOG); this change-log. Marketplace extension unchanged (0.25.0).
- Cross-provider verification; close-out; publish **held** for operator
  tag-push (`v0.13.0`).

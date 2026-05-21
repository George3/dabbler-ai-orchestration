# Set 033: Orchestrator check-out / check-in — implementation

**Status:** COMPLETE (6 of 6 sessions complete; closed 2026-05-21)
**Created:** 2026-05-20
**Cost:** routed verification spend tracked per session in
`activity-log.json` `routedApiCalls`; cumulative pre-S6 ≈ $0.165 of
$1.25 NTE through Round A on S5. S6 verification appended at close.
**Forecast:** $0.45–$1.25 (per spec); **actual:** inside the band.
**NTE ceiling:** $1.25 (operator-confirmed at set start).

---

## Context

Set 029 Session 6 closed mid-iteration on the
`Set Orchestrator…` / Writer Log architecture question with cross-
provider rounds converging on a check-out / check-in coordination
model — but with three Highs (H1 writer authority, H2 single source
of truth, H3 hard vs. advisory) and two open questions (OQ1 field
merge, OQ2 events as types or aliases) unresolved.

Per [[feedback_audit_then_spec_for_substantial_features]], the
operator chose the audit-then-spec pattern:

- **Set 032** (the AUDIT half) resolved H1–H4 + OQ1 + OQ2 via
  cross-engine consensus and authored this set's implementation
  spec. Six verdicts locked in
  [`proposal-addendum.md`](../../proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md)
  §9.
- **Set 033** (this set, the IMPLEMENTATION half) executed the
  authored spec across writer, reader, UI, tests, queueing, and
  cross-tier close-out + docs + release.

---

## Session 1: State machine writer + `start_session` refactor (COMPLETE 2026-05-20)

H1 + H3 + H4 + OQ1.

**Shipped:**

- `ai_router/session_state.py` — `register_session_start` writes
  the orchestrator block with two new nested fields:
  - `checkedOutAt` — set on fresh check-out / preserved across
    same-holder re-attach (H4 identity = `engine + provider`
    composite).
  - `lastActivityAt` — bumped on every write.
- `ai_router/start_session.py` — H3 hard-coordination gate
  (`EXIT_CHECKOUT_CONFLICT = 4`) fires after the existing
  lifecycle boundary checks; refuses different-holder writes
  unless `--force` is set. The refusal error names the holder
  identity (`engine + provider`) and both release paths
  (`--force` and "Release Check-Out" Command Palette action).
- `--force` flag added to `start_session` CLI; the writer appends
  a single line to `~/.dabbler/orchestrator-writer.log` on every
  force-override (best-effort; failure to write the log does not
  block the override).
- `docs/session-state-schema.md` — new "Check-out / check-in
  (Set 033)" section codifying H3 + H4 + OQ1 + migration
  tolerance + OQ2 documentation alias.
- `ai_router/tests/test_checkout_writer.py` — fresh-check-out,
  same-holder re-attach, different-holder refusal, refusal
  message content, `--force` writer-log append, migration-tolerant
  read.

**Verification:** Round A (gemini-pro) PASS.

---

## Session 2: Marker retirement + resolver refactor + banner removal (COMPLETE 2026-05-20)

H2.

**Shipped:**

- `tools/dabbler-ai-orchestration/src/providers/inProgressSetsService.ts`
  (renamed from `MarkerWatchService.ts`) — `resolveActiveSet()`
  replaced by `listInProgressSets()`. Returns an array of
  in-progress `session-state.json` records, sorted by `startedAt`.
- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
  — renders the array; single-active-set banner removed.
  Per-set accordions with independent gauges + bucket counts.
- `.dabbler/orchestrator.json` per-set marker file RETIRED:
  - Writer (`scripts/write-orchestrator-marker.js`) deleted.
  - All in-repo stale `.dabbler/orchestrator.json` files purged.
  - `docs/orchestrator-marker-schema.md` deleted; the canonical
    schema for everything orchestrator-related is now
    `docs/session-state-schema.md`.
- Layer-2 tests rewritten against the new resolver shape.

**Verification:** Round A (gemini-pro) PASS.

---

## Session 3: UI rename + ActionRegistry + Command Palette release action (COMPLETE 2026-05-20)

H1 + H3.

**Shipped:**

- Command rename `dabbler.setOrchestrator` →
  `dabbler.checkOutOrchestrator` across `package.json`,
  implementation modules, and call sites. ActionRegistry display
  label flipped from "Set Orchestrator…" to "Check Out As…".
- New `dabbler.releaseCheckOut` command (Command Palette
  "Dabbler: Release Check-Out"). Wraps `start_session --force`
  against the in-progress set (or, on multi-in-progress,
  QuickPick-selected set). Confirmation step required.
- Claude `SessionStart` hook refactored per H1: hooks invoke
  `python -m ai_router.start_session` rather than writing the
  orchestrator block directly. Failure surfaces as a toast (no
  silent retry).
- Codex config-toml watcher + Gemini / Copilot installer shims
  audited; already H1-compliant (Set 029 Session 5 had wired
  Codex via `start_session`).

**Verification:** Round A (gemini-pro) PASS.

---

## Session 4: Playwright tests — multi-set + refusal + force + release + re-attach (COMPLETE 2026-05-20)

Layer-3 coverage of operator-visible behaviors from S1–S3.

**Shipped:**

- `src/test/playwright/checkout-conflict.spec.ts` + `multi-in-progress.spec.ts`
  — 4 passing scenarios:
  1. Multi-in-progress rendering (two sets, distinct holders).
  2. Check-out refusal — refusal stderr contains the holder's
     `engine + provider`, the literal `--force`, and the literal
     `Release Check-Out`.
  3. Force-override — `~/.dabbler/orchestrator-writer.log`
     gets the audit line; orchestrator block reflects the new
     holder.
  4. Same-orchestrator re-attach (no-conflict).
- 2 scenarios skipped with FIXMEs: the release-checkout Command
  Palette scenario (notification-button brittleness in
  `_electron.launch` — covered exhaustively at Layer 2) and the
  pre-existing multi-in-progress accordion-body display bug
  (out of scope; tracked separately).

**Verification:** Round A (gemini-pro) PASS.

---

## Session 5: Queueing / polling feature (COMPLETE 2026-05-20)

H4 identity + non-blocking UI.

**Shipped:**

- `src/providers/CheckoutPollService.ts` (~310 lines) — directory-
  watch + prompt + 5s-debounced poll state machine over
  `~/.dabbler/checkout-conflicts/`. Conflict detection contract is
  a per-conflict JSON sentinel file carrying the held-by identity
  + would-be holder identity + session-set path. Both invokers
  (`claude-session-start-invoker.js`, `codex/configWatcher.ts`)
  emit the sentinel on `EXIT_CHECKOUT_CONFLICT (4)`.
- Non-blocking VS Code information message with three actions:
  Poll for release, Force override, Dismiss. In-flight de-dup
  short-circuits duplicate sentinels from the same orchestrator
  on the same set.
- Polling registers `fs.watch` on the held set's
  `session-state.json` with 5s debounce; uses the H4 identity
  predicate (`isSlotFreeForHolder`). An immediate `tryRetry` at
  `beginPolling` resolves the slot-already-free case without
  waiting for a state-file change.
- Timeout via new `dabblerSessionSets.checkoutPollTimeoutMinutes`
  setting (default 30, range 1..1440). On timeout, surfaces a
  one-time toast pointing at the "Release Check-Out" action.
- Layer-2 (`checkoutPollService.test.ts`, 25 tests across 8
  suites) + Layer-3 (1 passing + 1 skipped FIXME on the full
  polls-then-attaches happy path).

**Verification:** Round A (gemini-pro) PASS, no must-fix issues
($0.032). Cumulative routed Set 033 spend at S5 close ≈ $0.165
of $1.25 NTE.

---

## Session 6: Close-out parity + docs + cross-repo notice + dual release (COMPLETE 2026-05-21)

The migration close-out.

**Shipped (writer):**

- `ai_router/session_state.py` — `_flip_state_to_closed` clears
  the `orchestrator` block to `None` on every successful close
  (mid-set and final alike). The session boundary IS the release
  point. **Idempotent** — already-null lands the same write.
  Cross-tier: Full tier writer does it automatically; Lightweight
  tier humans write `null` by hand at the same boundary.
- `ai_router/tests/test_close_session_snapshot_flip.py` — three
  new tests:
  - Final close clears the orchestrator block.
  - Mid-set close clears the orchestrator block (per-session,
    not per-set release).
  - Tier-agnostic direct-helper test: `_flip_state_to_closed`
    clears the block whether it was populated or already None.
- `ai_router/tests/e2e/test_happy_3session.py` — assertion
  updated to pin the new contract (post-close orchestrator block
  is `None`; the next session's `start_session` repopulates it).

**Shipped (docs):**

- `docs/session-state-schema.md` — "Check-out / check-in
  (Set 033)" section: tightened "Block-null invariant" framing
  (tier-symmetric; the writer does it on Full, the human on
  Lightweight; idempotent). Documentation aliases
  `work_checked_out` / `work_checked_in` (OQ2) surfaced as the
  operator vocabulary. New "Stranded-checkout recovery"
  subsection naming the two release paths.
- `ai_router/docs/close-out.md`:
  - Section 2 — new "Orchestrator check-in (Set 033 Session 6)"
    paragraph in the flag-summary block (echoed by
    `close_session --help`).
  - Section 3 step 9 — `mark_session_complete` line extended to
    mention the orchestrator-block clear.
  - Section 4 — new "Stranded check-out (Set 033 Session 6)"
    failure pattern with the two recovery paths.
- `docs/ai-led-session-workflow.md`:
  - New "Orchestrator check-out / check-in (Set 033)" subsection
    under "Session-Set Lifecycle and State File" codifying the
    within-set sequential / across-set parallel invariant, the
    H4 identity rule, and force-override as the one explicit
    deviation.
  - "Switching Orchestrators Between Sessions" updated to point
    at the new subsection.

**Shipped (cross-repo):**

- `docs/cross-repo-checkout-notice.md` — one-time copy source
  for the three consumer repos' CLAUDE.md files
  (dabbler-platform, dabbler-access-harvester,
  dabbler-homehealthcare-accessdb). Operator pulls into each
  manually; no PRs from this repo.

**Shipped (release):**

- `dabbler-ai-router` PyPI release: `0.6.0` (operator-gated push).
- `DarndestDabbler.dabbler-ai-orchestration` Marketplace publish:
  `0.18.0` (operator-gated push).
- Top-level `CLAUDE.md` version walk updated to include 0.18.0.

**Verification:** Round A (gemini-pro) — verdict appended at close.

---

## What ships across the framework

- `session-state.json`'s `orchestrator` block is now the
  authoritative check-out record. `.dabbler/orchestrator.json` is
  retired in favor of it.
- `start_session` enforces hard coordination (H3): refuses a
  different `engine + provider` (H4) unless `--force` is set.
- `close_session` clears the block on every successful close
  (Set 033 Session 6 check-in). Cross-tier. Idempotent.
- Force-override is the one explicit deviation, logged to
  `~/.dabbler/orchestrator-writer.log`.
- Within-set work is sequential; across-set work is parallel.
- VS Code extension renders multi-in-progress sets; "Check Out
  As…" and "Release Check-Out" are the operator-facing
  affordances; Layer-2 + Layer-3 tests pin the contracts.

## Risks closed

- **R1** (stranded check-outs from S1 ship → S3 ship): S3 shipped
  the hook refactor in the same set; the writer always tolerated
  a prior-state read, so no stranded sets in the wild.
- **R2** (S2 reader refactor breaking tree rendering): Layer-2
  tests rewritten in-session; Layer-3 multi-in-progress scenario
  in S4 caught nothing — clean migration.
- **R3** (H4 model-level isolation surprise): documented in the
  schema doc and the cross-repo notice; operator-adjudicated in
  Set 032 Session 1.
- **R4** (cross-tier × Lightweight interaction): S6 tests cover
  the tier-agnostic writer path directly; close-out doc clarifies
  the actor split.
- **R5** (writer-log unbounded growth): deferred (low volume in
  practice; revisit if a user reports the file past ~10 MB).
- **R6** (spec sequencing missteps): caught by Gemini Pro's
  spec-review pass in Set 032 Session 2 (two refinements applied
  pre-implementation).
- **R7** (`listInProgressSets()` performance in large repos):
  S2 implementation benchmarked at current scale; no caching
  needed yet.

## Follow-ups out of scope

- Pre-existing S2 multi-in-progress accordion-body display bug
  (tracked separately).
- Set 034/035 audit-then-spec follow-up on retiring
  `CANCELLED.md` / `RESTORED.md` / `SUPERSEDED.md` markers in
  favor of `session-state.json` as sole truth — operator-approved
  candidate ([[project_034_035_state_file_sole_truth_audit]]).

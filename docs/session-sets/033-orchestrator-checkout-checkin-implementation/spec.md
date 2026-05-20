# Orchestrator check-out / check-in — implementation

> **Purpose:** implement the check-out / check-in migration for
> Full-tier (and Lightweight-tier on close) orchestrator coordination,
> per the six audit-locked verdicts from Set 032 Session 1
> (H1–H4, OQ1, OQ2).
> **Created:** 2026-05-19 (authored by Set 032 Session 2)
> **Session Set:** `docs/session-sets/033-orchestrator-checkout-checkin-implementation/`
> **Prerequisite:** Set 032 (`032-orchestrator-checkout-checkin-audit`) CLOSED.
> **Pre-audit basis:** [`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`](../../proposals/2026-05-19-orchestrator-tracking-architecture/)
> — `proposal.md`, `proposal-addendum.md` (§9 contains the locked
> verdicts), `README.md`.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification
> **Pattern:** Implementation half of audit-then-spec per
> [[feedback_audit_then_spec_for_substantial_features]] — Set 032
> shipped the audit; this set ships the code.

---

## Session Set Configuration

```yaml
totalSessions: 6
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
```

> **`requiresE2E: true`** — multi-set rendering + check-out conflict
> refusal are operator-visible behaviors that warrant Layer-3
> Playwright coverage (consistent with Set 027's e2e harness
> introduction; per [`CLAUDE.md`](../../../CLAUDE.md) "rendered-text
> invariants belong in Layer 3").
>
> **`effort: high`** — the change touches Python writers
> (`ai_router/start_session.py`, `ai_router/close_session.py`,
> `ai_router/session_lifecycle.py`), TypeScript readers
> (`MarkerWatchService`, `CustomSessionSetsView`), all in-flight
> `session-state.json` files across this repo + three consumer repos
> ([[project_consumer_repos]]), the canonical workflow doc, and the
> per-agent instruction files. High coordination risk; high cost if
> a writer-side bug ships and breaks an in-flight session.

---

## Project Overview

The orchestrator-tracking architecture audit (Set 029 S6 pre-audit
artifacts + Set 032 audit cycle) produced six locked verdicts that
together describe a check-out / check-in coordination model anchored
in `session-state.json` and enforced at the existing session
boundaries (`start_session` writer, `close_session` writer). Set 033
ships that model.

### The six locked verdicts (anchor)

Full reasoning at
[`docs/proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md`](../../proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md)
§9. Brief restatement here so the spec can be read on its own:

| Item | Verdict | Where it shows up |
|---|---|---|
| **H1** Writer authority | Router-only writes; hooks become invokers, not writers | S1 (writer), S3 (hook touchpoints — Claude `SessionStart` hook), S6 (cross-repo notifications) |
| **H2** Single source of truth | `session-state.json` canonical; `.dabbler/orchestrator.json` RETIRED entirely | S2 (resolver refactor + marker retirement + banner removal) |
| **H3** Hard coordination, not advisory | `start_session` REFUSES when held by a different `engine+provider`; refusal error MUST name the holder + the two release paths (`--force`, "Release Check-Out") | S1 (refusal logic), S3 (Command Palette "Release Check-Out") |
| **H4** Holder identity key | `engine + provider` composite (not `engine` alone, not `engine+provider+model`) | S1 (equality predicate), S3 (UI conflict prompt copy), S5 (queueing identity check) |
| **OQ1** Field merge | Merge into existing `orchestrator` block; +2 nested fields (`checkedOutAt`, `lastActivityAt`); block is `null` when `status != in-progress` | S1 (schema + writers), S2 (reader path) |
| **OQ2** Events as types or aliases | Aliases — `work_checked_out` / `work_checked_in` are documentation aliases for the existing `work_started` / `closeout_succeeded` ledger events; no schema change | S6 (doc updates only) |

### What ships across the six sessions

- **S1** — State-machine writer: `orchestrator` block on
  `session-state.json` becomes the authoritative check-out record.
  `start_session` enforces hard coordination with `--force`
  override. New nested fields `checkedOutAt` + `lastActivityAt`.
- **S2** — Reader-side migration: per-set marker
  (`.dabbler/orchestrator.json`) and `MarkerWatchService` precedence
  logic retired. `resolveActiveSet()` becomes `listInProgressSets()`;
  the tree provider renders multi-in-progress sets. Single-active-set
  banner removed.
- **S3** — UI affordances: `dabbler.setOrchestrator` →
  `dabbler.checkOutOrchestrator` ("Check Out As…"); ActionRegistry
  copy + per-row context-menu update; Command Palette "Release
  Check-Out" action; Claude `SessionStart` hook touchpoints
  refactored to invoke `start_session` rather than write directly
  (per H1).
- **S4** — Playwright coverage: multi-set rendering scenarios +
  check-out refusal + holder-name in refusal error + release-path
  visibility.
- **S5** — Queueing / polling: second orchestrator detects held
  check-out; offers poll / abort / force-override via a non-blocking
  UI flow using H4's identity predicate.
- **S6** — Close-out parity + docs + release: `close_session` clears
  the check-out across BOTH tiers (per operator's "Lightweight
  doesn't excuse skipping the lock" clarification mid-Set-029-S6);
  `docs/session-state-schema.md` + `ai_router/docs/close-out.md` +
  `docs/ai-led-session-workflow.md` updated for the new
  terminology + within-set sequential invariant; cross-repo CLAUDE.md
  notifications + PyPI release.

---

## Session 1 of 6: State machine in `session-state.json` + `start_session` refactor

**Goal:** make `orchestrator` block on `session-state.json` the
authoritative check-out record. Add hard coordination + `--force`
override. New nested timestamps. (H1 + H3 + H4 + OQ1.)

**Steps:**

1. **Schema delta on `session-state.json`.** Under `orchestrator`,
   add two nested fields:
   - `checkedOutAt: <ISO timestamp>` — set on transition to
     `status: in-progress`.
   - `lastActivityAt: <ISO timestamp>` — bumped on same-orchestrator
     re-attach / effort change / other in-state holder updates.
   `orchestrator` is `null` when `status != in-progress` (existing
   invariant, now codified).
2. **Update `docs/session-state-schema.md`** with the +2 fields,
   the H4 identity-equality rule (`engine + provider` composite),
   and the H3 hard-coordination invariant. Migration note: existing
   in-flight sets without `checkedOutAt` are tolerated on read;
   the next `start_session` populates the field.
3. **Refactor `ai_router/start_session.py`:**
   - On entry, read existing `orchestrator` block via
     `ai_router/session_state.py`.
   - Compute identity predicate: `existing.engine == new.engine
     AND existing.provider == new.provider`.
   - If equal → same holder; treat as re-attach: bump
     `lastActivityAt`, leave `checkedOutAt` unchanged, update
     mutable fields (`model`, `effort`) in place.
   - If unequal AND `--force` not set → REFUSE with a clear error
     message that names (a) the current holder (`engine + provider`)
     and (b) the two release paths (`--force`, "Release Check-Out"
     Command Palette action). Exit non-zero; do NOT mutate state.
   - If unequal AND `--force` set → log force-override to
     `~/.dabbler/orchestrator-writer.log` and proceed with the
     write; `checkedOutAt` is rewritten to now; `lastActivityAt`
     mirrors `checkedOutAt`.
4. **Add `--force` flag** to `start_session` CLI (`argparse`); pass
   through to the writer.
5. **`session_lifecycle.py` boundary update** — re-verify that
   `currentSession` / `lifecycleState` transitions still hold under
   the new equality predicate. Force-override is NOT a state-machine
   transition; it's an authority handoff.
6. **Unit tests** in `ai_router/tests/` covering:
   (a) fresh session start writes `checkedOutAt = lastActivityAt`;
   (b) same-holder re-attach bumps only `lastActivityAt`;
   (c) different-holder refusal returns non-zero + does NOT mutate;
   (d) refusal message contains both the holder identity AND both
   release paths;
   (e) `--force` writes through + appends to writer log;
   (f) tolerated read of an in-flight set with no `checkedOutAt`.
7. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `ai_router/tests/test_checkout_writer.py`
- `~/.dabbler/orchestrator-writer.log` (append-on-force-override; only
  created on first force-override invocation)

**Touches:**
- `ai_router/start_session.py`
- `ai_router/session_state.py` (schema definitions if any are pinned)
- `ai_router/session_lifecycle.py`
- `docs/session-state-schema.md`

**Ends with:** `start_session` enforces hard coordination per H3 + H4;
schema doc reflects the +2 fields; unit tests cover all six branches.

**Progress keys:** `session-001/schema-delta-applied`,
`session-001/start-session-refusal-wired`,
`session-001/force-flag-added`, `session-001/unit-tests-green`,
`session-001/schema-doc-updated`, `session-001/round-a-verification`

**Estimated cost:** $0.05–$0.15 (writer logic is small; verification
modest).

---

## Session 2 of 6: Marker retirement + resolver refactor + banner removal

**Goal:** retire `.dabbler/orchestrator.json` per-set marker + its
precedence logic entirely (H2). Replace `resolveActiveSet()` with
`listInProgressSets()` and render multi-in-progress sets in the
tree. Remove the single-active-set banner.

**Steps:**

1. **Audit MarkerWatchService.ts call sites.** Enumerate every
   consumer of `resolveActiveSet()` + every reader of
   `orchestrator.json`. Confirm the only sources of authority are
   `session-state.json` files post-S1.
2. **Introduce `listInProgressSets()`** in MarkerWatchService.ts
   (or its successor module). Returns the array of in-progress
   `session-state.json` records, sorted by `startedAt` ascending.
   Reads each set's `session-state.json` directly via the existing
   `fs.promises` scan in `scanState.ts` ([[project_029_s6_html_preview_iteration]]
   pattern: prefer async fs throughout).
3. **Refactor `CustomSessionSetsView.ts`** to render the array from
   `listInProgressSets()` rather than the resolved-active-set scalar.
   Per-set accordions remain — the change is from "one active set
   highlighted" to "N in-progress sets each in its own accordion".
4. **Remove the single-active-set banner** from
   `CustomSessionSetsView.ts` and any helper templates.
5. **Delete the per-set marker writer.** Search for any code that
   writes `.dabbler/orchestrator.json`; remove it. Includes
   `scripts/write-orchestrator-marker.js` if still present.
6. **Delete `.dabbler/orchestrator.json` files** in this repo's
   existing session sets (they become stale). Coordinate with
   consumer repos via S6's cross-repo notification — for THIS repo,
   delete now.
7. **Update `docs/orchestrator-marker-schema.md`** — either delete
   the file outright or replace with a single redirect note
   pointing at `docs/session-state-schema.md`. Operator decision
   captured during S2 via `AskUserQuestion` if not pre-decided here
   (default: delete; the schema was an implementation detail of the
   retired path).
8. **Layer-2 / Layer-3 tests update** — any test that asserts
   `resolveActiveSet()` behavior is rewritten against
   `listInProgressSets()`. Tests that scaffold a marker file are
   rewritten to scaffold `session-state.json` directly.
9. **End-of-session verification** (gemini-pro, Round A). The
   reader change is structural and high-risk; budget for a Round B
   if Round A flags must-fix.

**Creates:**
- (none new beyond test re-writes)

**Touches:**
- `tools/dabbler-ai-orchestration/src/providers/MarkerWatchService.ts`
  (renamed function exports; possibly rename file to
  `inProgressSetsService.ts` per operator preference — surface
  via `AskUserQuestion` in-session)
- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
- `tools/dabbler-ai-orchestration/src/providers/scanState.ts`
- `tools/dabbler-ai-orchestration/src/extension.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/markerWatchService.test.ts`
  (and any sibling tests covering marker behavior)
- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
  (delete)
- `docs/orchestrator-marker-schema.md` (delete or redirect)

**Deletes:**
- `.dabbler/orchestrator.json` files in any session-sets under this repo
- The marker-writer Node script (above)

**Ends with:** MarkerWatchService no longer reads or writes the
per-set marker file. Tree provider shows N in-progress sets. Banner
gone. All Layer-1 / Layer-2 tests green.

**Progress keys:** `session-002/list-in-progress-sets-introduced`,
`session-002/custom-view-multi-set-rendering`,
`session-002/banner-removed`,
`session-002/marker-writes-deleted`,
`session-002/stale-markers-purged`,
`session-002/marker-schema-doc-resolved`,
`session-002/layer2-tests-green`,
`session-002/round-a-verification`

**Estimated cost:** $0.10–$0.25 (largest reader-side change in the
set; verification may need Round B).

---

## Session 3 of 6: UI rename + ActionRegistry + Command Palette release action

**Goal:** rename the user-facing action to match the model. Add the
"Release Check-Out" Command Palette action that is one of H3's two
named release paths.

**Steps:**

1. **Rename command** `dabbler.setOrchestrator` →
   `dabbler.checkOutOrchestrator` in `package.json` `contributes.commands`,
   the implementation module (`src/commands/setOrchestratorManual.ts`
   → `src/commands/checkOutOrchestrator.ts`; or rename in place +
   update default export), and all internal call sites.
2. **Update ActionRegistry copy** in `src/providers/ActionRegistry.ts`
   — display label becomes "Check Out As…" (replacing
   "Set Orchestrator…"). Context-menu placement per the Set 029 S6
   verdict ([[project_029_pivot_to_per_set_identity]]) — right-click
   on in-progress rows, plus Command Palette always.
3. **Add "Release Check-Out" command** `dabbler.releaseCheckOut`:
   - Registered in `package.json` `contributes.commands` with a
     "Dabbler:" prefix for Command Palette discoverability.
   - Implementation invokes `start_session --force` against the
     currently-rendered in-progress set OR — if multiple in-progress
     sets — first prompts via QuickPick which set to release.
     Confirmation step required.
   - Force-override is logged to `~/.dabbler/orchestrator-writer.log`
     by S1's writer path; the UI command surfaces the same
     destination via a toast pointing at "Open Orchestrator Writer
     Log" command.
4. **Refactor Claude `SessionStart` hook** in
   `src/commands/installOrchestratorHookClaudeCode.ts` per H1
   (hooks become invokers, not writers). The hook MUST invoke
   `python -m ai_router.start_session` rather than write the
   `orchestrator` block directly. Failure is surfaced as a toast,
   not retried silently.
5. **Codex config-toml watcher review** —
   `src/codex/configWatcher.ts` is also a detector path. Confirm it
   currently invokes `start_session` (Set 029 S5 wired this) or
   refactor if not. If already correct, document the audit verdict
   in inline comment and move on.
6. **Gemini + Copilot installer shim review** —
   `src/commands/installOrchestratorHookGemini.ts` and
   `installOrchestratorHookCopilot.ts` are manual-only paths per
   [[project_029_pivot_to_per_set_identity]]. Confirm they don't
   write the orchestrator block directly; if they do, refactor to
   invoke `start_session`.
7. **Unit tests** for the rename + new command via the existing
   suite (`src/test/suite/actionRegistry.test.ts` +
   `setOrchestratorManual.test.ts` renamed accordingly).
8. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `src/commands/releaseCheckOut.ts` (new command implementation)
- `src/test/suite/releaseCheckOut.test.ts` (new tests)

**Touches:**
- `tools/dabbler-ai-orchestration/package.json` (commands, menus)
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts`
  (rename file/export)
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`
- `tools/dabbler-ai-orchestration/src/extension.ts` (registration)
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts` (if refactor needed)
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/setOrchestratorManual.test.ts`
  (rename to checkOutOrchestrator.test.ts)

**Ends with:** Command Palette shows "Check Out As…" + "Release
Check-Out"; hooks invoke `start_session` rather than writing
directly; unit tests green.

**Progress keys:** `session-003/command-renamed`,
`session-003/action-registry-copy-updated`,
`session-003/release-checkout-command-added`,
`session-003/claude-hook-refactored-to-invoker`,
`session-003/codex-watcher-audited`,
`session-003/installer-shims-audited`,
`session-003/unit-tests-green`,
`session-003/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 4 of 6: Playwright tests for multi-set rendering + check-out conflict

**Goal:** Layer-3 coverage of the operator-visible behaviors that
Sessions 1–3 introduced — multi-in-progress rendering, refusal
error content (H3), holder identity (H4), and release-path visibility.

**Steps:**

1. **Multi-in-progress rendering scenario.** Scaffold two session
   sets with `status: in-progress` and distinct `orchestrator.engine`
   values. Launch the extension via `electronLaunch.ts`. Assert
   both accordions render with their own gauges + bucket counts.
   Per the Layer-3 invariant in [`CLAUDE.md`](../../../CLAUDE.md),
   this is the right layer for "what the operator actually sees
   painted on screen".
2. **Check-out refusal scenario.** Scaffold a session set with
   `orchestrator.engine = claude` + `provider = anthropic` and
   `status: in-progress`. Invoke `start_session` from the test
   harness with `engine = gpt-5-4 + provider = openai`. Assert
   non-zero exit; assert stderr contains:
   - the existing holder's `engine + provider` (per H4 identity),
   - the literal substring `--force`,
   - the literal substring `Release Check-Out`.
3. **Force-override scenario.** Repeat (2) with `--force`. Assert
   exit zero; assert `orchestrator` block now reflects the
   gpt-5-4 holder; assert `~/.dabbler/orchestrator-writer.log` has
   an appended entry containing the prior holder + the new holder
   + an ISO timestamp.
4. **"Release Check-Out" Command Palette scenario.** From the
   in-progress state, trigger the `dabbler.releaseCheckOut` command
   via VS Code's command-execution API. Confirm the prompt, accept,
   and assert the `orchestrator` block is now null OR replaced by
   the operator's manually-chosen holder (depending on the
   implementation S3 settled on — the spec defers the precise
   semantic to S3's in-flight decision).
5. **Same-orchestrator re-attach (no-conflict) scenario.** Same
   holder calls `start_session` twice. Assert `checkedOutAt`
   unchanged across both writes; assert `lastActivityAt` bumped
   on the second.
6. **CI considerations.** All five scenarios must run under
   `xvfb-run` on Linux per [`.github/workflows/test.yml`](../../.github/workflows/test.yml).
   On Windows 11 + VS Code 1.120 the `@vscode/test-electron` runner
   is broken ([[project_playwright_electron_works_on_windows]]) —
   Playwright via `_electron.launch` is the working path, which
   these scenarios use.
7. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `tools/dabbler-ai-orchestration/src/test/playwright/checkout-conflict.spec.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/multi-in-progress.spec.ts`

**Touches:**
- `tools/dabbler-ai-orchestration/src/test/playwright/electronLaunch.ts`
  (helpers for scaffolding multi-in-progress fixture state; verify
  the existing helper accommodates this and extend if not)
- `tools/dabbler-ai-orchestration/playwright.config.ts` (if new files
  need explicit registration)

**Ends with:** Five Playwright scenarios green locally and in CI on
ubuntu-latest. Windows + macOS run per the existing matrix.

**Progress keys:** `session-004/multi-in-progress-spec-green`,
`session-004/conflict-spec-green`,
`session-004/force-override-spec-green`,
`session-004/release-checkout-spec-green`,
`session-004/reattach-spec-green`,
`session-004/ci-matrix-green`,
`session-004/round-a-verification`

**Estimated cost:** $0.05–$0.15 (test authoring + verification of
spec coverage, not heavy reasoning).

---

## Session 5 of 6: Queueing / polling feature

**Goal:** when a second orchestrator detects a held check-out
(refusal path from S1), offer poll / abort / force-override via a
non-blocking UI flow.

**Steps:**

1. **Detection path.** Refactor or extend the Claude `SessionStart`
   hook + Codex config-toml watcher so that when their `start_session`
   invocation returns non-zero with the holder-named refusal error
   from S1, the result is surfaced via a structured event the
   extension can subscribe to (rather than a free-text toast).
   Surface contract: `{ heldByEngine, heldByProvider, sessionSetPath,
   checkedOutAt }`.
2. **Polling prompt.** On detection, the extension shows a
   non-blocking VS Code information message with three actions:
   - **Poll** — the extension watches the held set's
     `session-state.json` for a transition out of `in-progress`
     (debounced ~5s polling using `fs.watch`) and auto-retries
     `start_session` for the would-be holder when free.
   - **Abort** — dismiss; no further action.
   - **Force override** — invoke `start_session --force`; same
     write-log + writer-log behavior as S1.
3. **Identity check uses H4.** Polling only auto-retries for the
   would-be holder (`engine + provider` composite match against the
   detection event's holder identity). If a third orchestrator
   joins mid-poll, the polling watcher does NOT yield to it — it
   continues for the holder that started the poll.
4. **Timeout / abandonment.** Polling auto-aborts after 30 minutes
   without resolution (configurable via a new
   `dabbler.checkoutPollTimeoutMinutes` setting; default 30). On
   abort, the extension surfaces a one-time toast pointing the
   operator at the Command Palette release action.
5. **Tests.** Layer-2 (`@vscode/test-electron`-style stub harness)
   for the polling state machine. Layer-3 Playwright scenario:
   "second orchestrator polls, holder closes, second orchestrator
   auto-attaches".
6. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `tools/dabbler-ai-orchestration/src/providers/CheckoutPollService.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/checkoutPollService.test.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/checkout-polling.spec.ts`

**Touches:**
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
  (structured event emission)
- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts`
  (structured event emission)
- `tools/dabbler-ai-orchestration/src/extension.ts` (service registration)
- `tools/dabbler-ai-orchestration/package.json` (new setting)

**Ends with:** A would-be second holder can poll for the in-flight
check-out to release without operator intervention; force-override
remains a one-click affordance from the same prompt.

**Progress keys:** `session-005/detection-event-contract-defined`,
`session-005/poll-service-implemented`,
`session-005/h4-identity-check-wired`,
`session-005/timeout-setting-added`,
`session-005/layer2-tests-green`,
`session-005/layer3-polling-scenario-green`,
`session-005/round-a-verification`

**Estimated cost:** $0.10–$0.25 (most net-new logic of any session).

---

## Session 6 of 6: Close-out parity + docs + cross-repo notifications + PyPI release

**Goal:** close out the migration. `close_session` clears the
check-out across BOTH tiers; canonical workflow / schema docs +
close-out doc updated; consumer repos receive a CLAUDE.md note;
new `dabbler-ai-router` PyPI release ships.

**Steps:**

1. **`ai_router/close_session.py` cross-tier check-in.**
   - On successful close, set `orchestrator: null` in
     `session-state.json` (Full and Lightweight tiers alike — per
     the operator's "Lightweight doesn't excuse skipping the lock"
     clarification mid-Set-029-S6).
   - Lightweight tier: same write; gates remain Lightweight-shaped
     (no router-side ledger writer change beyond clearing the
     block). `completedSessions[]` continues to be human-maintained
     for Lightweight ([[project_canonical_schemas_shipped]]).
   - **Idempotence:** `close_session` invoked on a set whose
     `orchestrator` block is already `null` (e.g., the previous
     holder force-released, or the session was closed via a path
     that already cleared it) is a successful no-op for the
     check-in step — the close-out's other writes proceed
     normally. This makes the check-in safe to retry and avoids
     coupling close-out success to check-out state.
2. **Unit tests** in `ai_router/tests/test_close_session.py`
   (extending existing coverage) for the Full-tier check-in and a
   Lightweight-tier fixture clearing the block on close.
3. **`docs/session-state-schema.md`** — add a "Check-out / check-in"
   section pointing at S1's schema delta + H3's hard-coordination
   invariant + H4's identity rule. Adopt the
   `work_checked_out` / `work_checked_in` aliases (OQ2) in
   doc-only prose; the ledger event names in `session-events.jsonl`
   remain `work_started` / `closeout_succeeded`.
4. **`ai_router/docs/close-out.md`** — Section 2 (the section
   `close_session --help` echoes) updated to mention the check-in
   step. Section 5 (failure modes) extended with the stranded
   check-out recovery path: `start_session --force` from the
   would-be next holder, or Command Palette "Release Check-Out".
5. **`docs/ai-led-session-workflow.md`** — codify the within-set
   sequential invariant: at most one in-progress session per session
   set; across-set parallelism IS allowed (multi-in-progress
   rendering exists precisely because this is the supported case);
   force-override is the one explicit deviation, logged in the
   writer log.
6. **Cross-repo CLAUDE.md notifications** ([[project_consumer_repos]]):
   - `dabbler-platform`
   - `dabbler-access-harvester`
   - `dabbler-homehealthcare-accessdb`
   Each gets a CLAUDE.md insertion (NOT a PR — operator pulls
   into each repo manually per existing pattern). The insertion
   describes the new commands, the refusal-error contract, and
   the recovery paths. Authored content goes into a single
   `docs/cross-repo-checkout-notice.md` for the operator to copy
   from.
7. **`change-log.md` for Set 033** (final-session aggregation
   pattern per [[project_final_session_changelog_pre_close]]).
8. **End-of-session verification** (gemini-pro, Round A; budget for
   Round B given the cross-tier writer change).
9. **PyPI release** of `dabbler-ai-router` — bump per the existing
   versioning convention in [`CLAUDE.md`](../../../CLAUDE.md);
   `python -m build` + `twine upload`. Operator-gated push (per
   the v0.17.x Marketplace pattern).
10. **VS Code Marketplace publish** — `npx vsce package` +
    `npx vsce publish` using
    `$env:AZURE_VSCODE_MARKETPLACE_TOKEN`
    ([[reference_vsce_pat]]). Operator-gated.
11. **`close_session` invocation** for Set 033 Session 6 itself.

**Creates:**
- `docs/session-sets/033-orchestrator-checkout-checkin-implementation/change-log.md`
- `docs/cross-repo-checkout-notice.md` (one-time copy source for the
  three consumer repos)

**Touches:**
- `ai_router/close_session.py`
- `ai_router/tests/test_close_session.py` (extend)
- `docs/session-state-schema.md`
- `ai_router/docs/close-out.md`
- `docs/ai-led-session-workflow.md`
- `CLAUDE.md` (top-level — version walk update for the new extension
  release)
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `tools/dabbler-ai-orchestration/package.json` (version bump)
- `pyproject.toml` (router version bump)

**Ends with:** Migration complete across writer (Python), reader
(TypeScript extension), tests (all three layers), canonical docs,
and consumer-repo notification text. Both registries are published.

**Progress keys:** `session-006/close-session-cross-tier-checkin`,
`session-006/close-session-tests-green`,
`session-006/schema-doc-updated`,
`session-006/close-out-doc-updated`,
`session-006/workflow-doc-invariant-codified`,
`session-006/cross-repo-notice-authored`,
`session-006/change-log-generated`,
`session-006/round-a-verification`,
`session-006/pypi-release-pushed`,
`session-006/marketplace-publish-completed`,
`session-006/close-session-succeeded`

**Estimated cost:** $0.10–$0.30 (cross-tier writer + docs + dual
release).

---

## Risks

- **R1 — Stranded check-outs in the wild.** Between S1 ship and S3
  ship, a Claude `SessionStart` hook that writes the marker directly
  could leave a stale `orchestrator` block in a real workspace.
  Mitigation: S1's writer tolerates a read of any prior state
  (the equality predicate handles it); S3 ships the hook refactor
  before the user-facing rename lands.
- **R2 — Reader refactor in S2 breaks tree rendering.** The
  `resolveActiveSet()` → `listInProgressSets()` change is the
  largest structural pivot in the reader. Mitigation: Layer-2
  tests rewritten in-session; Layer-3 multi-in-progress scenario
  in S4 catches what Layer 2 can't.
- **R3 — H4 identity edge cases.** Two orchestrators with the same
  `engine + provider` but different `model` are treated as the same
  holder by design. If the user expects model-level isolation
  (e.g., `claude-opus-4-7` vs. `claude-sonnet-4-6` as distinct
  check-outs), the implementation will surprise them. Mitigation:
  call this out in the schema doc and the cross-repo notice;
  operator adjudication in Session 1 of Set 032 explicitly chose
  composite over wider, so the spec follows.
- **R4 — Cross-tier check-in interaction with Lightweight
  human-maintained `completedSessions[]`.** Clearing
  `orchestrator` on Lightweight close is straightforward; the
  human still owns `completedSessions[]`. Mitigation: S6 tests
  cover a Lightweight fixture; the close-out doc clarifies that
  the block clear is automatic regardless of tier, while the
  ledger update remains tier-specific.
- **R5 — Force-override writer log grows unbounded.** Append-only
  log at `~/.dabbler/orchestrator-writer.log` has no rotation.
  Mitigation: defer (low volume in practice — force-override is the
  exception path); revisit if a user reports the file growing past
  ~10 MB.
- **R6 — Spec sequencing missteps despite the audit.** Six-session
  implementation with reader, writer, UI, tests, queueing, and
  cross-repo notification spans more surface than a typical Set.
  Mitigation: this spec was cross-reviewed by Gemini Pro in
  Set 032 Session 2 (per the spec's Step 3); any sequencing must-fix
  was applied before close.
- **R7 — `listInProgressSets()` performance in large repos.** S2
  replaces a single-marker read with an enumerate-and-scan of all
  session-set directories under `docs/session-sets/`. In a repo
  with hundreds of historical session sets, the per-call scan
  cost grows linearly. Mitigation: S2 implementation includes a
  one-time benchmark on this repo's current set count
  (~33 sets as of Set 033 start) and on a 200-set synthetic
  fixture; if the synthetic case exceeds ~50 ms per scan, add a
  cached index keyed on `session-state.json` mtime. Surfaced
  during Set 032 Session 2 cross-provider review.

---

## Routing notes

- **Within-session verification (every session):** gemini-pro per
  [[feedback_ai_router_usage]] (end-of-session only). Round A first;
  Round B only if must-fix surfaces.
- **No routed mid-session API calls.** All design questions are
  closed by the audit. In-session `AskUserQuestion` is the
  escalation path for edge cases (e.g., S2's marker-schema-doc
  delete-vs-redirect choice).
- **Implementation work uses the orchestrator directly.** No
  cross-engine consensus calls during code authoring — those happen
  at end-of-session verification only.

---

## Total estimated cost

- Session 1: $0.05–$0.15
- Session 2: $0.10–$0.25
- Session 3: $0.05–$0.15
- Session 4: $0.05–$0.15
- Session 5: $0.10–$0.25
- Session 6: $0.10–$0.30
- **Total Set 033 forecast: $0.45–$1.25.**

For context: Set 029's 6 sessions totaled ~$1.70 (heavy audit + 3
verification rounds in Session 1). Set 033 benefits from Set 032's
pre-shipped audit, so per-session verification spend should be
lower; the forecast above reflects that.

# Set 049 Session 4 — close-reason

S4 is the extension TS cleanup + Explorer revert session per spec
§5 S4, implementing operator-locked premise P4 (no orchestrator
information in the Session Set Explorer rendering — no harvest-record
badges, no coordination-conflict pills) alongside the TS-side
retirement of the chatSessionId / check-out / check-in surfaces.
S5 ships docs + version bumps + close-out per the locked arc.

## What S4 produced

### Pre-flight survey (Pass B + §4 gap close)

Spec §4 directed a focused re-survey before code-deletion to catch
non-runtime consumers Pass B identified as under-weighted. S4 opened
with that survey:

- **`sessionSetsWebviewProtocol.ts`** — declared `ConflictKind`,
  `ConflictSeverity`, `HarvestSignalsPayload`, `ConflictPayload`
  types + `RowPayload.harvestSignals` / `RowPayload.conflicts` fields.
  All retiring per P4. Confirmed: webview client.js was the sole
  consumer; deleting them did not break any non-rendering surface.
- **`HarvestService.ts`** — sole caller was `CustomSessionSetsView`
  (via `buildRow`). Spec said "stub-or-minimal shape" + "log-harvest
  scaffolding stays for non-conflict use" + Non-goal 2 caveats. With
  the sole caller disconnected, a stub serves no purpose; the
  load-bearing "log-harvest scaffolding" is the Python joiner in
  `ai_router/joiner/`, not the TS cache wrapper. Decision: delete the
  file (divergence from spec wording; rationale in §Spec divergences
  below). Noted for S5 to reflect in the change-log.
- **Consumer-repo hooks** (`dabbler-platform`,
  `dabbler-access-harvester`, `dabbler-homehealthcare-accessdb`) —
  none ship their own `claude-session-start-invoker.js`; they all
  inherit the shipped one in the extension VSIX. T2 accept-with-
  warning protects any legacy invoker still passing `--chat-session-id`.
- **Gemini + Copilot installer shims**
  (`installOrchestratorHookGemini.ts`,
  `installOrchestratorHookCopilot.ts`) — both depended entirely on
  retired surfaces (`dabbler.checkOutOrchestrator` quickpick +
  `dabbler.newChatIdWorkflowToast` toast). Post-rip they were
  broken-by-construction; deleted alongside (divergence from the
  spec's explicit retire list; rationale below).

No blockers surfaced. S4 proceeded with extension-TS cleanup as
scoped.

### Commands retired (3 from spec + 2 expanded)

Spec §5 S4 named: `dabbler.checkOutOrchestrator`,
`dabbler.releaseCheckOut`, `dabbler.newChatIdWorkflowToast`,
`chatSessionMismatchModal`, `CheckoutPollService`. S4 expanded with
2 commands whose entire reason-for-existence was the retired surface:
`dabbler.installOrchestratorHook.gemini` and
`dabbler.installOrchestratorHook.copilot`. Both shimmed onto the
retired `checkOutOrchestrator` quickpick + the retired `new_chat_id`
toast — broken by construction post-rip, with no useful behavior
remaining. The Claude installer (`dabbler.installOrchestratorHook.claudeCode`)
remains: it installs the canonical `SessionStart` hook (the post-S3
simplified `claude-session-start-invoker.js`).

Source file deletes:

- `src/commands/checkOutOrchestrator.ts`
- `src/commands/releaseCheckOut.ts`
- `src/commands/newChatIdWorkflowToast.ts`
- `src/commands/installOrchestratorHookGemini.ts`
- `src/commands/installOrchestratorHookCopilot.ts`

Provider deletes:

- `src/providers/CheckoutPollService.ts`
- `src/providers/chatSessionMismatchModal.ts`
- `src/providers/ReadOnlyIntentService.ts` (orphaned by the
  checkOutOrchestrator + CheckoutPollService deletes; deleted to
  match the spec's "stub-or-minimal" pruning discipline)

Plus `src/providers/HarvestService.ts` (spec divergence — see below).

### `package.json` reshape

- 5 command entries removed: `dabbler.checkOutOrchestrator`,
  `dabbler.releaseCheckOut`, `dabbler.installOrchestratorHook.gemini`,
  `dabbler.installOrchestratorHook.copilot`. (`dabbler.newChatIdWorkflowToast`
  was an internal helper; never had a Command Palette registration.)
- 1 config setting removed:
  `dabblerSessionSets.checkoutPollTimeoutMinutes` (only consumer was
  `CheckoutPollService`).

### `extension.ts` wiring trim

- 5 imports removed (the 5 deleted source files + `getReadOnlyIntentService`).
- 5 `safeRegister` calls removed (the 5 deleted commands).
- The inline `CheckoutPollService` instantiation block (~30 lines)
  removed.
- The `ReadOnlyIntentService` dispose wiring removed.
- New Set 049 comment block explains the rip and points at the
  surviving surfaces (Claude installer + writer-log opener).

### Set 045 Explorer surface revert (P4)

`CustomSessionSetsView.ts`:

- `HarvestService` import + instance + cache invalidation calls
  removed.
- `buildRow` no longer attaches `harvestSignals` / `conflicts` to
  the row payload.
- `dispose()` no longer calls `harvest.dispose()`; `refresh()` no
  longer calls `harvest.invalidate()`.

`src/types/sessionSetsWebviewProtocol.ts`:

- `ConflictKind`, `ConflictSeverity`, `HarvestSignalsPayload`,
  `ConflictPayload` types deleted.
- `RowPayload.harvestSignals` + `RowPayload.conflicts` fields
  deleted.
- New Set 049 comment documents the revert + Non-goal 2 caveat.

`media/session-sets-tree/tree.css`:

- `.harvest-badges` + `.harvest-badge*` + `.conflict-pills` +
  `.conflict-pill` + `.conflict-severity-*` rules removed (~95 lines).
- New Set 049 comment marks the revert point.

`media/session-sets-tree/client.js`:

- `renderHarvestBadges()` + `renderConflictPills()` functions
  deleted (~50 lines).
- `renderRow()` returns to the pre-Set-045 layout: name + fraction +
  description only.

### ActionRegistry trim

- `dabbler.checkOutOrchestrator` ("Set Orchestrator…") entry removed
  from `ROW_ACTIONS` (14 entries, was 15).
- `dabbler.openOrchestratorWriterLog` retained per spec T5
  (writer-log preserved provisionally).

### Test surface trims

Whole-file deletes (10 spec + 3 expansions):

- `checkOutOrchestrator.test.ts`
- `checkOutOrchestratorChatSessionMismatch.test.ts`
- `releaseCheckOut.test.ts`
- `chatSessionMismatchModal.test.ts`
- `checkoutPollService.test.ts`
- `readOnlyIntentService.test.ts` (S4 expansion — ReadOnlyIntentService deleted)
- `readOnlyIntentTiming.test.ts` (S4 expansion — same)
- `playwright/new-chat-id-cli-flow.spec.ts`
- `playwright/chatsessionid-takeover.spec.ts`
- `playwright/chatsessionid-missing-tolerance.spec.ts`
- `playwright/checkout-polling.spec.ts`
- `playwright/checkout-conflict.spec.ts`
- `playwright/harvest-signals.spec.ts`

Updates:

- `claudeSessionStartInvoker.test.ts` rewritten to match the post-S3
  shim exports (`parsePayload` + `recoverPriorClaudeModelEffort`).
  The pre-rip `extractSessionId` + `preserveExistingClaude` suites
  were broken since S3 (stale exports); S4 replaces them with
  coverage of the actual surviving surface, including the T3
  no-`"unknown"`-fallback contract.
- `actionRegistry.test.ts` — count assertion 15→14; "Set Orchestrator…
  is gated to in-progress" test replaced with "checkOutOrchestrator
  fully retired" + new "openOrchestratorWriterLog stays for all states"
  test.
- `rowMenuHelpers.test.ts` — `dabbler.checkOutOrchestrator` fixture in
  the flat-actions test replaced with `dabbler.openOrchestratorWriterLog`.
- `watcherInventory.test.ts` — allowlist trimmed from 3 entries to 1
  (CheckoutPollService's 2 entries removed; extension.ts tree-refresh
  line number updated from 150 to 141 after the wiring trim).
  Baseline-count assertion updated from 3 to 1.

### Cross-repo doc rewrite (T7)

`docs/cross-repo-checkout-notice.md` rewritten as a deprecation
instruction: "remove this content from your CLAUDE.md". Step-by-step
remediation for consumer repos with the Set 033 or Set 036 snippet
pasted in, plus a survives / retired summary so paster authors can
understand the rip-out scope without reading the spec.

## Test suite results

- **Layer-1 (Mocha unit)**: 553 passing, 2 failing.
  Both failures pre-existing and unrelated to S4 (verified by
  git-stash comparison against master HEAD before any S4 edits):
  - `configEditor-foundation`: `vscode.ViewColumn.One` undefined in
    the vscode-stub harness (test-scaffolding gap).
  - `notificationsSection`: `s5-test-notification disabled` regex
    no longer matches the rendered HTML (Set-026-era test, button
    state changed in a prior set without the test being updated).
- **Layer-3 (Playwright)**: 14 passing, 4 failing.
  All 4 failures pre-existing and unrelated to S4 (same stash
  comparison):
  - 3 `blocked-by-prereqs.spec.ts` failures: Windows-specific
    `FileExistsError` race in the temp-dir harness setup.
  - 1 `migration-cta-v4.spec.ts` failure: expected `"(needs
    migration)"` badge missing from the rendered row text.

S4 added no regressions. Net test-count drop on Layer-1 (~80 tests
removed) is consistent with the test-file deletions; no remaining
test references retired exports.

## Spec divergences

Two small departures from the literal spec text, both rationale-
documented above and pre-emptively flagged for S5 / verifier review:

1. **`HarvestService.ts` deleted, not stubbed.** Spec §5 S4 said
   "survives in a stub-or-minimal shape". With its sole caller
   disconnected and the load-bearing "log-harvest scaffolding"
   (Python joiner + parsers) living independently in `ai_router/`,
   a TS stub serves no purpose — any future TS surface that wants
   harvest data can shell out to the joiner CLI directly or
   re-add the cache wrapper. Cleaner than leaving dead code.
2. **Gemini + Copilot installer shims deleted.** Spec §5 S4's
   retire list named 5 commands; the 2 installer shims weren't on
   it. Post-rip they have nothing useful to do (both wrap the
   retired `checkOutOrchestrator` quickpick + the retired
   `new_chat_id` toast), so retiring them was the only honest move.
   The Claude installer (which IS load-bearing — it installs the
   `SessionStart` hook) survives.

## Defer to S5

Per the locked arc:

- **`CLAUDE.md`** rewrite (retire the "Hard-coordination enforcement
  (Sets 033 / 036) is OFF by default" section + add Set 049 entry
  to the version walk).
- **`docs/ai-led-session-workflow.md`** Step 6 / Step 8 references
  that cite the coordination layer.
- **Focused 15-20 item rip-out UAT checklist.**
- **PyPI `dabbler-ai-router` minor bump** (the orchestrator-block
  reshape + accept-with-warning behavior + `new_chat_id.py`
  retirement together justify a minor; operator picks at S5 start).
- **Marketplace `dabbler-ai-orchestration` minor bump** (parallel).
- **CHANGELOG entries** in both `ai_router/` and
  `tools/dabbler-ai-orchestration/`.
- **`change-log.md`** for Set 049 + close-out per workflow Step 8.
- **Verification**: Round A + Round B (final session).

## Cost

S1 spent $0.0475 routed (audit). S2 + S3 + S4 ran the rip without
invoking the router mid-session per the established discipline.
S4's only routed cost is the cross-provider verification at
close-out (Round A); subject to the Set 048 `runtime_mode`
short-circuit (`tier: full` + `requiresE2E: false` defaults to
zero-cost stub on verify), so the actual routed spend may be $0
for S4. Cumulative through S4 stays well under the $10 NTE.

## Why this S4 is heavy on deletions

Net diff: substantial deletion-dominant change. Set 045 (5 sessions)
and Set 033 / 036 (6 + 7 sessions) together contributed roughly 10
TS source modules + 13 TS test files + ~150 lines of CSS / JS that
S4 retires alongside the test files that exercised them. The
deletion footprint mirrors the spec's "removal-dominated" framing.

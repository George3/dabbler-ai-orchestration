# Set 029 Session 4 verification — Round A (provider-layer + types)

## Context

Set 029 Session 4 ships the **custom-tree pivot** in v0.16.0: replaces
the native `dabblerSessionSets` `TreeView` with a webview-rendered
custom tree, lifts the v0.15.0 gauges into per-row accordions on the
resolved in-progress set, and retires the dedicated
`dabblerOrchestratorIndicator` view in the same release.

Pre-S4 audit (2026-05-18) routed through Gemini Pro + GPT-5.4
landed at three-way agreement on Q1-Q11 + 10 must-fix tightening
items (M1-M10). Audit artifacts at
`docs/proposals/2026-05-18-custom-tree-implementation/`. Spec at
`docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
§"Session 4 of 6".

**Round A scope** (this round): the provider-layer extracts +
typed-protocol module + small abstraction modules. These are the
files where M2/M3/M4/M5/M7 + R13/R14 are most at risk. Round B
will cover `CustomSessionSetsView.ts` + `client.js` (the
integration surface where M1/M6/M8 + R10/R11/R12 live).

Splitting per memory `feedback_split_large_verification_bundles`
to stay under the bundle ceiling that gpt-5-4 timeouts at and to
keep each round's punch list focused.

## Files in this bundle (4 + 1 schema, ~700 LOC)

1. `src/providers/OrchestratorAccordion.ts` (431 LOC) — pure render
   helpers extracted from the retired
   `orchestratorIndicatorProvider.ts` (998 LOC). Per S4 M4: NO
   `vscode.*` lifecycle calls, NO filesystem watchers, NO
   message-protocol coupling.
2. `src/providers/MarkerWatchService.ts` (395 LOC) — marker reader
   + per-set marker watcher + state-watcher + workspace-folder
   listener + polling backstop. Per S4 M4: presentation-agnostic
   (emits typed events, not HTML).
3. `src/providers/ActionRegistry.ts` (79 LOC) — typed
   action-applicability predicates for the 14 row-context actions.
   Per S4 M2: single source of truth replacing the lost
   `package.json` `view/item/context` rules.
4. `src/providers/suppressionState.ts` (61 LOC) — pure reducer for
   manual-collapse-suppresses-auto-expand state, keyed on
   (slug, marker.updatedAt) tuple. Per S4 M7.
5. `src/types/sessionSetsWebviewProtocol.ts` (130 LOC) — typed
   discriminated unions for host↔webview messages with monotonic
   `version` field on render messages. Per S4 M3.

## What you're being asked to verify in Round A

Answer Q1–Q7 in order with **VERIFIED / MUST-FIX / SUGGEST** verdicts
plus 1–3 sentences of reasoning each. After Q1–Q7, emit a final
verdict line per the format at the bottom.

### Q1. OrchestratorAccordion extraction cleanliness (M4)

`OrchestratorAccordion.ts` should be pure render — no `vscode.*`
calls, no filesystem watchers, no lifecycle. Caller (in Round B)
takes a `RenderState` value and asks for HTML.

Verify:
- No `import * as vscode from "vscode"` or `import {} from "vscode"`.
- No `fs.readFileSync` or `fs.createReadStream` calls.
- Functions are deterministic state-in → string-out: `renderGaugeSvg`,
  `renderAccordionEmpty`, `renderAccordionLoaded`, `renderAccordionBody`,
  `describeMarker`, `describeRecommendation`, `modelTooltip`,
  `effortTooltip`, `tierToNeedleAngle`, `effortToNeedleAngle`,
  `effortColorBucket`, `fmtAge`, `escHtml`, `escAttr`,
  `computeMismatch`.

### Q2. HTML escape coverage (M5 / R13)

Per audit GPT-5.4 M5: every dynamic string interpolation into
webview HTML must go through `escHtml()` (or `escAttr()` for
attribute contexts).

Verify in `OrchestratorAccordion.ts`:
- `escHtml(marker.providerDisplayName)`, `escHtml(marker.modelDisplayName)`,
  `escHtml(describeMarker(marker))`, `escHtml(describeRecommendation(...))`,
  `escHtml(effortDisplayName(...))` all escape before interpolation.
- `escAttr(modelTip)`, `escAttr(effortTip)`, `escAttr(mismatch.reason)`,
  `escAttr(tier)`, `escAttr(signalKind)` all escape attribute values.
- Any string that flows directly into the rendered HTML without a
  call to `escHtml`/`escAttr` is a MUST-FIX.

### Q3. ActionRegistry (M2) — predicate correctness

`ActionRegistry.ts` exposes 14 actions (matching the 14
`view/item/context` entries deleted from `package.json` in this
session). The `when` predicates must reproduce the original
declarative gating exactly:

- 7 "open" actions (openSpec / openActivityLog / openChangeLog /
  openAiAssignment / openSessionState / openFolder / copySlug):
  always available.
- `openUatChecklist`: gated on `supports.uat && set.config.requiresUAT`.
- `revealPlaywrightTests`: gated on `supports.e2e && set.config.requiresE2E`.
- `copyStartCommand.default` + `copyStartCommand.parallel`: gated on
  `state === "in-progress" || state === "not-started"`.
- `cancel`: gated on `state ∈ {in-progress, not-started, complete}`.
- `restore`: gated on `state === "cancelled"`.
- `migrate`: gated on `set.needsMigration`.

Verify each predicate matches the spec. `applicableActions(set, supports)`
returns pre-sorted by `group` so menu order is deterministic.

### Q4. suppressionState (M7) — tuple-key semantics

Per audit Q2(a) + M7: suppression keyed by the
`(slug, marker.updatedAt)` tuple. Manual collapse suppresses for
that occurrence ONLY; the next SessionStart writes a fresh marker
with a new `updatedAt`, so the suppression naturally lifts without
explicit aging.

Verify:
- `isSuppressed(state, slug, updatedAt)` returns true iff
  `state[slug] === updatedAt`.
- `suppress(state, slug, updatedAt)` returns a NEW object (immutable).
- `clearSuppression(state, slug)` returns the SAME instance when the
  slug isn't present (no-allocation optimization).
- `prune(state, visibleSlugs)` drops entries whose slug is no longer
  visible; returns the SAME instance when no change.

### Q5. Versioned message protocol (M3)

Per audit GPT-5.4 M3: every render message carries a monotonic
`version: number`. Webview client drops messages with
`version < currentVersion` to prevent stale watcher/polling repaints.

Verify in `sessionSetsWebviewProtocol.ts`:
- `RowsSnapshotMsg`, `ScanStateChangedMsg`, `SuppressionEchoMsg` all
  have `version: number`.
- `ReadyMsg`, `ExecuteCommandMsg`, `ShowRowContextMenuMsg`,
  `ToggleRowMsg`, `ActivateRowMsg` (webview → host messages) do NOT
  carry a version (they're one-shot commands, not snapshots).
- `RowPayload` has the shape needed to drive the webview rendering:
  slug, name, state, description, contextValue, iconSlug,
  needsMigration, isResolvedSet, accordionHtml (pre-rendered or null).

### Q6. MarkerWatchService presentation-agnostic boundary (M4)

`MarkerWatchService.ts` should NOT generate HTML or webview commands.
It owns: marker reader, watchers, state computation. Emits typed
state changes via `vscode.EventEmitter<MarkerSnapshot>`.

Verify:
- No `escHtml`, no template strings building `<div>` / `<svg>`.
- `snapshot()` returns `{ resolution: SetResolution, state: RenderState }`
  — typed shapes, not strings.
- `computeState(resolution)` reads the marker file via `fs.readFileSync`,
  parses JSON, validates `sessionSetSlug` against `resolution.slug`,
  computes mismatch via `findActiveRecommendation()` → `computeMismatch()`.
- The slug-mismatch fallback logs to `vscode.OutputChannel` named
  "Dabbler Orchestrator Indicator" and returns `{ kind: "empty" }`
  (R8 wrong-set-attachment guard preserved from S3).

### Q7. Walk-up resolver fail-closed posture (R8 carry-forward)

`resolveActiveSet()` in `MarkerWatchService.ts` mirrors the writer-
side `walkUpResolveSet()` in `scripts/write-orchestrator-marker.js`
(S3-shipped). Both must fail closed identically:

- 0 in-progress sets → `{ kind: "unresolved", reason: "no-in-progress-set" }`
- >1 in-progress sets → `{ kind: "unresolved", reason: "multiple-in-progress-sets", candidates: [...] }`
- No `docs/session-sets/` directory anywhere in the walk → `{ kind: "unresolved", reason: "no-docs-session-sets" }`
- No workspace folder → `{ kind: "unresolved", reason: "no-workspace" }`

Verify the resolver semantics match the S3 writer's resolver
(symmetry is load-bearing: a writer that wrote to set X but a
reader that resolved set Y would silently mismatch).

---

## Final verdict (Round A)

Emit one summary line at the end:

`VERDICT: VERIFIED` if Q1–Q7 all pass without must-fix items
`VERDICT: MUST-FIX (<count>)` if any Q has a must-fix
`VERDICT: SUGGEST (<count>)` if no must-fix but ≥1 suggest items

Followed by a 2–3-sentence overall summary.

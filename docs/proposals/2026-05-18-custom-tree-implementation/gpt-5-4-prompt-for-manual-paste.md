# GPT-5.4 manual-paste prompt — custom-tree IMPLEMENTATION audit (Set 029 S4)

> **For the operator:** Open this file, select-all + copy, paste into
> GitHub Copilot's chat with the GPT-5.4 model selected. The framing
> tells GPT-5.4 that Gemini Pro will give an independent verdict
> separately — DON'T tell GPT-5.4 what Gemini said. Save GPT's
> response to `consensus-gpt-5-4-manual.md` in this same directory,
> then let me know it's done so I can synthesize both verdicts.
>
> **Why manual paste:** the GPT-5.4 API was 429-rate-limited during
> Set 029 S1-S3 verification rounds. Manual paste in GitHub Copilot
> bypasses the API throttle. Same model, same depth. Per memory
> `feedback_split_large_verification_bundles`.

---

You are one of two independent reviewers for a design proposal in
the Dabbler AI Orchestration codebase. The other reviewer (Gemini
Pro) will give their verdict separately — I am NOT showing you
their response because I want your independent view first.

**Important context:** this is the SECOND audit in a two-step
process for the same feature. The macro pivot itself (TreeView →
WebviewView for `dabblerSessionSets`) was decided in an earlier
audit at `docs/proposals/2026-05-18-custom-tree-pivot/` (which you
reviewed earlier today). S3 has SHIPPED — per-set markers, the
walk-up resolver with fail-closed posture, and `SessionSetsModel.ts`
extraction are all in production code (commit f1cc44d). This audit
is about the IMPLEMENTATION SHAPE for S4 — message protocol, ARIA
semantics, auto-expand persistence, context-menu mechanism, scope
packaging. **The pivot itself is locked; do not re-debate it.**

Review the proposal below and give your verdict on each of the
eleven open questions (Q1–Q11) plus the eight cross-cutting checks
listed under "What to verify in the consensus call". Structured
response per question — **verdict + reasoning + any must-fix items**.
Be explicit about concrete must-fix items vs. recommendations vs.
nice-to-haves. Where you think the proposal is fundamentally wrong
(not just a question I asked), say so directly — the operator wants
your real view, not a polite ratification.

The operator wants three-way agreement (operator + Gemini + you)
before this is formalized in spec.md for Session 4 of Set 029
(orchestrator model & effort indicator gauges).

---

# S4 implementation — custom-tree pivot design audit

**Date:** 2026-05-18
**Status:** Authored as the pre-S4 audit per memory
  `feedback_audit_then_spec_for_substantial_features`. S3 has shipped
  (commit `f1cc44d`); this proposal is informed by the actual S3
  ship (per-set markers, walk-up resolver with fail-closed posture,
  `SessionSetsModel.ts` data-layer extraction).
**Builds on:** `../2026-05-18-custom-tree-pivot/proposal.md`
  (the macro pivot proposal — pivot-itself decision is locked) and
  `../2026-05-18-custom-tree-pivot/synthesis.md`
  (operator decisions D1/D2/D3 from the pivot consensus).
**Target session:** Set 029 Session 4 (custom-tree implementation)
**Reviewers requested:** GPT-5.4 (manual paste in GitHub Copilot per
  established workaround per memory
  `feedback_split_large_verification_bundles`), Gemini Pro
  (via `dabbler-ai-router`)

---

## TL;DR

S3 shipped per-set markers, the walk-up resolver, and
`SessionSetsModel.ts` as a 131-LOC pure-function data layer. S4
re-registers `dabblerSessionSets` as a `WebviewViewProvider`, lifts
the v0.14.2 gauge HTML/SVG/CSS from
`orchestratorIndicatorProvider.ts` into per-row accordions, and
retires the dedicated `dabblerOrchestratorIndicator` view. The 14
row-context menu actions, ARIA tree semantics, `viewsWelcome`
empty state, loading-state UX, and Playwright Layer-3 coverage all
have to be reimplemented in the webview surface.

The pivot-itself decision is locked (per the prior synthesis). What
this audit decides: the **shape** of the reimplementation choices —
message protocol, ARIA semantics, auto-expand persistence, context
menu pattern, scope packaging — so S4 can ship a coherent webview
tree without operator-visible regressions.

Cost: roughly 600-1000 LOC of new webview code + lifted gauge code,
reimplementation of native-tree affordances, Playwright spec rewrite.

---

## What S3 actually shipped (post-pivot baseline)

Reading the current code (post-commit `f1cc44d`):

### `SessionSetsModel.ts` (131 LOC)

Pure functions, no `vscode.TreeItem` coupling:

- `needsMigrationBadge(set)`, `iconUriFor(extensionUri, state)`,
  `isCurrentSessionInFlight(set)`, `progressText(set)`,
  `touchedDate(set)`, `uatBadge(set)`, `forceClosedBadge(set)`,
  `modeBadge(set)` (no-op stub)
- `bucketSets(all): BucketedSets` (in-progress / not-started /
  complete / cancelled)
- `sortBucket(subset, groupKey)` (not-started by name asc; everything
  else by lastTouched desc)
- `ICON_FILES` mapping

This is the layer the S4 webview consumes directly. The interface
is stable — no further extraction needed.

### `SessionSetsProvider.ts` (246 LOC, thin TreeDataProvider shim)

Owns: refresh signaling (`_onDidChangeTreeData`), scan-cache
(`_cache`), loading sentinel (`makeLoadingSentinel`), group items
(`makeGroup`), set items (`makeSetItem` — assembles `description`
from model helpers, builds tooltip MarkdownString, sets
`contextValue`, sets default `command` to `openSpec`).

Most of `makeSetItem`'s logic (`folderTooltip`, `contextValueFor`,
`liveSessionTooltipLines`, `configTooltipLines`) is rendering chrome
that needs to port to the webview. None of it is TreeView-specific
beyond the `MarkdownString` tooltip wrapper.

### `orchestratorIndicatorProvider.ts` (998 LOC)

Owns: per-set marker reader, watcher rebinding on workspace-folder
change, state-watcher for session-state.json files, polling backstop
(60s), full gauge rendering pipeline (`renderGaugeSvg`,
`describeMarker`, `describeRecommendation`, mismatch detection
helpers, tier/effort rank logic, message handlers for
install-hook / set-orchestrator / open-writer-log buttons).

The render helpers (lines ~164-263, ~691-849) lift cleanly. The
view-resolution lifecycle (`resolveWebviewView`, the watcher
plumbing, the workspace-folder listener) gets folded into the new
custom-tree provider OR kept as a service consumed by the custom
tree. Q1 surfaces this choice.

### `scripts/write-orchestrator-marker.js` (S3 walk-up resolver)

`walkUpResolveSet(startCwd)` returns either `{ slug, dir }` on
success or `{ reason }` on fail-closed. Reasons:
`no-docs-session-sets` | `no-in-progress-set` |
`multiple-in-progress-sets`. The render side must already handle
the "no resolvable set" case via the existing empty-state CTA.
S4 doesn't change the resolver — it just consumes the resolution.

### `package.json` contributions to reproduce

- **`view/title` actions (3):** refresh, showCostDashboard, getStarted
- **`view/item/context` actions (14):** openSpec, openActivityLog,
  openChangeLog, openAiAssignment, openUatChecklist (uat-gated),
  revealPlaywrightTests (e2e-gated), openSessionState, openFolder,
  copyStartCommand.default (in-progress|not-started), copyStartCommand.parallel
  (same), copySlug, cancel (in-progress|not-started|done), restore
  (cancelled), migrate (needs-migration)
- **`viewsWelcome` entry:** gated on
  `dabblerSessionSets.scanState == ready`; markdown text with two
  `command:` links (copyAdoptionBootstrapPrompt, getStarted) plus an
  external README link
- **3 `when`-clause context keys:** `dabblerSessionSets.scanState`,
  `dabblerSessionSets.uatSupportActive`, `dabblerSessionSets.e2eSupportActive`

### Playwright surface to rewrite

`src/test/playwright/orchestrator-indicator.spec.ts` (751 LOC) and
`src/test/playwright/treeView.spec.ts` (265 LOC) cover the current
dual-view surface. S4 collapses to one spec file covering the
unified webview surface. Other Playwright specs (loading-state,
migration-cta) have selectors that need updating because the
rendered DOM moves from native-tree-item to webview-`<div>`.

---

## Locked from the pivot synthesis (do not re-litigate)

These pieces survive the implementation audit unchanged:

- **Pivot itself.** The macro decision (custom tree vs.
  per-workspace markers) is locked. Reviewers should not re-debate
  this — it shipped in S3 and works.
- **Storage shape:** Shape A (in-tree under
  `<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`),
  gitignored. Locked by S3.
- **Schema v3 with `sessionSetSlug`.** Locked, shipped, validated by
  reader.
- **Walk-up resolver with fail-closed posture.** Locked, shipped.
  S4 does NOT re-touch resolver semantics.
- **Multi-writer precedence + Windows retry loop.** Unchanged.
- **All S2 visual work.** SVG semi-circle gauges, IBM colorblind-safe
  palette, capacity bars, inverted-band headers, container queries,
  mismatch badge — lifted wholesale into accordion body.
- **`SessionSetsModel` is the data layer.** S4 consumes it; does
  not extend or reshape.
- **Drag/drop and multi-select stay deferred.** Not used today.

---

## Proposed S4 implementation

### View registration

`dabblerSessionSets` re-registers as `WebviewViewProvider` (same view
id, same view container, same name "Session Sets"). The
`dabblerOrchestratorIndicator` view container entry retires from
`package.json`.

The view container icon, ordering, `contextualTitle`, and welcome
content stay — only the `type` flips from native tree to `"webview"`.

### Tree shell (~600 LOC new code)

A single webview renders a vertical list of bucket groups, each
containing rows. Structure:

```
<div role="tree" aria-label="Session Sets">
  <div role="group" aria-label="In Progress (1)">
    <button role="treeitem" aria-level="1" aria-expanded="true" data-slug="029-...">
      <span class="row-header">
        <span class="icon">…</span>
        <span class="name">029-orchestrator-model-effort-gauges</span>
        <span class="description">3/6 · session 4 in flight · 2026-05-18</span>
      </span>
      <div class="accordion-body" role="region">
        <!-- lifted gauge HTML/SVG/CSS from orchestratorIndicatorProvider -->
      </div>
    </button>
  </div>
  <div role="group" aria-label="Not Started (2)">…</div>
  …
</div>
```

ARIA tree semantics per WAI-ARIA 1.2: `role="tree"` on the
container, `role="treeitem"` on each row, `aria-expanded` on
collapsible rows, `aria-level` for screen reader hierarchy,
`aria-selected` on focused row. Single-select tree (operator
selects at most one row).

### Accordion body (lifted from `orchestratorIndicatorProvider`)

The accordion body of an in-progress row shows the v0.14.2 gauge
treatment verbatim. For non-in-progress rows, the accordion body is
empty by default (Q3 surfaces whether to repurpose for AI-assignment
preview).

The accordion-body HTML is generated by the extension host (not the
webview) per message-response — that keeps the gauge code path
identical to v0.14.2's, just delivered via postMessage instead of
HTML-as-page.

### Auto-expand / collapse behavior (refined from pivot Q4)

- **On SessionStart hook fire** (S3 walk-up writes a per-set marker):
  the affected set auto-expands.
- **On session close** (state.json `currentSession` flips to null):
  the accordion body retires; row auto-collapses.
- **Manual collapse:** clicking the row header toggles; manual choice
  suppresses auto-expand for **the current session occurrence only**
  (per pivot synthesis — GPT-5.4 refinement). Suppression key is
  keyed on (slug, marker `updatedAt` timestamp), not the slug
  indefinitely.
- **Persistence:** workspaceState (per-window) keyed on slug. Q2
  surfaces whether this should be file-backed.

### Context-menu handling (14 actions)

Webview's `contextmenu` event listener fires `preventDefault` and
posts `{ command: "showRowContextMenu", slug, x, y }` to the
extension host. Host responds with `vscode.commands.executeCommand`
dispatch via a custom QuickPick (per Q6 — declarative menu in
package.json is no longer applicable since we lost
`view/item/context` semantics).

Alternative considered (Q6): keep `view/item/context` entries in
package.json with `viewItem` glob matching against the slug-encoded
context value, and fire VS Code's native menu via
`vscode.commands.executeCommand('editor.action.showContextMenu')` —
but that command doesn't accept arbitrary contextValue overrides
from webview, so this path doesn't work cleanly.

### Title-bar actions (3 actions)

Preserved via `view/title` package.json contribs. These work for
webview views identically to tree views — no reimplementation needed.

### `viewsWelcome` empty state

The webview reads the `viewsWelcome` contents string at activation
(or has it injected by the extension host) and renders it as HTML
with command links rewritten as `<a href="command:...">` (already
supported in webview). The package.json declaration stays as
authoritative source — extension host parses it.

Alternative considered (Q3): hand-author HTML mirroring the welcome
content. Rejected — package.json declaration must stay as the
authoritative copy so power-users reading the source can find it.

### Loading-state UX

Today, `scanState == loading` puts a "Setting up your project…"
sentinel TreeItem in the tree. In the webview, the same text renders
as a centered `<div>` until scanState transitions to `ready`.

Scan-state observation: the extension host posts state-change
messages to the webview (not the webview observing
`vscode.contextKeyService` directly — webviews can't read context
keys cleanly). Q5 confirms this.

### Multi-window observation (refined from pivot Q5)

Both windows that have the same workspace open render the same per-set
marker (per pivot synthesis — feature, not bug). Freshness cue: small
"updated Xs ago" text in the accordion-body footer (already shown in
v0.14.2's gauge — no new affordance needed). Q7 surfaces alternative
treatments.

### Migration / retirement of `dabblerOrchestratorIndicator`

S4 deletes the `dabblerOrchestratorIndicator` view entry from
`package.json`. The `orchestratorIndicatorProvider.ts` file itself
stays — its render helpers (`renderGaugeSvg`, `describeMarker`,
`describeRecommendation`, mismatch logic) are imported by the new
custom-tree provider. The `WebviewViewProvider` class wrapper
inside that file retires.

Alternative: extract render helpers into a sibling module
`OrchestratorAccordion.ts`. Q1 surfaces this.

---

## Open design questions for the reviewers

**Q1 — Render-helper extraction boundary.** The 998-LOC
`orchestratorIndicatorProvider.ts` mixes (a) the
`WebviewViewProvider` lifecycle (which retires in S4) with (b) pure
render helpers and watcher plumbing that the new custom tree
consumes. Options:

- **(a)** Extract render helpers into a new sibling
  `OrchestratorAccordion.ts`; the custom-tree provider imports
  them. Cleaner separation; smaller diff in the existing 998-LOC
  file (mostly deletions of the WebviewViewProvider class).
- **(b)** Leave helpers as exports from
  `orchestratorIndicatorProvider.ts`; just remove the class
  wrapper. Minimal churn.
- **(c)** Inline everything into the new custom-tree provider.
  Worst — that file gets 1500+ LOC.

Proposed: **(a)**, with the lifecycle pieces (state-watcher,
workspace-folder listener, marker watcher rebinding, polling
backstop) moving to a `MarkerWatchService.ts` consumed as a
dependency by the new custom-tree provider. Three files instead of
one 998-LOC file is more readable, and the lifecycle service can be
unit-tested in isolation (something not possible today). Reviewers
to confirm or push back.

**Q2 — Auto-expand suppression state shape.** Manual-collapse-
suppresses-auto-expand needs to persist (per pivot synthesis: "for
the current session occurrence only"). Options:

- **(a)** `workspaceState` keyed on `<slug>+<marker.updatedAt>`.
  Per-window. Survives reload. Naturally aging because the key
  changes on every new SessionStart.
- **(b)** File-backed JSON in
  `<workspace>/docs/session-sets/<slug>/.dabbler/ui-state.json`.
  Shared across windows. Persists outside VS Code restart.
- **(c)** Memory-only (per `WebviewView` instance). Doesn't survive
  view re-resolution.

Proposed: **(a)**. The behavior the operator wants — "I clicked to
collapse, don't keep re-opening it on me until the next session" —
maps to the (slug, updatedAt) tuple precisely. Cross-window
suppression sync (b) would actively surprise: collapsing in window
A shouldn't hide the gauge in window B. Memory-only (c) loses the
suppression on any view re-resolution (e.g., view-container
collapse / expand toggle), which is too aggressive a reset.

**Q3 — Accordion body for non-in-progress rows.** In-progress rows
default-expand to show gauges. Non-in-progress rows:

- **(a)** Empty accordion body; no expand toggle visible (header
  is non-toggleable).
- **(b)** Expandable to show static metadata (spec link preview,
  last-touched timestamp, change-log preview).
- **(c)** Expandable to show AI-assignment preview when
  `ai-assignment.md` is present (next-session recommendation for
  complete sets; current-session for in-progress; future-session
  for not-started).

Proposed: **(a)** for v1 — the spec scope is the gauges, not row
detail surfacing. (c) is appealing as a follow-on but expands
scope past S4 budget. Reviewers can argue (b) or (c) if the
operator's workflow leans on quick metadata access.

**Q4 — Auto-collapse on session-end.** When `currentSession` flips
from N to null (close-out), the gauge retires:

- **(a)** Row auto-collapses to header only.
- **(b)** Row stays expanded but accordion-body shows a "Session N
  complete — N+1 of M up next" summary panel (uses ai-assignment
  data if present).
- **(c)** Row stays expanded with empty accordion-body until
  next SessionStart fire.

Proposed: **(a)**. Symmetric with auto-expand-on-start. (b) is
appealing but cross-cuts Q3 and inflates scope.

**Q5 — Scan-state observation by the webview.** The webview needs to
know when scanState transitions (loading → ready) to swap the
sentinel for the row list. Options:

- **(a)** Extension host posts explicit state-change messages
  (`{ command: "scanStateChanged", state: "ready" }`) on every
  transition. Webview re-renders.
- **(b)** Webview polls a state endpoint every 100ms during
  loading. Trash.
- **(c)** Extension host re-renders the full webview HTML on each
  state change (replaces `webview.html`). Heavyweight.

Proposed: **(a)**. The state transition is rare (once per scan,
seconds-scale), and the webview already has a message receiver for
context-menu plumbing.

**Q6 — Context-menu mechanism.** The 14 row-context actions today
fire from VS Code's native right-click menu. In the webview:

- **(a)** Webview captures `contextmenu` event, posts to host;
  host fires a custom `QuickPick` with the applicable commands.
  Cross-platform; theme-aware; minor UX divergence from
  declarative menus.
- **(b)** Webview captures `contextmenu`, posts to host; host
  fires `vscode.commands.executeCommand("workbench.action.showCommandPalette")`
  with a filter for the matching commands. Discoverable but
  unusual UX.
- **(c)** Render a custom HTML `<menu>` inside the webview on
  right-click. Most-native-feeling but requires reimplementing
  theme + a11y + keyboard nav for the menu itself.

Proposed: **(a)**. Operator-visible behavior: right-click shows a
QuickPick with the 14 (gated) actions. Native QuickPick chrome,
theme-aware, keyboard-navigable. Reviewers to push back if (c) is
strongly preferable for fidelity to today's UX.

**Q7 — Freshness cue treatment.** Per pivot synthesis (GPT-5.4
addition), multi-window observation needs a freshness cue. v0.14.2's
gauge already shows "updated Xs ago" in the gauge footer. Options:

- **(a)** Just rely on existing "updated Xs ago" footer text. No
  new affordance.
- **(b)** Add a small pulse animation on the row when marker
  updates (CSS keyframe, 1.5s decay). Visible across windows.
- **(c)** Add a colored dot indicator (green = fresh <30s, yellow =
  fresh <5min, grey = older) next to the row header timestamp.

Proposed: **(a)** for v1 (already there, zero new code). (b) is
nice-to-have if cross-window confusion turns up in real use; defer
to v1.1. (c) duplicates information already in the gauge body.

**Q8 — Orphan-render shape (revisit from S3 D3).** S3 fail-closes
silently on `no-in-progress-set` and `multiple-in-progress-sets`.
Now that we have a richer UI:

- **(a)** Keep S3's silent fail-close. Custom tree renders with
  no orchestrator info; existing CTA in the empty-state row of the
  In Progress bucket says "no in-progress set". Zero new code.
- **(b)** "Recent activity" pseudo-section above the bucket groups
  shows the orphan marker if it exists. Requires an orphan-write
  path the resolver currently does NOT have (S3 explicitly chose
  not to write orphans).
- **(c)** In the `multiple-in-progress-sets` fail-close case,
  render a banner above the In Progress bucket: "Multiple sets in
  progress — orchestrator info hidden (see writer log)" with a
  link to open the log.

Proposed: **(a)** + **(c)**. (a) preserves the existing
fail-closed posture; (c) adds operator-actionable signal for the
specific failure-mode (multiple in-progress) without writing
orphan markers (preserves S3's identity-only-in-canonical-model
property).

**Q9 — "Attached to: <slug>" badge in the accordion body.** S3
risk R8 (wrong-set attachment after stale state) suggested a small
badge on the gauge. Now that the gauge is INSIDE the row of the
set it's attached to, the visual association is much stronger.

- **(a)** Skip the badge — the row IS the slug, no badge needed.
- **(b)** Keep the badge as a paranoia affordance (small
  "attached to: <slug>" text in the gauge footer alongside the
  "updated Xs ago" text).

Proposed: **(a)**. The custom tree makes the badge redundant.
Reviewers to confirm.

**Q10 — Scope packaging.** Reimplementation surface (~1100-1400 LOC
new + lifted code + Playwright rewrite) is on the upper end of
single-session work. Options:

- **(a)** Single S4. All deliverables in one session: registration
  pivot, lift, accordion plumbing, kbd nav, context menu, ARIA,
  loading state, Playwright rewrite, retirement of indicator view.
- **(b)** Split S4a (custom tree shell + accordion + auto-expand +
  loading state) + S4b (full context-menu + ARIA + Playwright
  rewrite + indicator-view retirement). Set grows 6 → 7.
- **(c)** Behind config flag `dabblerSessionSets.useCustomTree`
  (default false). S4 ships the new view but the user opts in.
  S5/S6 polish; flag-flip in a follow-on Set 030 release.

Proposed: **(a)**. The pieces are tightly coupled — splitting
gives two sessions each with partial UX (a tree without context
menus is unusable). The Playwright rewrite is mechanical (selector
churn, not test redesign). The flag approach (c) means shipping
two parallel code paths and a long deprecation window for no
external-consumer gain.

**Q11 — Retire `dabblerOrchestratorIndicator` view in S4 or S5?**

- **(a)** Retire in S4 (delete view contribution from
  `package.json`, delete `WebviewViewProvider` class). The
  accordion body becomes the only gauge surface from day one.
- **(b)** Keep both views in S4 (custom tree + dedicated
  indicator) so operators have a fallback if the accordion body
  regresses; retire in S5 after a verification round.

Proposed: **(a)**. Marketplace download count is 3 (all operator's
own per memory `project_marketplace_download_count`); a parallel
deprecation window costs more than the safety it buys. Reviewers
to confirm.

---

## Implementation surface (S4 scope, post-audit)

Estimated LOC and file impact assuming proposed defaults
(Q1=a, Q3=a, Q4=a, Q5=a, Q6=a, Q10=a, Q11=a):

**New files:**

- `src/providers/CustomSessionSetsView.ts` (~500 LOC): webview
  provider, message protocol, kbd nav, ARIA, context menu plumbing,
  lifecycle.
- `src/providers/OrchestratorAccordion.ts` (~400 LOC, extracted):
  render helpers (`renderGaugeSvg`, `describeMarker`,
  `describeRecommendation`, mismatch logic, tier/effort rank).
- `src/providers/MarkerWatchService.ts` (~150 LOC, extracted):
  state-watcher, workspace-folder listener, marker watcher
  rebinding, polling backstop.
- `media/session-sets-tree/tree.css` (~150 LOC new + lifted gauge
  CSS): accordion + bucket groups + selection + focus styling.
- `src/test/playwright/session-sets-tree.spec.ts` (~500 LOC,
  replaces orchestrator-indicator + treeView specs): all existing
  scenarios ported + new for kbd nav, context menu, ARIA, auto-
  expand/collapse, scan-state transition.

**Modified:**

- `src/providers/SessionSetsProvider.ts`: **deleted** (or reduced
  to a thin re-export of `SessionSetsModel` named exports for
  test-file imports; see Q1).
- `src/providers/orchestratorIndicatorProvider.ts`: collapsed to
  re-exports only after helpers move to
  `OrchestratorAccordion.ts` + lifecycle moves to
  `MarkerWatchService.ts`; or deleted entirely.
- `src/extension.ts`: register `CustomSessionSetsView` instead of
  `SessionSetsProvider` + `OrchestratorIndicatorProvider`.
- `package.json`: flip `dabblerSessionSets.type` to `webview`;
  delete `dabblerOrchestratorIndicator` view entry; delete
  `view/item/context` entries (now handled via webview-fired
  QuickPick); preserve `view/title` + `viewsWelcome` +
  `commands` + `configuration`.
- `src/test/playwright/orchestrator-indicator.spec.ts`: deleted.
- `src/test/playwright/treeView.spec.ts`: deleted (logic ports to
  new spec).
- `src/test/playwright/loading-state.spec.ts`: selector updates.
- `src/test/playwright/migration-cta.spec.ts`: selector updates.
- `src/test/suite/sessionSetsProvider.test.ts`: repointed to
  `SessionSetsModel` (Layer-2 — already done in S3 per spec; this
  audit confirms).
- `CHANGELOG.md`: entry under [0.16.0] (per Q11/pivot precedent on
  minor bumps for architectural changes).

**Version bump:** 0.15.0 → **0.16.0** (minor — architectural
change: TreeView → WebviewView).

Total: ~1100-1300 LOC new code, ~750 LOC deleted, ~60 LOC
package.json churn, ~300 LOC Playwright spec rewrite.

---

## Risks

- **R1 — Reimplementation regressions.** Kbd nav, context menus,
  ARIA, viewsWelcome, loading state all need to feel native. Each
  has a Playwright scenario per Q10 / scope. Mitigation: Layer-3
  coverage explicit for all five; operator manual smoke before
  declaring done.

- **R2 — Webview message-protocol coupling.** Every UI action
  becomes a postMessage round-trip. If the protocol is poorly
  designed, every new action requires a host+webview change.
  Mitigation: generic `executeCommand` message pattern (Q6=a) keeps
  the protocol stable; new commands work without new message
  shapes.

- **R3 — Performance: webview vs. native tree.** Webview rendering
  is heavier than native tree. Today's workspaces have <10 sets;
  not a problem. Mitigation: render budget check before merge;
  collapse rendering for non-in-progress bucket bodies by default
  (Q3=a contributes naturally).

- **R4 — Theming gaps.** Webview must consume `--vscode-*` CSS
  vars consistently. The v0.14.2 gauge CSS already does this for
  the gauge body; the tree shell CSS adds new surfaces (row hover,
  selection, focus, bucket headers). Mitigation: light/dark theme
  parity check in the Playwright smoke.

- **R5 — Tab order / focus loss.** Native tree handles
  focus/blur cleanly. Webview tree-item focus is non-trivial;
  accordion collapse can drop the operator's nav context.
  Mitigation: ARIA tree spec compliance (Q4 — WAI-ARIA single-
  select tree pattern); Playwright kbd nav coverage.

- **R6 — Webview right-click QuickPick UX divergence.** QuickPick
  chrome is different from native context-menu chrome (cmd-palette
  styling vs. native menu styling). Operator-visible change.
  Mitigation: QuickPick is theme-aware and keyboard-navigable;
  most operators will not notice after a brief acclimation. If the
  feedback round flags this, Q6=c (custom HTML menu) is the
  fallback for v1.1.

- **R7 — Render-helper extraction risk.** Lifting 400 LOC of gauge
  rendering out of the indicator provider introduces risk of
  rendering regressions. Mitigation: the Playwright Layer-3 smoke
  for the gauges (signalKind matrix, confidence, mismatch badge)
  ports from the old file to the new spec; ports are mechanical
  selector churn, not new test logic.

- **R8 — Lost `view/item/context` discoverability for power-users.**
  Today, power-users can read `package.json` to find what actions
  apply to a row. With QuickPick-based menus, the action set is
  defined in TypeScript. Mitigation: keep the per-action
  `command:` entries in `package.json`'s `commands` block (they
  already exist for the Command Palette); only the
  `view/item/context` entries retire. The actions remain
  discoverable via cmd-palette.

---

## What to verify in the consensus call

Per memory `feedback_audit_then_spec_for_substantial_features`,
reviewers please assess:

1. **Q1-Q11**: for each, either confirm the proposed default or
   surface a stronger alternative with reasoning. Where you
   diverge, present the divergence so the operator can decide
   (per memory `feedback_prefer_ai_consensus_over_human_prompt`).

2. **Implementation surface table**: anything underestimated or
   overestimated in LOC? Anything missing from the new-files /
   modified-files list?

3. **Risks R1-R8**: anything missing, anything mis-sized?

4. **Scope packaging (Q10)**: confirm single-S4 is workable, or
   argue specifically why splitting is necessary.

5. **Render-helper extraction (Q1)**: confirm three-file
   factoring is the right shape, or argue for fewer/more.

6. **ARIA + kbd nav scope**: do we need anything beyond the WAI-
   ARIA 1.2 single-select tree pattern (up/down sibling, left
   collapse/parent, right expand/first-child, enter activate,
   home/end, type-ahead search)? Type-ahead is a real native-tree
   affordance — should it ship in v1 or move to v1.1?

7. **Test-layer impact (audit-style cross-check)**: the audit
   assumes Layer-1 pytest is unaffected, Layer-2 already pointed
   to `SessionSetsModel`, Layer-3 Playwright rewrite is in scope.
   Cross-check this against what S3 actually shipped.

8. **Cost estimate**: $0.10-$0.30 single end-of-session verification
   forecast (per spec). With three new files (~1100-1300 LOC new)
   and one rewrite, is the single-round forecast realistic, or
   should we pre-plan for Round-B sub-session split per memory
   `feedback_split_large_verification_bundles`?

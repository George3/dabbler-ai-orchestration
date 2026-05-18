# Set 029 spec delta — S4 custom-tree implementation (DRAFT)

> **Status:** Authored 2026-05-18 from the S4 implementation audit. Replaces the high-level S4 scaffold currently in `spec.md` lines ~622–696 ("Session 4 of 6: Custom-tree pivot (NEW; high-level scaffold — gated by its own pre-session audit)").
>
> **Audit artifacts:**
> - `proposal.md` (this directory)
> - `consensus-gemini-pro.json` + `consensus-gpt-5-4-manual.md`
> - `synthesis.md` — both reviewers ratify all 11 answers; no operator divergences. GPT-5.4 adds 8 must-fix tightening items + 3 missing risks. Gemini adds Round-B planning + type-ahead TODO.
>
> **Locked decisions (Q1–Q11, both reviewers concur):**
> - **Q1** (extraction): three-file factor — `CustomSessionSetsView` + `OrchestratorAccordion` + `MarkerWatchService`. Plus `ActionRegistry` per GPT M2 and a webview-side `client.js` per GPT M6.
> - **Q2** (suppression): `workspaceState` keyed on `<slug>:<marker.updatedAt>` (tuple form, not slug alone).
> - **Q3** (non-in-progress rows): empty accordion body, no expand toggle visible.
> - **Q4** (auto-collapse): symmetric with auto-expand; focus stays on row when body removed.
> - **Q5** (scan-state): host posts explicit state-change messages; webview re-renders.
> - **Q6** (context menu): QuickPick fired by host. Same predicates drive right-click, `Shift+F10`, Context Menu key.
> - **Q7** (freshness cue): existing "updated Xs ago" footer is sufficient for v1.
> - **Q8** (orphan): keep S3 silent fail-close; add banner for `multiple-in-progress-sets` ambiguity.
> - **Q9** (badge): no "attached to: <slug>" badge; row IS the slug.
> - **Q10** (scope): single S4 for implementation; pre-plan Round-B verification.
> - **Q11** (retire indicator view): retire in S4, gated on indicator-action parity + kbd/focus parity.
>
> **Operator reviews this delta before I apply it to `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`.**

---

## Replacement for "Session 4 of 6" section

### Session 4 of 6: Custom-tree pivot (REVISED 2026-05-18 via custom-tree-implementation audit)

**Goal:** Replace the native `dabblerSessionSets` `TreeView` with a webview-rendered custom tree (same view id, same view container). Lift the v0.14.2 orchestrator gauges into per-row accordions on in-progress rows so the orchestrator UI is contextually anchored to the work it describes. Retire the dedicated `dabblerOrchestratorIndicator` view in the same session. The S3 per-set markers + walk-up resolver + `SessionSetsModel` data layer carry forward unchanged.

**Operator decisions encoded** (per [`docs/proposals/2026-05-18-custom-tree-implementation/synthesis.md`](../../proposals/2026-05-18-custom-tree-implementation/synthesis.md), three-way agreement: operator + Gemini Pro + GPT-5.4):

- **Q1–Q11 all locked at proposed defaults** — see synthesis.md table for the full grid; no reviewer divergences on the answer set.
- **M1–M10 tightening items** (mostly from GPT-5.4) — see step list below; absorbed into spec.
- **R9, R10, R11 added** (invalid interactive nesting, XSS escaping, message ordering); **R5 upgraded** to top-tier risk (focus/a11y is the easiest way for a custom tree to feel broken); **R6 downgraded** to mid-tier (QuickPick is acceptable v1 fidelity loss).
- **Cost forecast bumped** from $0.10–$0.30 to **$0.20–$0.60** with Round-B verification pre-planned.

**Steps:**

1. **Re-register `dabblerSessionSets` as `WebviewViewProvider`.** Same view id, same view container, same name "Session Sets". Flip `type` in `package.json` from native tree (default) to `"webview"`. Container icon, ordering, `contextualTitle`, `viewsWelcome` declaration all preserved. Delete the `dabblerOrchestratorIndicator` view entry in the same package.json edit (per M8: gated on accordion-body preserving install-hook + set-orchestrator + open-writer-log buttons).

2. **DOM structure (per M1 — invalid-nesting fix).** Do NOT use `<button role="treeitem">` wrapping the accordion body. Use focusable container with separate header control:
   ```html
   <div role="tree" aria-label="Session Sets">
     <div role="group" aria-label="In Progress (1)">
       <div role="treeitem" tabindex="-1" aria-level="1" aria-expanded="true"
            aria-selected="false" data-slug="029-...">
         <div class="row-header" role="presentation">
           <span class="icon">…</span>
           <span class="name">029-…</span>
           <span class="description">3/6 · session 4 in flight · 2026-05-18</span>
         </div>
         <div class="accordion-body" role="region" aria-label="Orchestrator">
           <!-- lifted gauge HTML; may contain buttons safely -->
         </div>
       </div>
     </div>
   </div>
   ```
   Roving `tabindex` (or `aria-activedescendant`) tracks the focused row. Accordion-body buttons (install-hook, set-orchestrator, open-writer-log) are NOT nested inside an interactive treeitem button — they're inside a `role="region"`, which is valid.

3. **ARIA tree semantics (WAI-ARIA 1.2 single-select tree pattern).** Required for v1:
   - `role="tree"` on container; `role="group"` on bucket; `role="treeitem"` on each row; `role="region"` on accordion body.
   - `aria-level`, `aria-expanded` (only on expandable rows — non-in-progress rows omit it per M's "no inert chevron"), `aria-selected` on focused row.
   - Roving `tabindex` (single tabstop into the tree; arrow keys move focus within).
   - Keyboard: ↑/↓ sibling, ←/→ collapse/expand (or parent/first-child), Enter/Space activate (= openSpec for v1 per M's primary-activation rule), Home/End first/last, `Shift+F10` + Context Menu key open the action QuickPick on the focused row.
   - Tab from inside expanded accordion exits cleanly to next focusable element outside the tree (no focus traps).
   - `// TODO: type-ahead search (deferred to v1.1)` comment in the kbd handler per Gemini M10.

4. **Three-file extraction (per Q1 + M4).**
   - `src/providers/OrchestratorAccordion.ts` (~400 LOC, new): pure render functions lifted from `orchestratorIndicatorProvider.ts` — `renderGaugeSvg`, `describeMarker`, `describeRecommendation`, `tierRank`, `effortRank`, `fmtAgeStandalone`, `providerHasExtraCapacity`, mismatch helpers, `escHtml`, the visual-treatment matrix. **No `vscode.*` lifecycle calls; no filesystem watchers.** Just deterministic string-in → HTML-out.
   - `src/providers/MarkerWatchService.ts` (~150 LOC, new): the marker reader, the `session-state.json` watcher, the workspace-folder listener, the polling backstop. **Emits typed events / state**, not HTML or webview commands. Disposable; injected into the view provider as a dependency. Unit-testable in isolation (which today's mixed provider is not).
   - `src/providers/CustomSessionSetsView.ts` (~500 LOC, new): the `WebviewViewProvider`. Owns lifecycle (resolveWebviewView, dispose), consumes `SessionSetsModel` + `MarkerWatchService` + `OrchestratorAccordion`, serializes render snapshots, posts messages to the webview, receives webview messages and dispatches via `ActionRegistry` + `vscode.commands.executeCommand`.
   - **Delete** `src/providers/SessionSetsProvider.ts` (no re-export shell — per M4). Test files that imported helpers from it repoint to `SessionSetsModel`.
   - **Delete** `src/providers/orchestratorIndicatorProvider.ts` (no re-export shell — per M4). Its render helpers are now in `OrchestratorAccordion.ts`; its lifecycle is now in `MarkerWatchService.ts` + `CustomSessionSetsView.ts`.

5. **`ActionRegistry` (per M2).** New `src/providers/ActionRegistry.ts` (~150 LOC). One typed module with the 14 row-actions, each as `{ id, label, when: (set: SessionSet, supports: { uat, e2e }) => boolean }`. The same predicates drive (a) the right-click QuickPick, (b) `Shift+F10` / Context Menu key, (c) any future inline overflow button. Replaces the lost `view/item/context` declarative rules in `package.json` — those entries are **deleted** from package.json in this session.

6. **Webview client script (per M6 — separate from view provider).** New `media/session-sets-tree/client.js` (~200 LOC). Owns kbd navigation, selection-state bookkeeping, contextmenu event capture, postMessage to the host. Keeping this OUT of `CustomSessionSetsView.ts` (which runs in the extension host) is a hard rule — host file stays focused on lifecycle + message protocol; client.js stays focused on user interaction. Cross-script type safety via the shared protocol module (step 7).

7. **Typed message protocol with monotonic version (per M3).** New `src/types/sessionSetsWebviewProtocol.ts` (~100 LOC). Discriminated unions for `HostToWebview` and `WebviewToHost` messages; every render message carries a monotonic `version: number` field. Webview client.js drops any render message with `version < currentVersion`. Snapshot-style payloads for row list; narrow event messages for UI-only state (focus moved, accordion toggled). Eliminates the message-ordering race when watcher events + polling backstop + manual refresh race.

8. **Suppression-state persistence (per Q2 + M7).** `workspaceState` key shape: `dabbler.sessionSets.suppressedExpand`, value = `Record<string, string>` mapping `slug` → `marker.updatedAt` of the suppressed occurrence. A row is suppressed iff `state[slug] === currentMarker.updatedAt`. Manual re-expand (click chevron) clears `state[slug]`. Prune: on every persist, drop entries whose slug is no longer in any bucket's set list. Reducer logic in `src/providers/suppressionState.ts` (small file, ~50 LOC, fully unit-tested per M6).

9. **HTML escaping (per M5).** Every dynamic string interpolation into webview HTML goes through `escHtml()` (lifted from `orchestratorIndicatorProvider.ts` into `OrchestratorAccordion.ts`). Includes: set names, descriptions, recommendation text, marker `model` / `modelDisplayName` / `effort.native`, ai-assignment recommendation, "updated Xs ago" formatted strings. Layer-2 test: set name with `<script>` content renders escaped, not executed.

10. **`viewsWelcome` empty state.** Preserve the `viewsWelcome` declaration in `package.json` (operator-discoverable). Extension host parses the contents string at activation, passes to webview as initial render state; webview renders as HTML with `command:` links intact (webview supports `command:` href natively when `enableCommandUris: true`).

11. **Loading-state UX.** When `scanState == loading`, webview renders centered `<div>` "Setting up your project…" with subtext "scanning session sets…". Identical text to today's loading sentinel. Host posts `{ type: "scanStateChanged", state: "loading"|"ready", version }` on every transition.

12. **Orphan handling (per Q8 = a+c).** S3's silent fail-close behavior preserved: when the resolver returns `{ reason: "no-in-progress-set" | "no-docs-session-sets" }`, no marker is written, no accordion is rendered. Add: when `{ reason: "multiple-in-progress-sets" }`, render a banner above the In Progress bucket: `"Multiple in-progress sets — orchestrator info hidden. [Open writer log]"`. Banner is visually distinct from ordinary empty-state copy (lighter background, info-icon prefix).

13. **Indicator-action parity (per M8 — ship blocker for retirement).** Before `dabblerOrchestratorIndicator` view entry is deleted, the accordion body MUST preserve:
    - **Install hook button** (CTA when no marker): fires `dabbler.installOrchestratorHook.claudeCode`.
    - **Set orchestrator button** (CTA when fresh marker / always-available action): fires `dabbler.setOrchestrator`.
    - **Open writer log button** (footer link): fires `dabbler.openOrchestratorWriterLog`.
    All three buttons fire via the same `postMessage` → `vscode.commands.executeCommand` plumbing as the context-menu actions.

14. **Title-bar actions preserved.** `view/title` entries in `package.json` (refresh, showCostDashboard, getStarted) work identically for webview and tree views. No code change.

15. **Layer-2 unit coverage (per M6).** New unit-test files:
    - `src/test/suite/actionRegistry.test.ts` (~100 LOC): every action × every state combination × uat/e2e gating.
    - `src/test/suite/suppressionState.test.ts` (~50 LOC): tuple-key reducer, manual-reexpand clearing, pruning.
    - `src/test/suite/markerWatchService.test.ts` (~100 LOC): state-transition emission (scan / marker-changed / workspace-folder-changed); subscription lifecycle.

16. **Layer-3 Playwright rewrite.** New `src/test/playwright/session-sets-tree.spec.ts` (~500 LOC). Scenarios:
    - Bucket grouping + sort order (port from `treeView.spec.ts`).
    - Accordion auto-expand on SessionStart marker write; auto-collapse on session close.
    - Manual collapse suppresses auto-expand for current occurrence only (write fresh marker → suppression released).
    - Right-click on row opens QuickPick with applicable actions only (assert against `ActionRegistry` expectations).
    - `Shift+F10` and Context Menu key open same QuickPick.
    - Kbd nav: ↑/↓/Home/End/Enter/Space behavior; focus stays on row when accordion collapsed; Tab exits tree cleanly.
    - Multiple-in-progress-sets banner renders with link to writer log.
    - `viewsWelcome` empty state renders with command links functional.
    - Loading-state sentinel → ready transition swaps cleanly.
    - All gauge scenarios from `orchestrator-indicator.spec.ts`: signalKind matrix (current/configured-default/last-observed/manual), confidence-low rendering, mismatch badge, stale state, schema-v3 slug mismatch fallback.
    - HTML escape: set name with `<script>` renders as text.
    - Indicator-action parity: install-hook + set-orchestrator + open-writer-log buttons fire correct commands.
    - Theme parity: light + dark theme screenshots of an in-progress row with expanded accordion.

17. **Selector updates on other Playwright specs.** `src/test/playwright/loading-state.spec.ts` and `src/test/playwright/migration-cta.spec.ts` selectors change from native-tree `[role=treeitem]` / `[aria-label]` patterns to webview-side `[data-slug]` / `[role=treeitem]` patterns (overlap intentional — ARIA role survives). Logic unchanged; assertion strings updated.

18. **Delete superseded files.**
    - `src/providers/SessionSetsProvider.ts` (deleted; tests repointed to `SessionSetsModel`).
    - `src/providers/orchestratorIndicatorProvider.ts` (deleted; helpers moved to `OrchestratorAccordion.ts`, lifecycle moved to `MarkerWatchService.ts`).
    - `src/test/playwright/orchestrator-indicator.spec.ts` (deleted; logic ported to `session-sets-tree.spec.ts`).
    - `src/test/playwright/treeView.spec.ts` (deleted; logic ported to `session-sets-tree.spec.ts`).
    - Package.json `view/item/context` entries (all 14 — actions now fired by `ActionRegistry` via QuickPick).
    - Package.json `dabblerOrchestratorIndicator` view entry.

19. **Version bump:** 0.15.0 → **0.16.0** (minor — architectural change: TreeView → WebviewView).

20. **CHANGELOG.** New `[0.16.0]` entry describing the pivot. Cross-link to `proposal.md` + `synthesis.md`. Notes: indicator-view retired in same release (no parallel surfaces); QuickPick replaces native context menu (UX divergence, theme-aware); `view/item/context` removed from package.json (`ActionRegistry` is the new authority).

**Creates:**

- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
- `tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
- `tools/dabbler-ai-orchestration/src/providers/MarkerWatchService.ts`
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`
- `tools/dabbler-ai-orchestration/src/providers/suppressionState.ts`
- `tools/dabbler-ai-orchestration/src/types/sessionSetsWebviewProtocol.ts`
- `tools/dabbler-ai-orchestration/media/session-sets-tree/client.js`
- `tools/dabbler-ai-orchestration/media/session-sets-tree/tree.css`
- `tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/suppressionState.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/markerWatchService.test.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/session-sets-tree.spec.ts`

**Touches:**

- `tools/dabbler-ai-orchestration/package.json` (flip view type to webview; delete indicator view entry; delete 14 `view/item/context` entries; preserve `view/title`, `viewsWelcome`, commands, configuration; version bump)
- `tools/dabbler-ai-orchestration/src/extension.ts` (register `CustomSessionSetsView`; remove `SessionSetsProvider` + `OrchestratorIndicatorProvider` registrations)
- `tools/dabbler-ai-orchestration/src/test/playwright/loading-state.spec.ts` (selector updates)
- `tools/dabbler-ai-orchestration/src/test/playwright/migration-cta.spec.ts` (selector updates)
- `tools/dabbler-ai-orchestration/src/test/suite/sessionSetsProvider.test.ts` (repoint imports from deleted `SessionSetsProvider` to `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/CHANGELOG.md` ([0.16.0] entry)

**Deletes:**

- `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/treeView.spec.ts`

**Ends with:** Custom tree shipped in v0.16.0. Single unified webview surface; `dabblerOrchestratorIndicator` retired same release. Gauges anchored in-row for in-progress sets. 14 row-actions fired via `ActionRegistry` + QuickPick. WAI-ARIA 1.2 single-select tree pattern with roving tabindex. Versioned monotonic message protocol prevents stale-render races. All dynamic text HTML-escaped. Layer-2 unit coverage for `ActionRegistry`, suppression-state reducer, `MarkerWatchService`. Layer-3 Playwright rewrite covers kbd nav, context menu, ARIA, indicator-action parity, theme parity, schema-v3 slug validation. 0.16.0 packaged, not yet published (publish in S6).

**Progress keys:**

`session-004/view-pivot-shipped`, `session-004/dom-structure-correct`,
`session-004/aria-tree-compliant`, `session-004/three-file-extraction-done`,
`session-004/action-registry-shipped`, `session-004/client-script-extracted`,
`session-004/versioned-protocol-shipped`, `session-004/suppression-reducer-tested`,
`session-004/html-escape-everywhere`, `session-004/viewswelcome-parity`,
`session-004/loading-state-parity`, `session-004/orphan-banner-shipped`,
`session-004/indicator-action-parity`, `session-004/layer2-unit-coverage`,
`session-004/playwright-rewrite-green`, `session-004/selector-updates-applied`,
`session-004/superseded-files-deleted`, `session-004/version-bumped`

**Estimated cost (REVISED per audit synthesis):** **$0.20–$0.60** with Round-B pre-planned per memory `feedback_split_large_verification_bundles`. Round-A verifies the implementation bundle (~1500 LOC pre-split into sub-bundles per the same memory if >700 LOC per slice); Round-B verifies fixes applied.

---

## Risk table additions

Add three new risks; resize two existing risks.

| ID | Change |
|---|---|
| R5 (tab order / focus loss) | **Upgraded to top-tier risk** per GPT-5.4: "the easiest way for a custom tree to feel broken." Mitigation unchanged (WAI-ARIA tree pattern + roving tabindex) but treated as ship-blocker. Layer-3 kbd nav coverage explicit. |
| R6 (QuickPick UX divergence) | **Downgraded to mid-tier risk** per GPT-5.4: "smaller than the focus/a11y risk; an acceptable fidelity loss for v1." Mitigation unchanged. |
| **R9 (new)** | **Invalid interactive nesting / focus trap risk.** Wrapping `role="treeitem"` `<button>` around accordion-body with internal buttons (install-hook, set-orchestrator, open-writer-log) is invalid HTML and bad a11y — interactive content inside an interactive button. Mitigation: M1 fixes the DOM (focusable container, separate header, body in `role="region"` outside the treeitem tabstop). Layer-3 Playwright kbd nav covers focus traversal in/out of expanded accordion. |
| **R10 (new)** | **Webview content-escaping risk (XSS via marker payload).** Set names, descriptions, recommendation text, marker fields all flow into webview HTML. Without escaping, a `<` in a session-set name (or, in the worst case, an attacker-controlled marker payload) corrupts the rendered tree or executes script. Mitigation: M5 mandates `escHtml()` on every dynamic interpolation; Layer-2 + Layer-3 tests cover injection-attempt payloads. |
| **R11 (new)** | **Message-ordering race.** Watcher events / polling backstop ticks / scan refreshes / manual refresh can race in the host; stale messages can repaint over fresh state in the webview. Mitigation: M3 (monotonic `version` field on every render message; webview client.js drops out-of-order). Layer-2 tests verify the reducer drops stale versions. |

---

## Cost-budget update for spec

Update the spec.md "Total estimated cost" table:

- **Custom-tree implementation audit (this audit, 2026-05-18):** $0.025 — Gemini Pro consensus call only (GPT-5.4 via manual paste in GitHub Copilot = $0.00 per `feedback_split_large_verification_bundles`). Authored proposal + synthesis + this S4 spec delta.
- **Session 4 forecast: $0.20–$0.60** (revised from $0.10–$0.30 per Gemini M9 + GPT cost note). Round-A on implementation bundle + Round-B fixes-applied pre-planned.
- **Session 5 forecast: $0.10–$0.30** (unchanged).
- **Session 6 forecast: $0.05–$0.15** (unchanged).
- **Total Set 029 forecast remainder: $0.375–$1.075** (was $0.30–$1.00).
- **Cumulative end of Set 029: $1.95–$2.65** against $5.00 NTE. Headroom intact.

---

## What I'll do once operator approves this delta

1. Apply the replacement section to `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md` (replaces lines ~622–696 — current Session 4 of 6 high-level scaffold).
2. Add R9, R10, R11 to the Risks section; update R5 and R6 wording.
3. Update the "Total estimated cost" section per the budget bumps above.
4. Update the CHANGELOG note pointing at this audit (custom-tree implementation audit, $0.025).
5. Commit as `Set 029 Session 4 spec: custom-tree implementation (post-audit)`.

Nothing in this list ships code — just spec changes. The actual S4 implementation runs as its own session, gated on this spec approval.

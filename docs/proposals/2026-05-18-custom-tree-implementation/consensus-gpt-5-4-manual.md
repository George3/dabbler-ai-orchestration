# GPT-5.4 review - custom-tree implementation

## Overall recommendation

**Recommendation:** Approve the direction, but do not lock this into `spec.md` until six items are tightened: the DOM/a11y shape, the action-registry replacement for `view/item/context`, the webview message contract, the extraction boundary, dynamic-text escaping, and the test plan.

The proposal is directionally right. `SessionSetsModel.ts` is already the correct data-layer seam, the current indicator provider really is doing too many jobs, and keeping two parallel surfaces would create more drift than safety. The main risk is not the pivot itself. The main risk is recreating native-tree behavior badly in a webview: invalid interactive nesting, focus loss, action-applicability drift, and racey host/webview updates.

## Q1 - Render-helper extraction boundary

**Verdict:** Approve option (a), with one tightening.

**Reasoning:** The current `orchestratorIndicatorProvider.ts` is visibly mixed-concern: render helpers, marker resolution, watcher plumbing, polling backstop, and the `WebviewViewProvider` wrapper all live together. S4 should split those concerns now rather than dragging them into a larger custom-tree file. The proposed three-way factoring is the right shape.

**Must-fix items:**
- `MarkerWatchService` should stay presentation-agnostic. It should emit typed state or events, not HTML or webview-specific commands.
- `OrchestratorAccordion` should be pure render logic plus formatting helpers; keep filesystem watchers and VS Code lifecycle out of it.
- Do not keep a dead `orchestratorIndicatorProvider.ts` wrapper around as a re-export shell unless it materially reduces churn. If the old view is retired in S4, deleting the obsolete provider is cleaner than preserving a misleading file.

## Q2 - Auto-expand suppression state shape

**Verdict:** Approve option (a), but the key shape needs to be stricter than the prose currently says.

**Reasoning:** Per-window persistence is correct. File-backed suppression would create surprising cross-window coupling, and memory-only suppression is too fragile for a webview surface that can be disposed and recreated. The behavior being asked for is occurrence-scoped, not slug-scoped.

**Must-fix items:**
- Persist suppression by the full occurrence key: `<slug>:<marker.updatedAt>`, not just by slug. The proposal currently says both things; the tuple is the correct one.
- Bound or prune old suppression entries so `workspaceState` does not accumulate stale keys indefinitely.
- Manual re-expand should clear suppression for the current occurrence immediately.

## Q3 - Accordion body for non-in-progress rows

**Verdict:** Approve option (a) for v1.

**Reasoning:** The feature being shipped is the in-row orchestrator gauge, not a generalized row-details surface. Reusing the accordion body for metadata or AI-assignment previews would widen scope and create another content model to stabilize. For the current set counts in this product, the operator does not need that complexity on day one.

**Must-fix items:**
- Non-expandable rows should not advertise `aria-expanded` and should not show an inert chevron.
- Non-in-progress rows still need a primary activation path, ideally the current `openSpec` behavior on click/Enter.
- Do not render empty `role="region"` containers for rows that cannot expand.

## Q4 - Auto-collapse on session-end

**Verdict:** Approve option (a).

**Reasoning:** It is the cleanest symmetric pair with auto-expand-on-start and avoids dragging Q3's deferred preview ideas back into scope. Keeping an expanded but empty shell would feel broken; keeping a summary panel would become a second feature.

**Must-fix items:**
- Focus must stay on the row when the accordion body is removed; do not strand focus inside disappearing content.
- Auto-collapse should be driven by the same resolved marker/state update path as auto-expand, not by a second ad hoc heuristic.

## Q5 - Scan-state observation by the webview

**Verdict:** Approve option (a).

**Reasoning:** The host is already the authoritative state owner. Polling is unnecessary, and full `webview.html` replacement will cause avoidable focus churn and more brittle rendering. Explicit state-change messages are the correct mechanism.

**Must-fix items:**
- Use a versioned or monotonic message contract so scan refreshes, marker updates, and close-out updates cannot apply out of order.
- Prefer snapshot-style payloads for the row list plus narrow event messages for UI-only changes; that keeps the protocol stable as the view grows.

## Q6 - Context-menu mechanism

**Verdict:** Approve option (a) for v1.

**Reasoning:** Reimplementing a fully accessible HTML context menu in the webview is too much scope for too little user value. QuickPick is a UX change, but it is native enough, keyboard-friendly, and much cheaper to make correct. The key is to prevent command-applicability logic from scattering across the host and webview.

**Must-fix items:**
- Replace the lost `view/item/context` rules with one typed action registry in TypeScript. The same predicates should drive right-click, keyboard context-menu, and any future inline action entrypoint.
- Support `Shift+F10` and the Context Menu key for the focused row, not just mouse right-click.
- If QuickPick is the menu, the `x`/`y` coordinates are unnecessary; do not build protocol surface you are not going to use.

**Recommendations:**
- A small inline overflow button is a reasonable v1.1 addition if the right-click-only discovery cost turns out to matter.

## Q7 - Freshness cue treatment

**Verdict:** Approve option (a).

**Reasoning:** The existing `updated Xs ago` footer is enough for v1. Adding pulse or color-dot affordances would be more animation and state logic for marginal informational gain. The real freshness signal is already present in the gauge body.

**Must-fix items:**
- None beyond keeping the footer text updating correctly when the underlying marker changes.

## Q8 - Orphan-render shape

**Verdict:** Approve option (a) plus (c).

**Reasoning:** S3 intentionally chose fail-closed identity. S4 should preserve that. But the richer UI can and should distinguish "no in-progress set" from "multiple in-progress sets caused ambiguity." A banner for the ambiguity case is actionable without weakening the fail-closed posture or inventing orphan marker semantics.

**Must-fix items:**
- Keep the `multiple-in-progress-sets` case visually distinct from ordinary empty-state copy.
- Do not write orphan markers or synthesize pseudo-attached gauge rows.
- The ambiguity banner should include a direct path to remediation, such as the writer log or session-state inspection command.

## Q9 - "Attached to: <slug>" badge in the accordion body

**Verdict:** Approve option (a).

**Reasoning:** Once the gauge lives inside the row for the resolved set, the badge becomes redundant UI. The stronger safeguard is not a visible badge; it is keeping the existing slug-integrity check and its tests.

**Must-fix items:**
- Retain the `sessionSetSlug` mismatch guard in the reader and in Playwright coverage even if the badge is removed.

## Q10 - Scope packaging

**Verdict:** Approve option (a), with a verification caveat.

**Reasoning:** The implementation is tightly coupled. Splitting it into a visible half-state would produce a worse operator experience and extend the period where two mental models are in play. A config flag would be even worse because it doubles the supported surface with little external-user benefit.

**Must-fix items:**
- Treat keyboard parity, action parity, welcome/loading parity, and indicator-action parity as S4 exit criteria, not stretch goals.
- Plan for at least one likely verification follow-up round even if the implementation itself stays in one session. The coding scope can be single-session while the verification budget still assumes one more pass.

## Q11 - Retire `dabblerOrchestratorIndicator` view in S4 or S5

**Verdict:** Approve option (a).

**Reasoning:** Keeping both views alive would create duplicate truth surfaces, duplicate tests, and the temptation to postpone cleanup. With a three-download operator-only surface, the deprecation window costs more than it protects.

**Must-fix items:**
- Do not retire the old view until the accordion body preserves the current install-hook, set-orchestrator, and writer-log affordances.
- Delete the old view contribution and obsolete tests in the same session so the codebase cannot drift into dual maintenance mode.

## Cross-cutting checks

### 1. Q1-Q11 summary

The proposed defaults are mostly right. My meaningful divergences are not on the answers themselves; they are on the hidden implementation details underneath them: the DOM structure, the action registry, the message protocol, and the verification surface.

### 2. Implementation surface table

**Verdict:** Underestimated slightly.

**Reasoning:** The table is missing at least three likely pieces if this is implemented cleanly:
- A dedicated webview client script for keyboard navigation, selection state, and postMessage handling. If all of that is inlined into `CustomSessionSetsView.ts`, the LOC estimate is artificially low and the maintainability cost goes up.
- A shared protocol/action-types module so host and webview are not stringly typed.
- New unit-test files for the action registry, suppression-state reducer, and `MarkerWatchService` behavior.

**Adjustment:** I would treat the real surface as roughly 1300-1700 LOC of new code if those pieces are first-class, not 1100-1300.

### 3. Risks R1-R8

**Verdict:** The list is good, but two risks are missing and one is undersized.

**Missing risks:**
- **Invalid interactive nesting / focus trap risk.** The proposal's sample DOM puts a `role="treeitem"` button around the accordion body. If that body contains buttons or links, that is invalid HTML and bad accessibility.
- **Webview content escaping risk.** Set names, descriptions, recommendation text, and marker-derived strings must be HTML-escaped before insertion into the webview. The current proposal does not call this out.
- **Message ordering risk.** Watcher events, polling backstop ticks, and scan refreshes can race. Without monotonic snapshots, stale content can repaint over fresh content.

**Risk sizing:**
- R5 should be treated as one of the top risks, not a mid-list concern. Keyboard/focus regressions are the easiest way for a custom tree to feel broken.
- R6 is real, but smaller than the focus/a11y risk. QuickPick is an acceptable fidelity loss for v1.

### 4. Scope packaging (Q10)

Single-S4 implementation is workable. Single-round verification is the optimistic part. I would keep the implementation in one session but pre-plan the verification budget as if a Round B is likely.

### 5. Render-helper extraction (Q1)

Three-file factoring is the right shape:
- webview provider
- pure accordion render helpers
- marker watch / resolution service

I would avoid a fourth long-lived compatibility shell unless import churn makes it temporarily useful.

### 6. ARIA + keyboard-nav scope

**Must-ship in v1:**
- roving `tabindex` or `aria-activedescendant` pattern for row focus
- Up/Down, Home/End, Left/Right, Enter/Space
- `Shift+F10` / Context Menu key
- predictable Tab behavior into and out of expanded accordion content

**Must-fix structural point:**
- Do not model the row as a `<button>` that wraps the accordion body. Use a focusable treeitem container with a separate header control, or another structure that avoids nested interactive content.

**Type-ahead search:**
- Defer to v1.1. It is a real native-tree affordance, but with today's small set counts it is not worth blocking S4.

### 7. Test-layer impact

**Verdict:** Layer 1 is unaffected, but Layer 2 is not quite as frozen as the audit assumes.

**Reasoning:**
- Layer 1 pytest should remain unchanged.
- Existing Layer 2 coverage for `SessionSetsModel` remains valid.
- New Layer 2 coverage is still warranted for the new non-UI logic: action applicability, suppression-state persistence rules, and watcher/service behavior.
- Layer 3 Playwright rewrite is definitely in scope, as the proposal says.

So the cross-check is: the S3 ship keeps the current data-layer assumption valid, but S4 adds new logic that should not be tested only through Electron.

### 8. Cost estimate

**Verdict:** `$0.10-$0.30` is a floor, not a plan.

**Reasoning:** A clean first-pass implementation might hit that number, but Electron Playwright, keyboard handling, and selector churn make one extra verification pass plausible. I would budget more like `$0.20-$0.60` or explicitly plan one main verification bundle plus a smaller follow-up bundle. That is still compatible with a single-S4 implementation; it just avoids pretending the first pass will certainly be the last.

## Consolidated must-fix list

1. Do not use a `<button>` treeitem that wraps the accordion body; fix the DOM structure so interactive controls inside expanded content remain valid and accessible.
2. Replace `view/item/context` with one typed action registry in TypeScript so command applicability cannot drift across right-click, keyboard menu, and future entrypoints.
3. Version the host/webview message protocol so scan updates, marker changes, and polling backstop events cannot repaint stale state.
4. Keep the extraction boundary clean: pure render helpers, presentation-agnostic watcher service, and no misleading dead provider shell unless there is a short-lived migration reason.
5. HTML-escape all dynamic text inserted into the webview.
6. Add Layer 2 unit coverage for the new logic introduced by S4 instead of relying solely on the Playwright rewrite.
7. Key collapse suppression by occurrence (`slug + updatedAt`), not just slug.
8. Treat keyboard/focus parity and current indicator-action parity as ship blockers for retiring the old view.

## Final verdict

**Approve with required implementation corrections before spec lock.** The proposal is on the right path and the answer set for Q1-Q11 is mostly correct. The places that need tightening are the ones native trees used to solve for free: DOM validity, focus management, action gating, state synchronization, and non-Playwright testability. If those are nailed down in the spec, S4 should proceed as a single implementation session with the old indicator retired in the same pass.
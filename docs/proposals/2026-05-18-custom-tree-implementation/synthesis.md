# Synthesis — S4 custom-tree implementation audit

**Date:** 2026-05-18
**Inputs:**
- `consensus-gemini-pro.json` (Gemini Pro via `dabbler-ai-router`, $0.025, 8419 in / 1426 out)
- `consensus-gpt-5-4-manual.md` (GPT-5.4, manual paste in GitHub Copilot, $0.00)
**Status:** **No divergence on the 11 answers.** Both reviewers approve every proposed default (Q1–Q11). GPT-5.4 adds eight must-fix tightening items + three missing risks + an enlarged surface estimate; Gemini adds two items (Round-B planning + type-ahead TODO). Consolidated below; applied to the spec delta.

---

## Both reviewers agree (Q1–Q11)

| # | Question | Locked answer |
|---|---|---|
| Q1 | Render-helper extraction boundary | (a) three-file: `CustomSessionSetsView` + `OrchestratorAccordion` + `MarkerWatchService` |
| Q2 | Auto-expand suppression state shape | (a) `workspaceState` keyed on `<slug>:<marker.updatedAt>` |
| Q3 | Accordion body for non-in-progress rows | (a) empty / no expand toggle |
| Q4 | Auto-collapse on session-end | (a) auto-collapse to header only |
| Q5 | Scan-state observation by webview | (a) host posts explicit state-change messages |
| Q6 | Context-menu mechanism | (a) QuickPick fired by host |
| Q7 | Freshness cue treatment | (a) rely on existing "updated Xs ago" footer |
| Q8 | Orphan-render shape | (a)+(c) keep S3 fail-close; add banner for `multiple-in-progress-sets` |
| Q9 | "Attached to: <slug>" badge | (a) skip — row IS the slug |
| Q10 | Scope packaging | (a) single S4 |
| Q11 | Retire `dabblerOrchestratorIndicator` view in S4 or S5 | (a) retire in S4 |

Eleven of eleven Qs ratified. No operator decisions needed on the answer set itself.

---

## Tightening items must-fix before spec lock

### From GPT-5.4 (eight items)

**M1. DOM structure: don't wrap accordion body in a `<button>` treeitem.**
The proposal's sample DOM (`<button role="treeitem">` containing `<div role="region">` containing potential buttons/links) is invalid HTML — interactive content nested inside a button. **Fix:** focusable treeitem container (`<div role="treeitem" tabindex="-1">`) with a separate header control inside it; accordion body sits outside the button's tabstop. Use roving `tabindex` or `aria-activedescendant` for row focus.

**M2. Typed action registry replaces lost `view/item/context`.**
Today, declarative `package.json` rules decide which of the 14 actions apply to a row based on `viewItem` matching. With the webview, this logic moves to TypeScript. **Fix:** one `ActionRegistry` module with typed predicates `applies(set: SessionSet): boolean` per action; same predicates drive (a) right-click QuickPick, (b) `Shift+F10` / Context Menu key, (c) future inline overflow button. Predicates cannot scatter across host and webview.

**M3. Versioned/monotonic message protocol.**
Watcher events, polling backstop ticks, scan refreshes, and marker updates can race. Stale content can repaint over fresh content without monotonic snapshots. **Fix:** every webview-render message carries a monotonic version field; webview ignores any message with version older than its current. Prefer snapshot-style payloads for row list + narrow event messages for UI-only changes (kbd nav focus, expand toggle).

**M4. Extraction boundary cleanliness.**
- `MarkerWatchService.ts` stays presentation-agnostic — emits typed state/events, NOT HTML or webview commands.
- `OrchestratorAccordion.ts` stays pure render — no filesystem watchers, no `vscode.*` lifecycle calls.
- Old `orchestratorIndicatorProvider.ts` is **deleted** (not preserved as re-export shell) — the file would be misleading after S4.

**M5. HTML-escape all dynamic text.**
Set names, descriptions, recommendation text, marker-derived strings all flow from JSON files into webview HTML. **Fix:** all string interpolations into webview HTML use an `escHtml()` helper (the existing one in `orchestratorIndicatorProvider.ts` lifts cleanly into `OrchestratorAccordion.ts`). Test coverage for an injection-attempt set name.

**M6. Layer-2 unit coverage for new S4 logic.**
The proposal only counts Playwright Layer-3 in scope. **Fix:** add Layer-2 unit tests for:
- `ActionRegistry`: applicability predicates for each of the 14 actions (in-progress / not-started / cancelled / done / needs-migration / uat / e2e gating).
- Suppression-state reducer: `(slug, updatedAt) → suppressed?` semantics; manual re-expand clears suppression for current occurrence; pruning of stale keys.
- `MarkerWatchService`: state transitions (scanState, marker-changed, workspace-folder-changed) emit correct typed events.

**M7. Suppression key shape: `<slug>:<marker.updatedAt>` exact.**
Proposal prose says "keyed on slug" in one place and "(slug, updatedAt) tuple" in another. **Fix:** spec text uses the tuple form everywhere. Also: prune old keys (e.g., on every persist, drop entries where slug is no longer in-progress) so `workspaceState` doesn't accumulate.

**M8. Indicator-view retirement gate.**
Don't delete `dabblerOrchestratorIndicator` until accordion preserves all three indicator-row affordances: install-hook button, set-orchestrator button, open-writer-log button. Keyboard + focus parity is also a ship blocker. Both reviewers explicitly call these out as "exit criteria, not stretch goals."

### From Gemini Pro (two items)

**M9. Round-B verification pre-planned.**
Single-round forecast ($0.10–$0.30) is unrealistic for ~1300–1700 LOC of new code touching webview, ARIA, focus, message protocol, and Playwright. **Fix:** budget $0.20–$0.60 with Round-B explicitly planned (per memory `feedback_split_large_verification_bundles`). Treat first verification as Round-A; expect Round-B for must-fix items surfaced by the verifier.

**M10. Type-ahead search TODO comment.**
WAI-ARIA tree pattern includes type-ahead search. Deferred to v1.1, but should be marked with a `// TODO: type-ahead search (deferred to v1.1)` in the kbd handling code so the gap is discoverable.

---

## Risks — additions and resizing per GPT-5.4

### Three new risks (must be in S4 spec section)

**R9 — Invalid interactive nesting / focus trap risk.** The original sample DOM wraps `role="region"` content inside `role="treeitem" <button>`. Invalid HTML, bad a11y. **Mitigation:** M1 fixes the DOM. Layer-3 Playwright kbd-nav scenarios cover focus traversal in/out of expanded accordion.

**R10 — Webview content-escaping risk (XSS via marker payload).** Marker JSON, set names, ai-assignment text all flow into webview HTML. Without escaping, an attacker (or, more realistically, a typo-introduced `<` in a session-set name) corrupts the rendered tree. **Mitigation:** M5 (mandatory `escHtml()` on every dynamic interpolation). Playwright test: set name with `<script>` content renders as text, not script.

**R11 — Message ordering race.** Concurrent watcher events / polling ticks / manual refresh can paint stale state over fresh. **Mitigation:** M3 (monotonic version field on every render message; webview drops out-of-order messages).

### Risk resizing

- **R5 (tab order / focus loss):** **upgrade to top-tier risk.** GPT-5.4 explicitly: "the easiest way for a custom tree to feel broken." Mitigation: WAI-ARIA tree pattern compliance + roving tabindex; Layer-3 kbd nav coverage covers in/out of accordion.
- **R6 (QuickPick UX divergence):** **downgrade to mid-tier risk.** GPT-5.4 explicitly: "smaller than the focus/a11y risk; an acceptable fidelity loss for v1." Mitigation unchanged.

---

## Implementation surface — adjusted up

### LOC estimate

Original proposal: 1100–1300 LOC new + 750 deleted + 60 package.json churn + 300 Playwright rewrite.

GPT-5.4 adjustment: **1300–1700 LOC new** if separate webview client script + shared protocol/action-types module + Layer-2 unit tests are first-class. Both reviewers agree the proposal counts these somewhat informally.

**Locked estimate:** 1300–1700 LOC new code, 750 LOC deleted, 60 LOC package.json churn, 300 LOC Playwright rewrite, ~200 LOC new Layer-2 unit tests.

### New files (post-tightening)

Original three from proposal, plus three from must-fix:

- `src/providers/CustomSessionSetsView.ts` (~500 LOC) — view provider, message handler, lifecycle
- `src/providers/OrchestratorAccordion.ts` (~400 LOC, extracted) — pure render helpers
- `src/providers/MarkerWatchService.ts` (~150 LOC, extracted) — watcher plumbing, presentation-agnostic
- **`src/providers/ActionRegistry.ts` (~150 LOC, new per M2)** — typed action applicability predicates
- **`media/session-sets-tree/client.js` (~200 LOC, new per GPT M2/M6)** — webview-side kbd nav, selection, postMessage handler. Lifting kbd code OUT of CustomSessionSetsView.ts keeps the host file focused on lifecycle + message protocol.
- **`src/types/sessionSetsWebviewProtocol.ts` (~100 LOC, new per GPT M3)** — typed message contract (HostToWebview / WebviewToHost discriminated unions + monotonic version field)
- `media/session-sets-tree/tree.css` (~150 LOC + lifted gauge CSS)
- `src/test/playwright/session-sets-tree.spec.ts` (~500 LOC, replaces two existing specs)
- **`src/test/suite/actionRegistry.test.ts` (~100 LOC, new per M6)** — applicability predicates × all 14 actions × all state combinations
- **`src/test/suite/suppressionState.test.ts` (~50 LOC, new per M6)** — tuple-key reducer + pruning
- **`src/test/suite/markerWatchService.test.ts` (~100 LOC, new per M6)** — state transition emission

### Modified files (unchanged from proposal)

- `src/providers/SessionSetsProvider.ts` — **deleted**.
- `src/providers/orchestratorIndicatorProvider.ts` — **deleted** (per M4; no re-export shell).
- `src/extension.ts` — register `CustomSessionSetsView`.
- `package.json` — flip type to webview; delete indicator view entry; delete `view/item/context` entries; preserve title/welcome/commands/config.
- `src/test/playwright/orchestrator-indicator.spec.ts` — deleted.
- `src/test/playwright/treeView.spec.ts` — deleted.
- `src/test/playwright/loading-state.spec.ts` — selector updates.
- `src/test/playwright/migration-cta.spec.ts` — selector updates.
- `CHANGELOG.md` — [0.16.0] entry.

### Version bump

**0.15.0 → 0.16.0** (minor — architectural change). Unchanged from proposal; both reviewers confirm.

---

## Cost budget — adjusted

Original proposal estimate: $0.10–$0.30 single end-of-session verification.

**Locked estimate (per Gemini M9 + GPT cost note):** **$0.20–$0.60** with Round-B explicitly planned. Round-A verification on the implemented bundle (~1500 LOC pre-split into sub-bundles per `feedback_split_large_verification_bundles`); Round-B fixes-applied verification.

Set 029 cumulative after S4 + S5 + S6 forecast revision:
- S4 audit (this): $0.025 (Gemini) + $0.00 (GPT manual) = **$0.025 actual**
- S4 verification: $0.20–$0.60 (revised from $0.10–$0.30)
- S5 verification: $0.10–$0.30 (unchanged)
- S6 verification: $0.05–$0.15 (unchanged)
- **Total Set 029 remaining: $0.375–$1.075** (was $0.30–$1.00)
- **Cumulative end of Set 029: $1.95–$2.65** against $5.00 NTE. Headroom intact.

---

## What's locked for the spec delta

Per memory `feedback_audit_then_spec_for_substantial_features` — three-way agreement (operator implicitly via "Audit-then-implement, all in S4" answer, Gemini Pro, GPT-5.4) achieved. The spec delta will:

1. Lock Q1–Q11 answers at proposed defaults.
2. Absorb M1–M10 must-fix items into the Session 4 spec body.
3. Add R9, R10, R11 to the Risks section (and resize R5/R6).
4. Bump LOC + cost estimates.
5. Add `type-ahead search` TODO note per Gemini M10.
6. Pre-plan Round-B verification per M9.

No operator divergences to resolve. Ready for spec delta application on operator approval.

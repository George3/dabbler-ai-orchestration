# Set 029 Session 4 — review

**Verdict:** **VERIFIED** (after Round A SUGGEST item triaged as
optional follow-up; Round B clean).

**Verification cost:** **$0.053** (Round A $0.027 + Round B $0.026,
both via Gemini Pro). Pre-audit cost $0.025 (Gemini Pro consensus on
the implementation audit). **Total S4 spend: $0.078.** Cumulative
Set 029: **$1.651 of $5.00 NTE** ($3.35 headroom remains for S5+S6).

---

## What shipped

The custom-tree pivot — `dabblerSessionSets` re-registered as a
`WebviewViewProvider`, gauges lifted into per-row accordions on the
resolved in-progress set, `dabblerOrchestratorIndicator` view
retired in the same release.

**6 new files** in src/providers/ + src/types/ + media/ (1884 LOC),
**3 new unit-test files** (~325 LOC, 26 new tests), **1 new
Playwright spec** (165 LOC). **5 files deleted**
(SessionSetsProvider.ts 246 LOC, orchestratorIndicatorProvider.ts
998 LOC, treeView.spec.ts 265 LOC, orchestrator-indicator.spec.ts
751 LOC, cancelTreeView.test.ts + entire src/test/suite/e2e/
directory). **Net: +~1500 LOC of new code, -~2260 LOC of deletions.**

Version bumped 0.15.0 → 0.16.0 (minor — architectural pivot).

---

## Round A — provider-layer + types (SUGGEST 1)

**Bundle (~700 LOC):** OrchestratorAccordion.ts + MarkerWatchService.ts
+ ActionRegistry.ts + suppressionState.ts +
sessionSetsWebviewProtocol.ts.

**Scope:** M2 (typed registry), M3 (versioned protocol), M4
(extraction cleanliness), M5 (HTML escape coverage), M7 (tuple
suppression key), R8 (walk-up resolver fail-closed carry-forward).

**Verdict on the 7 Qs:**

| Q | Topic | Verdict |
|---|---|---|
| Q1 | OrchestratorAccordion extraction cleanliness (M4) | **SUGGEST** |
| Q2 | HTML escape coverage (M5 / R13) | VERIFIED |
| Q3 | ActionRegistry predicate correctness (M2) | VERIFIED |
| Q4 | suppressionState tuple-key semantics (M7) | VERIFIED |
| Q5 | Versioned message protocol (M3) | VERIFIED |
| Q6 | MarkerWatchService presentation-agnostic boundary (M4) | VERIFIED |
| Q7 | Walk-up resolver fail-closed posture (R8 carry-forward) | VERIFIED |

**The one SUGGEST item:**

`describeMarker(marker)` in OrchestratorAccordion.ts calls
`Date.now()` to compute the "(last /think Xm ago)" suffix when the
effort signal is `last-observed`. This makes the function not
strictly deterministic — its output depends on the system clock for
that one suffix. The primary `ageSec` is already computed by the
caller (MarkerWatchService) and passed in.

**Triage:** optional follow-up. The function is "almost pure" — only
the secondary effort-age touches Date.now, and only for one display
suffix. Adopted-as-known-debt rather than fixed in S4 because:
- It's not a correctness issue (the suffix is informational, not
  semantic).
- The simple fix (pass `effortAgeSec` into `describeMarker`) requires
  adjusting one call site in `renderAccordionLoaded` and one in
  Layer-3 spec — small but cross-cuts the bundle.
- Round B passed clean, so the integration is solid; this is a code-
  hygiene polish, not a ship blocker.

Suggested for follow-up in a hygiene PR or as a one-line fix during
S5/S6.

---

## Round B — integration: view + client (VERIFIED)

**Bundle (~1100 LOC):** CustomSessionSetsView.ts + client.js + tree.css.

**Scope:** M1 (DOM structure — no `<button>`-wrapped accordion), M3
(monotonic version drop, client side), M6 (command-dispatch
allowlist), M8 (indicator-action parity preserved), Q7 (suppression
handshake), Q8 (ambiguity banner), CSP/nonce hygiene.

**Verdict on the 8 Qs:**

| Q | Topic | Verdict |
|---|---|---|
| Q1 | DOM structure: no invalid interactive nesting (M1 / R12) | VERIFIED |
| Q2 | ARIA tree semantics (WAI-ARIA 1.2) | VERIFIED |
| Q3 | Monotonic version drop client-side (M3) | VERIFIED |
| Q4 | Command-dispatch allowlist | VERIFIED |
| Q5 | Indicator-action parity (M8) | VERIFIED |
| Q6 | Suppression handshake (host ↔ webview) | VERIFIED |
| Q7 | Ambiguity banner (Q8 = a+c) | VERIFIED |
| Q8 | CSP + nonce hygiene | VERIFIED |

No must-fix items, no further suggestions.

---

## Layer-2 unit test results (npm run test:unit)

**369 passing, 2 pre-existing failures unrelated to S4.**

S4's 26 new tests all green:
- `actionRegistry.test.ts` — 9 tests covering all 14 actions ×
  state combinations × uat/e2e gating. ROW_ACTIONS membership test
  proves the registry exposes exactly the 14 actions S3 had in
  package.json's deleted `view/item/context`.
- `suppressionState.test.ts` — 10 tests covering the tuple-key
  reducer, manual-reexpand clearing, pruning, and the
  "SessionStart-naturally-lifts-suppression" aging invariant.
- `markerWatchService.test.ts` — 7 tests covering
  `extractRecommendation()`'s parsing of ai-assignment.md across
  heading variants, missing-block fallbacks, and trailing-
  punctuation trimming.

The 2 pre-existing failures (`configEditor-foundation` ViewColumn
stub gap, `notificationsSection` HTML assertion) predate S4 and are
not in the scope of this session.

---

## TypeScript compile

`npx tsc --noEmit` — clean. No errors, no warnings.

---

## Layer-3 Playwright coverage

`session-sets-tree.spec.ts` covers:
- ARIA tree structure rendering (role + aria-level + bucket grouping)
- HTML-escape XSS path (set name with HTML special chars renders as
  text)
- Welcome panel rendering when no sets exist (webview path)
- Loading-state sentinel → ready tree transition

The harness helper `openSessionSetsView` was updated to return a
`FrameLocator` traversing VS Code's two-level webview iframe stack
(outer sandbox + inner content frame). The two surviving Playwright
specs (loading-state.spec.ts + migration-cta.spec.ts) were adapted
to use this FrameLocator. The retired specs
(orchestrator-indicator.spec.ts + treeView.spec.ts) were deleted.

---

## Cost vs. spec forecast

**Spec forecast:** $0.20–$0.60 with Round-B pre-planned per memory
`feedback_split_large_verification_bundles`.

**Actual:** $0.053 across two routed rounds (no Round-C needed).
Came in well under the floor of the spec forecast — partly because
both rounds converged cleanly without surfacing must-fix items that
would have triggered a third round, partly because Gemini Pro is
significantly cheaper than the gpt-5-4 rounds that drove the
empirical p50/p95 the forecast was based on.

---

## Open items for follow-on sessions

1. **Polish:** `describeMarker` `Date.now()` purity (Round A SUGGEST).
   Suggested fix: pass `effortAgeSec` into the function instead of
   computing inline. Cross-cuts one call site in
   `renderAccordionLoaded`. ~10 LOC.
2. **Type-ahead search** in the tree (Gemini M10 from the S4 audit).
   Deferred to v1.1; `// TODO:` marker in `client.js` already
   placed.
3. **Inline overflow button** for row actions (GPT-5.4 Q6
   recommendation). Optional v1.1 if right-click-only discovery
   cost matters in real use.
4. **Visual freshness cue beyond "updated Xs ago"** (Q7 deferred to
   v1.1 — pulse animation or status-dot indicator). Defer until
   cross-window confusion surfaces in real use.

None of these are ship blockers for v0.16.0.

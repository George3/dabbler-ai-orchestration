# Session 2 review summary — Set 029 (orchestrator model & effort indicator gauges)

**Date:** 2026-05-18
**Verdict:** VERIFIED after three verification rounds against gpt-5-4
**S2 routed cost:** $0.578 (A $0.152 + B $0.206 + C $0.220)
**Cumulative set cost:** $1.423 against the operator's $5.00 NTE

## Quick scorecard

| Round | Bundle | Cost | Findings | Outcome |
|---|---|---|---|---|
| A | marker writer + CSS visual matrix (~605 LOC) | $0.152 | 3 must-fix (TOCTOU, UserPromptSubmit clobber, stripes painted behind SVG) + 1 should-fix (docs drift) | All addressed |
| B | provider + installer (~565 LOC) | $0.206 | 2 must-fix (effort suffix wrong signal, gauge angle math inverted) | All addressed |
| C | confirmation pass on full post-fix bundle | $0.220 | 4/5 fully resolved, 1 partial (UserPromptSubmit re-read before tmp write, not before rename) | Tightened mechanically |

Round-by-round finding count: 3 → 2 → 1 (convergence, not spiral per
memory `feedback_verifier_spiral_recruit_codex`). No Round D needed.

## What shipped

- **Orchestrator Indicator webview view** pinned above the Session Sets
  tree (`dabblerOrchestratorIndicator`, type:`webview`, no
  `initialSize` per audit S3). Two semi-circle CSS gauges side-by-
  side: Model (low/mid/flagship → red/yellow/green) and Effort
  (Low/Medium/High/Extra-High/Max) plus a binary Thinking LED beside
  the effort gauge.
- **Visual-treatment matrix** per signalKind (REVISED 2026-05-18):
  current/configured-default/last-observed/manual + a signal-agnostic
  stale-overlay painted ABOVE the gauge artwork via
  `.stale .gauge-cell::before` pseudo-element (Round A Q8 fix).
- **Tooltip copy embeds confidence explicitly** ("live signal (low
  confidence — hook payload missing model)", etc.).
- **Claude SessionStart hook installer command** — idempotent edit of
  `~/.claude/settings.json`, installs SessionStart × 4 source matchers
  (startup/resume/clear/compact) + one UserPromptSubmit hook. Preserves
  foreign hooks.
- **Shared `write-orchestrator-marker.js` helper** — four modes,
  multi-writer precedence with re-read-immediately-before-rename TOCTOU
  closure, 5-attempt retry loop at 50/200/600/1200ms backoff, confidence-
  low producer rule on missing/null/unparseable payload model.
- **8 Playwright scenarios** at `src/test/playwright/orchestrator-indicator.spec.ts`,
  all green. (Initial run had a broken iframe selector — fixed by
  switching from `frameLocator` to the lower-level
  `contentFrame().childFrames()` API to reach the programmatically-
  added webview content frame.)

## Operator-on-device feedback applied mid-S2

Three live observations after seeing the rendered gauges:

1. **Medium effort gauge color arc rendered "too low"** — was at
   -120° (1/3 fill) vs. the Model gauge for Opus at -30° (5/6 fill).
   Visually jarring imbalance. Re-centered the 5-level effort scale
   so Medium sits at the gauge center (-90°, half-fill).
2. **Fonts + gauges too small for legibility.** Bumped gauge SVG
   70×38 → 100×54, fonts ~40-50% bigger across the board, container
   max-height 100 → 150px.
3. **Responsive layout needed.** Added a media query that wraps the
   second gauge below the first at panel widths <260px.

The audit-locked "≤100px hard constraint" D3 phrasing is now
superseded; documented via superseding notes in audit-summary.md and
spec.md plus a new "Mid-S2 sizing + responsive-wrap revision"
section in CHANGELOG. Memory `gauges-sizing-followup` updated to
reflect that this is now SHIPPED, not pending.

## R7 pre-implementation verification

WebFetch against the official Claude Code hooks docs confirmed all
three preconditions: `/clear` fires `SessionStart` with
`source: "clear"`, `/think*` are per-message escalations (not
session settings), `UserPromptSubmit` exposes the `prompt` field
with full message text. R7 both-conditions are TRUE; SessionStart
hook clobbers effort to Medium on every source value. UserPromptSubmit
`/think*` detection ships at full functionality.

## Spec drift corrections

- spec.md S2 step 8 said "0.13.17 → 0.13.18" (authored before Set 030
  shipped 0.14.x); corrected to 0.14.1 → 0.14.2.
- spec.md S2 step 7 said "tools/dabbler-ai-orchestration/tests/playwright/";
  actual path is `src/test/playwright/` (aligned to existing
  `playwright.config.ts` `testDir`).

## Process notes for future calibration

- **Bundle splitting works.** S1 had three sequential rounds against
  spec.md regions because each round exposed un-bundled territory.
  S2's split-by-component-layer (A: data + visual, B: integration +
  hook) kept each bundle under 700 LOC AND surfaced findings that
  were focused on the bundled code, not adjacent un-bundled code.
- **Round C is cheap insurance.** $0.220 to confirm 4 of 5 fixes
  fully resolved and surface the one residual race-window that the
  Round A fix missed. Worth it.
- **Verifier output-token cost variance is high.** Round B emitted
  12k output tokens for a ~9.5k input prompt; Round C emitted 12k
  for a ~13k input. The cost-per-input-token is fairly stable but
  output tokens drive cost as much as input. Memory
  `feedback_split_large_verification_bundles` should track output
  size, not just input LOC.
- **Operator on-device feedback is invaluable.** The Medium-too-low
  gauge issue would not have been caught by the Playwright scenarios
  (which check CSS classes, not pixel positions). The gauge angle
  math bug (Round B Q4 must-fix) was also a visual-correctness issue
  that the verifier caught via geometric reasoning that the
  Playwright tests can't see.

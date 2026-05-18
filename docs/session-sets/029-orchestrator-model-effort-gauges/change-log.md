# Set 029: Orchestrator Model & Effort Indicator Gauges

**Status:** In progress (2 of 6 sessions complete; mid-set pivot 2026-05-18 reshaped 4 → 6 sessions)
**Created:** 2026-05-17
**Cost so far:** $1.464 (S1 $0.845 + S2 $0.578 + mid-set custom-tree-pivot audit $0.022 Gemini Pro; GPT-5.4 via manual paste = $0.00).
**Forecast remaining:** $0.40–$1.25 across S3 + S4 audit + S4/S5/S6 verifications.
**NTE ceiling:** $5.00 (operator-confirmed 2026-05-18 at S1 resume).

---

## Context

The operator routinely switches the orchestrator model down for cheap
tasks (Claude Haiku for a quick rename) and sometimes forgets to
switch back up to Opus before starting substantive work. The failure
mode is silent: a new session opens on a lower-tier model, output
quality is wrong, and the session has to be aborted or salvaged.

Set 029 adds an always-on visual signal — two semi-circle CSS gauges
pinned above the Session Set Explorer — that makes the current
orchestrator model and effort level glance-readable at all times.

v1 supports all four of the operator's orchestrator surfaces (Claude
Code, Gemini Code Assist Agent, Codex, GitHub Copilot) with
auto-detection where viable and a manual-override quickpick command
as the universal fallback.

---

## Session 1: cross-provider design audit (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after three verification rounds + one cross-
engine consensus call. All 12 Round-A must-fix items addressed in
Round B; incidental drift surfaced in Rounds B and C closed
mechanically against locked D1–D10 / Q1–Q6 decisions.

**Deliverables:**

- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/audit-summary.md`
  (post-Round-C, all locked-design decisions captured)
- `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
  (post-Round-C, drift-free, Goal state aligned with D1–D10 + Q1–Q6)
- `session-reviews/session-001/` (Rounds A/B/C + consensus call
  scripts, prompts, raw responses, and session-001-review.md)

**Locked design decisions Session 2 implements verbatim:**

1. Marker schema v2 at `~/.dabbler/current-orchestrator.json`
   with `signalKind` (`current` | `configured-default` |
   `last-observed` | `manual`), `confidence`, `effort.signalKind`,
   `effort.confidence`, `effort.observedAt`, `stalenessMaxSec`
   (default 28800s = 8h).
2. Claude `SessionStart` hook (NOT Stop) writes the marker on
   session start; `UserPromptSubmit` hook (field-availability
   gated) writes effort updates on `/think*`.
3. Multi-writer precedence policy (`current` > `manual` >
   `last-observed` > `configured-default`) with read → re-read
   immediately before atomic rename → skip-if-weaker semantics.
   Manual-override quickpick has a force-override escape hatch.
4. Windows retry loop: 5 attempts at 50/200/600/1200ms backoff
   (~2050ms total ceiling).
5. Confidence-low producer rule: helper emits `confidence: "low"`
   + `model: "unknown"` on missing/null/unparseable payload.
6. Pre-implementation `/clear` dual-condition verification: only
   clobber `last-observed` on `/clear` if `/clear` both fires
   SessionStart AND resets effort.
7. Visual-treatment matrix: stripes are stale-only;
   `configured-default` = dashed rim + DEFAULT pill;
   `last-observed` = hollow rim + clock-icon overlay + time-elapsed
   sublabel; `manual` = solid + operator-icon overlay.
8. No `initialSize`; container height cannot be guaranteed
   (documented in CHANGELOG); Playwright screenshot assertions in
   clean profile only.

**Process notes worth surfacing:**

- The router-call waiver from S1 step 2 (no `route_audit.py`) is
  durably noted in spec.md so future maintainers don't expect that
  file.
- A new in-session-consensus class of router call was introduced
  this session per memory `feedback_prefer_ai_consensus_over_human_prompt`:
  design refinements get routed through GPT-5.4 + Gemini Pro before
  AskUserQuestion. Successfully rehearsed here; the formal
  `delegation.decision_consensus` config knob remains a candidate
  follow-on session set (see `docs/planning/delegation-consensus-config.md`).
- Round-A bundles should include the entire spec.md in future
  audit-then-spec sessions; Rounds B and C exposed pre-audit drift
  in regions not bundled in Round A. Cost-wise this is fine —
  session-verification at the gpt-5-4 rate handles full spec.md
  bundles for under $0.50.
- Round C cost $0.36 vs. typical p50 $0.13 due to gpt-5-4 emitting
  22k output tokens. Note for memory `feedback_split_large_verification_bundles`
  scope — output-token blowup can drive cost as much as input-token
  size.

**Cost breakdown:**

| Round | Tokens (in/out) | Cost | Verdict |
|---|---|---|---|
| Round A verification | 14,923 / 15,144 | $0.264 | REJECTED, 12 must-fix |
| Bucket-2 consensus (gpt-5-4 + gemini-pro) | 2,606+2,794 / 4,915+83 | $0.085 | Both engines accept direction |
| Round B verification | 17,043 / 6,333 | $0.138 | 12 ADDRESSED + 1 new |
| Round C verification | 10,660 / 22,077 | $0.358 | 1 ADDRESSED + 2 new mechanical |
| **Session 1 total** | — | **$0.845** | VERIFIED |

## Session 2: core webview + Claude detection + hook installer (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after three verification rounds (Round A + Round B + Round C confirmation). 5 must-fix items surfaced across A/B; all addressed; Round C confirmed 4/5 fully resolved and surfaced one residual race-window in the user-prompt-submit merge branch (re-read happened before tmp write rather than immediately before rename); tightened mechanically. Round-by-round finding count was 3→2→1 — convergence, not spiral per memory `feedback_verifier_spiral_recruit_codex`. No Round D.

**Deliverables (Claude-only v1 preview):**

- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts` (~395 LOC) — `WebviewViewProvider` for `dabblerOrchestratorIndicator`. Marker reader + FileSystemWatcher + 60s poll backstop + 50ms render debounce. Renders SVG semi-circle gauges with the audit-locked visual-treatment matrix (current/configured-default/last-observed/manual). Tooltip copy embeds confidence explicitly.
- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js` (~410 LOC after R-A/R-C tightenings) — shared marker writer. Four modes (session-start, user-prompt-submit, manual, configured-default). Multi-writer precedence with re-read-immediately-before-rename closing the TOCTOU window. 5-attempt retry loop at 50/200/600/1200ms backoff for Windows file-watcher contention. Confidence-low producer rule when SessionStart payload `.model` is missing/null/unparseable. Reused by Session 3 writers.
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts` (~170 LOC) — idempotent installer for SessionStart × 4 source matchers (startup/resume/clear/compact) + UserPromptSubmit hook in `~/.claude/settings.json`. Atomic write. Preserves foreign hooks verbatim.
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManualStub.ts` (~25 LOC) — stub for `dabbler.setOrchestrator`; surfaces a "coming in 0.14.3" dialog with one-click jump to the Claude installer until Session 3 lands the full quickpick.
- `tools/dabbler-ai-orchestration/src/commands/openOrchestratorWriterLog.ts` (~25 LOC) — opens `~/.dabbler/orchestrator-writer.log` for diagnosing skipped marker writes.
- `tools/dabbler-ai-orchestration/media/orchestrator-indicator/indicator.css` (~250 LOC after sizing+overlay revisions) — visual-treatment matrix CSS + responsive-wrap at <260px panel widths + stale-overlay pseudo-element painting at z-index 2 above the gauge artwork.
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts` — 8 Playwright scenarios (current Opus, Haiku, low-confidence, last-observed effort, configured-default, stale, empty-state, and helper-precedence non-Electron). All green.

**Pre-implementation verification (R7 dual-condition check):**

WebFetch against the official Claude Code hooks docs confirmed all three preconditions: `/clear` fires `SessionStart` with `source: "clear"` (matcher table); `/think*` are per-message escalations not session settings (so `/clear` is a fresh-session boundary semantically — R7 BOTH conditions TRUE); `UserPromptSubmit` payload includes the `prompt` field with full user-submitted text (so `/think*` prefix detection ships at full functionality without the Medium-only fallback). Design decision: SessionStart hook clobbers effort to Medium on ALL source values (startup/resume/clear/compact) — simpler than per-source branching and lagging-signal-resistant.

**Mid-S2 operator feedback (live, after first Playwright run):**

After seeing the rendered gauges, the operator flagged: (a) the Medium effort gauge's color arc was visually too low compared to the Model gauge — was at -120° (1/3 fill) while the Model gauge for Opus rendered at -30° (5/6 fill); (b) fonts + gauges needed to be ~40-50% bigger for legibility; (c) the layout needed to wrap responsively when the panel is narrow. Applied in-session: Medium effort needle re-centered to -90° (gauge midpoint, half-fill) with other levels redistributed; gauge SVG 70×38 → 100×54 (~43% bigger); font sizes bumped ~40-50%; container max-height 100 → 150px; responsive wrap at <260px. The audit-locked "≤100px hard constraint" in D3 is now superseded; documented with a superseding note in audit-summary.md and spec.md. Memory `gauges-sizing-followup` updated to reflect this is now SHIPPED, not pending. New CHANGELOG section "Mid-S2 sizing + responsive-wrap revision" added.

**Significant verifier findings + fixes:**

| Round | Finding | Fix |
|---|---|---|
| Round A Q2 | TOCTOU race in `attemptWriteWithPrecedence` — read-once-decide-write left a race window | Added re-read immediately before `renameSync`; skip with `weaker-than-existing-on-reread` reason if a stronger fresh marker raced ahead |
| Round A Q6 | UserPromptSubmit merge/bootstrap could clobber fresher SessionStart markers | Rewrote the merge branch to read latest snapshot inside the try block, immediately before `writeFileSync` + `renameSync` |
| Round A Q8 | Stale stripes used `background-image` on `.gauge-svg` which paints BEHIND the SVG content, not as a true overlay; also alpha was 18% vs. the audit's 50% target | Replaced with `.stale .gauge-cell::before` absolute-positioned at z-index 2 with `pointer-events: none` and 45% alpha |
| Round B Q1 | `renderLoaded` effort suffix branches (`(default)` / `(manual)`) keyed off `marker.signalKind` (top-level model signal) instead of `marker.effort.signalKind` | All three effort suffix branches now check `marker.effort.signalKind`; effort and model are independent axes per schema v2 |
| Round B Q4 | Gauge angle math used a `180 + needleAngleDeg` offset that inverted the y-axis, sending -90° DOWN instead of UP — all needle/fill endpoints were BELOW the visible viewBox | Removed the `180 +` offset; use angle directly. SVG's y-down axis naturally inverts sin behavior: `cy + radius * sin(-90°) = cy - radius` correctly places the endpoint at top-center. Also simplified `largeArc = 0` always (upper-semicircle arcs are always ≤180°) |
| Round C residual | The Round A Q6 fix re-read happened BEFORE the tmp-file write, not immediately before rename — partial fix | Tightened: `readExistingMarker()` now happens inside the try block immediately before `writeFileSync` + `renameSync`. Residual window matches `attemptWriteWithPrecedence`. |

**Process notes:**

- The Playwright iframe selector was broken in the initial spec — `iframe[title*="Orchestrator"]` doesn't match because VS Code wraps webview views in `iframe.webview` (no title) and the actual content lives in a PROGRAMMATIC child iframe added by the outer iframe's service-worker bootstrap (no `<iframe>` element in the outer DOM, so Playwright's `frameLocator` chains can't see it). Fix used the lower-level Frame API: `page.locator('iframe.webview').elementHandle()` → `contentFrame()` → `childFrames()`. Documented in the helper's comments + the activity log.
- Pre-existing `treeView.spec.ts` failures (2 of them) reproduce on clean master without S2 changes — unrelated.
- Pre-existing `notificationsSection.test.ts` + `configEditor-foundation.test.ts` failures in `npm run test:unit` also reproduce on master — unrelated Set-026/Set-030-era test issues, not regressions from S2.
- Spec drift correction: spec.md S2 step 8 said "0.13.17 → 0.13.18" (authored 2026-05-17, before Set 030 shipped its 0.14.x line); corrected to 0.14.1 → 0.14.2.
- The `tests/playwright/` path in spec.md S2 step 7 should be `src/test/playwright/` — aligned to the actual `playwright.config.ts` `testDir`. Spec is durably stale on the path; CHANGELOG documents the correction.

**Cost breakdown:**

| Round | Tokens (in/out) | Cost | Verdict |
|---|---|---|---|
| Round A verification (marker writer + CSS) | 9,255 / 8,607 | $0.152 | 3 must-fix |
| Round B verification (provider + installer) | 9,590 / 12,159 | $0.206 | 2 must-fix |
| Round C confirmation pass | 13,361 / 12,407 | $0.220 | 4/5 fully fixed, 1 residual; tightened |
| **Session 2 total** | — | **$0.578** | VERIFIED |

Bundle splitting per memory `feedback_split_large_verification_bundles`: full set of code was ~1170 LOC, split into A (~605 LOC) and B (~565 LOC) to stay under the 700-LOC ceiling. Round C re-bundled the full post-fix versions of all three high-leverage files.

## Mid-set pivot (2026-05-18) — custom-tree audit

Post-S2 polish surfaced a structural issue: the v0.14.2
`~/.dabbler/current-orchestrator.json` is a single global file. The
operator's three-parallel-window workflow (per memory
`project_consumer_repos`) means every window's SessionStart hook
clobbers the same marker — the most-recently-started session wins,
the others' gauges silently show wrong data.

An initial fix path (per-workspace markers hashed by workspace
folder path) was drafted at
[`docs/proposals/2026-05-18-per-workspace-orchestrator-markers/`](../../proposals/2026-05-18-per-workspace-orchestrator-markers/)
and reviewed by Gemini Pro + GPT-5.4 (manual paste). Mid-review
the operator and I concluded the underlying issue is the **identity
model**, not just the marker path. A second pivot proposal at
[`docs/proposals/2026-05-18-custom-tree-pivot/`](../../proposals/2026-05-18-custom-tree-pivot/)
re-routed the design through both reviewers.

**Reviewer verdicts converged on 7 of 10 questions; diverged on
3.** Operator decisions resolved the divergences (split S3 from
custom-tree work; fail-closed on ambiguous resolution; no
workspace orphan marker). Set 029 reshapes:

| New session | Goal | Status |
|---|---|---|
| S3 | Per-session-set identity (marker schema v3, walk-up resolver, `SessionSetsModel` extraction) | pending |
| S4 | Custom-tree pivot (webview-based Session Sets tree with embedded gauges) | pending, gated by own pre-session audit |
| S5 | Non-Claude detection + manual override (renumbered from old S3, content unchanged) | pending |
| S6 | Polish + README + Marketplace publish (renumbered from old S4, content unchanged) | pending |

The pivot itself shipped no code; spec.md was updated to reflect
the new structure. v0.14.2 stays the released-but-unpublished
state of the extension until S3 ships 0.15.0.

**Cost:** $0.022 (Gemini Pro consensus call; GPT-5.4 manual = $0.00).

## Session 3: (pending — per-session-set identity)

(populated at session close)

## Session 4: (pending — custom-tree pivot; gated by own pre-session audit)

(populated at session close)

## Session 5: (pending — non-Claude provider detection)

(populated at session close)

## Session 6: (pending — polish + marketplace publish)

(populated at session close)

---

## Final cost summary

(populated after Session 6 close-out)

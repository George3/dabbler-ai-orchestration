# Set 029: Orchestrator Model & Effort Indicator Gauges

**Status:** In progress (1 of 4 sessions complete)
**Created:** 2026-05-17
**Cost so far:** $0.845 (S1 actual); forecast $1.15–$1.75 inclusive
of S2–S4 verification calls.
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

## Session 2: (pending — core webview + Claude detection)

(populated at session close)

## Session 3: (pending — non-Claude provider detection)

(populated at session close)

## Session 4: (pending — polish + marketplace publish)

(populated at session close)

---

## Final cost summary

(populated after Session 4 close-out)

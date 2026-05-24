# Open-Question Resolution — Set 045 / Session 1

> **Status:** Session 1 spike complete 2026-05-24.
> **Source:** Set 044 proposal v1 §6 carried four open empirical
> questions into Set 045. This document records the spike-pass
> resolution of each. The detailed evidence lives in the companion
> artifacts under
> [`spike-prototypes/`](spike-prototypes/) and
> [`joiner-location-decision.md`](joiner-location-decision.md).

---

## Q1. What fraction of real-world AI sessions are Dabbler-launched vs. free-running?

**Resolution:** **Clock-started.** A self-observation log was
designed and initialized; the bypass-rate fraction will be computed
at the start of Set 045 S5 (Explorer integration) from 1–2 weeks of
operator activity.

- **Log file (operator-local):** `~/.dabbler/bypass-observation-log.jsonl`.
- **Schema + capture protocol:**
  [`spike-prototypes/bypass_observation_log_schema.md`](spike-prototypes/bypass_observation_log_schema.md).
- **Capture mechanism for the observation window:** end-of-day
  reflective entries (lowest-friction) plus optional per-session
  entries. Wrapper-automated capture replaces manual entries
  post-S3 when `dabbler-launch` ships.
- **Decision rules:** ranges < 25% / 25–60% / > 60% map to different
  investment-split implications (see the schema doc §5). The locked
  dual-primary architecture from Set 044 is correct regardless of
  the fraction — the question only sharpens prioritization between
  S3 (wrapper) and S4 (Claude parser) work.

**Why this is enough for the spike pass:** the question requires
*operator-time observation* to answer (no amount of analytical work
in a single session can produce it). The S1 deliverable is the
infrastructure to make the answer accumulate; the actual fraction
lands by S5.

---

## Q2. Can the wrapper-record schema be deterministically joined to provider-native logs?

**Resolution:** **YES.** The prototype
[`spike-prototypes/correlation_prototype.py`](spike-prototypes/correlation_prototype.py)
demonstrated 1:1 binding on real on-disk logs for both backends at
a 30-second window.

### Evidence (from `correlation_prototype_report.json`)

| Scenario | Window | Result |
|---|---|---|
| Positive Claude (launch 5 s before native first event) | 30 s | **1:1 bind** to `ef28a7ff…` (this very session's JSONL) |
| Positive Claude | 5 s | **1:1 bind** (same) |
| Positive Claude | 2 s | no-match (window too tight; native first event lags wrapper ~5 s) |
| Positive Copilot (launch 5 s before `session.start` event) | 30 s | **1:1 bind** to `5ef62da5…` |
| Negative — launch 10 minutes off | 30 s | correctly no-match |
| Negative — wrong workspace_cwd | 30 s | correctly no-match |
| Ambiguity probe — Claude 1 hour window | 1 h | still 1:1 (workspaces don't host concurrent bracketed sessions in practice) |

### Recommendations baked into the Set 045 implementation

- **Default conflict window:** 30 s. Tight enough to avoid spurious
  ambiguity in busy workspaces; wide enough to absorb Claude's
  observed ~5 s subprocess-spawn-to-first-event lag.
- **Hard prerequisite:** `workspace_cwd` canonicalization
  (case-insensitive on Windows, forward-slash, no trailing slash).
  The Claude project-dir slug encodes cwd ambiguously (dashes in
  the original path become path separators after the slug round-
  trip), so the join must consult the `cwd` field on the JSONL's
  first user record rather than relying on the slug.
- **Multi-match handling:** on any join that produces > 1 candidate
  within the window, the joiner emits a structured ambiguity
  warning rather than silently picking one. The empirical risk is
  low (the ambiguity probe at 1 h still hit 1:1), but the
  production joiner cannot rely on luck.
- **No-match tolerance:** the joiner does NOT treat "no-match"
  as a coordination conflict. The AI subprocess may have failed to
  spawn, or the operator may have launched and immediately killed.
  The wrapper's launch record is preserved for audit; the joiner
  simply leaves the row un-bound.

---

## Q3. What's the actual phrasing-trigger boundary on Claude's injection classifier?

**Resolution:** **Analytical pass complete; eight-run follow-on
ablation protocol authored, optional for the operator to execute.**
The defensive canonical-template recommendations below are
*sufficient* for Set 045 S4 to ship without running the ablation.

- **Full analysis:**
  [`spike-prototypes/claude_phrasing_ablation_analysis.md`](spike-prototypes/claude_phrasing_ablation_analysis.md).
- **Strongest two hypotheses (from Claude's own thinking
  paraphrase in S4b):**
  - **H1:** the "harvest" / "harvester" lexical family is the
    primary trigger.
  - **H8 (composite):** "harvest" + pretense self-disclosure
    ("NOT a real project") together cross the threshold; either
    alone is below.
- **Defensive canonical template rules for S4** (applicable
  *independently* of whether the operator runs the ablation):
  1. Avoid the "harvest" lexical family entirely. Use "downstream
     tooling", "session-boundary markers", "correlation".
  2. Avoid pretense self-disclosure. Do not include "NOT a real
     project", "synthetic", "smoke probe", or similar self-flagging
     language. A synthetic-test variant of the template can live
     under a clearly-different filename so it is never picked up
     by real consumer-project CLAUDE.md resolution.
  3. Frame the marker as a *project convention* the assistant is
     asked to follow, not as a *data-emission request* directed at
     the model.
  4. Keep caps emphasis to a minimum.
- **Optional ablation protocol** ($1–3 estimated cost): 8 fresh
  Claude Code runs (A1 control + A2–A8 single-variable
  reintroductions) against `c:\tmp\dabbler-log-harvest\synthetic-set\`
  with matched S4b experimental controls. If run, the results
  upgrade the defensive posture from "best-evidence-defensive" to
  "isolated-trigger-defensive". Operator-runnable at any point
  before or during Set 045 S4.

### Per-turn skip is a separate finding, already absorbed by v1.1

Per-turn marker skip on Claude is independent of phrasing-trigger
and is permanently out of the Set 044 v1.1 contract (proposal §4.3).
Set 045 S4 will author a session-start-only canonical template; no
per-turn-marker work.

---

## Q4. Where does the joiner live — Python (sibling to `ai_router`) or TypeScript (inside the extension)?

**Resolution:** **Python**, working module **`ai_router.joiner`**.

- **Full rationale + benchmark:**
  [`joiner-location-decision.md`](joiner-location-decision.md).
- **Both prototypes built and verified** —
  [`spike-prototypes/joiner_python_sketch.py`](spike-prototypes/joiner_python_sketch.py)
  and
  [`spike-prototypes/joiner_typescript_sketch.ts`](spike-prototypes/joiner_typescript_sketch.ts)
  detect the synthetic engine-mismatch conflict correctly and
  produce 0 conflicts on the control state.
- **Surprise empirical finding:** the idiomatic TypeScript port
  scans 461 native session logs in **2,589 ms** vs Python's
  **36 ms** (~70× slower). Fixable in TS with `readline` streaming,
  but the idiomatic-language perf delta is itself a signal.
- **Decisive criteria (Python wins):** reuse of existing `ai_router/`
  state-file + lifecycle infra, headless testability via pytest,
  cross-tier reusability (Lightweight tier via PyPI), perf on real
  workload, debuggability.
- **Decisive criteria (TypeScript wins):** in-process IPC to
  Explorer (~50–100 ms savings per refresh), in-process file
  watching via `vscode.FileSystemWatcher`.
- **Why Python wins net:** the Explorer's latency budget is
  bounded by operator perception of "live", which is ~1 second.
  Python's IPC overhead (≤100 ms per refresh) is well within that
  budget; the reuse + testability advantages dominate.
- **What would flip this decision:** Lightweight tier retirement,
  Explorer cadence dropping below 100 ms, or `ai_router` migrating
  to TypeScript. None on the visible roadmap.

Pass A in Set 044 favored Python 2-1; this benchmark + reuse
analysis confirms.

---

## Summary table

| # | Question                                | Status                                  | Carry-forward into |
|---|------------------------------------------|------------------------------------------|--------------------|
| Q1 | Bypass rate                             | Clock-started; observation log live      | S5 (Explorer integration) reads log + computes fraction |
| Q2 | Deterministic correlation               | Proven on real on-disk logs (Claude + Copilot) at 30 s window | S2 (joiner design) consumes window + cwd-canonicalization rules; S3 (wrapper) writes records the joiner can bind |
| Q3 | Claude phrasing-trigger boundary        | Hypothesis matrix + defensive template rules + optional ablation protocol | S4 (Claude parser + narration v1.1 template) authors the canonical CLAUDE.md per the four defensive rules; optional ablation runs upgrade the defensive posture |
| Q4 | Joiner location                          | Locked to Python (`ai_router.joiner`)    | S2 (joiner design + canonical schema) authors the Python module; S5 (Explorer integration) shells out to it |

All four questions are resolved sufficiently for S2–S6 to proceed
without further empirical work. Set 045's locked architectural
commitments from Set 044 proposal v1 §"Locked architectural
commitments" are unchanged.

## Carry-forward to Session 2

S2 starts from a position of:
1. Joiner location locked to Python.
2. Conflict-detection semantics seeded by the engine-mismatch
   sketch in the Python prototype (one of three conflict modes the
   proposal §4.4 enumerates; S2 designs the full set).
3. Canonical Harvest Record schema is derived FROM the joiner's
   semantic needs (per Set 044 Pass B consensus — schema is NOT
   pre-committed before joiner design).
4. Correlation join keys + window confirmed: `(workspace_cwd
   canonical, time_window=30s, conv_id post-bind)`.
5. The throwaway spike prototypes are kept under `spike-prototypes/`
   as a reference but are NOT promoted to the shipping `ai_router.joiner`
   surface — S2 designs the real module from a clean sheet,
   informed by the prototypes.

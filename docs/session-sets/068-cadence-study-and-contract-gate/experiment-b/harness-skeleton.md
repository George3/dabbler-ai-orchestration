# Experiment B — Harness Skeleton (Set 068 S2)

> The S2 deliverable is this skeleton + the pre-registered `cost_model.py`. S3
> implements the builders/runners/grader against these signatures, seeds the
> snapshots + defects, runs the **pilot** (pre-registration §10), then the
> K-repeat two-provider sweep, and writes `experiment-b-results.md` against
> `experiment-b-preregistration.md`. Mirrors the Experiment A harness shape
> (`../067-…/experiment-a/{build_trees,run_arms,grade}.py`).

## Directory layout (S3 creates)

```
experiment-b/
  cost_model.py          # SHIPPED S2 (pre-registered; do not edit in S3)
  harness-skeleton.md    # SHIPPED S2 (this file)
  catalogue.json         # S3: seeded defects (schema below), authored before runs
  build_snapshots.py     # S3: writes snapshots/<unit>/S<i>/ frozen trees + the diffs
  run_arms.py            # S3: drives R/Q/E (+P optional) per provider, K repeats
  grade.py               # S3: predicate match + symmetric audit -> earliest-catch
  snapshots/<unit>/S<i>/ # S3: the staged frozen trees (S(i) = S(i-1) + session i diff)
  raw/<unit>/<arm>_<prov>_S<i>_k<k>.json   # S3: every raw output, persisted FIRST (L-064-3)
  experiment-b-data.json # S3: graded metrics (earliest-catch, costs, contrasts)
```

## `catalogue.json` schema (per-defect fields — pre-committed taxonomy, §4)

```jsonc
{
  "severity_weights": { "Critical": 3, "Major": 2, "Minor": 1 },
  "units": {
    "<unit>": {
      "n_snapshots": 5,
      "snapshot_files": { "1": ["a.py"], "2": ["a.py","b.py"], ... },  // full tree at S(i)
      "session_diff_files": { "1": ["a.py"], "2": ["b.py"], ... },     // R's surface = S(i)\S(i-1)
      "Q_surface_files": ["e.py","b.py"]   // Q's end-of-set snippet (prereg §3a), pinned BEFORE runs
    }
  },
  "defects": [
    {
      "id": "BD1",
      "unit": "<unit>",
      "t0": 2,                        // introduction snapshot (1-based)
      "coupling_depth": 3,            // d = number of later snapshots that build on it
      "dependent_snapshots": [3,4,5], // the specific downstream dependents (|.| == d)
      "vis_at_intro": "in-snippet",   // in-snippet | cross-file  (recognizable from S(t0)\S(t0-1)?)
      "vis_at_close_for_Q": "cross-file", // in-snippet | cross-file (recognizable from Q_surface_files?)
      "class_label": "cadence-payoff",// cadence-payoff | coupling-blind | always-visible | no-coupling
      "severity": "Critical",
      "file": "b.py", "symbol": "build_index",
      "description": "<seeded mechanism>",
      "predicate": { "all": [ ["anchor tokens"], ["concept tokens"] ] }  // Exp A grading rule
    }
  ]
}
```

Invariants S3 must assert when seeding (and the grader re-checks), per prereg §4:
- `class_label == "no-coupling"`     ⇔ `coupling_depth == 0`.
- `class_label == "cadence-payoff"`  ⇔ `coupling_depth > 0 ∧ vis_at_intro=="in-snippet" ∧ vis_at_close_for_Q=="cross-file"`.
- `class_label == "coupling-blind"`  ⇔ `coupling_depth > 0 ∧ vis_at_intro=="cross-file"`.
- `class_label == "always-visible"`  ⇔ `coupling_depth > 0 ∧ vis_at_intro=="in-snippet" ∧ vis_at_close_for_Q=="in-snippet"`.
- `len(dependent_snapshots) == coupling_depth`, all `> t0`, all `<= n_snapshots`.
- **Minimum counts (prereg §4):** `≥3` cadence-payoff, `≥2` each control class —
  else expand snapshots before spending.
- `vis_at_intro` is checked against `session_diff_files[t0]`; `vis_at_close_for_Q`
  against `Q_surface_files` — both committed before any arm runs.
- Each defect has a deterministic falsifier attempt recorded (feeds the S5 gate);
  the snapshots are correct-by-construction except for the seeds.

## Arm-runner interface (`run_arms.py`)

```python
# Arm R  (per-session routed):   for i in 1..n: route(task="code-review", context=session_diff(S_i))
# Arm Q  (end-of-set routed):    route(task="code-review", context=Q_surface_files)         once
#                                (Q_surface_files = prereg §3a; NOT the whole aggregate diff)
# Arm E  (end-of-set path-aware): pull_route(provider, sandbox=tree(S_n))                   once
# Arm P  (per-session path-aware, OPTIONAL): for i in 1..n: pull_route(provider, sandbox=tree(S_i))
#
# Every arm runs per provider in {gpt-5.4, gemini-2.5-pro}, K=3 repeats.
# Each run's raw output is written to raw/<unit>/<arm>_<prov>_S<i>_k<k>.json BEFORE any
# grading/printing (L-064-3). A path-aware run that stops on token-budget with no verdict
# is recorded as a FAILED arm, not silently dropped (L-067-1).
def run_arm(arm: str, provider: str, unit: str, k: int) -> list[dict]: ...
```

`session_diff(S_i)` = the files in `S(i)\S(i-1)` (the session-i change set a per-session
reviewer is handed); `tree(S_i)` = the full `S(i)` directory (the path-aware
sandbox). The `run_test` cage (`ai_router.run_test_sandbox`) provides the
disposable worktree when an arm needs to execute the snapshot's tests; review-only
arms read the frozen tree directly.

## Grader interface (`grade.py`)

```python
# PER REPEAT (prereg §6/§7 -- NOT union-over-K): c_k(arm, defect) = smallest
# snapshot in repeat k whose combined finding text matches the predicate AND
# (cross-file cells) survives the symmetric mechanism audit; n+1 if uncaught in k.
def first_catch_in_repeat(arm: str, provider: str, defect: Defect, k: int) -> int: ...

# Binding stability gate (prereg §7): realized iff c_k <= t0 + REALIZE_SLACK in
# >= ceil(2K/3) repeats.
def realized_early_catch(arm, provider, defect, K=3, REALIZE_SLACK=1) -> bool: ...

def grade() -> dict:  # writes experiment-b-data.json. Per arm/provider:
    # - per-repeat first-catch c_k per defect; realized-early-catch flags
    # - per-repeat class catch-timing gaps g_k and per-repeat class costs (cost_model)
    # - per-repeat contrast X_k; decision stat mean_k X_k, band = max_k-min_k (prereg §6);
    #   median reported as a sign-agreement robustness check (not a separate threshold)
    # - catch-rate@close, $/wall/probes, false-positive rate
    # - union-over-K + reliable-across-K as SECONDARY descriptive signals only
    # - the R-vs-Q / R-vs-E / Q-vs-E contrasts
    ...
```

The grader imports `cost_model` (unchanged) and reuses the Experiment A predicate
matcher + the symmetric cross-file audit rule (`experiment-a-regrade/`).

## Decision wiring

`grade()`'s output feeds the §8 decision rule directly, all on the **per-repeat
aggregated** metrics with the **binding stability gate**: (1) the realized-early-
catch majority on the cadence-payoff class; (2) the cadence-payoff-class
catch-timing gap `g_k` and rework saving `s_k` (R earlier/cheaper than Q/E,
`|mean_k| > band` per prereg §6, median agreeing in sign); (3) the no-coupling AND
always-visible null checks. S3
reports the verdict (holds / does not hold / unresolved); S4 consumes it for
keep/demote/retire.

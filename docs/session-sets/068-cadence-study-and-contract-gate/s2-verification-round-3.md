# Set 068 S2 -- Cross-provider verification ROUND 3 (gpt-5.4)

> Independent verifier: gpt-5.4 (openai). Re-check of the two residual
> Major findings (decisive-statistic/band spec; Q-surface contradiction).

Round 3 check, focused only on the two residual Majors from Round 2.

## Finding 2 residual: decisive statistic / band / median specification
**Status: FULLY RESOLVED.**

What was still wrong in R2 was:
1. median had become decision-binding without a defined threshold, and
2. the band rule mixed contrast-level quantities (`g_k`) with arm-level bands.

Those are now pinned cleanly.

### Concrete fixes
- In `experiment-b-preregistration.md` §6:
  - `"Every decisive quantity is a per-repeat contrast value X_k"`
  - `"band = max_k X_k − min_k X_k"`
  - `"The decision statistic is mean_k X_k"`
  - `"The median of X_k is reported alongside as a robustness check but is not itself a separate decision threshold"`
  - `"a mean/median sign disagreement is flagged as unresolved"`

  That fully removes the old undefined “median exceeds band” problem.

- Same section names the only two decisive contrast types explicitly:
  - `g_k` = class catch-timing gap
  - `s_k` = class rework-cost saving

  And both are already contrast-level quantities, so the band being the range of that same `X_k` resolves the prior arm-band mismatch.

- In `experiment-b-preregistration.md` §8, the decision rule now matches §6:
  - HOLDS clause 2 uses `|mean_k g_k| > band` and `mean_k s_k > band`
  - median is only required to `"agree in sign"`
  - DOES-NOT-HOLD clause 2 uses `"within the noise band (or mean/median sign disagreement)"`

- In `experiment-b/harness-skeleton.md`, under `grade()`:
  - `"per-repeat contrast X_k; decision stat mean_k X_k, band = max_k-min_k (prereg §6); median reported as a sign-agreement robustness check (not a separate threshold)"`

That closes the exact ambiguity I left open in R2. I do **not** see any remaining Major on band/statistic specification.

---

## Finding 3 residual: Q surface contradiction
**Status: FULLY RESOLVED.**

What was still wrong in R2 was that taxonomy/invariants used `Q_surface_files`, while the actual Q run still appeared to use `aggregate_diff(S_n)` in some places.

That contradiction is now gone.

### Concrete fixes
- In `experiment-b-preregistration.md` §3 arms table:
  - Arm Q is now `"route() over Q's end-of-set surface (Q_surface_files, §3a), once"`

- In §3a:
  - `"Q's end-of-set surface = ... Q_surface_files"`
  - `"Arm Q is run on precisely that bundle — never on the whole aggregate diff"`
  - `"vis_at_close_for_Q and the class invariants are checked against the same Q_surface_files, so classification and the actual Q run cannot drift"`

- In `experiment-b/harness-skeleton.md`:
  - schema includes `"Q_surface_files"`
  - invariants check `vis_at_close_for_Q` against `Q_surface_files`
  - runner comment now says:
    - `"Arm Q (end-of-set routed): route(task="code-review", context=Q_surface_files) once"`
    - `"(Q_surface_files = prereg §3a; NOT the whole aggregate diff)"`

So the classifier surface and the executed Q surface are now the same pinned object everywhere. That fully resolves the R2 Major.

---

## New inconsistency introduced by the edits
I do see **one new Minor wording issue**, but not a new Major.

### Minor: false “equivalently” claim in §8
In `experiment-b-preregistration.md` §8, DOES-NOT-HOLD clause 1 says:

- R does not realize the early window ... `"equivalently the R-vs-Q per-repeat gap is within band"`

Those are **not equivalent**.

Why not:
- the realized-early-catch gate is about whether `R` catches by `t0 + REALIZE_SLACK` in `>= 2/3` repeats, for a majority of cadence-payoff defects;
- an `R-vs-Q` gap being outside/inside band is a different contrast-level condition.

A defect can fail the early-window threshold yet still have a substantial positive `R-vs-Q` gap later. So this should not be called “equivalent.”

This is a **Minor** clarity issue because the operative rule itself is still explicit in §7/§8, and the harness wiring still points to the realized-early-catch majority. But I would delete or rephrase that “equivalently” sentence to avoid misimplementation.

## Bottom line
Both Round-2 residual **Majors are now fully resolved**. I do not see any remaining Critical/Major from those issues.

```json
{"verdict":"VERIFIED","issues":[{"severity":"Minor","location":"experiment-b-preregistration.md §8, DOES-NOT-HOLD clause 1","problem":"The text says failure of the realized-early-catch gate is 'equivalently' the R-vs-Q per-repeat gap being within band. Those are not logically equivalent: R can miss the t0+1 early-window threshold yet still beat Q by a material later gap. Recommend deleting 'equivalently' or reframing it as a separate corroborating condition, not an equivalence."}]}
```

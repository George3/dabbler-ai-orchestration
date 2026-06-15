# Set 068 S2 -- Cross-provider verification ROUND 2 (gpt-5.4)

> Independent verifier: gpt-5.4 (openai). Re-check of the 3 Round-1 findings
> (1 Minor + 2 Major) after remediation.

Round 2 review, focused on whether each R1 finding is now resolved.

## Finding 1 (R1 Minor): Exp A “conservative floor” overclaim
**Status: RESOLVED.**

This is fixed in both the prose and the data.

Concrete checks:

- `experiment-a-regrade.md` §3 no longer claims the automated GPT primary is a “conservative floor.”
- `experiment-a-regrade-data.json` now includes audited **replicate-level** quantities:
  - `per_arm.A1.replicate_mean_sym_audited = 0.6389`
  - `per_arm.A2.replicate_mean_sym_audited = 0.5833`
  - `per_arm.B1.replicate_mean_sym_audited = 0.9259`
  - `per_arm.B2.replicate_mean_sym_audited = 0.8611`
- The new audited replicate-mean contrasts in `contrasts.*.sym_audited_replicate_mean` are arithmetically correct:
  - GPT: `0.9259 - 0.6389 = 0.2870`, band `0.0555`
  - Gemini: `0.8611 - 0.5833 = 0.2778`, band `0.0556`

So the prior unsupported lower-bound wording is gone, and the replacement claim is now backed by the delivered audited replicate-level numbers.

---

## Finding 2 (R1 Major): Exp B primary not stability-binding; band formula imprecise
**Status: PARTIALLY RESOLVED, but NOT fully resolved.**

### What is resolved
You did fix the main structural problems I raised:

- `experiment-b-preregistration.md` §7 makes the primary empirical quantity **per-repeat** first catch `c_k(arm, defect)`, with union-over-K demoted to secondary/descriptive.
- §7 adds a **binding** stability gate: realized-early-catch requires `c_k <= t0 + 1` in `>= ceil(2K/3) = 2` repeats.
- §6 pins a repeat-level band construction instead of leaving it hand-wavy.

Those are substantive improvements.

### What is still not pinned enough
There is still a material specification gap in the decisive statistics:

1. **§6 defines resolution only for the mean, but §8 makes both mean and median decision-binding.**
   - §6: “A contrast's **mean gap** is `mean_k` of the per-repeat gaps; it is resolved only if `|mean_k| > band`.”
   - §8: the HOLDS clause requires the catch-timing gap and rework-cost saving, “**mean and median across K**,” to be earlier/cheaper and to “**exceed the noise band**.”

   The median is now part of the decision rule, but there is **no exact median-band rule** specified.

2. **For catch-timing gaps, the band definition is internally inconsistent.**
   - §6 defines `g_k` as a **contrast-level** quantity:
     `g_k = mean_{defects in class}[ c_k(comparator) − c_k(R) ]`
   - In the same section, it also says for a contrast, `band = max(band_armB, band_armA)`.

   That max-of-arm-bands rule fits **arm-level** metrics like `cost_k(arm)`, but not a contrast-level `g_k` already defined directly on the contrast. For timing gaps, it is unclear whether the operative band is:
   - the range of the `g_k` values, or
   - a max of arm-level timing bands computed some other way.

That remaining ambiguity is analytic discretion in the decision rule, so I cannot clear the R1 Major yet.

---

## Finding 3 (R1 Major): migration mechanism not operationalized; Q could still see the defect
**Status: PARTIALLY RESOLVED, but NOT fully resolved.**

### What is resolved
You did add the missing machinery:

- `experiment-b-preregistration.md` §3a pins routed surfaces conceptually.
- §4 adds `vis_at_close_for_Q`.
- `experiment-b/harness-skeleton.md` adds `Q_surface_files`.
- The new “always-visible” control and minimum-count assertions are good additions.

That addresses the conceptual hole I flagged.

### What still fails
The actual **Q surface** is still specified inconsistently across the updated deliverables:

1. **`experiment-b-preregistration.md` §3 table** defines Q as:
   - “`route()` over `S(n)`'s **aggregate diff**, once”

2. **`experiment-b-preregistration.md` §3a** defines Q differently:
   - Q sees the **final session diff plus headline changed file(s)** by the Experiment A snippet rule,
   - explicitly **omitting earlier-session files not re-touched late**

3. **`experiment-b/harness-skeleton.md` run interface** reverts to the broader definition:
   - “Arm Q: `route(task="code-review", context=aggregate_diff(S_n))` once”

4. Meanwhile the taxonomy and invariants are checked against **`Q_surface_files`**:
   - `catalogue.json` schema includes `Q_surface_files`
   - invariants say `vis_at_close_for_Q` is checked against `Q_surface_files`

So the classification logic assumes one Q surface, while the runner spec still says Q may be run on a different, broader one. That means the same seed could be labeled `cross-file@close` relative to `Q_surface_files` but still be visible to the actual Q run if Q gets `aggregate_diff(S_n)`.

That is exactly the kind of implementation-dependent slippage that made the original defect material.

---

## New defect introduced by the changes
Yes: the **mean+median decision wording** in `experiment-b-preregistration.md` §8 introduces a new ambiguity beyond the original text, because median is now made verdict-binding without a pinned band rule for median. That is not just the old imprecision surviving; it is a new mismatch created by the revised decision rule.

---

```json
{"verdict":"ISSUES_FOUND","issues":[{"severity":"Major","claim":"experiment-b-preregistration.md §§6-8: Experiment B's decisive timing/cost statistics and noise-band test are fully pre-pinned","problem":"The update correctly moves the primary to per-repeat first-catch and adds a binding >=2/3 stability gate, but the decision rule is still not fully specified. §6 defines resolution only for the mean contrast ('|mean_k| > band'), while §8 requires both mean and median across K to 'exceed the noise band' without defining the exact median-band computation. Also, catch-timing gap g_k is defined as a contrast-level quantity, yet §6 also states 'contrast band = max(band_armB, band_armA)', which fits arm-level metrics like cost but not a direct contrast-level g_k. This leaves analytic discretion in the decisive rule.","fix":"Make one exact decision statistic authoritative, or explicitly define both. For timing gaps, either (a) decide only on mean_k with band = max(g_k)-min(g_k), keeping median descriptive, or (b) add an explicit median decision rule and its band. Separately define the band rule for contrast-level timing gaps versus arm-level cost contrasts."},{"severity":"Major","claim":"experiment-b-preregistration.md §3/§3a and experiment-b/harness-skeleton.md: Q's end-of-set routed surface is operationally pinned before runs","problem":"The update adds vis_at_close_for_Q and Q_surface_files, but the actual Q surface remains contradictory. Prereg §3/table and the harness runner specify Q as route() over aggregate_diff(S_n), while §3a and the catalogue schema define Q via a narrower snippet surface (final-session diff + headline changed files, omitting earlier untouched files). Because vis_at_close_for_Q and class-label invariants are checked against Q_surface_files, but the runner may feed aggregate_diff(S_n), cadence-payoff vs always-visible classification and the R-vs-Q interpretation remain implementation-dependent.","fix":"Choose one Q surface definition and use it everywhere. If Q is the snippet-bounded control, replace aggregate_diff(S_n) in §3/table and the runner skeleton with the explicit Q_surface_files bundle. If aggregate_diff(S_n) is intended, then redefine vis_at_close_for_Q and the class invariants against that actual aggregate-diff surface."}]}
```

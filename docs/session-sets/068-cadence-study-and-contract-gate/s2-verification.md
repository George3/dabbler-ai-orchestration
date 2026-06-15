# Set 068 S2 -- Cross-provider verification (gpt-5.4)

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Round 1. Target: the symmetric re-grade inference + the
> Experiment B pre-registration/design (no production code this session).

I verified the re-grade much more than the design.

## A. Symmetric-audit soundness

### A1. `B1:D12` rejection / `B2:D12` keep
This part checks out.

- In `experiment-a-regrade/pathaware-crossfile-evidence.md`, **B1:D12** is triggered only by the **D9** finding text:
  - B1 k1/k2/k3 all say `all_refs` returns only assignment refs and that refs from `collect_call_refs` / `collect_return_refs` are “silently dropped”.
  - None of B1 k1/k2/k3 names the actual D12 mechanism: **`collect_call_refs` only accepting a single bare identifier via `isidentifier()`**.
- So the rationale in `audit-symmetric.json` reject note is correct: this is cross-finding token spillover, not a real D12 mechanism catch.
- Conversely, **B2:D12** is properly kept:
  - `pathaware-crossfile-evidence.md`, D12 / B2 k2 explicitly says:
    > `collect_call_refs` ... only parse[s] function calls with a single argument that is a simple identifier ... because it checks if the entire substring ... `isidentifier()`.
  - That is the seeded mechanism.

So on the core disputed cell, the symmetric re-grade is sound.

### A2. Sampled keeps
I spot-checked the requested cells.

- **D5** (`B1:D5`, `B2:D5`): both arms explicitly name the duplicate `"minus"` operator name collision and `REGISTRY = {op.name: op ...}` overwrite/drop mechanism. Defensible keep.
- **D9** (`B1:D9`, `B2:D9`): both explicitly name `analyzer.all_refs` returning only `collect_assignment_refs(...)` and omitting `collect_call_refs` / `collect_return_refs`. Defensible keep.
- **D10** (`B1:D10`, `B2:D10`): both explicitly name `build_index` doing `name = str(ref)` on dict-shaped refs instead of using `ref['name']`. Defensible keep.
- **D6**, especially **`B2:D6`**:
  - `B2` k1 is not the real D6 mechanism.
  - But `B2` k3 includes:
    > `precedence(symbol)` ... implementation uses the parameter to look up ... `PRECEDENCE` ... keyed by operator names, not symbols
  - That *does* name the seeded key-drift mechanism. Since the grading being discussed is **union-over-K**, keeping `B2:D6` on that basis is consistent, not gratuitous.

### A3. Symmetry with the routed standard
The standard appears applied symmetrically in the sampled cells.

- `../067-.../experiment-a/audit.json` kept **`A1:D6`** because A1 named the name-vs-symbol drift; rejected **`A2:D6`** because A2 only said “unknown symbols default to 0”.
- The re-grade keeps **`B2:D6`** only because one replicate names the name-vs-symbol drift, which matches the routed standard.
- Same pattern for:
  - **D10**: routed `A1:D10` kept only because it explicitly named `name = str(ref)`; path-aware keeps do the same.
  - **D9**: routed D9s rejected for docstring “subset/superset” nitpicks; path-aware D9s kept because they name `all_refs` omitting call/return refs.
  - **D13**: routed D13s rejected for generic schema/validation talk; path-aware D13s kept because they explicitly name `data.get("version", 1)` against a required/no-default schema field.

I did not find a sampled path-aware keep that should have been rejected under the routed quoted-mechanism rule.

---

## B. Re-grade inference

### B1. Primary-vs-union reading
The arithmetic in `experiment-a-regrade.md` matches `experiment-a-regrade-data.json` exactly.

From Deliverable 3:

- **GPT** `B1−A1` primary:
  - `0.9815 - 0.7500 = 0.2315`
  - band `max(0.0556, 0.0834) = 0.0834`
  - so **EXCEEDS**
- **Gemini** `B2−A2` primary:
  - `0.8611 - 0.7778 = 0.0833`
  - band `max(0.0556, 0.1111) = 0.1111`
  - so **INSIDE**

And yes, calling the union the “audit-dependent secondary” view is correct for the audited union regimes in the re-grade.

### B3. D5 vs D9 erratum correction
This correction is right.

`experiment-a-regrade-data.json` → `existence_proofs` shows:

- **D5**:
  - `pathaware_B1_all_k = true`
  - `pathaware_B2_all_k = true`
  - `routed_A1_any_k = false`
  - `routed_A2_any_k = false`
- **D9**:
  - both routed `*_any_k = true`

Given the routed audit notes in Deliverable 7 say those D9 routed matches were wrong-mechanism false positives, the re-grade is correct to say:

- **D5** = fully audit-independent existence proof
- **D9** = audit-conditional existence proof

That tightens, not overturns, the erratum.

### B4. H2 split
This is also fair.

- Deliverable 3 `H2.automated` shows `A1_auto` and `A2_auto` are identical sets, with `second_routed_provider_adds = 0.0`.
- So “a second routed provider adds nothing” is indeed audit-independent.
- The `+0.3056` context-vs-routed-pair magnitude comes from `H2.sym_union`, so downgrading that magnitude to exploratory is the honest move.

---

## C. Experiment B design validity

The overall cadence idea is coherent, but I found **two material pre-registration defects**.

### C1/C2. Cadence mechanism is plausible, but not fully operationalized
The narrative in `experiment-b-preregistration.md` §§1–4 says the key mechanism is:

- defect is **in-snippet at introduction**
- later becomes **cross-file by set close**
- therefore R has a unique early window that Q loses

But the actual schema in `experiment-b/harness-skeleton.md` only pre-registers:

- `t0`
- `coupling_depth`
- `dependent_snapshots`
- `vis_at_intro`

It does **not** pre-register any `vis_at_close` / “requires omitted file at close” property.

That matters because **Q** is defined as routed over the **aggregate diff of `S(n)`**. If the final aggregate diff still contains all relevant changed files, then a supposed “cadence-payoff” defect may remain diagnosable to Q. In that case, a null R-vs-Q result would not cleanly falsify the cadence defense; it could just mean the seeded defect never actually migrated out of Q’s snippet surface.

So the mechanism is plausible, but the current pre-registration does not pin it down tightly enough.

### C3/C4. Primary timing metric is too optimistic / not fully pinned
The larger design problem is in `experiment-b-preregistration.md` §7 and `experiment-b/harness-skeleton.md`:

- primary empirical metric = **earliest catch snapshot per defect**
- but defined as **union over K**
- and the grader interface similarly defines `earliest_catch(...)` as a union-over-K quantity

This is not a good primary for nondeterministic runs.

A one-off lucky early catch in 1/3 repeats can set `c = t0` for an arm even if the arm is usually late or misses. The prereg says “reliable-across-K” is reported as a stability signal, but **that stability is not made binding in the §8 decision rule**.

Relatedly, §6’s noise-band description is not precise enough for these new timing/cost outcomes:
> max−min over the K runs, averaged across the relevant snapshots

That was fine in Experiment A’s scalar catch-rate setting, but here the decisive quantities are:

- per-defect first-catch times
- class-level timing gaps
- class-level total costs

The exact repeat-level summary and exact band computation are not fully specified, leaving analytic discretion for S3.

### C4. Cost model itself
`experiment-b/cost_model.py` is otherwise honest as code:

- deterministic
- empirical input restricted to `caught_at`
- invariants claimed in the prereg do hold in the code:
  - `d=0` timing-invariant
  - `d>0` monotone non-decreasing
  - never-caught > caught-at-end

I do **not** see post-hoc tunability in the shipped function itself.

---

## D. Internal consistency

I found no arithmetic mismatches between `experiment-a-regrade.md` and `experiment-a-regrade-data.json`.

Numbers I checked:

- per-arm replicate means and bands
- all six contrast table entries
- `2/8` and `13/14` strict-survival counts
- D5/D9 existence-proof booleans
- H2 `+0.0000` and `+0.3056`

Those all line up.

---

## One inference overreach in Deliverable 1

The main re-grade is solid, but there is one overclaim:

### “Automated primary is a conservative floor for GPT”
`experiment-a-regrade.md` §3 says the primary `+0.2315` GPT gap is a **conservative floor** because A1 still gets mechanism-wrong cross-file credit (`D9`, `D13`).

That is not established from the delivered evidence, because **B1 primary is also inflated** by a mechanism-wrong cross-file credit:

- `audit-symmetric.json` rejects **`B1:D12`**
- `pathaware-crossfile-evidence.md` shows B1’s D12 predicate fires in **k1/k2/k3**

So the no-audit primary inflates **both** arms. The delivered materials do not include audited **replicate-level** means, only audited union-level outcomes. Since union-level and replicate-mean are different metrics, the fact that GPT sym-union gap is `+0.25` does **not** prove the audited replicate-mean gap must be `>= +0.2315`.

The directional GPT result still stands; this issue is about the “floor” wording.

---

```json
{"verdict":"ISSUES_FOUND","issues":[{"severity":"Minor","claim":"experiment-a-regrade.md §3 / §5: the GPT automated-primary gap (+0.2315) is a 'conservative floor' and the true mechanism-standard gap is >= +0.23","problem":"The delivered evidence shows the no-audit primary inflates both sides, not just A1. `audit-symmetric.json` rejects `B1:D12`, and `pathaware-crossfile-evidence.md` shows that false-positive D12 match occurs in B1 k1/k2/k3. Without audited replicate-level means, it does not follow that the mechanism-audited replicate-mean GPT gap must be at least +0.2315; union-level `+0.25` is a different metric.","fix":"Either compute and report the symmetric-audit replicate means for A1 and B1, or soften the text to say the primary GPT result remains positive/exceeds band but is not proved to be a lower bound on the mechanism-audited replicate-mean gap."},{"severity":"Major","claim":"experiment-b-preregistration.md §§7-8 and experiment-b/harness-skeleton.md: Experiment B's primary timing/cost outcome is pre-committed and falsifiable","problem":"The prereg makes `earliest-catch` a union-over-K quantity. That lets a one-off lucky early repeat set `c=t0`, while 'reliable-across-K' is only reported, not made binding in the decision rule. In the same sections, the noise-band computation for the new timing/cost outcomes is not fully specified, leaving analytic discretion in S3.","fix":"Pre-register repeat-level primary summaries (e.g. per-repeat first-catch time and per-repeat total cost, then compare means/medians across K), specify the exact noise-band formula for each decisive metric, and make stability binding (e.g. require >=2/3 repeats to realize the early catch or treat union-over-K earliest catch as secondary only)."},{"severity":"Major","claim":"experiment-b-preregistration.md §§1-4 / harness-skeleton.md: the 'cadence-payoff' class operationalizes the claimed in-snippet@intro -> cross-file@close migration mechanism","problem":"The narrative hypothesis requires defects that are local in the introducing diff but become non-local to end-of-set routed review. But the committed schema only records `vis_at_intro` and `coupling_depth`; it does not require that a cadence-payoff defect be cross-file relative to Q's final routed surface. Since Q is defined as routed over `aggregate_diff(S_n)`, the final diff may still contain all relevant changed files, so a null R-vs-Q result could reflect seed construction rather than falsifying cadence.","fix":"Add a pre-registered field/invariant such as `vis_at_close_for_Q` or `requires_omitted_file_at_close`, require `cadence-payoff` defects to be `in-snippet@intro` and `cross-file@close` relative to Q, and set a minimum count for that class before running S3."}]}
```

# Set 068 S3 -- Cross-provider verification (gpt-5.4)

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Round 1. Target: the Experiment B run + cadence verdict
> against the fixed S2 pre-registration (harness faithfulness, grader
> correctness, inference honesty). No production code / no release this session.

Overall: **the S3 run is mostly faithful to the fixed prereg, and the top-line verdict “DOES NOT HOLD via B3” is mechanically supported.** I do **not** see a wrong branch read-off, a union-over-K mistake, or evidence that the session rewrote the yardstick after seeing data.

The main problems I found are:
1. one **substantive overstatement** in the results narrative about arm **E**’s capability, and
2. a couple of **grader-faithfulness gaps** that do not flip this session’s verdict but are real deviations from the prereg/claims.

## A. Harness faithfulness

### A1. Taxonomy / snapshot construction / pinned surfaces
This part is faithful.

- `build_snapshots.py` builds exactly the monotone 5-snapshot chain required:
  - S1 `quantity.py`
  - S2 adds `registry.py`
  - S3 adds `convert.py`
  - S4 adds `aggregate.py`
  - S5 adds `api.py`, `report.py`
- `catalogue.json` matches that layout:
  - `snapshot_files`
  - `session_diff_files`
  - `Q_surface_files = ["aggregate.py", "api.py", "report.py"]`

That `Q_surface_files` choice matches prereg §3a: **final diff** (`api.py`, `report.py`) plus the **headline compute file** (`aggregate.py`), with earlier files omitted.

Class counts also satisfy the prereg minima in `catalogue.json`:
- cadence-payoff: 5
- coupling-blind: 2
- always-visible: 2
- no-coupling: 3

The shipped defects satisfy the intended structural labels:
- cadence-payoff: BD1–BD5 all have `d>0`, `vis_at_intro=in-snippet`, `vis_at_close_for_Q=cross-file`
- coupling-blind: BD6–BD7 have `d>0`, `vis_at_intro=cross-file`, `vis_at_close_for_Q=cross-file`
- always-visible: BD8–BD9 have `d>0`, intro+close both in-snippet
- no-coupling: BD10–BD12 have `d=0`

### A2. Are BD6 / BD7 genuinely cross-file at intro?
**Yes, in the shipped source the earlier docstring leak appears fixed.**

- BD6 (`aggregate.py`):
  - `catalogue.json` says the decisive contract is in `convert.py`: “returns None for unknown units and callers MUST drop None.”
  - In `build_snapshots.py`, `AGGREGATE_PY` does **not** restate that contract; it only says:
    - `"(Aggregation forwards each (value, unit) to convert(); see convert.py for its return contract.)"`
  - That points upstream without leaking the actual `None` rule.

- BD7 (`convert.py`):
  - `catalogue.json` says the decisive contract is in `registry.py`: aliases are valid inputs.
  - In `build_snapshots.py`, `CONVERT_PY` says only:
    - “converts between registered units”
  - It does **not** reveal the alias set or promise alias acceptance locally.

So the shipped builder does match the claimed pilot fix.

### A3. Are cadence-payoff defects genuinely in-snippet@intro and Q-omitted at close?
**Yes.**

Examples:
- BD1/BD2: `quantity.py` docstring says `mm=0.001`, `km=1000.0`; code sets `"mm": 0.01`, `"km": 100.0`.
- BD4/BD5: `convert.py` docstring says multiply-to-base then divide-to-target and “never rounds”; code does inverse math and `return round(result)`.

And all cadence-payoff files (`quantity.py`, `registry.py`, `convert.py`) are omitted from `Q_surface_files`.

## B. Grader correctness

### B1. Per-repeat catch timing vs union-over-K
**Correct.**

`grade.py` uses:
- `first_catch_in_repeat(arm, provider, defect, k)`
- then computes contrasts per `k` in `_contrast_for_class(...)`

So the decisive `c_k`, `g_k`, `s_k` are indeed **per-repeat**, not unioned across K. This is faithful to prereg §6–§8.

### B2. File-in-surface gating
**Mostly faithful in effect for this session, but not literally implemented as claimed.**

What the file says:
- `grade.py` docstring claims:
  - “An arm can only catch a defect whose **EVIDENCE FILE** is in that arm’s surface ...”

What `_in_surface(...)` actually does:
- it checks only `defect["file"]`.

That is fine for purely local defects, but it is **not literally the same as “evidence file”** for the coupling-blind cases.

Concrete example:
- BD6’s `catalogue.json` description says the decisive contract lives in **`convert.py`**
- but BD6’s `file` is **`aggregate.py`**
- `_in_surface("R", BD6, 4)` therefore returns true because `aggregate.py` is in the S4 diff, even though the decisive upstream contract file is omitted.

In **this dataset**, that did not alter the verdict:
- `experiment-b-data.json` shows R and Q both miss BD6 and BD7 in all repeats
- `audit.json` has `removals: []`
- so there was no spurious credited catch to strip

But the implementation is looser than the grading rule it describes.

### B3. Band rule / realized-early / cost model mapping
Mostly correct.

- `MAJORITY = ceil(2K/3) = 2` for `K=3` is implemented correctly.
- `realized_early_catch(...)` uses `c_k <= t0 + REALIZE_SLACK`.
- Costs map `n+1` to `None` before calling `cost_model.arm_cost(...)`.

One real caveat:
- prereg §6 says mean/median sign disagreement should be **unresolved**
- but `grade.py::_band_stats` sets
  - `resolved = abs(mean) > band`
  - and only reports `mean_median_sign_agree` separately

So the sign-agreement rule is **not enforced in the boolean `resolved` field**. No decisive cell flips here, but it is a real prereg-faithfulness gap.

### B4. Symmetric audit
Within the material provided, the symmetric structure is there:
- `audit.json` removal key shape is symmetric
- `grade.py` applies it to all arms via `AUDIT_REMOVE`

I cannot fully re-audit the “no removals” claim from the supplied excerpt alone because the raw per-run JSONs are not included here, but nothing in `experiment-b-data.json` contradicts the stated nulls/catches.

## C. Verdict inference

### C1. A1 and A2 support
**Supported.**

From `experiment-b-data.json`:
- `decision_contrasts.openai.R_realizes_cadence_payoff_early_window.n_realized = 5`
- `decision_contrasts.google.R_realizes_cadence_payoff_early_window.n_realized = 5`

Cadence-payoff contrasts:
- R vs Q:
  - both providers `g = 4.0`, `s = 66.0`, resolved
- R vs E:
  - openai `g = 3.0`, `s = 27.0`, resolved
  - google `g = 3.0667`, `s = 30.0`, resolved

So A1 and A2 are genuinely supported.

### C2. A3 fails and B3 fires
**Supported.**

R vs Q controls:
- no-coupling:
  - openai `s = 1.0`, resolved
  - google `s = 1.0`, resolved
- always-visible:
  - both `s = 3.0`, resolved

That is enough to fail A3 and trigger B3.

### C3. BD12 / the no-coupling control: legitimate confound or seed-design error?
**Both readings are defensible; bottom line: it is a caveat, but not a verdict-flipper.**

Why the results doc’s attribution is correct:
- `experiment-b-data.json` shows the no-coupling R-vs-Q saving is exactly 1.0 in both providers.
- BD10 and BD11 are caught equally by R and Q.
- BD12 is caught by R at 1 and missed by Q (`6,6,6`), so it alone drives the class residual.
- That means the doc is correct that the residual is a **surface-coverage artifact**, not a coupling-growth/timing effect.

Why a skeptic can still object:
- prereg §4 verbally frames no-coupling as a “built-in null”
- choosing a **Q-invisible** d=0 defect means this control is not null for **catch-vs-escape surface effects**
- so the no-coupling half of A3 was made easier to fail than a fully Q-visible null would have been

Why this does **not** overturn the session verdict:
- the **always-visible** control is independently positive (`s=3.0` both providers)
- so even if you discounted BD12 as an unfortunate seed choice, A3 still fails and B3 still fires

So I would treat BD12 as a **real design caveat**, but **not** as evidence the S3 verdict was mis-read.

### C4. B3 gloss vs B1 gloss
**The document reads this correctly.**

- B1 is false because R **does** realize the early window (5/5 both providers).
- B3 is true because control residuals are present.
- So the operative gloss is indeed:
  - **not** “no cadence value”
  - but rather “the measured R-vs-Q saving is not cleanly attributable to Q-invisible cadence alone”

That is faithful to prereg §8.

### C5. R-vs-E residual value and E capability claim
The first half is right:
- the cadence-payoff R-vs-E saving is real and resolved
- that is R’s one clearly supported **cadence-specific** residual value

But the doc **overstates E** in a key way:

- `experiment-b-results.md` §2 table says:
  - `E gemini | 11/12 | (1 minor)`
- but `experiment-b-data.json -> arms -> E_google -> per_defect -> BD6`
  shows the miss is **BD6**
- and `catalogue.json` labels BD6 severity **Critical**, not Minor

Also:
- results §2 says E “catches everything, including the two coupling-blind defects R structurally misses”
- results §5 says E “catches the two coupling-blind defects R misses”
- but `E_google` does **not** catch BD6 (`caught_at_close_majority: false`), only BD7

So the direction “E > R at close” is still true:
- E_openai = 12/12
- E_google = 11/12
- R both providers = 10/12

And the coupling-blind class still favors E overall:
- openai `s = -12`
- google `s = -6`

But the narrative should be weakened to:
- **OpenAI-E catches both coupling-blind misses**
- **Google-E catches one of the two**
- E still outperforms R overall, but not as absolutely as claimed

## D. run_test live use
`run_arms.py::run_pull` clearly wires `RunTestConfig` for arm E only, so the harness supports the claim.

But in the materials provided here, the results doc’s factual claim of an actual live invocation:
- “a turn-8 `run_test` call, `raw=true`, `error=false`, green suite”

is **not independently checkable**, because no raw `raw/numkit/E_*_S5_k*.json` trace is included/cited in the supplied evidence packet. So the claim may well be true, but it is not substantiated **here** with a precise raw-file/turn citation.

## E. Internal consistency / stats honesty
Aside from the E/Gemini overstatement, the numbers I checked do line up with `experiment-b-data.json`:
- R/Q/E close-coverage counts
- class contrasts
- costs
- B3 branch read-off

The small-n caveat is adequate and honestly stated.

## Bottom line
- **Execution faithfulness:** mostly good
- **Grader correctness:** mostly good, with two minor faithfulness gaps
- **Verdict correctness:** **yes**, the B3 read-off is supported
- **Inference honesty:** mostly good, but the doc **overstates E** in a way that matters for the keep-vs-replace discussion

```json
{"verdict":"ISSUES_FOUND","issues":[{"severity":"Major","claim":"experiment-b-results.md overstates arm E's capability, especially for Gemini","problem":"Results §2 says 'E gemini | 11/12 | (1 minor)', but experiment-b-data.json shows E_google's only majority miss is BD6, and catalogue.json labels BD6 as Critical. The same section and §5 also say E catches 'the two coupling-blind defects R misses', which is false for Google: arms.E_google.per_defect.BD6 has caught_at_close_majority=false, so Google-E catches only BD7 of the two.","fix":"Correct the table row to identify the missed defect/severity accurately, and qualify the capability claim provider-specifically: E_openai catches both coupling-blind defects; E_google catches one of two, while still beating R overall (11/12 vs 10/12 and coupling-blind s=-6)."},{"severity":"Minor","claim":"grade.py claims to gate catches on the defect's 'evidence file' being in-surface","problem":"grade.py::_in_surface checks only defect['file'], not the actual upstream evidence file(s). For BD6, catalogue.json says the decisive contract lives in convert.py, but _in_surface gates on aggregate.py. That means the structural cross-file restriction is looser than advertised and depends on predicate/audit discipline rather than the surface gate alone.","fix":"Extend the catalogue with explicit evidence_files (or required_files) per defect and make _in_surface require those files, or state plainly that the gate is on the defect file only and cross-file strictness is enforced by audit."},{"severity":"Minor","claim":"grade.py does not fully implement the prereg mean/median sign-disagreement rule","problem":"Prereg §6/§8 says a mean/median sign disagreement should be treated as unresolved. In grade.py::_band_stats, resolved is computed solely as abs(mean)>band; mean_median_sign_agree is reported separately but not folded into resolved. No decisive cell flips in this dataset, but the grader is not literally faithful to the prereg rule.","fix":"Set resolved = abs(mean)>band and sign_agree, or post-process any sign-disagreement cell to unresolved before writing experiment-b-data.json."},{"severity":"Minor","claim":"The live run_test-use claim is not directly substantiated in the supplied evidence packet","problem":"run_arms.py wires RunTestConfig for arm E, and experiment-b-results.md §1 claims an actual 'turn-8 run_test call, raw=true, error=false', but no raw E trace JSON or precise raw-file/turn citation is included in the materials above, so the claim cannot be independently verified from the supplied evidence alone.","fix":"Add an explicit citation to the raw trace file and turn index (or embed the trace excerpt) in experiment-b-results.md and/or audit.json."}]}
```

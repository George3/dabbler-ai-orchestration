# Experiment B — Results (the cadence study, Set 068 S3)

> **Status:** RUN + GRADED + cross-provider verified. Graded against the FIXED
> `experiment-b-preregistration.md` (S2) — the verdict below is read off the
> pre-committed decision rule (§8), not chosen after seeing the numbers.
> **Created:** 2026-06-15 (Session 3).
> **Harness:** `experiment-b/{build_snapshots,run_arms,grade,cost_model}.py`,
> `catalogue.json`, `audit.json`; raw outputs under `experiment-b/raw/numkit/`;
> graded metrics in `experiment-b/experiment-b-data.json`.
> **Metered spend:** ~$0.85 total (pilot ~$0.23 incl. a GPT path-aware
> convergence check; full K=3 two-provider sweep ~$0.47; graded-arm sum $0.6173).

---

## 0. TL;DR — the cadence verdict

**The cadence MECHANISM is empirically real and large, but the pre-registered
"cadence defense holds" verdict is NOT obtained: clause A3 (clean controls)
fails and clause B3 fires.** Per-session routed (**R**) realizes the early
window on **5/5** cadence-payoff defects in **both** providers and saves resolved
rework over both end-of-set routed (**Q**) and end-of-set path-aware (**E**) on
that class — so R *does* catch the migrating coupling defects at introduction.
**But** R's advantage over Q is **confounded**: the no-coupling control shows a
small resolved R saving (a pure **surface-coverage** artifact — R is handed every
file's diff across the build, Q sees only the end-of-set snippet), and the
always-visible control shows a small resolved R saving (pure **earliness**).

Per the pre-registered rule this maps to the **DOES-NOT-HOLD branch, via clause
B3** — "the saving is a surface artifact or pure earliness, **not Q-invisible
cadence**." The B3 gloss is the operative one; B1's "no cadence value" gloss does
**not** apply (B1 is false — the cadence mechanism is present). The honest
one-line reading for S4: **R's edge over end-of-set is real but narrow and is
largely the same context-access effect Experiment A already attributed — which
end-of-set path-aware (E) largely provides (E gpt 12/12; E gemini 11/12, missing
one Critical) while also outscoring R on total capability.**

---

## 1. What was built and run

A single multi-session unit (**numkit**, a tiny numeric-length toolkit) was built
as **5 monotone snapshots** S1→S5 (each source file introduced once and frozen;
later files genuinely import earlier ones, so a defect in an early file is
depended on by later snapshots). **12 defects** were seeded across the four
pre-registered taxonomy classes (invariants asserted before any spend):

| Class | Count | Defects |
|---|---|---|
| cadence-payoff (`d>0`, in-snippet@intro, cross-file@close) | 5 | BD1 BD2 (quantity factors), BD3 (registry alias→alias), BD4 BD5 (convert inverted / rounds) |
| coupling-blind (`d>0`, cross-file@intro) | 2 | BD6 (aggregate mean drops no None), BD7 (convert local `_VALID` rejects registry aliases) |
| always-visible (`d>0`, in-snippet@intro **and** @close) | 2 | BD8 (sum init 1.0), BD9 (max returns min) |
| no-coupling (`d=0`) | 3 | BD10 (report `%.1f`), BD11 (api arg-swap), BD12 (quantity `describe` order) |

**Arms** (per prereg §3), run per provider (`gpt-5.4`, `gemini-2.5-pro`), **K=3**:

- **R** — per-session routed: `providers.call_model` over each session diff
  `S(i)\S(i-1)`, i=1..5 (the current Full-tier cadence).
- **Q** — end-of-set routed: `call_model` over the pinned `Q_surface_files`
  (`aggregate.py, api.py, report.py`) once (pure cadence control for R).
- **E** — end-of-set path-aware: `pull_route` over the whole final tree S5 **plus
  the S1 `run_test` cage** (the proposed replacement, Set 066).
- **P** (per-session path-aware) was **not run** — optional/pilot-gated in the
  prereg, not consumed by the decision rule (R-vs-Q / R-vs-E), and it carries the
  highest L-067-1 cost (n× path-aware loops). This omission is logged, not silent.

**`run_test` exercised live (run-test contract §6).** Every arm-E run was offered
the disposable-worktree cage (a temp one-commit git repo of S5, command
`python -m pytest -q`). E invoked `run_test` inside the metered loop — verified in
the persisted trace `experiment-b/raw/numkit/E_google_S5_k1.json`
(`trace.tool_calls` includes a `run_test` entry at `turn: 8`, `raw: true`,
`error: false`; the smoke suite is green) — the first end-to-end metered use of the
Set 068 S1 cage. The seeded bugs live in paths the smoke suite does not cover
(which is *why* they escape a test run), so a green `run_test` did not hand E the
answers.

**Pilot (prereg §10) caught a real seed defect before the paid sweep.** The
one-provider pilot confirmed all three seams *and* surfaced that the two
coupling-blind defects' own introducing files leaked the cross-file contract in
their docstrings (which would have made them in-snippet, contradicting their
pre-registered `coupling-blind` label). The implementation was corrected to match
the **fixed** taxonomy (the alias contract now lives only in `registry.py`; the
None-drop contract only in `convert.py`) and the affected cells were re-run before
the sweep — a fix of code to the fixed design, not of the design to the data.

---

## 2. Coverage at close (descriptive)

Defects caught by a majority of K repeats by set close, per arm (of 12):

| Arm | catch@close /12 | what it misses | mean probes | metered $ (K=3) |
|---|---|---|---|---|
| **E** gpt | **12/12** | — | 10.0 | 0.237 |
| **E** gemini | 11/12 | **BD6** (Critical coupling-blind: aggregate mean drops no None) | 8.3 | 0.147 |
| **R** gemini | 10/12 | BD6, BD7 (coupling-blind, cross-file@intro) | n/a | 0.043 (15 runs) |
| **R** gpt | 10/12 | BD6, BD7 | n/a | 0.140 (15 runs) |
| **Q** gemini | 4/12 | all 5 cadence-payoff + BD6/BD7 + BD12 (omitted files) | n/a | 0.012 |
| **Q** gpt | 4/12 | same | n/a | 0.039 |

Reading: **E** (path-aware) is the capability ceiling — **E gpt catches all 12,
including both coupling-blind defects R structurally misses; E gemini catches
11/12, missing the Critical coupling-blind BD6** (so path-aware is not a perfect
ceiling — one provider still missed a cross-file Critical). **R** catches 10/12,
including **all 5 cadence-payoff defects, at their introduction**, missing only the
2 coupling-blind (cross-file@intro). **Q** is crippled by the snippet surface
(4/12) — it sees only the 3 end-of-set files, so it misses every defect in an
omitted file regardless of coupling. The internal consistency check **Q vs E**
reproduces Experiment A's capability finding in the staged setting (path-aware ≫
end-of-set routed).

---

## 3. The decisive per-repeat contrasts (prereg §6–§8)

All quantities are per-repeat contrasts aggregated across K; **resolved** iff
`|mean_k| > band` where `band = max_k − min_k`; the median must merely agree in
sign. Positive = R earlier / R cheaper.

### 3a. Binding stability gate (clause A1)

**R realizes the cadence-payoff early window (caught at `c_k ≤ t0+1` in ≥2/3
repeats) on 5/5 cadence-payoff defects, in BOTH providers.** A1 is **satisfied**.
(Q and E run only at close, so their realized-early flag is 0/5 by construction —
the gate is R-specific.)

### 3b. Cadence-payoff class — R vs Q and R vs E

| Contrast | provider | catch-timing gap g (mean / band / resolved) | rework saving s (mean / band / resolved) |
|---|---|---|---|
| **R vs Q** | gpt | 4.0 / 0.0 / ✅ | 66.0 / 0 / ✅ |
| **R vs Q** | gemini | 4.0 / 0.0 / ✅ | 66.0 / 0 / ✅ |
| **R vs E** | gpt | 3.0 / 0.0 / ✅ | 27.0 / 0 / ✅ |
| **R vs E** | gemini | 3.07 / 0.2 / ✅ | 30.0 / 9 / ✅ |

R is **earlier and cheaper** than both comparators on the cadence-payoff class,
fully resolved. Against **Q**, R wins because Q never sees the defective (omitted)
files; against **E** — the capability-superior replacement — R still wins because
it catches the migrating coupling defects at `t0` whereas E catches them only at
close (`c=5`), paying the coupling-growth rework the cost model charges. **This
R-vs-E cadence-payoff saving is the single genuine residual value of per-session
routed over the path-aware replacement** (clause A2 satisfied, and the saving is
**concentrated** in the cadence-payoff class: 66 vs control residuals of 1–3).

### 3c. The controls — NOT null (this is what denies a clean HOLDS)

| Control contrast | provider | g (mean/band/res) | s (mean/band/res) | reading |
|---|---|---|---|---|
| **no-coupling** R vs Q | gpt | 1.67 / 0 / ✅ | **1.0 / 0 / ✅** | surface artifact (BD12 only) |
| **no-coupling** R vs Q | gemini | 1.67 / 0 / ✅ | **1.0 / 0 / ✅** | surface artifact (BD12 only) |
| **always-visible** R vs Q | both | 1.0 / 0 / ✅ | **3.0 / 0 / ✅** | pure earliness (R sees aggregate at S4, Q at S5) |
| **coupling-blind** R vs Q | both | 0.0 / 0 / ❌ | 0.0 / 0 / ❌ | R and Q both miss → no diff (expected) |
| **coupling-blind** R vs E | gpt / gemini | −1.0 / −0.5 | **−12 / −6** | E **beats** R (E's capability — the 2 defects R misses) |

The **no-coupling** R-vs-Q saving (s=1.0) is driven **entirely by BD12**, a
`d=0` defect that is *also* Q-invisible (`quantity.py` omitted from Q's surface):
Q never catches it and pays the escape penalty, so R "saves" 1 unit — a **pure
surface-coverage effect** (R is handed `quantity.py` in the S1 diff; Q is not),
with **zero** timing component (the other two no-coupling defects, BD10/BD11, are
Q-visible and contribute exactly 0). The **always-visible** R-vs-Q saving (s=3.0)
is the **structural 1-snapshot earliness**: R reviews `aggregate.py` at its S4
introduction, Q at S5, so R catches BD8/BD9 one snapshot sooner even though Q also
catches them.

---

## 4. Verdict against the pre-registered decision rule (§8)

| Clause | Required for | Result |
|---|---|---|
| **A1** R realizes early window on cadence-payoff (majority) | HOLDS | ✅ 5/5 both providers |
| **A2** cadence-payoff g R-earlier & `|mean|>band`; s>band over E and Q; concentrated | HOLDS | ✅ (g 3–4, s 27–66, resolved, concentrated) |
| **A3** no-coupling **AND** always-visible show **no** R advantage beyond band | HOLDS | ❌ **FAILS** (no-coupling s=1.0, always-visible s=3.0, both resolved) |
| **B1** R does **not** realize early window | DOES NOT HOLD | ❌ false |
| **B2** rework saving within band / mean-median sign disagreement | DOES NOT HOLD | ❌ false |
| **B3** an apparent R saving **also appears** in a control (surface artifact / pure earliness, not Q-invisible cadence) | DOES NOT HOLD | ✅ **TRUE** |

Clause **A3 fails** → not a clean HOLDS. Clause **B3 fires** → the pre-registered
verdict is **CADENCE DEFENSE DOES NOT HOLD (via B3)**.

**Faithful interpretation (the B3 gloss, NOT the B1 gloss).** The pre-registration
attaches "Experiment B finds no cadence value" to clause **B1** (R failing to
realize the early window). **B1 is false here** — that gloss does not apply and
must not be carried into S4. The operative gloss is **B3's**: *R's measured
advantage over end-of-set routed is real but is substantially a **surface-coverage
artifact** (R is handed every file's diff across the build; the end-of-set snippet
is not) plus **pure earliness**, so it cannot be cleanly attributed to
**Q-invisible cadence** alone.* The cadence mechanism is present and large; the
controls deny it a **clean** attribution.

---

## 5. Honesty notes & threats (prereg §9)

- **Small n.** One unit, 12 defects, K=3. Most bands are 0 because the catches are
  near-deterministic (a wrong factor / inverted maths is reliably flagged or
  reliably missed), so the effects are **reproducible** but rest on a **single
  staged unit** — the direction is robust; precise magnitudes are illustrative,
  not population estimates. The honesty rule (§6) binds: where a contrast is
  within band (coupling-blind R-vs-Q) it is reported unresolved, not over-read.
- **The controls behaved exactly as designed — and that is the finding.** The
  no-coupling and always-visible residuals are not noise to be explained away;
  they are the pre-registered instruments isolating that R's raw R-vs-Q advantage
  is part surface-coverage, part earliness. They did their job.
- **R's only win over the path-aware replacement (E) is the cadence-payoff
  rework-timing saving** (g≈3, s≈27–30). E otherwise dominates: **E gpt catches
  both coupling-blind defects R misses (12/12); E gemini catches one (BD7) but
  misses the Critical BD6 (11/12)** — so R-vs-E on the coupling-blind class is
  s = −12 (gpt) / −6 (gemini), i.e. E cheaper, more strongly for gpt. So R is
  **not** strictly dominated — it buys early-catch rework savings on migrating
  coupling defects — but that value is **narrow** and entangled with the
  context-access effect E (largely) provides. Note path-aware E is **not** a
  perfect ceiling: one provider (gemini) still missed a cross-file Critical.
- **Author-seeded / author-staged** (§9). The migration property is constructed;
  the cost model is pinned and deterministic; the snapshot dependency graph and
  Q-surface were committed before runs. BD12's Q-invisibility (which drove the
  no-coupling residual) is a deliberate seed property, surfaced honestly here.
- **L-067-1.** GPT path-aware (arm E) **converged** on these tiny trees (9–11
  probes, verdict, no `token-budget` empty stop) — the prereg mitigation (keep
  trees small) held. No arm errored; no token-budget failures to record.
- **Symmetric audit (§4).** Every automated catch in the decisive cells was read
  and confirmed a real mechanism identification (`audit.json`, with quotes); **no
  removals**. R's cadence-payoff catches name the concrete wrong value / inverted
  maths / rounding; E's coupling-blind catches name the cross-file contract; Q's
  misses and R's coupling-blind misses are the true null, not removed catches.

---

## 6. What S4 consumes (input, not the decision)

S4 makes the **keep / demote / retire** call via cross-provider consensus +
operator confirmation. Experiment B contributes:

1. **Pre-registered verdict: cadence defense DOES NOT HOLD (clause B3)** — R's edge
   over end-of-set is not cleanly attributable to Q-invisible cadence; it is
   largely surface-coverage (the Experiment A context-access effect) + earliness.
2. **But the cadence mechanism is real:** R catches migrating coupling defects at
   introduction (5/5 early window) and that saves **resolved** rework even versus
   the path-aware replacement E (the one place R beats E). The keep-leaning
   argument is this narrow rework-timing saving; the demote/retire-leaning argument
   is that E leads on capability (12/12 gpt, 11/12 gemini) and largely provides
   R's surface-coverage edge.
3. **Capability ranking at close (staged):** E (11–12/12) ≫ R (10/12) ≫ Q (4/12),
   reproducing Experiment A in the cadence setting.
4. **Cost shape:** per 5-session set, R = 5 routed calls (cheap, ~$0.04–0.14 here);
   E = 1 path-aware call (~$0.15–0.24 here). Per call E is ~6× R; per set the ratio
   narrows because R fires every session.

The pre-registration's B-branch reading is **demote or retire** (lead with
end-of-set path-aware + the S5 contract-test gate); the narrow R-vs-E
rework-timing saving is the countervailing consideration S4 must weigh.

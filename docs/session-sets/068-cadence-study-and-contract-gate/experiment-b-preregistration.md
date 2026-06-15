# Experiment B — Pre-Registration (Set 068 S2)

> **Status:** PRE-REGISTERED. Written **before** building the staged-snapshot
> harness (S3) and **before** running any arm. This file pins the hypotheses,
> the staged-snapshot intervention, the arms, the defect taxonomy, the
> **pre-committed rework cost model**, the metrics, the noise band, and the
> decision rule that will read as "cadence defense holds / does not hold" — so
> the verdict in `experiment-b-results.md` (S3) is graded against a fixed
> yardstick, not one chosen after seeing the numbers.
> **Created:** 2026-06-15 (Session 2).
> **Design source:** Set 065 `forward-ab-design.md` (Experiment B) + the Set 067
> Experiment A result + this set's `experiment-a-regrade.md`.
> **Execution vehicle:** the S1 `run_test` disposable-worktree cage
> (`ai_router/run_test_sandbox.py`) + the `pull_route` adapter (path-aware arms)
> + `route()` (routed arms).

---

## 1. The one question Experiment B exists to answer (Q5)

Experiment A (capability) **ruled out** a *capability* defense for per-session
routed verification: on identical frozen code, routed caught nothing path-aware
missed (H3 empty), and path-aware caught real cross-file Criticals routed missed
(H1). The re-grade confirms the *direction* (D5 clean existence proof; routed
cross-file strict survival 2/8 vs path-aware 13/14).

Routed's **only surviving defense is cadence**: *per-session* routed runs after
**each** session, so it can catch a defect **earlier during construction** —
before later sessions build on it — whereas a single **end-of-set** path-aware
pass catches everything only at the end, after the dependent work exists.
Experiment A held cadence constant by design and **cannot** test this. Experiment
B varies cadence directly.

**The non-obvious mechanism that makes this worth testing (not just dismissing).**
A defect that is **cross-file / coupled by set close** is often **in-snippet at
the session that introduces it** — at introduction, the dependent code does not
exist yet, so the defect's evidence is local to that session's own diff. Experiment
A's decomposition is decisive here:

- Routed is **strong on in-snippet** defects (it ties path-aware) and **weak on
  cross-file** (2/8 post-audit).
- So a coupling defect could **migrate**: in-snippet at session N (where
  per-session routed *might* catch it) → cross-file by set close (where end-of-set
  routed *cannot*, and only path-aware can).

If that migration is real, per-session routed has a genuine cadence edge: it gets
a shot at the defect during the one window where routed is strong. If instead the
coupling defects are cross-file even at introduction — or routed misses them at
session N anyway — the cadence opportunity is **unrealized** and the defense is
hollow. **That is the empirical crux.**

---

## 2. The intervention — staged snapshots of a multi-session build

A single unit of work is built as an **ordered sequence of snapshots**
`S1 -> S2 -> ... -> Sn`, each representing one session's construction checkpoint
of a frozen tree (the dabbler calculator / numeric-toolkit mock-repo style,
fully seedable, small enough that GPT path-aware converges — see L-067-1
mitigation, Section 9). Snapshots are **monotone**: `S(i)` is `S(i-1)` plus
session `i`'s diff. Later snapshots **genuinely depend** on earlier files (that
dependency is what creates coupling).

Each snapshot has a well-defined **session diff** (`S(i) \ S(i-1)`) — the change
set a per-session reviewer is handed — and a **full tree** (`S(i)` in its
entirety) — what an end-of-set reviewer sees at the end.

The snapshots and the dependency graph are **fixed and committed in S3 before any
arm runs**; this pre-registration fixes their *required properties* (monotone,
genuine cross-snapshot dependency, the defect taxonomy below), not the specific
code.

---

## 3. Arms — cadence × context (the two real regimes + cadence controls)

The decision is between two **real-world regimes** the workflow actually offers,
so those are the primary arms; two control arms isolate cadence from context.

| Arm | Cadence | Context | What it is | Priority |
|---|---|---|---|---|
| **R** | per-session | routed (session diff) | `route()` over each `S(i)\S(i-1)`, i=1..n — **the current Full-tier cadence** | **primary** |
| **E** | end-of-set | path-aware (full tree) | one `pull_route()` over `S(n)` — **the proposed replacement** (Set 066) | **primary** |
| **Q** | end-of-set | routed (final snippet) | `route()` over **Q's end-of-set surface** (`Q_surface_files`, §3a), once — **pure cadence control for R** | secondary |
| **P** | per-session | path-aware | `pull_route()` over each snapshot | optional / pilot-gated |

Each arm is run **per provider** (GPT `gpt-5.4`, Gemini `gemini-2.5-pro`), holding
provider constant within a contrast, exactly as Experiment A did. K repeats
(Section 6).

**The three load-bearing contrasts:**

- **R vs Q (pure cadence, context held = routed).** Same surface (routed/snippet),
  differ only in *when*. Does seeing the defect early — while it is still
  in-snippet in its introducing diff — let routed catch a coupling defect that
  end-of-set routed (Q) misses because by then it is cross-file? **This is
  routed's cadence defense in its cleanest, cheapest form.**
- **R vs E (the keep-vs-replace regime comparison).** Per-session routed (status
  quo) vs a single end-of-set path-aware pass (replacement). This is the contrast
  the S4 keep/demote/retire decision consumes. It is **cadence-and-context
  confounded by design** — that is intentional, because these are the two regimes
  on offer; the R-vs-Q control is what attributes any R advantage to cadence
  specifically rather than to surface.
- **Q vs E (end-of-set capability, staged).** Reproduces Experiment A's
  capability finding in the staged setting as an internal consistency check
  (path-aware should beat routed at the end).

### 3a. The routed-snippet surfaces (pinned — they define the visibility axes)

The routed arms (R, Q) are **snippet-bounded** (no whole-repo probe access — that
is what distinguishes them from the path-aware arm E). Two surfaces are fixed here,
both following Experiment A's snippet-construction rule (*the natural changed
file(s) a reviewer is handed*, the rest **omitted**):

- **R's per-session surface at session `i`** = the session-`i` diff
  `S(i)\S(i-1)` — the files that session changed.
- **Q's end-of-set surface** = the snippet a single end-of-set routed reviewer is
  handed for the finished unit: the **final session's diff** `S(n)\S(n-1)` plus
  the **headline changed file(s)** of the set, by the Experiment A "files a
  reviewer is handed" rule — explicitly **omitting** earlier-session files that
  were not re-touched late. Q does **not** receive the whole tree and cannot probe.
  This exact file list is the catalogue's **`Q_surface_files`** (§11 / harness
  schema), and **Arm Q is run on precisely that bundle** — never on the whole
  aggregate diff. `vis_at_close_for_Q` and the class invariants are checked against
  the same `Q_surface_files`, so classification and the actual Q run cannot drift.

These surfaces are committed in S3's catalogue (the exact file list per surface)
**before** any arm runs, so "in-snippet vs cross-file" is a checkable property of
the seed, not a post-hoc call.

---

## 4. Defect taxonomy (pre-committed) — three orthogonal axes

Every seeded defect is labelled on **three pre-registered** axes, fixed before runs:

1. **Coupling depth `d`** = the number of **later** snapshots that build on the
   defective code (downstream dependents). `d = 0` = no downstream coupling;
   `d > 0` = a coupling defect whose cost grows the longer it goes uncaught.
2. **Visibility at introduction (`vis_at_intro`)** = `in-snippet@intro` (the
   defect is recognizable from evidence fully inside the introducing session's
   diff `S(t0)\S(t0-1)` — **R's surface at `t0`**) vs `cross-file@intro` (evidence
   already requires a file that diff omits).
3. **Visibility at close, relative to Q (`vis_at_close_for_Q`)** = `in-snippet@close`
   (recognizable from **Q's end-of-set surface**, §3a) vs `cross-file@close`
   (by close the decisive evidence — the dependents / now-distributed contract —
   lives in a file **omitted from Q's surface**, so a snippet-bounded end-of-set
   routed reviewer structurally misses it).

The third axis is what makes the migration mechanism (§1) a **checkable seed
property** rather than a narrative: a cadence-payoff defect must be *recognizable
early by R* **and** *invisible to end-of-set routed Q* — otherwise a null R-vs-Q
would reflect the seed (Q could still see it), not a real absence of cadence value.

This yields the cells that make the experiment falsifiable:

| Class | `d` | vis@intro | vis@close (Q) | Prediction |
|---|---|---|---|---|
| **Cadence-payoff (the hypothesis)** | `> 0` | **in-snippet@intro** | **cross-file@close** | R has a real early window (in-snippet@intro) that Q has lost by close (now omitted from Q's surface); **R's cadence edge lives here, and ONLY here** |
| **Coupling-but-blind control** | `> 0` | cross-file@intro | cross-file@close | routed misses even at `t0` -> cadence opportunity unrealized -> **no R edge** though cost compounds (the hollow-defense mode) |
| **Always-visible control** | `> 0` | in-snippet@intro | **in-snippet@close** | Q can still see it at close -> **R and Q both catch; no cadence edge** (isolates that R's edge needs Q-invisibility, not just earliness) |
| **No-coupling control (null)** | `0` | either | either | cost does not grow with delay -> **cadence shows no benefit by construction** (built-in null; any R "advantage" here is noise) |

**Minimum seeding (asserted before the sweep):** at least **3** cadence-payoff
defects (the class the hypothesis lives in) AND at least **2** each of the three
control classes; if the catalogue cannot meet this, S3 expands the snapshots
before spending. The grader asserts the taxonomy invariants
(`cadence-payoff ⇔ d>0 ∧ in-snippet@intro ∧ cross-file@close`; `no-coupling ⇔ d=0`)
against the committed per-surface file lists.

Each defect also carries a **severity** (Critical=3 / Major=2 / Minor=1), its
introduction snapshot `t0`, its set of downstream-dependent snapshots, and a
deterministic **catch predicate** (the Experiment A grading mechanism: file/symbol
anchor + concept token over the arm's combined finding text), authored with the
catalogue in S3 before any arm runs. The trees are otherwise correct by
construction; any non-seed finding that is not a genuine pre-existing bug is a
false positive.

> **Symmetric grading from the start.** Per `experiment-a-regrade.md`, the
> cross-file catch audit (does the text NAME THE MECHANISM, not match a token
> carried by another finding) is applied to **all** arms from the outset — not
> one-directionally. The audit rule and per-cell quotes are committed with the
> S3 results.

---

## 5. The pre-committed rework cost model (the deterministic half)

The honest separation: **catch timing is measured empirically** (when does each
arm first flag each defect — the stochastic, agentic measurement); **rework cost
is a fixed deterministic function** of that timing and the known dependency graph.
The cost model is pinned **here, before any data**, and ships as code
(`experiment-b/cost_model.py`) so the verdict cannot be tuned post hoc.

For a defect with introduction snapshot `t0`, coupling depth `d`, severity weight
`w`, first caught by an arm at snapshot `c` (or never):

```
elapsed         = max(0, c - t0)                  # snapshots between intro and catch
dependents_built = min(d, elapsed)                # downstream work done on the bug before catch
rework_units(c) = BASE_FIX + COUPLING_PENALTY * dependents_built
                  + (ESCAPE_PENALTY if never caught else 0)
cost(defect)    = w * rework_units(c)
```

Pre-registered constants (fixed now): `BASE_FIX = 1`, `COUPLING_PENALTY = 1`
rework-unit per dependent snapshot built on the bug, `ESCAPE_PENALTY = 1 + d`
(a never-caught coupling defect costs strictly more than catching it at set end).
Total arm cost = `sum over defects`. **The only empirical input is `c` per defect
per arm.** Everything else is a property of the committed snapshot graph.

Intuition this encodes: catching a coupling defect **at introduction** (`c = t0`)
costs `w * BASE_FIX` (just fix it); catching the **same** defect at set end after
`d` dependents costs `w * (BASE_FIX + d)` (fix it **and** unwind the dependents).
For `d = 0` defects, `rework_units` is `BASE_FIX` regardless of `c` — so the
no-coupling control **cannot** show a cadence benefit, by construction.

`cost_model.py` ships with a self-test asserting these invariants (e.g. equal cost
across catch timing when `d=0`; monotone non-decreasing cost in `c` for `d>0`).

---

## 6. Sample size, repeats, blinding, noise band (pre-committed)

- **Snapshots:** one unit with `n ≈ 4–6` ordered snapshots (or 2 small units of
  3 each), built so later snapshots genuinely depend on earlier files.
- **Defects:** `~12–18` seeded across the snapshots, spanning the three taxonomy
  classes with the **cadence-payoff class well represented** (it is where the
  hypothesis lives) plus both controls.
- **K = 3 repeats** per arm per provider per snapshot. Agentic non-determinism is
  carried through the analysis as a **per-repeat distribution**, never collapsed to
  a single union before the decision (see §7) — this is the change the S2
  verification required: a one-off lucky catch in 1/3 repeats must not set the
  verdict.
- **Blind:** no arm sees another arm's output; remediation is **not** applied
  between snapshots (the snapshots are pre-built frozen checkpoints, so every arm
  reviews the identical staged tree — this removes a remediation-quality
  confound: we measure *catch timing*, the cost model supplies the rework, rather
  than letting one arm's fix quality perturb a later snapshot).
- **Noise band (single pinned formula).** Every decisive quantity is a **per-repeat
  contrast value** `X_k` (one number per repeat `k`, already a B-minus-A style
  contrast). Its **band is its own across-K range**: `band = max_k X_k − min_k X_k`.
  The decision statistic is **`mean_k X_k`** (the across-K mean); the contrast is
  **resolved** iff `|mean_k X_k| > band`, else reported **"too small to resolve at
  this n/K."** The **median** of `X_k` is reported alongside as a robustness check
  but is **not** itself a separate decision threshold (it must merely agree in
  sign; a mean/median sign disagreement is flagged as unresolved). This single rule
  removes the earlier `max(band_armB, band_armA)` ambiguity — there are no
  arm-level bands in the decision, only the contrast's own range. The two decisive
  per-repeat contrasts are:
  - **class catch-timing gap** `g_k = mean_{defects in class}[ c_k(comparator) − c_k(R) ]`
    where `c_k(arm)` is that arm's first-catch snapshot **in repeat `k`** (`n+1` if
    not caught in repeat `k`); positive = R earlier;
  - **class rework-cost saving** `s_k = cost_k(comparator) − cost_k(R)` where
    `cost_k(arm) = cost_model.arm_cost` over `{defect: c_k(arm)}` restricted to the
    class; positive = R cheaper.

---

## 7. Metrics (per arm, per provider, aggregated)

- **Per-repeat first-catch snapshot** `c_k(arm, defect)` (PRIMARY, empirical): the
  smallest snapshot at which the arm flags the defect **within repeat `k`**, or
  `n+1` if not caught in that repeat. The decisive timing/cost quantities (§6, §8)
  are computed **per repeat then aggregated across K** (mean and median both
  reported) — *not* from a union-over-K. The **union-over-K earliest-catch** and
  the **reliable-across-K** (caught at ≤ some snapshot in all K) are reported as
  **secondary/descriptive** stability signals only.
- **Realized-early-catch flag** per (arm, defect): the arm catches the defect at
  `c_k ≤ t0 + REALIZE_SLACK` (`REALIZE_SLACK = 1`, pre-registered) in a
  **majority of repeats** (`≥ ⌈2K/3⌉ = 2` of 3). This is the **binding stability
  gate** the decision rule (§8) uses for "R realizes the early window" — a single
  lucky repeat does not count.
- **Catch-timing gap** by taxonomy class = the per-repeat `g_k` of §6 (positive =
  R earlier), reported as mean and median across K with the noise band.
- **Rework-weighted total cost** per arm under §5's model, computed **per repeat**
  then aggregated, **broken out by taxonomy class** (any saving must be
  concentrated in the cadence-payoff class).
- **Severity-weighted catch rate at set close** (does the arm eventually catch?
  — confirms E/P reach the defects R may catch early).
- **Cost** ($ metered), **wall-clock**, **tool-call count** (path-aware arms).
- **False-positive rate** (non-seed, non-pre-existing findings), per arm.

---

## 8. Decision rule — "cadence defense holds / does not hold"

Pre-committed mapping (the S3 verdict cites these; S4 consumes them):

All clauses use the **per-repeat aggregated** metrics and the **binding
stability gate** (§7), never a union-over-K.

- **CADENCE DEFENSE HOLDS** iff **all** of:
  1. **R realizes the early window** on the **cadence-payoff** class: the
     *realized-early-catch flag* (§7 — caught at `c_k ≤ t0 + REALIZE_SLACK` in
     `≥2/3` repeats) is set for a **majority** of cadence-payoff defects. A single
     lucky repeat does not qualify;
  2. R's class catch-timing gap `g_k` vs the end-of-set comparator is
     **R-earlier and `|mean_k g_k| > band`** (§6 rule; the median of `g_k` agreeing
     in sign as the robustness check), **and** the **rework-cost saving** `s_k` for
     R over E (and over Q) likewise has `mean_k s_k > band` and is **concentrated
     in the cadence-payoff class**; and
  3. the **no-coupling control** (`d=0`) **and** the **always-visible control**
     (Q-visible at close) show **no** R advantage beyond the band (the saving is
     cadence + Q-invisibility, not a global routed artifact or mere earliness).
  → S4 reading: **keep** routed as a cheap early gate (cadence value confirmed),
  regardless of the Experiment A capability overlap.

- **CADENCE DEFENSE DOES NOT HOLD** iff **any** of:
  1. R does **not** realize the early window on the cadence-payoff class (the
     stability gate fails — R misses these at `t0` in a majority of repeats, the
     in-snippet window does not save routed, consistent with the Exp A / re-grade
     weakness). This is the primary trigger; a within-band R-vs-Q per-repeat gap is
     a separate corroborating signal, **not** an equivalent of it (a defect can
     fail the early-window gate yet still show a later R-vs-Q gap). **Or**
  2. the rework saving `s_k` has `mean_k s_k` within the noise band (or mean/median
     sign disagreement); **or**
  3. an apparent R saving also appears in the **no-coupling** or **always-visible**
     control (it is a surface artifact or pure earliness, not Q-invisible cadence).
  → S4 reading: **demote or retire** routed (Experiment A ruled out capability;
  Experiment B finds no cadence value), lead with end-of-set path-aware + the
  contract-test gate (S5).

- **UNRESOLVED** — if the decisive contrasts fall within the noise band at this
  n/K, the verdict is **"cadence effect too small to resolve at this scale"**;
  S4 then decides under explicit uncertainty (default: the cheaper-to-operate
  regime), and the honest non-result is recorded rather than a manufactured one.

**Falsifiable failure mode honored:** the design *can* return "cadence holds." If
per-session routed catches the migrating coupling defects at introduction and that
demonstrably saves rework over a single end-of-set pass, the result will say so
and routed stays — that is the outcome that would *keep* routed.

---

## 9. Pre-registered threats to validity (acknowledged up front)

- **R-vs-E is cadence×context confounded** (per-session→routed, end-of-set→
  path-aware). **Mitigation:** the R-vs-Q control isolates the pure cadence
  effect within the routed surface; any R advantage in R-vs-E is attributed to
  cadence only insofar as R-vs-Q corroborates it.
- **Author-seeded, author-staged.** The migration property (in-snippet@intro →
  cross-file@close) is constructed. **Mitigation:** an explicit
  coupling-but-blind control and a no-coupling null; the cost model is fixed
  before data; the snapshot dependency graph is committed before runs.
- **Cost model is a model, not measured dollars.** **Mitigation:** it is
  pre-registered, deterministic, shipped as code with invariant self-tests, and
  the **primary** outcome (earliest-catch snapshot) is purely empirical — the
  model only converts timing to a comparable scalar. Results report the raw
  catch-timing gaps alongside the modeled cost so a reader can re-weight.
- **L-067-1 (GPT over-probes / exhausts budget on non-trivial path-aware
  sandboxes).** **Mitigation:** keep snapshot trees small (Exp A's tiny trees let
  GPT converge); treat a `stop=token-budget` with no verdict as a **failed arm**
  (record it, do not silently drop); for the path-aware end-of-set arm prefer the
  converging providers and report GPT path-aware coverage separately if it
  degrades. (If S1/S6 lands the budget-aware forced verdict, enable it for the
  path-aware arms.)
- **Automated grading error.** Same mitigation as Exp A: deterministic predicate
  primary + symmetric manual audit (Section 4) with committed quotes + the
  cross-provider verification of the S3 analysis.
- **Small n.** The Section 6 honesty rule binds: unresolved effects are declared
  unresolved, not over-read.

---

## 10. Pilot gate (before any paid sweep) — L-067-3 / Set 067 methodology

Before the metered K-repeat sweep, S3 runs a **pilot**: **one** snapshot unit,
**one** provider, **one** repeat, exercising **R**, **Q**, and **E** end to end,
to confirm (a) the harness drives all three regimes through the `run_test` cage /
`pull_route` / `route()` seams, (b) earliest-catch is instrumented per defect, (c)
`cost_model.py` computes from the recorded catch snapshots, and (d) GPT path-aware
converges on the snapshot trees (L-067-1). The pilot's raw output is persisted to
disk first (L-064-3). Only after the pilot passes does the full K-repeat,
two-provider sweep run.

---

## 11. Harness skeleton (shipped this session; S3 fills it in)

The S2 deliverable is the **skeleton + the pre-registered cost model**, not the
run. Created under `experiment-b/`:

- `cost_model.py` — the Section 5 rework cost model, with invariant self-tests
  (pre-registered; committed before data).
- `harness-skeleton.md` — the snapshot directory layout, the catalogue schema
  (the per-defect fields of Section 4), and the arm-runner / grader interface
  signatures S3 implements (`build_snapshots.py`, `run_arms.py`, `grade.py`,
  mirroring the Experiment A harness shape).

S3 implements the builders/runners/grader against these signatures, seeds the
snapshots + defects, runs the pilot, then the sweep, and writes
`experiment-b-results.md` against this pre-registration.

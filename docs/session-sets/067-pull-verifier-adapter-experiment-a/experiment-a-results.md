# Experiment A — Capability Results (Set 067 S3)

> **Status:** COMPLETE. The blind, parallel, frozen-tree capability test from
> Set 065 `forward-ab-design.md`, run with the shipped `ai_router/pull_verifier.py`
> adapter (S1+S2). Graded against the **pre-registered** criteria in
> [`experiment-a-preregistration.md`](experiment-a-preregistration.md) — written
> before any data. **Created:** 2026-06-15 (Session 3).
>
> **Headline verdict: path-aware capability is CONFIRMED (H1).** On identical
> frozen code, the path-aware adapter caught **5 cross-file defects routed
> single-shot missed — including both seeded Criticals** — while routed caught
> **nothing** path-aware missed (H3 empty). The edge is **context-access, not a
> second provider** (H2): a second routed validator added zero; path-awareness
> added +0.31 weighted catch rate beyond it. A deterministic falsifier suite
> covered 19/20 defects (H4); the one it could not (a latent dead branch) was
> caught only by agent *reasoning*.

All raw arm outputs are in [`experiment-a/raw/`](experiment-a/raw/); the machine
metrics in [`experiment-a/experiment-a-data.json`](experiment-a/experiment-a-data.json);
the audit decisions (with quotes) in [`experiment-a/audit.json`](experiment-a/audit.json).

---

## 1. Setup actually run

- **Instrument:** 5 frozen "calculator / numeric-toolkit" trees, **20 seeded
  defects** spanning all 8 `forward-ab-design.md` classes (2 Critical, 12 Major,
  6 Minor; 2 novel-reasoning controls). Each defect pre-labelled
  `probeable|novel` and `in-snippet|cross-file`, with a pre-registered catch
  predicate. Built by `build_trees.py`; catalogue in `catalogue.json`.
- **Arms (2×2, context × provider), all on the BUGGY frozen tree, blind,
  single-round, K=3:**
  - **A1** routed GPT-5.4 · **A2** routed Gemini-2.5-pro — `providers.call_model`,
    fed only the per-tree **snippet** (the file a single-shot reviewer is handed).
  - **B1** path-aware GPT-5.4 · **B2** path-aware Gemini-2.5-pro —
    `pull_route(...)`, whole-tree sandbox + read-only probes.
  - Reasoning held **constant** across the context contrast (routed arms use the
    same reasoning knobs as the `pull_verifier` executor block). The only
    difference between A and B is the context surface.
- **Grading:** pre-registered deterministic predicates (automated) + a
  pre-registered **manual audit** of routed×cross-file catches (Section 5).
- **Spend:** 60 runs, ~**$1.38** metered. Falsifier suite: `falsifier_suite.py`.

The instrument self-check passed before spending: 19/20 falsifiers discriminate
(fail on the buggy tree, pass on the fixed tree); D16 is the documented
non-discriminating latent control.

---

## 2. The defect matrix (who caught what — union over K, audited)

| Defect | Sev | Context | Class | A1 | A2 | B1 | B2 |
|---|---|---|---|:--:|:--:|:--:|:--:|
| D1 | Major | in-snippet | too-narrow-regex | ✓ | ✓ | ✓ | ✓ |
| D2 | Major | in-snippet | silent-coercion | ✓ | ✓ | ✓ | ✓ |
| D3 | Minor | in-snippet | count-undercount | ✓ | ✓ | ✓ | ✓ |
| D4 | Major | in-snippet | type/shape | ✓ | ✓ | ✓ | ✓ |
| **D5** | **Critical** | **cross-file** | **dup-key collision** | · | · | ✓ | ✓ |
| D6 | Major | cross-file | join-key drift | ✓ | · | ✓ | ✓ |
| D7 | Minor | in-snippet | local-logic | ✓ | ✓ | ✓ | ✓ |
| D8 | Minor | in-snippet | silent-coercion | ✓ | ✓ | ✓ | ✓ |
| **D9** | **Critical** | **cross-file** | **index undercount (C9)** | · | · | ✓ | ✓ |
| D10 | Major | cross-file | type/shape | ✓ | · | ✓ | ✓ |
| **D11** | Minor | **cross-file** | local-logic | · | · | ✓ | ✓ |
| **D12** | Major | **cross-file** | too-narrow-validation | · | · | ✓ | ✓ |
| **D13** | Major | **cross-file** | default-injection | · | · | ✓ | ✓ |
| D14 | Major | in-snippet | type/shape | ✓ | ✓ | ✓ | ✓ |
| D15 | Minor | in-snippet | too-narrow-validation | ✓ | ✓ | ✓ | ✓ |
| D16 | Major | in-snippet | **novel: latent dead branch** | ✓ | ✓ | ✓ | · |
| D17 | Major | in-snippet | remediation-regression | ✓ | ✓ | ✓ | ✓ |
| D18 | Major | in-snippet | cross-file-contract-drift | ✓ | ✓ | ✓ | ✓ |
| D19 | Minor | in-snippet | dup-key collision | ✓ | ✓ | ✓ | ✓ |
| D20 | Major | in-snippet | **novel: emergent invariant** | ✓ | ✓ | ✓ | ✓ |

**Weighted catch rate (union over K):** A1 0.69 · A2 0.58 · **B1 1.00 · B2 0.94**.
Routed-pair (A1∪A2) **0.69**; path-aware-pair (B1∪B2) **1.00**.

The pattern is the result: **there is no positive in-snippet context gain** —
routed ties path-aware on the in-snippet defects (A1, A2, and B1 each 13/13; B2
misses one in-snippet defect, the D16 latent control). **On the 7 cross-file
defects, path-aware catches all 7; routed-pair catches 2** — and those 2 (D6, D10)
are exactly the ones whose evidence partially leaks into the snippet (Section 5).

---

## 3. Verdicts against the pre-registered criteria

### H1 — context-access (the primary capability claim): **CONFIRMED**

- Same-provider context contrast: **B1−A1 = +0.306** weighted, **B2−A2 = +0.361**
  weighted. Both **exceed the noise band** (max across-K spread 0.083 / 0.111).
- The gap is **entirely in the cross-file subclass** — `gained_in_snippet = []`
  for both contrasts. Path-aware's *gains* over same-provider routed are exactly
  cross-file (B1: D5,D9,D11,D12,D13; B2: D5,D6,D9,D10,D11,D12,D13), with **no
  in-snippet gains**. The only in-snippet difference runs the other way: B2 misses
  the D16 latent control (`lost_vs_routed=[D16]` for B2−A2) — which does not affect
  the cross-file-concentrated gain, but means path-aware is not strictly lossless.
- **≥1 high-severity cross-file defect caught by path-aware-pair, missed by
  routed-pair:** YES — **D5 (Critical** dup-key) and **D9 (Critical** index
  undercount), plus D11, D12, D13.

This meets the pre-registered H1-CONFIRMED rule exactly. Path-awareness catches
real, high-severity defects that snippet-fed routed structurally cannot — the
C3/C9 retrospective existence-proofs reproduce as an average effect here.

### H3 — routed's unique *capability*: **RULED OUT**

`routed-pair − path-aware-pair = ∅`. On identical frozen code, routed caught
**nothing** path-aware missed. This rules out a *capability* defense for routed
(consistent with the retrospective's empty "missed-by-both" bucket). It does
**not** settle keep/demote/retire: routed's only surviving defense is **cadence**
(catching defects earlier during construction), which Experiment A holds constant
by design — that is **Experiment B (Set 068)**.

### H2 — provider-multiplicity vs context-access: context-access is the lever

- A second **routed** provider bought **nothing**: routed-pair = 0.694 =
  best-single-routed (A1) = 0.694 (A2's catches are a subset of A1's).
- Path-awareness added **+0.306** beyond a second routed validator
  (path-aware-pair 1.0 − routed-pair 0.694). This is numerically the same resolved
  gap as B1−A1 and exceeds the noise band, so the H2 reading is **resolved** under
  the same pre-registered band comparison as H1 (not a sub-band near-tie).

So the retrospective's entangled question resolves, **in this experiment**, toward
**context-access**: "just add a second routed validator" would **not** have
closed the gap; reading the repo did. (Provider-multiplicity within *path-aware*
also added little here — the single GPT path-aware arm B1 already caught 20/20;
B2 added nothing and missed D16. The dominant axis is context, with a small
provider main-effect favoring GPT in both contexts.)

### H4 — probeable coverage / the contract-test lever

- **Falsifier coverage 19/20 (0.95)** — matches the retrospective's ~92%. The one
  defect no deterministic falsifier can discriminate is **D16** (a latent
  `if n < 0` dead branch where `n = len(...)`; behaviour is identical buggy-vs-fixed
  on all reachable inputs).
- **The agent caught the falsifier's blind spot by reasoning:** D16 was caught by
  A1, A2, and B1 — i.e. by *reading and reasoning*, not by any round-trip test.
  This is the retrospective's prediction made concrete: a contract-test gate
  carries the bulk (~95%) deterministically; the expensive agent is needed for
  the **non-probeable residual** and for discovering which falsifiers to write.
- **Honesty caveat (pre-stated):** the falsifiers were authored knowing the
  seeds, so this measures *"is the defect class mechanically falsifiable given
  knowledge of it"* — **not** *"could a blind author pre-author it cheaply."* The
  latter is the open question for the 068 contract-test gate.

### Overall capability verdict → S4 gate

**Path-aware capability is CONFIRMED.** Per the pre-registered S4 gate, Session 4
should **wire the optional automated `path-aware-critique.json` producer** (manual
stays the default; producer opt-in).

---

## 4. Cost, latency, false positives, non-determinism

| Arm | $/run | wall/run | probes/run | union catch |
|---|---|---|---|---|
| A1 routed GPT | $0.024 | ~17s | — | 15/20 |
| A2 routed Gemini | $0.005 | ~32s | — | 13/20 |
| B1 path-aware GPT | $0.033 | ~21s | 5.1 | 20/20 |
| B2 path-aware Gemini | $0.030 | ~32s | 3.5 | 19/20 |

Path-aware costs ~1.4× (GPT) to ~6.6× (Gemini) routed per run — a modest premium
for +0.31 weighted catch rate and 5 extra real defects (2 Critical). Every
path-aware run issued real probes (the instrumented signature; mean 3.5–5.1
tool calls); no zero-tool-call runs.

**False positives:** 5 path-aware findings did not match a seed predicate. On
inspection **none is spurious over-escalation**: they are either the **same seeded
defect** described in wording the predicate missed (e.g. B1 tree2 k3 restates D5),
or a **genuine secondary consequence** of a seed (e.g. B2 flags `round(None)` would
crash when an unknown op returns `None` — a real downstream effect of D18). This
contrasts with the retrospective's Gemini-009 over-escalation worry: at this
scale path-aware did not manufacture false defects. (It also means path-aware's
*true* coverage is marginally understated by the automated grade.)

**Non-determinism (K=3):** noise bands are small — routed 0.083 / 0.111,
path-aware 0.056 / 0.056. Path-aware was the more *stable* arm (B1 reliable-across-all-K
on 19/20; B2 on 15/20). Routed's per-replicate weighted rates: A1 [0.78,0.78,0.69],
A2 [0.78,0.83,0.72] (reported on the automated grade; the audit applies at the
union level — Section 5).

---

## 5. Grading, the audit, and why it is load-bearing (honesty)

The pre-registration (Section 5) commits to manually auditing every routed×cross-file
catch plus a sample of other matches. In practice **the only score-changing
(override-generating) cells were routed×cross-file** — the other inspections
(path-aware catches, in-snippet routed catches) confirmed the automated grade and
produced no overrides. The automated predicates initially credited **routed** with
4 cross-file catches per arm. The audit rule (*a routed catch of a cross-file
defect counts only if the text names the actual defect mechanism, not a generic
conditional hypothetical or a substring artifact*) removed 6 of them, with quotes
recorded in [`audit.json`](experiment-a/audit.json):

- **D9 (×6):** routed only nitpicked that `build_index`'s docstring says "superset"
  while it (correctly) filters KNOWN refs — never seeing that `all_refs` (in the
  omitted `analyzer.py`) drops call/return refs. Matched on the `all_refs`
  import-mention + a "subset" token. **Rejected.**
- **D13 (×5):** routed flagged `validate`/`count`/the dead branch but never the
  version-default-injection (needs the omitted `schema.py`). **Rejected.**
- **D10 A2:** the predicate token `dict` matched the substring inside
  "contra**dict**s"; A2 never flagged `str(ref)`. **Rejected.** (A1 genuinely
  flagged `str(ref)` as wrong-data — **kept**.)
- **D6 A2:** a generic "default-0 masks typos" note, not the name-vs-symbol drift
  (A1 identified the real drift from the `symbol` parameter — **kept**).

**Transparency:** under *pure automated* grading the B2−A2 gap (+0.111) sits at the
noise floor and would read "too small to resolve"; the **audit** (objective,
pre-registered, quoted) is what cleanly resolves H1 to +0.31/+0.36. The B1−A1 gap
exceeds the band even pre-audit. The audit is author-applied — a real dependency —
so the raw texts and per-finding quotes are committed for the cross-provider
verifier to check. Two routed cross-file catches **survive** the audit (D6, D10),
which is the honest finding that those two defects are partly snippet-visible (a
suspicious parameter name; a suspicious `str(ref)`).

---

## 6. Limitations (pre-registered threats, honored)

- **Author-seeded defects** may be unrepresentatively findable. Mitigated by
  spanning the retrospective's real classes + novel controls; an ecological
  harvester-tree secondary was scoped optional and **not run** this session.
- **Small n (5 trees, K=3):** resolves large effects (the C3/C9 magnitude) and the
  probeable fraction — **not** small ones. The honesty rule was applied (the
  near-floor pre-audit B2−A2 gap is reported as such).
- **Grading depends on the manual audit** for routed×cross-file (Section 5) — the
  single largest subjectivity; mitigated by an objective rule, committed quotes,
  and cross-provider review.
- **Mock-repo simplicity:** real codebases are larger and messier; the
  context-access effect could be larger (more to miss) or smaller (more snippet
  leakage). Direction, not magnitude, is the claim.
- **In-snippet defects show no context gap** — expected and is the built-in
  control (Trees 1 & 5): where path-awareness *shouldn't* help, it doesn't.
- **Falsifier pre-authoring caveat** (Section 3, H4): coverage measures mechanical
  falsifiability given seed knowledge, not blind pre-authoring.

---

## 7. Implications for Set 068 (carried, not decided here)

- **Keep/demote/retire routed** needs **Experiment B (cadence)** — A rules out
  routed's *capability* defense only.
- **Contract-test / CDC gate** is well-supported: ~95% of these defects are
  deterministically falsifiable; reserve the agent for the non-probeable residual
  (the D16 class) and for *authoring* the falsifiers.
- **Producer wiring (S4):** capability confirmed → wire the opt-in automated
  `path-aware-critique.json` producer.

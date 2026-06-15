# Experiment A — Pre-Registration (Set 067 S3)

> **Status:** PRE-REGISTERED. Written **before** building the seed harness and
> **before** running any arm. This file pins the hypotheses, arms, metrics,
> grading rule, sample size, and the decision rule that will read as "capability
> confirmed / not confirmed" — so the verdict in `experiment-a-results.md` is
> graded against a fixed yardstick, not one chosen after seeing the numbers.
> **Created:** 2026-06-15 (Session 3).
> **Design source:** Set 065 `forward-ab-design.md` (Experiment A) +
> `bake-off-results.md`. **Adapter under test:** the shipped
> `ai_router/pull_verifier.py` (`pull_route()`), S1+S2 cross-provider VERIFIED.

---

## 1. What Experiment A can and cannot answer

Experiment A is the **blind, parallel, frozen-tree** capability test. Every arm
reviews the **identical** frozen code; no arm sees any other arm's output;
cadence and round-count are held constant (single-round per arm per tree). This
removes the order / remediation-state / sequencing confounds the Set 065
retrospective could not.

- **It answers (capability sense):** does path-aware critique catch real defects
  routed single-shot misses on identical code (Q1); how much of any edge is
  context-access vs a second provider (Q2); does routed catch anything
  path-aware misses on the same code (Q3, *capability*); what fraction of catches
  a deterministic falsifier suite captures (Q4).
- **It deliberately does NOT answer:** routed's **cadence** value (Q5) — whether
  per-session routed catches defects *earlier during construction* and so reduces
  compounding rework. Cadence is held constant here by construction. That is
  **Experiment B (Set 068)**. A "routed has no unique capability" result here
  therefore **rules out only a capability defense** for routed; it does not by
  itself justify demoting routed.

---

## 2. Arms — 2×2 factorial (context × provider) + derived pair cells

| Arm | Context | Provider | Mechanism |
|---|---|---|---|
| A1 | routed (snippet/diff) | GPT (`gpt-5.4`) | `providers.call_model`, snippet pasted into prompt |
| A2 | routed (snippet/diff) | Gemini (`gemini-2.5-pro`) | `providers.call_model`, snippet pasted into prompt |
| B1 | path-aware (repo + probes) | GPT (`gpt-5.4`) | `pull_route(provider="openai")`, sandbox = full tree |
| B2 | path-aware (repo + probes) | Gemini (`gemini-2.5-pro`) | `pull_route(provider="google")`, sandbox = full tree |

Provider is held identical across the context contrast (GPT in A1=B1; Gemini in
A2=B2), which is what makes **B1−A1** and **B2−A2** clean context-access
contrasts. Derived cells: **routed-pair = A1∪A2**, **path-aware-pair = B1∪B2**.

**The context manipulation is the load-bearing design choice.** The routed arms
receive only a realistic **snippet/diff** — the file(s) a single-shot reviewer
would naturally be handed — *not* the whole tree. The path-aware arms receive the
**sandbox root** and must `grep`/`read_file`/`list_dir` to retrieve ground truth.
Defects are deliberately split (Section 4) into **in-snippet** (evidence fully
inside the pasted snippet — a control where context-access should give no edge)
and **cross-file** (evidence requires reading a file the snippet omits — where
context-access is predicted to pay off). If the trees were tiny enough to paste
whole, the context contrast would collapse; the snippet boundary is what creates
it.

---

## 3. Sample size, repeats, blinding

- **Trees:** ~5 frozen trees (the controlled **calculator / numeric-toolkit
  mock-repo**, fully seedable). Each tree is a self-contained directory.
- **Defects:** ~25 total seeded across the trees, spanning the
  `forward-ab-design.md` catalogue classes (Section 4), each pre-labelled
  `probeable | novel` and `in-snippet | cross-file`, each with a fixed severity.
- **K = 3 repeats** per arm per tree (all four arms; routed arms are stochastic
  too and cheap). Agentic-arm non-determinism is reported as a **distribution**,
  not a point estimate.
- **Blind:** no arm is shown another arm's output. All arms get the same task
  instruction per tree. Routed and path-aware differ ONLY in context surface.
- **Honesty (pre-committed):** n≈5 trees × K=3 resolves **large** effects (the
  C3/C9 magnitude) and the probeable-coverage fraction. It will **not** resolve
  small effects. Any contrast whose point gap falls **within the K-repeat noise
  band** (defined Section 6) is reported as **"too small to resolve at this
  n/K"** — not over-read as a win or a tie.

---

## 4. Defect catalogue classes (pre-committed)

Spanning the `forward-ab-design.md` classes; each instance is labelled
`probeable|novel` and `in-snippet|cross-file` and assigned a severity:

1. index/count undercount (C9-class)
2. name-collision / dup-key (C3-class)
3. too-narrow regex / validation (010-class)
4. type/shape contradiction across surfaces (010 MakeTable-class)
5. silent coercion / default-injection
6. cross-file contract / join-key drift (011 C1-class)
7. remediation-introduced regression (011 R2-class)
8. **≥2 genuinely novel-reasoning controls** — latent-not-currently-triggerable
   and/or emergent-invariant defects, designed so that a deterministic falsifier
   **cannot** be authored even *with* knowledge of the defect (the hard-case
   control that bounds what a contract-test gate can carry).

The trees are otherwise correct by construction: any arm finding that does not
map to a seeded defect and is not a genuine pre-existing bug is a **false
positive** (Section 5).

---

## 5. Metrics (per arm, per tree, and aggregated)

- **True-positive catch rate** on seeded defects, reported **severity-weighted**
  (Critical=3, Major=2, Minor=1) and **unweighted**, with the
  **probeable/novel** and **in-snippet/cross-file** splits broken out separately.
- **Union vs reliable catch:** a defect is *caught (union)* by an arm if caught
  in **≥1 of K** runs; *reliably caught* if caught in **all K** runs. Both are
  reported (union drives the coverage/marginal-value analysis; reliable is the
  stability signal).
- **False-positive rate:** findings not mapping to any seeded defect and not a
  genuine pre-existing bug, per arm (severity-weighted and count). This is the
  path-aware cost the retrospective flagged (Gemini's 009 over-escalations).
- **Cost** ($ metered), **token usage**, **tool-call count** (path-aware arms —
  the instrumented probes-actually-ran signature), **wall-clock latency**.
- **Falsifier-suite coverage** (Section 7).

### Grading rule (pre-committed, deterministic + audited)

Each seeded defect carries a **catch predicate**: a deterministic matcher
(case-insensitive keyword/regex set requiring the defect's *file/symbol* anchor
**and** a *concept* token) run over the union of an arm's `findings[].description`
+ `summary`. A predicate match = caught. The predicates are authored as part of
the catalogue (Step 2), **before** any arm runs. Because automated grading risks
**false negatives** (an arm describes the bug in words the predicate misses) and
**false positives** (a predicate fires on an unrelated mention), the orchestrator
**manually audits** every (a) predicate non-match where the arm flagged the right
file, and (b) predicate match, on a sampled basis, and records any corrections in
`experiment-a-results.md`. Automated grade is the primary number; the audit
delta is reported as a grading-uncertainty band. This grading dependence is a
stated limitation, not hidden.

---

## 6. Noise band

For each arm×tree, K=3 runs give a catch-rate sample. The **noise band** for a
contrast is the larger of the two arms' across-K spread (max−min over the K runs,
averaged across trees). A contrast (e.g. B1−A1) is **resolved** only if its mean
gap **exceeds** this band; otherwise it is "too small to resolve at this n/K."

---

## 7. The falsifier arm (Q4) and its honesty caveat

Before any agent runs (Step 3), a **deterministic falsifier** (an assert /
round-trip / count test) is authored for **every** seeded defect that is
*believed* mechanically falsifiable, and the attempt is made for **all** defects
including the novel controls. The falsifier suite must **fail on the buggy tree
and pass on the fixed tree** for each defect it claims.

- **Falsifier coverage** = fraction of seeded defects for which a falsifier that
  discriminates buggy-from-fixed could actually be authored. By construction the
  novel controls should resist falsification → coverage ≈ the probeable fraction.
- **Agent-vs-falsifier:** report whether the agent arms catch materially more
  than the falsifier suite (expected: agents add the novel residual + the
  discovery of *which* invariants to assert).
- **Caveat (pre-stated, from the retrospective):** the author planted the seeds,
  so authoring a falsifier here tests only *"is this defect class mechanically
  falsifiable given knowledge of it"* — **not** *"could a blind author
  pre-author the falsifier cheaply."* The latter is out of scope for Experiment A
  and is noted as the residual open question for the contract-test gate (068).

---

## 8. Decision rule — what reads as "capability confirmed / not confirmed"

Pre-committed mapping (the verdict in `experiment-a-results.md` cites these):

- **H1 — context-access (primary capability claim).** *CONFIRMED* iff: the mean
  catch-rate advantage of path-aware over same-provider routed (`(B1−A1)` and
  `(B2−A2)`, averaged) **exceeds the noise band (Section 6)** **and** is carried
  by the **cross-file** defect subclass, **and** at least one **Critical/Major
  cross-file** defect is caught by path-aware-pair (B1∪B2, union over K) and
  **missed by routed-pair** (A1∪A2, union over K). *NOT CONFIRMED* if the gap is
  within the noise band or is not concentrated in the cross-file subclass.
  - Falsifiable failure mode honored: if routed (snippet-fed) catches the
    cross-file defects about as often as path-aware, H1 is **not confirmed** and
    that is reported plainly.

- **H2 — provider-multiplicity vs context-access.** Report
  `(B1∪B2) − (A1∪A2)` (does path-awareness beat a second routed validator?) and
  `(A1∪A2) − A1` (how much a second routed provider alone buys). *Reading:* if
  routed-pair closes most of the gap to path-aware-pair → multiplicity explains
  most of the edge (the cheap fix is a second routed validator); if path-aware-pair
  still leads beyond the noise band → context-access adds value beyond a second
  provider. Resolved only if gaps exceed the noise band; else "too small to
  resolve."

- **H3 — routed's unique capability.** Compute
  `caught(A1∪A2, union-over-K) MINUS caught(B1∪B2, union-over-K)` on the seeded
  catalogue. *RULED OUT (capability)* iff this set is **empty** — routed catches
  nothing path-aware misses on identical code (consistent with the retrospective;
  routed's only surviving defense becomes cadence → Experiment B / 068).
  *CONFIRMED-UNIQUE* iff non-empty — name the defect(s) and keep routed on
  capability grounds.

- **H4 — probeable coverage / contract-test lever.** Report falsifier coverage
  and the agent-vs-falsifier comparison (Section 7). *Reading:* falsifier ≈ agent
  on probeable defects → a contract-test gate carries the bulk deterministically,
  agents reserved for the novel residual (the 068 lever); large agent-over-falsifier
  margin → agents are doing irreducible work.

- **Overall capability verdict.** Path-aware capability is *CONFIRMED* when H1 is
  CONFIRMED. The producer-wiring decision in **S4** is gated on this verdict: H1
  CONFIRMED → wire the optional automated `path-aware-critique.json` producer; H1
  NOT CONFIRMED → record the capability gap and **defer** the producer (the
  adapter still ships as a library seam), per spec S4 Step 2.

---

## 9. Pre-registered threats to validity (acknowledged up front)

- **Author-seeded defects may be unrepresentatively findable.** Mitigated by
  spanning the retrospective's real classes and including novel controls; the
  ecological secondary (a harvester frozen tree) is **optional** this session.
- **Automated grading error** (Section 5) — mitigated by manual audit + reported
  uncertainty band.
- **Snippet construction is a judgment** — the snippet boundary determines the
  context contrast. The boundary rule is fixed in Step 2 (the snippet = the
  natural "changed file(s)" a reviewer would be handed) and frozen before runs.
- **Small n** — Section 3/6 honesty rule binds: unresolved effects are declared
  unresolved.

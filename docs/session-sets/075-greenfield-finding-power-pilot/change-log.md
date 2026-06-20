# Change Log — Set 075 (Greenfield Finding-Power Pilot)

> **What this set delivered.** Sets 072–073 built the provider×surface verification-matrix
> instrument and ran it on **already-built, already-verified, already-remediated** diffs —
> measuring cost / noise / false-positive rate and the provider×surface *interaction*, but
> **not raw finding power** (the defects were already removed before the matrix ran). Set 075
> **stands up a greenfield finding-power pilot**: it authors the canonical protocol + standard
> instruction addendum for running the matrix **inside a consumer repo at Step 6,
> pre-remediation, on fresh not-yet-verified work** (defects still present), defines the
> adjudication rubric + diff-class stratification + telemetry/aggregation contract, and
> **enables the two source-bearing pilot repos**. The actual matrix runs happen in those
> repos' own sessions; a **future canonical synthesis set** scores the accumulated telemetry.
> This set ships **no `ai_router` code and no release** — it is protocol + rollout.
>
> **What it measures (honestly):** relative finding **yield + precision against the
> adjudicated union — NOT recall** (L-073-1 discipline). The matrix varies **provider, not
> framing**; both arms stay strong adversarial (**L-069-2**, hard constraint).
>
> **Settled strategy:** [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md) §10.
> **Canonical protocol:** [`greenfield-matrix-protocol.md`](../../greenfield-matrix-protocol.md) ·
> [`greenfield-adjudication-rubric.md`](../../greenfield-adjudication-rubric.md) ·
> [`greenfield-matrix-addendum.md`](../../../ai_router/prompt-templates/greenfield-matrix-addendum.md).
> **Release:** **none** (no version bump; no PyPI publish; no extension / Marketplace change).

---

## Session 1 of 2 — Protocol + addendum + rubric + telemetry/aggregation contract

**Status:** CLOSED, VERIFIED (gpt-5-4 cross-provider; converged over FOUR substantive rounds —
every round drove a real correctness fix, not nit-churn, per L-070-1 / L-071-1). No code
change. No release.

### Delivered

- **[`docs/greenfield-matrix-protocol.md`](../../greenfield-matrix-protocol.md)** — the
  canonical protocol: **D1** Step-6 pre-remediation timing + canonical invocation; **D2**
  relative-yield-not-recall framing + per-arm scoring (TP / FP / precision /
  share-of-adjudicated-union / unique-TPs / cost-per-TP against the adjudicated union);
  **D3** record-then-remediate freeze; **D4** doc-only exclusion; **D5** committed telemetry
  layout + the required `metadata.json` contract (incl. the `matrixArms[]` list, since one run
  scores one push + two pull arms); the two validity threats + mitigations (diff-class
  stratification with platform-as-lead; the fixed rubric); the 2-cell roster + code-focused
  range discipline; seeding-as-fast-follow; the cohort table; a Terminology block fixing
  *roster entry / matrix cell / arm*.
- **[`ai_router/prompt-templates/greenfield-matrix-addendum.md`](../../../ai_router/prompt-templates/greenfield-matrix-addendum.md)**
  — the reusable per-session instruction block consumer repos reference.
- **[`docs/greenfield-adjudication-rubric.md`](../../greenfield-adjudication-rubric.md)** — the
  FIXED TP/FP/duplicate/unclear rubric + the per-arm scoring table (defeats adjudication
  drift, Threat 2).
- **`telemetry/`** skeleton: `README.md` (D5 layout + required metadata contract + cohort) and
  per-repo placeholders for `dabbler-platform` (lead) and `dabbler-access-harvester`
  (supporting); migration-orchestrator excluded (D4).

Full detail in the S1 `disposition.json` and `s1-verification*.md` (saved raw, never edited).

---

## Session 2 of 2 — Consumer enablement + deferred-repo record + close

**Status:** CLOSED. No `ai_router` code change. No release.

### Delivered

- **Cohort enabled** (each committed + pushed in its OWN repo):
  - **`../dabbler-platform`** (LEAD, source-dominated) — `requirements.txt` router pin
    `>=0.1.0 → >=0.26.0`; addendum reference wired into `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`
    (commit `aac874e`). Venv upgraded 0.10.0 → 0.26.1; matrix CLI confirmed importable and
    parsing the addendum's exact args.
  - **`../dabbler-access-harvester`** (SUPPORTING, packaging-small/confounded) —
    `requirements.txt` router pin `>=0.15.0 → >=0.26.0`; addendum wired into the three
    instruction files (commit `a70c023`). Venv upgraded 0.18.0 → 0.26.1; CLI confirmed.
- **Deferral recorded** for **`../dabbler-access-migration-orchestrator`** (doc-only, zero
  source diffs) — excluded from the finding-power pool in the protocol (D4 / §10) and a
  one-line note added to its `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` (do not run the matrix for
  finding-power here; optional pull-only sidecar only, tagged `diffClass=docs-only-excluded` /
  `includedInFindingPower=false`; commit `f7547a4`).
- **§10 added to [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md)**
  — the pilot is live; what it measures (relative yield, not recall); the cohort (platform
  lead / harvester supporting / migration-orchestrator deferred); the two validity threats +
  mitigations; all held decisions (live default pull provider, RETIRE) stay held; the matrix is
  still not RETIRE evidence; synthesis is a future set.
- **Routed next-session-set recommendation** (`route(task_type="analysis")`, cross-provider
  from the Claude orchestrator) → [`s2-next-set.md`](s2-next-set.md): primary
  `076-seeded-recall-calibration-lane` (the fast-follow that is **not gated on consumer
  telemetry accumulation** — so it can run in parallel with the consumer matrix runs — though
  it carries its own design-approval prerequisite, the seeded-recall experimental design + the
  initial defect corpus); fallback WAIT, then open the **greenfield finding-power synthesis**
  set once its data gate is met.
- **Lesson L-075-1** authored (`lessons-learned.md`): a `requirements.txt` pin bump is not
  enablement until the target venv is actually upgraded and the entrypoint confirmed.

### End-of-set deliverables (the standing pilot)

A standing, comparable pilot that turns the Sets 072–073 already-built telemetry into a
**fresh-work finding-power** measurement — run inside the consumer repos at Step 6
pre-remediation, frozen as an immutable measurement, adjudicated by a fixed rubric, stratified
by diff class (platform the lead signal), and pooled in canonical for a future synthesis —
while holding every not-yet-earned decision (the live default pull provider, RETIRE) exactly
where Sets 072–073 left it.

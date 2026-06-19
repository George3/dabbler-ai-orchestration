# Change Log — Set 072 (Verification Tuning: Provider×Surface Matrix + Verification-Only Application Mode)

> **What this set delivered.** Set 070 built the dual-surface verifier to **hold
> provider equal across arms** — by design, to isolate *surface* as the only
> variable and keep the equal-arms artifact clean RETIRE evidence. An independent
> operator-run field study (`../kick-the-orchestrator-tires`, 18 push-vs-pull runs)
> found what that design is structurally blind to: **provider and surface
> interact**, and the live default pairing (`push = gpt-5-4` / `pull =
> gemini-2.5-pro`) is the study's *single weakest pull configuration*. Set 072 adds
> the **opt-in matrix seam** (without weakening the equal-arms steelman default), a
> **verification-only application mode** that points a configured provider×surface
> matrix at an **already-built** target repo — emitting per-cell telemetry **and** a
> consolidated fixer-facing remediation report as a byproduct of real verification
> work — and a **cross-run aggregator** that rolls many runs over one target into a
> single corroboration-annotated remediation backlog. It also folds in the deferred
> **L-069-1** sibling-reader hardening.
>
> **Settled strategy:** [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md) § 8.
> **As-built detail:** [`ai_router/docs/pull-verifier.md`](../../../ai_router/docs/pull-verifier.md).
> **Release:** `ai_router` **0.26.0** (PyPI). No extension / Marketplace change
> (Explorer/UI was a set non-goal).

---

## Session 1 of 4 — Matrix-mode seam + L-069-1 sibling-reader hardening

**Status:** CLOSED, VERIFIED (gpt-5-4 R1 clean). No release.

### Shipped

- **Opt-in matrix-mode seam in `dual_surface_verify.run_dual_surface`** — new
  optional per-arm `push_provider` / `pull_provider` / `push_model` / `pull_model`.
  Any one set turns on `matrix_mode`: each arm resolves independently, the **strong
  adversarial framing gate stays on both arms** (L-069-2 — the matrix varies
  *provider*, not framing), and only the provider/model **equality refusal** is
  skipped (divergence recorded as intentional). With none set, the equal-arms
  steelman default is **byte-for-byte unchanged** and still raises
  `UnequalArmsError`. Attestation gained `mode` / `intentionalDivergence` /
  `requestedPush+PullProvider+Model` (the actual reported identities stay under
  `pushProvider`/`pullProvider`); `DualSurfaceRun.mode` threads through
  `to_dict()` / `build_comparison_artifact`; `COMPARISON_SCHEMA_VERSIONS → (1, 2)`
  (v1 still accepted, v2 requires `mode`). `_arms_held_equal` **strengthened** to
  reject a matrix artifact as RETIRE evidence.
- **L-069-1 sibling-reader hardening** — the non-list-`entries` guard at all four
  sibling readers (`read_path_aware_critique` / `has_path_aware_critique_record`;
  `read_verification_mode` / `has_verification_mode_record`) + `UnicodeError` on the
  two `dedicated_verification.py` readers.

---

## Session 2 of 4 — External-target wrapper + per-cell telemetry + report artifact

**Status:** CLOSED, VERIFIED (gpt-5-4; one S2 conformance-test iteration). No release.

### Shipped

- **`ai_router/verification_only_app.py`** — a thin orchestration over
  `run_dual_surface` (matrix mode), no arm logic of its own, pointable at an
  **external** built target via the runner's `sandbox_dir` seam.
  `run_verification_matrix` runs one matrix-mode call per `MatrixCell` (push×pull
  cross-product); a failing cell is recorded as a `SkippedCell` so one provider
  failure never aborts the matrix (L-067-1).
- **`CellTelemetry`** stamps every confound this set does *not* vary —
  orchestrator provider/model, push & pull provider/model (the **actual** reported
  identities), per-arm framing strength, surfaces run, diff size/shape, and
  `push_broker` / `pull_broker = "none"`. Writes `verification-matrix-report.json`
  + a pure-Python `validate_matrix_report` at **L-066-1 parity** (never raises).
- **`build_remediation_report`** consolidates the run's cell findings via the Set
  070 `merge_findings` provenance merge (`push-only` / `pull-only` / `both`),
  dedups by stable key, severity-ranks, and writes a fixer-facing
  `remediation-report.{json,md}` — the artifact a target repo remediates from
  **without re-running verification**.
- **CLI** (`run` subcommand) + commentary-only `verification_only:` block under
  `pull_verifier` in `router-config.yaml` (no behavioral knob; live default pull
  provider unchanged). Schema docs `docs/verification-matrix-report-schema.md`,
  `docs/remediation-report-schema.md`.

---

## Session 3 of 4 — Cross-run remediation aggregator

**Status:** CLOSED, VERIFIED (gpt-5-4 R1 → R2; one Major adopted, one declined). No release.

### Shipped

- **`aggregate_remediation_reports`** — rolls up N per-run remediation reports over
  **one** target (a `MixedTargetError` guard refuses a mixed-target set) into
  `remediation-backlog.{json,md}`. Re-runs `merge_findings` across runs keyed by
  stable `defectKey` (max severity, union provenance/surfaces) and annotates each
  finding with **corroboration = the count of *distinct* runs** that surfaced it (a
  cross-config confidence/priority signal); an unkeyed finding is its own
  single-run group and never corroborates (safe over-split).
- **`validate_remediation_backlog`** — L-066-1 parity (distinct + member run refs;
  `corroboration == distinct count`; provenance invariants on a stripped core).
  CLI `aggregate` subcommand. Schema doc `docs/remediation-backlog-schema.md`.
- **R1 adjudication:** adopted the *corroboration-distinctness* Major (count distinct
  runs, not `len(runs)`); declined the converse `provenanceComplete` two-way Major
  (the S2-adjudicated/R2-confirmed over-reach — the three canonical sibling
  validators all enforce one-way; the rejected shape is conservative, never
  producer-emitted).

---

## Session 4 of 4 — Synthesis + docs + release + dogfood + first external run + close

**Status:** CLOSED, VERIFIED. **Release: `ai_router` 0.26.0** (PyPI tag
`v0.26.0`, operator-pushed on a green-`Test` SHA).

### Shipped

- **Synthesis.** `docs/verification-surface-strategy.md` § 8 (the provider×surface
  matrix instrument + the verification-only application mode; the honest correction
  that **surface is not fully orthogonal to provider**; the equal-arms mode remains
  the **only** RETIRE-evidence path with `_arms_held_equal` now actively refusing a
  matrix artifact; the **consumer-handoff model**). `ai_router/docs/pull-verifier.md`
  Set 072 as-built section.
- **Lesson L-072-1** — *an equal-arms A/B isolates its one variable and is
  structurally blind to that variable's interactions; add a complementary matrix
  instrument and measure on real built targets, never weaken the original control*
  (cites L-069-2, L-066-1).
- **Release.** `ai_router` `0.25.0 → 0.26.0` (`pyproject.toml` + `__version__`);
  CHANGELOG `[0.26.0]` (folds in the unreleased `routedApiCalls`-omitted change).
- **Next-session-set recommendation** (routed, gemini-pro): primary = a second
  external target (`dabbler-platform`) for cross-target provider×surface telemetry;
  alternative = the greenfield finding-power track.

### Dogfood (pathAwareCritique: required) — the matrix mode over this set's own diff

Ran the new matrix mode over the set's own diff (`ea393eb..HEAD`,
`push:openai × {pull:openai, pull:google}`); the multi-provider
`path-aware-critique.json` gate artifact was produced separately by
`pull_critique` (GPT-5.4 + Gemini-Pro). Per **L-070-1**, the dogfood artifacts are
kept as evidence and every finding adjudicated in `disposition.json`.

**The headline (L-070-1 in action): the repo-reading path-aware critique caught a
real Major the routed/snippet surfaces missed.** GPT-5.4's path-aware arm found that
`aggregate_remediation_reports` (S3) rebuilt raw findings from contributor-local
`severity` only — but the remediation-report schema marks a contributor's
`severity`/`category` **optional** (`_validate_contributor` accepts a contributor
that omits them; the finding-level `severity` is authoritative). So a **valid** per-run
report whose contributor omitted severity would be re-merged as *unspecified* and
**down-ranked** in the backlog (a Major sorting below a Minor). Verified real (not the
S3 F1-style conservative/never-emitted shape — this is a *corrupting* direction
reachable via a validator-accepted input), **fixed before release**: the
reconstruction now falls back to the parent finding's severity/category (+ a
regression test). Gemini's path-aware arm returned `VERIFIED` / 0 findings.

The matrix dogfood (the new mode over own diff) separately surfaced **4 Major
findings, all non-substantive** — no new code defect, so that dogfood converged:

- **F1 / F2 (push-only, GPT-5.4):** meta-confusion — the snippet-fed push arm misread
  its own **elided** 1.8 MB diff *input* as an incomplete review *response*. False
  positives (the snippet-fed-push context-gap Experiment A documented).
- **F3 (push-only, GPT-5.4):** "matrix mode lacks requested-vs-actual identity
  validation." **Verified false** — `CellTelemetry` stamps the **actual** reported
  identity (`push_result.provider/model`, `dual_surface_verify.py` line 635) and the
  attestation also records `requestedPushProvider/Model`, so attribution is always
  correct and any divergence is auditable. Skipping the equality *refusal* is the
  spec's explicit non-goal (matrix divergence is intentional). Context-gap.
- **F4 (pull-only, Gemini):** framing artifact — the dogfood pointed the pull arm at
  the repo root, so the target name `dabbler-ai-orchestration` (the repo) did not
  match a session-set slug the pull instruction expected. Invocation artifact, not a
  code defect.

(A transient first dogfood attempt skipped both cells on an Anthropic `529`
Overloaded on the push arm — which *demonstrated* the L-067-1 producer-skip
discipline: the run completed, recorded both `SkippedCell`s, and wrote valid empty
reports. Re-run with `push:openai` produced the findings above.)

### First real external run on `../dabbler-access-harvester` (the load-bearing check)

Ran the wrapper over the harvester's set-018 change (`c11038e..e17bd41`) with the
best-guess matrix `push:anthropic × {pull:openai, pull:google}` including the
**Gemini-pull-under-strong-framing cell**. Result — recorded in
`harvester-run/verification-matrix-report.json` + `remediation-report.{json,md}`:

- **The Gemini-pull cell (`pull=google/gemini-2.5-pro`) returned `VERIFIED` — a
  verdict, NOT silence** (the load-bearing acceptance check). Consistent with
  "Gemini-quiet-on-pull was a framing artifact, now fixed by the strong
  devil's-advocate framing."
- Per-cell telemetry present and complete (orchestrator `anthropic/claude-opus-4-8`,
  push & pull provider+model, both arms `adversarial-devils-advocate`, surfaces,
  diff size/shape, brokers `none`). Both `validate_matrix_report` and
  `validate_remediation_report` round-trip.
- Both push arms (Anthropic) `VERIFIED`, 0 findings; the GPT-pull arm produced 1
  Minor, pull-only, unkeyed **meta**-finding (a complaint about prompt instruction
  tension — "not a substantive code verdict"), not a harvester code defect. The
  consolidated remediation report carries it with provenance. A clean,
  low-false-positive datapoint under strong framing across two providers and two
  surfaces.

---

## End-of-set deliverables (all shipped)

- The **opt-in matrix-mode seam** in `ai_router/dual_surface_verify.py` (S1), with
  the equal-arms steelman default provably unchanged and `_arms_held_equal` still
  rejecting matrix artifacts as RETIRE evidence.
- The **L-069-1 sibling-reader hardening** (S1) at all four reader sites.
- The **verification-only application mode** — `ai_router/verification_only_app.py`
  (S2): `run_verification_matrix`, `CellTelemetry`, the
  `verification-matrix-report.json` + `validate_matrix_report`,
  `build_remediation_report` → `remediation-report.{json,md}`, and the CLI.
- The **cross-run aggregator** (S3): `aggregate_remediation_reports` →
  `remediation-backlog.{json,md}` (deduped, max-severity, corroboration-annotated,
  mixed-target-guarded) + `validate_remediation_backlog`.
- The synthesis update (incl. the consumer-handoff model), the `ai_router` **0.26.0**
  PyPI release, this set's dogfood artifact, and the **first real external run on
  `../dabbler-access-harvester`** producing per-cell telemetry, a usable consolidated
  remediation report, and a non-silent Gemini-pull verdict (S4).

A canonical apparatus that can be pointed at an already-built solution to do real
verification work *and* measure — for the first time, on real diffs — how
verification **provider interacts with verification surface**, shipping today's
best-guess defaults while stamping every not-yet-varied confound so the defaults can
be refined as telemetry accumulates — and emitting, alongside the telemetry, a
**consolidated remediation report** the target repo acts on directly, never
re-running verification itself.

# Verification Tuning — Provider×Surface Matrix + Verification-Only Application Mode (Set 072)

> **Purpose:** Give the canonical apparatus a **verification-only application
> mode** that can be pointed at an **already-built** target repo and run a
> **provider×surface matrix** (push = snippet-fed single-shot; pull = repo-reading
> agentic loop, *different providers allowed per arm*), emitting per-cell findings
> **plus** telemetry. Set 070 built the dual-surface instrument to **hold provider
> equal across arms** — by design, to isolate *surface* as the only variable. An
> independent field study (`../kick-the-orchestrator-tires/docs/study-findings.md`,
> 18 runs across its sets 002–005) found the opposite of what that design can
> measure: **provider and surface interact**, and our live default pairing
> (`push = gpt-5-4` / `pull = gemini-2.5-pro`) is the study's *single weakest pull
> configuration*. This set adds the **opt-in matrix seam** (without weakening the
> equal-arms steelman default), the **external-target wrapper** that does real
> verification work on a built solution while emitting the provider×surface
> telemetry as a byproduct, and folds in the deferred **L-069-1** sibling-reader
> hardening that `set-072-consolidate-apparatus` had queued.
>
> **Design rationale (required reading):** the field study above is the scoping
> input; **L-069-2** (never weaken framing — the matrix varies *provider*, not
> framing, so both arms stay strong adversarial) and **L-069-1** (fix every
> sibling site of a bug class) in
> [`docs/planning/lessons-learned.md`](../../planning/lessons-learned.md) are the
> hard constraints; **L-066-1** (produce↔validate parity) governs the new report
> artifact.
> **Created:** 2026-06-19.
> **Session Set:** `docs/session-sets/072-verification-tuning/`
> **Prerequisite:** Set 071 complete (it shipped the materiality gate + blocking
> classifier; the matrix seam and external-target wrapper this set adds must extend
> the Set 070/071 verification machinery additively, never weaken it).
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification (gated:
> run `python -m ai_router.routed_gate` per session; this set touches the shared
> dual-surface verifier surface, so expect REQUIRED throughout).

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
pathAwareCritique: required   # edits the shared dual-surface verification surface (high blast radius); continue the dogfood norm
contractGate: advisory        # light dogfood of the floor; record the durable seed at set start (070 shipped the start_session fix)
prerequisites:
  - slug: 071-verifier-materiality-and-nitpick-discipline
    condition: complete
```

> Rationale: pure `ai_router` machinery + one new module + a PyPI release; **no UI
> surface**, so no UAT/E2E gate. **Full tier** — every session is cross-provider
> verified (gated). `pathAwareCritique: required` because this set changes the
> **shared verification surface** (`dual_surface_verify.run_dual_surface`) and adds
> a verification-producing wrapper; the blast-radius predicate scores it
> `required`. `contractGate: advisory` — Session 1 records the durable
> `contractGate` seed at set start (the Set 070 S1 `start_session` fix is in place,
> so this is the normal path, not a new fix).

---

## Project Overview

### Background

Set 070 shipped `ai_router/dual_surface_verify.py:run_dual_surface`: it runs the
**push** arm (snippet-fed `call_model` over the committed diff, repo-blind) and
the **pull** arm (`pull_route` repo-reading agentic loop) over the **same
committed state**, with **provider, model, and framing held equal across arms** —
a steelman of each surface that isolates *surface* as the only variable. It takes
a single `provider` scalar, pins it to both arms, and raises `UnequalArmsError`
if the arms diverge (the equality is *measured* from each arm's reported identity,
not assumed). `docs/verification-surface-strategy.md` treats provider as
orthogonal infrastructure held constant.

An independent operator-run field study in `../kick-the-orchestrator-tires`
(`docs/study-findings.md`, 18 push-vs-pull runs across its sets 002–005) reached
three conclusions:

1. **Push won on incisiveness — but only on small, snippet-fittable diffs**, and
   the study flags this would likely **flip toward pull** on a large diff (its #1
   caveat). Real built targets supply large cross-file diffs, exercising this for
   free.
2. **Use both surfaces, always** — complementary; push/pull disagreement is itself
   diagnostic of which arm had repo/spec context.
3. **Provider × surface interact (the strongest finding).** Gemini: strong on
   push, quiet on pull. GPT: reliable on both. Anthropic: highest ceiling, lowest
   reliability. The study calls our live default (`push = gpt-5-4` / `pull =
   gemini-2.5-pro`) the *single weakest pull configuration*.

Our instrument cannot measure finding #3 (it pins one provider to both arms), and
our live default may be underweighting pull. One lever the study left
**uncontrolled is framing** — it compared whatever framing each harness shipped.
Our templates are now *both* strong devil's-advocate
(`classify_framing_strength → ADVERSARIAL`), so "Gemini-quiet-on-pull" may already
be a fixed framing artifact. That is cheap to check, and is the load-bearing first
datapoint this set collects.

### Design inputs (the operator decision)

Rather than run another **synthetic** provider×surface study (burning tokens on
toy diffs), point a systematic provider×surface verification at a **real,
already-built solution** — first target `../dabbler-access-harvester`. Its error
domain is reduced (prior verification thinned it) but real; every run does
*useful* verification work **and** emits provider×surface telemetry as a
byproduct, and its large cross-file diffs close the study's snippet caveat for
free. Philosophy: **ship a best-guess-optimized verification process now; refine
as real telemetry accumulates** — no synthetic confound-set gate.

The honest read of an already-built target: this is a strong test of **cost /
noise / false-positive rate / which surface surfaces residual hard-to-find
issues**, and a *weak* test of raw finding power (full finding-power tests want a
greenfield build — a future track). The mode is built so confounds we do **not**
vary yet (orchestrator provider; a future push/pull broker) are **stamped into
telemetry** now, keeping later data comparable.

### What this set delivers

1. **An opt-in matrix-mode seam** in `run_dual_surface`: new optional per-arm
   `push_provider` / `pull_provider` / `push_model` / `pull_model` params. When any
   is set, the runner resolves each arm independently, **keeps the strong
   adversarial framing gate on both arms** (L-069-2 — the matrix varies provider,
   not framing), and **does not require or raise on provider/model divergence** —
   divergence is recorded as intentional. With none set, the equal-arms steelman
   default is **byte-for-byte unchanged**, still refusing accidental divergence.
2. **A verification-only application mode** — `ai_router/verification_only_app.py`
   (the only net-new module): a thin orchestration over `run_dual_surface` (matrix)
   and `produce_path_aware_critique`, pointable at an **external** target repo via
   their existing `sandbox_dir` seam, running a configured set of provider×surface
   **cells** and writing a `verification-matrix-report.json` artifact with per-cell
   findings + telemetry. Best-guess defaults: both arms strong framing; pull = GPT
   reliable default; push = Anthropic or GPT; the first run includes a
   **Gemini-on-pull-under-strong-framing cell**.
3. **A fixer-facing remediation report** emitted by every run — the verification we
   do *is* the verification, so its findings must be usable for remediation **without
   the target re-running anything**. The mode consolidates findings across all cells
   via the Set 070 provenance merge (`merge_findings`: push-only / pull-only / both),
   deduplicated by stable finding key, severity-ranked, with file/location / impact /
   evidence retained and the experiment metadata dropped — a `remediation-report`
   (machine `.json` + human-readable `.md`) the target repo consumes directly. The
   `verification-matrix-report.json` (experimental, per-cell) and the remediation
   report (fixer-facing, consolidated) are **two distinct outputs of one run.** A
   **cross-run aggregator** (S3) then merges the remediation reports from *many* runs
   over one target into a single deduplicated **remediation backlog** — the
   end-of-exploration handoff — where a finding surfaced by multiple provider×surface
   configs carries that cross-config corroboration as a confidence/priority signal.
4. **Per-cell telemetry** (`CellTelemetry`) that stamps every confound — orchestrator
   provider/model, push & pull provider/model, per-arm framing strength, surfaces
   run, diff size/shape, and `push_broker`/`pull_broker="none"` — plus a pure-Python
   `validate_matrix_report` with L-066-1 produce↔validate parity.
5. **The L-069-1 sibling-reader hardening** (the deferred `set-072-consolidate`
   residual): the proven non-list-`entries` guard applied to the 4 unguarded sibling
   readers in `path_aware_critique.py` and `dedicated_verification.py`, plus
   `UnicodeError` added to the two readers that lack it.
6. A synthesis update, focused tests, an `ai_router` **PyPI release** (minor,
   `0.25.0 → 0.26.0`), dogfood (`pathAwareCritique: required`), `change-log.md`, and
   the **first real external run on `../dabbler-access-harvester`** producing a genuine
   **remediation report** and confirming per-cell telemetry + that the Gemini-pull
   cell returns a verdict (not silence).

### Scope (in)

- Additive matrix-mode params + `matrix_mode` branch + intentional-divergence
  attestation in `ai_router/dual_surface_verify.py`; `DualSurfaceRun.mode`;
  `COMPARISON_SCHEMA_VERSIONS → (1, 2)` (schema `1` stays accepted).
- New `ai_router/verification_only_app.py` (`run_verification_matrix`, `MatrixCell`
  / `CellResult` / `VerificationOnlyReport` / `CellTelemetry`,
  `validate_matrix_report`, CLI) — **reusing** `run_dual_surface` and
  `produce_path_aware_critique`, no parallel arm-execution logic.
- The `verification-matrix-report.json` artifact + its schema doc.
- The **remediation report** consolidation: a `build_remediation_report` helper that
  runs `merge_findings` across the run's cells (provenance-tagged), dedups by stable
  key, severity-ranks, and writes a fixer-facing `remediation-report.json` + `.md` —
  the deliverable a target repo consumes without re-running verification.
- The **cross-run aggregator** (`aggregate_remediation_reports`): merges N per-run
  remediation reports over **one** target into a single `remediation-backlog.{json,md}`,
  deduped across runs by stable key, max-severity, with each finding annotated by the
  runs/configs that surfaced it (cross-config corroboration → confidence) and a guard
  that refuses to merge reports from different targets.
- L-069-1: the non-list-`entries` guard at `read_path_aware_critique`,
  `has_path_aware_critique_record`, `read_verification_mode`,
  `has_verification_mode_record`; `UnicodeError` added to the two
  `dedicated_verification.py` readers.
- Commentary-only `router-config.yaml` block documenting the shipped best-guess
  defaults (no new behavioral knob).
- Tests: matrix-mode units (equal-arms default unchanged; intentional divergence
  recorded; framing still enforced in matrix mode; `_arms_held_equal` still rejects
  a matrix artifact as RETIRE evidence); L-069-1 reader hardening; wrapper +
  telemetry + validator units (all via injected fakes, **no metered calls**).

### Non-goals (out)

- **Weakening the equal-arms steelman default or the adversarial framing.** L-069-2
  is a hard constraint: matrix mode varies **provider**, not framing — both arms
  stay strong adversarial. The default (no per-arm params) path must be unchanged
  and still refuse accidental divergence. **Do NOT weaken `_arms_held_equal`** — a
  matrix artifact is a per-cell instrument, *not* RETIRE telemetry.
- **Changing the live `router-config.yaml` default pull provider.** The Gemini-pull
  cell is an *experiment cell*; hold any default change until it reports (and that
  decision belongs to a later set, on accumulated telemetry).
- **Retiring or demoting push.** This set measures; it changes no
  keep/demote/retire posture (the operator RETIRE precondition in
  `verification-surface-strategy.md` §5.1 still stands).
- **Greenfield builds, contract-driven development, an orchestrator-provider sweep,
  or a push/pull broker.** Named as future tracks; this set only *stamps* their
  confounds into telemetry so later work stays comparable.
- **Explorer / extension UI**; any Marketplace bump. Field pilots in consumer repos
  beyond the single first run on harvester.

### Standards

- **Additive over the equal-arms default (L-069-2 + Set 070).** Every matrix change
  is opt-in; the "equal-arms default unchanged" test is the guardrail — a change
  that alters the no-per-arm-params path is invalid.
- **Produce↔validate parity (L-066-1).** `validate_matrix_report` must accept
  exactly what `run_verification_matrix` writes and reject malformed envelopes
  (int-not-bool guards; never raises).
- **Fix every sibling site (L-069-1).** The non-list-`entries` guard lands at all
  four reader sites in one pass; do not leave a known sibling latent.
- **Stamp confounds you don't vary.** Orchestrator provider/model and the
  broker fields are recorded per cell even though this set holds them constant.
- **Dogfood honestly (L-070-1).** The end-of-set path-aware critique is iterative;
  keep the final round as the gate artifact and adjudicate every finding in the
  disposition — do not chase a pristine post-fix snapshot.

---

## Sessions

### Session 1 of 4: Matrix-mode seam + L-069-1 sibling-reader hardening

**Steps:**
1. Register; **record the durable `contractGate: advisory` seed at set start** (via
   `start_session --contract-gate advisory`). Read §*Design inputs* above, L-069-2,
   L-069-1, and `dual_surface_verify.py` — `run_dual_surface`, the equality
   attestation + `UnequalArmsError`, `ArmFraming`/`classify_framing_strength`, the
   `DualSurfaceRun` dataclass + `to_dict()`/`build_comparison_artifact`,
   `COMPARISON_SCHEMA_VERSIONS`, `_resolve_model`, and `_arms_held_equal`.
2. **Add the matrix-mode seam to `run_dual_surface`** (additive, opt-in): new
   optional `push_provider` / `pull_provider` / `push_model` / `pull_model`;
   `matrix_mode = (push_provider is not None) or (pull_provider is not None)`. In
   matrix mode resolve each arm via `_resolve_model`, **keep the framing gate on
   both arms**, and skip *only* the provider/model equality refusal (record it as
   intentional). Extend the attestation dict with `mode`, `intentionalDivergence`,
   `requestedPush/PullProvider/Model`; keep existing measured keys for back-compat.
   Add `DualSurfaceRun.mode`; thread through `to_dict()`/`build_comparison_artifact`;
   bump `COMPARISON_SCHEMA_VERSIONS → (1, 2)` (keep `1`). **Do not weaken
   `_arms_held_equal`.**
3. **Fold in L-069-1**: apply the proven non-list-`entries` guard
   (`entries = log.get("entries"); if not isinstance(entries, list): return <no-record
   default>`) at `read_path_aware_critique`, `has_path_aware_critique_record`
   (`path_aware_critique.py`), `read_verification_mode`, `has_verification_mode_record`
   (`dedicated_verification.py`); add `UnicodeError` to the two
   `dedicated_verification.py` readers' `except`.
4. Tests — `test_dual_surface_matrix_mode.py`: equal-arms default unchanged (provider
   divergence with no per-arm params still raises `UnequalArmsError`, attestation
   `mode=="equal-arms"`); intentional divergence (`push=anthropic`/`pull=google`) →
   no raise, `mode=="matrix"`, `intentionalDivergence==True`, both framings strong;
   framing still enforced in matrix mode (a weakened push template still raises);
   `_arms_held_equal` still rejects a matrix artifact as RETIRE evidence. And
   `test_activity_log_reader_hardening.py`: all 4 readers return the no-record
   default (no raise) on non-list `entries` and invalid-UTF-8. All via injected
   fakes — **no metered calls**.
5. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Creates:** `ai_router/tests/test_dual_surface_matrix_mode.py`,
`ai_router/tests/test_activity_log_reader_hardening.py`.
**Touches:** `ai_router/dual_surface_verify.py`, `ai_router/path_aware_critique.py`,
`ai_router/dedicated_verification.py`.
**Ends with:** matrix mode records `mode:"matrix"`/`intentionalDivergence:true` with
both framings strong; the equal-arms default still refuses accidental divergence; all
four sibling readers survive non-list/invalid-UTF-8 logs; suite green; session
**VERIFIED**.
**Progress keys:** `matrix-seam`, `intentional-divergence-attested`, `l069-1-hardened`, `s1-verified`.

### Session 2 of 4: External-target wrapper + per-cell telemetry + report artifact

**Steps:**
1. Register; read S1 deliverables and `pull_critique.py` —
   `produce_path_aware_critique`, its `sandbox_dir` / `_default_sandbox_for` seam,
   the `_FALLBACK_INSTRUCTION` path, the Set-066 Finding shape, and the ASCII
   status helper.
2. Build **`ai_router/verification_only_app.py`** (thin orchestration, no arm logic
   of its own): `run_verification_matrix(target_repo, *, base_ref, head_ref, matrix,
   ..., orchestrator_provider, orchestrator_model, run_dual_surface_fn=...)` grouping
   push/pull rows into pairings, one matrix-mode `run_dual_surface` call per pairing,
   pointed at the **external** `target_repo` via `sandbox_dir`; `MatrixCell` /
   `CellResult` / `VerificationOnlyReport` dataclasses.
3. Add **`CellTelemetry`** (composing the run attestation — no duplication): stamps
   orchestrator provider/model, push & pull provider/model, per-arm framing strength,
   surfaces run, diff size/shape (via the runner's existing diff dispatch), and
   `push_broker`/`pull_broker="none"`. Write the **`verification-matrix-report.json`**
   artifact + a pure-Python `validate_matrix_report` mirroring
   `validate_comparison_artifact` (L-066-1, never raises). Cell findings reuse the
   Set-066 Finding shape. **Also** add `build_remediation_report(report)`: consolidate
   the run's cell findings via `merge_findings` (provenance push-only / pull-only /
   both), dedup by stable finding key, severity-rank, and write a fixer-facing
   `remediation-report.json` + `remediation-report.md` (file/location / impact /
   evidence / provenance retained; experiment metadata dropped) — the artifact a
   target repo remediates from without re-running verification.
4. Add the **CLI** (`python -m ai_router.verification_only_app run --target ...
   --base ... --cell push:anthropic --cell pull:google --out report.json`;
   ASCII-only status; returns int). Add a **commentary-only** `verification_only:`
   block under `pull_verifier` in `router-config.yaml` documenting the shipped
   defaults — **no behavioral knob; the live default pull provider is unchanged.**
5. Tests — `test_verification_only_app.py` (injected fake runner, **no metered
   calls**): per-cell telemetry stamps every confound; `validate_matrix_report`
   accepts well-formed / rejects non-object/bad-schema/bad-cell; the external
   `sandbox_dir` is honored (fake asserts it received the external path);
   `build_remediation_report` consolidates cells (a finding seen on both surfaces
   appears once with `both` provenance), severity-ranks, and round-trips its `.json`.
   Author the schema docs `docs/verification-matrix-report-schema.md` and
   `docs/remediation-report-schema.md`.
6. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Creates:** `ai_router/verification_only_app.py`,
`ai_router/tests/test_verification_only_app.py`,
`docs/verification-matrix-report-schema.md`, `docs/remediation-report-schema.md`.
**Touches:** `ai_router/router-config.yaml` (commentary only),
`ai_router/dual_surface_verify.py` (`__all__` exports if needed).
**Ends with:** a CLI run under a fake runner produces **both** a
`verification-matrix-report.json` (every cell stamping orchestrator/push/pull
provider+model, per-arm framing, surfaces run, diff size/shape) **and** a consolidated
fixer-facing `remediation-report.{json,md}`; both validators round-trip; session
**VERIFIED**.
**Progress keys:** `external-target-wrapper`, `per-cell-telemetry`, `matrix-report-artifact`, `remediation-report`, `s2-verified`.

### Session 3 of 4: Cross-run remediation aggregator

**Steps:**
1. Register; read S2 deliverables — the per-run `remediation-report` shape,
   `build_remediation_report`, the `merge_findings` provenance contract, and
   `docs/remediation-report-schema.md`.
2. Add **`aggregate_remediation_reports(reports)`** to `verification_only_app.py`:
   take N per-run remediation reports over **one** target (guard: refuse a mixed-target
   set), re-run `merge_findings` across runs keyed by stable finding key, take **max
   severity** across runs, and annotate each finding with the runs/cells/configs that
   surfaced it (the cross-config corroboration count is a confidence/priority signal).
   Write `remediation-backlog.{json,md}` — the end-of-exploration handoff — and a
   pure-Python `validate_remediation_backlog` (L-066-1 parity, never raises).
3. Add the CLI subcommand `python -m ai_router.verification_only_app aggregate
   --report a.json --report b.json --out backlog.json` (ASCII status; returns int).
4. Tests (fixtures, **no metered calls**): a finding present in 2 runs appears once
   with both runs in provenance and corroboration count 2; severity = max across runs;
   a mixed-target report set is rejected; the backlog validator round-trips.
5. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Creates:** `docs/remediation-backlog-schema.md`; aggregator tests (extend
`test_verification_only_app.py`).
**Touches:** `ai_router/verification_only_app.py`.
**Ends with:** N per-run remediation reports aggregate into one deduped,
corroboration-annotated `remediation-backlog`; the mixed-target guard holds; session
**VERIFIED**.
**Progress keys:** `cross-run-aggregator`, `corroboration-annotation`, `backlog-validator`, `s3-verified`.

### Session 4 of 4: Synthesis + docs + release + dogfood + first external run + close

**Steps:**
1. Register; read S1–S3 deliverables.
2. Update `docs/verification-surface-strategy.md` (record the new provider×surface
   matrix instrument and that provider and surface interact per the field study —
   surface is *not* fully orthogonal to provider; the equal-arms mode remains the
   RETIRE-evidence path, the matrix mode is a per-cell instrument) and
   `ai_router/docs/pull-verifier.md`. Record the **first per-cell datapoint** incl.
   the Gemini-pull cell. **Document the consumer handoff model**: canonical runs the
   verification-only mode against a built target and emits the consolidated
   `remediation-report`; the target repo (e.g. harvester) **consumes the report for
   remediation and never re-runs verification** — exploration produces usable
   findings, not just telemetry. Author a lesson if warranted (candidate: "the
   dual-surface equal-arms design isolates surface but cannot see provider×surface
   interaction; measure the interaction on real built targets, not synthetic diffs"
   — cite L-069-2, L-066-1).
3. Finalize tests; bump `ai_router` **minor** (`0.25.0 → 0.26.0`); ship the **PyPI
   release** per the publish runbook (green-`Test`-on-the-tagged-SHA; verify tag
   commit == fixed SHA, Set 068 lesson; operator pushes/approves the tag). Record the
   publish run id post-release. Backfill `CHANGELOG.md` if any prior entry is missing.
4. `change-log.md`; route the next-session-set recommendation via
   `route(task_type="analysis")` (candidate: a second external target —
   `dabbler-platform` — or the greenfield-testing track that supplies full-error-domain
   finding-power data); cross-provider verification.
5. **Dogfood** (`pathAwareCritique: required`; `contractGate: advisory`): run the new
   matrix mode over **this set's own diff** (per L-070-1, keep the final round as the
   gate artifact and adjudicate every finding in the disposition).
6. **First real external run on `../dabbler-access-harvester`**: run the wrapper over
   the harvester's diff (`--base`/`--head` anchoring a real change) with the
   best-guess matrix incl. the Gemini-pull-strong-framing cell; record **both** the
   `verification-matrix-report.json` and the consolidated **`remediation-report.{json,md}`**
   (the genuine, usable findings harvester can remediate from); **confirm per-cell
   telemetry is present, the remediation report consolidates real findings with
   provenance, and the Gemini-pull cell returns a verdict, not silence** (the
   load-bearing acceptance check). If Gemini is silent, that IS the datapoint —
   record it; the live-default pull-provider decision stays held. `close_session`;
   set closes.

**Creates:** the synthesis update (incl. the consumer-handoff model), the candidate
lesson, `change-log.md`, this set's dogfood / path-aware-critique artifact, the
harvester `verification-matrix-report.json` **and `remediation-report.{json,md}`**.
**Touches:** `docs/verification-surface-strategy.md`, `ai_router/docs/pull-verifier.md`,
`docs/planning/lessons-learned.md` (if a lesson is authored), `ai_router/CHANGELOG.md`,
version metadata (`pyproject.toml` / `__version__`).
**Ends with:** the verification-only matrix mode is documented + released; the first
external harvester run produced per-cell telemetry, a **usable consolidated remediation
report**, and a non-silent Gemini-pull verdict (or recorded its silence as the
datapoint); set closed.
**Progress keys:** `synthesis-updated`, `released`, `change-log-written`, `dogfooded`, `first-external-run`, `remediation-report-produced`, `s4-verified`.

---

## End-of-set deliverables

- The **opt-in matrix-mode seam** in `ai_router/dual_surface_verify.py` (S1) — per-arm
  providers/models, intentional-divergence attestation, `DualSurfaceRun.mode`,
  schemaVersion 2 (1 still accepted) — with the equal-arms steelman default provably
  unchanged and `_arms_held_equal` still rejecting matrix artifacts as RETIRE evidence.
- The **L-069-1 sibling-reader hardening** (S1): the non-list-`entries` guard at all
  four reader sites + `UnicodeError` on the two `dedicated_verification.py` readers.
- The **verification-only application mode** — `ai_router/verification_only_app.py`
  (S2): `run_verification_matrix` over an external target, `CellTelemetry` stamping
  every confound, the `verification-matrix-report.json` artifact + `validate_matrix_report`
  (L-066-1 parity), the **`build_remediation_report` consolidation** (`merge_findings`
  provenance → deduped, severity-ranked `remediation-report.{json,md}`), and the CLI.
- The **cross-run aggregator** (S3): `aggregate_remediation_reports` →
  `remediation-backlog.{json,md}` (deduped across runs, max-severity,
  corroboration-annotated, mixed-target-guarded) + `validate_remediation_backlog` —
  the end-of-exploration handoff that rolls many runs into one fix-list.
- The synthesis update (incl. the **consumer-handoff model** — canonical runs the
  verification, the target remediates from the report and never re-runs), an
  `ai_router` **PyPI release** (`0.26.0`), this set's dogfood artifact, `change-log.md`,
  and the **first real external run on `../dabbler-access-harvester`** producing
  per-cell telemetry, a **usable remediation report**, and the Gemini-pull-under-
  strong-framing datapoint (S4).

A canonical apparatus that can be pointed at an already-built solution to do real
verification work *and* measure — for the first time, on real diffs — how
verification **provider interacts with verification surface**, shipping today's
best-guess defaults while stamping every not-yet-varied confound so the defaults can
be refined as telemetry accumulates — and emitting, alongside the telemetry, a
**consolidated remediation report** so the verification we run during exploration
becomes a usable fix-list the target repo acts on directly, never re-running
verification itself.

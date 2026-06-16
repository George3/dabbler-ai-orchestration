# Change Log — Set 069 (Automated Pull-Critique Capabilities)

> **What this set delivered.** The automated `pull_critique` producer is no longer
> a read-only commentator. It can now generate **execution-backed, replayable**
> evidence, and reproduced probeable defects can be promoted into the deterministic
> floor under a quality gate — closing the automated-vs-manual gap the 0.22.x
> release exposed (the automated run missed two Major bugs the manual run
> reproduced by executing code). Everything is **additive**: absent the new config,
> a critique is byte-for-byte the read-only Set 067/068 loop.
>
> **Design rationale (now BUILT):**
> [`docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md`](../../proposals/2026-06-16-pull-architecture-capabilities/proposal.md).
> **Settled strategy:** [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md) § 6.
> **Release:** `ai_router` **0.23.0** (PyPI). No extension / Marketplace change
> (the Explorer/UI was a Set-068 non-goal carried forward).

---

## Session 1 of 6 — Single execution-evidence protocol + evidence-tiered findings

**Status:** CLOSED, VERIFIED (gpt-5.4, 4-round L-066-1 parity loop). No release.

### Shipped

- **`ai_router/evidence_protocol.py`** — the one protocol both the manual and
  automated critics share. A finding carries an evidence tier —
  `REPRODUCED` / `ASSERTED` / `HYPOTHESIS` (default `ASSERTED`, additive) — that the
  **orchestrator** applies, **never the agent**. `REPRODUCED` requires a
  servant-captured transcript (pinned ref, trusted `commandId` **XOR** `templateId`
  + typed args, pristine-checkout status, exit, raw output, output hash) that
  **replays on a second pristine checkout** with a matching hash. The
  **meta-oracle rule** holds by construction: an executed finding drives a **real
  public entrypoint**, not an agent-built harness.
- **Set 066 schema + pure-Python validator extended** to carry evidence-tiered
  findings; a `REPRODUCED` finding lacking a valid replayed transcript is
  **invalid** (`ARTIFACT_INVALID_EVIDENCE`). L-066-1 parity throughout (type-check
  optional fields, int-not-bool); the R1→R4 loop chased a whitespace-vs-`minLength`
  parity gap to `pattern: "\\S"` on all 13 fields.

---

## Session 2 of 6 — Trusted-command execution + diff-awareness + deeper probing

**Status:** CLOSED, VERIFIED (gpt-5.4 R1 FAIL → R2 PASS). No release.

### Shipped

- **Trusted-command execution in `pull_critique`** (additive; no config = the
  read-only Set 067/068 path). A critic may **trigger** an operator-authored
  command id in the disposable-worktree `run_test` cage — **never author argv**,
  fresh checkout, hard caps. `_dispatch_run_test` captures a clean-run execution
  with a **resolved trusted `command_id`** (`RunTestConfig.resolve_id`, not the
  model's raw name), dispatched **outside** the byte-equality guard.
- **`get_diff` tool + `DiffConfig`** — raw unified diff + changed-path list (never
  a model-summarized symbol map), dispatched to `git` directly like `run_test`.
- **S1 protocol wired** — findings carry `evidence_tier` + an orchestrator-stamped
  transcript; `submit_verdict` evidence fields are gated behind
  `allow_evidence = run_test_config != None`; `_stamp_evidence_tiers` confers
  `REPRODUCED` only via `_run_pristine_replay` hash-match, else collapses to a
  read-claim (`HYPOTHESIS` preserved).
- **`budget_caps_for_paths`** — blast-radius-budgeted loop depth
  (required/advisory/none = 1.0/0.6/0.4× + floors). CLI flags for all of the above.

---

## Session 3 of 6 — The probe-template lane (the missing middle)

**Status:** CLOSED, VERIFIED (gpt-5.4 R1→R3 PASS). No release.

### Shipped

- **`ai_router/probe_templates.py`** — operator-authored, **versioned** probe
  harnesses the critic invokes with **typed, validated args**
  (`validate_template_args` enforces required/type/enum/no-unknown-keys and
  **never raises** — an invalid call returns a raw `ERROR:` the model can correct).
  The harness runs **inside the cage** (`python -m ai_router.probe_templates --run`)
  and drives the code under review's **public entrypoint**, printing a deterministic
  `PROBE_RESULT:` line so a pristine replay reproduces the same hash.
- **`run_probe_template` tool** — each `_Execution` carries its own replay
  repo/ref/caps; the agent supplies a `templateId` + typed args, the orchestrator
  confers `REPRODUCED` only after a matching pristine replay.
- **Seed library** (`BUILTIN_PROBE_TEMPLATES`) — drives `ai_router`'s own public
  entrypoints; the templates that would have caught the two 0.22.x bug classes.
- **Live dogfood find (L-069-1).** `malformed_artifact_bytes` reproduced a
  **still-latent instance of the 0.22.x `UnicodeError` class** — four readers in
  `path_aware_critique.py` caught only `(OSError, json.JSONDecodeError)` and
  crashed on invalid UTF-8 — fixed by adding `UnicodeError` (the same fix Set 068
  applied to `contract_gate`).

---

## Session 4 of 6 — Podman model-authored-probe lane (rung b) — GREEN spike

**Status:** CLOSED, VERIFIED (gpt-5.4 R1 NEEDS_FIX → R2 PASS). No release.
**Spike gate:** **GREEN** (6/6 acceptance criteria, podman 4.9.3) → full lane.

### Shipped

- **`ai_router/podman_sandbox.py`** — `run_test_sandbox`'s sibling, isolation by
  `podman run`: `--network=none`, `--read-only` rootfs, repo bind-mounted
  read-only at `/repo`, **tmpfs** `/scratch` (the only writable place),
  `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--rm`, hard wall-clock
  timeout + crash-safe force-remove, lane **label** for lane-local disk hygiene.
  `build_probe_argv` wraps the model's body as `python -B -c` with
  `PYTHONPATH=/repo`. + **`podman/Containerfile`** (no-secrets, operator-authored;
  production must digest-pin — `image_is_digest_pinned()` surfaces an un-pinned run
  with a `NOTE:`).
- **`run_authored_probe` tool + `PodmanLaneConfig`** — autonomous, severity-gated
  (fire only on a critical/major claim unconfirmable via the cheaper lanes). The
  AI safety check (`default_triage`) is **triage-only**: reject/escalate,
  **never approve** (the container is the boundary).
- **Central safety property.** A model-authored probe can **never** mint
  `REPRODUCED` — `validate_transcript` requires a trusted `commandId` XOR
  `templateId`, so `_build_transcript` returns `None` for an authored execution and
  the finding is **capped at `HYPOTHESIS`** (the S5 ratchet is the only promotion
  path). The human stays the meta-oracle defense.
- **Carried the spike's three findings:** cgroup-v2-only resource caps
  (`cgroup_caps_enforceable()`), ~10s rootless-WSL teardown timeout, stdout/stderr
  split (only stdout is hashed). Real-podman cage regressions (`--network=none`,
  read-only, teardown, **disk-footprint**) run on Linux CI / WSL and **skip on the
  Windows host** by design.

---

## Session 5 of 6 — Ceiling→floor ratchet + measured replacement gate (rungs 5–6)

**Status:** CLOSED, VERIFIED (gpt-5.4 R1 FAIL → R2 PASS). No release.

### Shipped

- **`ai_router/floor_ratchet.py`** — the candidate-falsifier artifact
  (`candidate-falsifiers.json`) + the quality-gated admission gate. A reproduced
  probeable defect yields a candidate that is **never auto-merged**
  (`build_candidate_from_finding` always emits `humanSignoff={status:"pending"}`
  and extracts the falsifier **from the reproduced transcript**).
  `admission_decision` runs five mechanical gates (fails-on-old, passes-on-fixed on
  a *different* ref, drives-a-public-contract, flake-check, has-owner) and admits
  **only when all five pass AND human sign-off is `approved`**; a **rubber-stamp guard**
  rejects a human-approved candidate whose mechanical gate fails.
  `check_floor_ratchet_coverage` enforces the mandatory-coverage rule (a PENDING
  candidate satisfies it; a REJECTED one does not).
- **`ai_router/replacement_gate.py`** — a **pre-registered** seeded + holdout
  benchmark (`benchmark-registration.json`) + a raw scoreboard
  (`replacement-scoreboard.json`) + `score_benchmark` that **derives** recall /
  precision / replay-success / false-`REPRODUCED` (verdict never hand-asserted;
  the closed schema rejects a smuggled `verdict`/`meets`/`cadence` field). Honesty
  rules: underpowered forces `meets_thresholds = False`; zero-denominator metrics
  are `None`; the **manual run is never retired** (strongest recommendation =
  reduce manual to a periodic backstop). Carries the gated-surface telemetry the
  Set 068 DEMOTE said RETIRE reopens on.
- Three JSON Schemas + example fixtures + two pure-Python validators (L-066-1
  parity); CLIs `python -m ai_router.floor_ratchet` /
  `python -m ai_router.replacement_gate`.

---

## Session 6 of 6 — Synthesis + docs + release + dogfood + close

**Status:** CLOSED, VERIFIED. **`ai_router` 0.23.0 released to PyPI.**

### Shipped

- **Doc synthesis.** `docs/verification-surface-strategy.md` § 6 (*Set 069 — the
  execution-backed evidence layer*) records the as-built capability ladder, the
  **GREEN** Podman spike outcome, and how the ratchet/replacement-gate instrument
  the §5 RETIRE-reopen question. `ai_router/docs/pull-verifier.md` gained the S5
  ratchet/replacement-gate section. The proposal status is flipped to **BUILT**.
- **Release.** `ai_router` bumped **0.22.1 → 0.23.0**; CHANGELOG 0.23.0 entry;
  PyPI publish per the runbook (green-`Test`-on-the-tagged-SHA prerequisite;
  tag's commit verified == the fixed SHA; operator pushes/approves the tag).
- **Dogfood.** This set ran under `pathAwareCritique: required` (its own gate) +
  `contractGate: advisory`, plus the now-execution-capable producer over this
  set's own diff.

### End-of-set deliverables (all present)

The single execution-evidence protocol + evidence-tiered findings (S1); trusted-
command execution + `get_diff` + bounded multi-turn probing (S2); the
probe-template lane + seed library (S3); the Podman model-authored-probe lane
(S4); the quality-gated ceiling→floor ratchet + the measured replacement gate
(S5); the synthesis update, the `ai_router` 0.23.0 PyPI release, this set's
dogfood artifacts, and this change log (S6).

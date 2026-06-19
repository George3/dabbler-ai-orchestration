# Cross-Target Verification Telemetry — Second External Target (`dabbler-platform`) (Set 073)

> **Purpose:** Take the Set 072 verification-only application mode to a **second
> real built target** (`../dabbler-platform`) and turn one datapoint into two.
> Set 072 shipped the provider×surface matrix + the verification-only app mode and
> ran it once, on `dabbler-access-harvester`. That single run produced a
> load-bearing observation — **Gemini-pull, the field study's "single weakest pull
> configuration," returned a clean verdict (not silence) under strong framing** —
> but N=1 supports no provider×surface *interaction* conclusion and cannot move the
> live default-pull-provider question. This set runs the same matrix against
> `dabbler-platform`, **aggregates the harvester + platform remediation reports into
> the first cross-target backlog**, and asks the one question that matters: **does
> the Gemini-pull-not-silent result replicate on a second, independent target?** It
> emits a genuine remediation report `dabbler-platform` can consume (the
> consumer-handoff model) as the byproduct of useful verification work.
>
> **Design inputs (required reading):** Set 072's `change-log.md` and
> `docs/verification-surface-strategy.md` §8 (the matrix instrument, the
> consumer-handoff model, "surface is not fully orthogonal to provider"); the Set 072
> S4 **harvester learnings** (per-cell telemetry stamps *actual* identities;
> **push is blind to a large elided diff → pick CODE-FOCUSED diff ranges**, not a
> golden-output-dominated range; transient provider 529s happen — the L-067-1
> producer-skip handles them, but run load-bearing cells sequentially and be ready to
> re-run). Hard constraints: **L-069-2** (never weaken framing — both arms stay strong
> adversarial), **L-066-1** (produce↔validate parity on every artifact), and the two
> newly-promoted Conventions — **fix every sibling site of a bug class** and **frame
> an iterative dogfood as evidence, not a clean snapshot**.
> **Created:** 2026-06-19.
> **Session Set:** `docs/session-sets/073-cross-target-verification-telemetry/`
> **Prerequisite:** Set 072 complete (it shipped `ai_router` 0.26.0 with the matrix
> seam, `verification_only_app`, and the cross-run aggregator this set exercises).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification (gated: run
> `python -m ai_router.routed_gate` per session).

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
pathAwareCritique: advisory   # primarily an application/telemetry set; escalate to required only if a session changes the shared verification surface (e.g. the pull-template tension fix)
contractGate: none
prerequisites:
  - slug: 072-verification-tuning
    condition: complete
```

> Rationale: this set **runs** the Set 072 apparatus against a second target and
> analyzes the result; it does not build new core machinery, so **no UI/UAT/E2E
> gate**. **Full tier** — every session is cross-provider verified (gated).
> `pathAwareCritique: advisory` (not `required`): the primary work is application-level
> (running the matrix, aggregating, analyzing) rather than a change to the shared
> `dual_surface_verify` surface; the close-out warns on a missing artifact but does not
> block. If S2 ends up changing the shared verification surface (e.g. the optional
> pull-template instruction-tension fix), the blast-radius predicate will recommend
> escalating to `required` — confirm at that point. `contractGate: none` — there is no
> deterministic contract floor to dogfood here.

---

## Project Overview

### Background

Set 072 (`ai_router` 0.26.0) shipped the opt-in **provider×surface matrix seam** in
`dual_surface_verify.run_dual_surface`, the **verification-only application mode**
(`ai_router/verification_only_app.py`: `run_verification_matrix` over an external
target via `sandbox_dir`; per-cell `CellTelemetry`; the consolidated fixer-facing
`remediation-report.{json,md}`), and the **cross-run aggregator**
(`aggregate_remediation_reports` → `remediation-backlog.{json,md}`, corroboration =
distinct-run count, `MixedTargetError`-guarded). It ran the mode once, on
`dabbler-access-harvester`, and learned:

1. **Gemini-pull is NOT quiet under strong framing** — the field study's "weakest pull
   config" returned a clean `VERIFIED` with `provenanceComplete=true`. The strongest
   single observation, but **N=1**.
2. **Strong framing did not manufacture nit-churn** — 0 substantive findings, 1 Minor
   pull-only *meta*-finding (a complaint about a real tension in our own pull template).
3. **Push is blind to a large elided diff** — the harvester range was dominated by a
   23.7k-line golden-output regeneration the push arm elided; pull was the load-bearing
   surface (confirming the field study's #1 caveat on real targets).
4. **Not learned:** raw finding power (an already-built, thinned target tests
   cost/noise/false-positive rate, not catch power) and any provider×surface
   *interaction* (one target / one diff).

### The question this set answers

**Does the Gemini-pull-not-silent result replicate on a second, independent built
target?** That is the one finding from Set 072 that, if it holds, bears on the held
live default-pull-provider decision (`verification-surface-strategy.md` §5.1 — still
held; this set does **not** change it). A second target also produces the first
**cross-target** remediation backlog (exercising `aggregate_remediation_reports` on
real, independently-generated reports rather than fixtures) and a second per-cell
telemetry record toward the comparable corpus §8 says the matrix defaults will
eventually be refined on.

### What this set delivers

1. A **real verification-only matrix run against `../dabbler-platform`** over a
   **code-focused** diff range (the Set 072 harvester lesson — avoid golden-output- or
   generated-file-dominated ranges that the push arm elides), with the best-guess matrix
   including the **Gemini-pull-under-strong-framing cell**; produces
   `verification-matrix-report.json` + the consolidated `remediation-report.{json,md}`
   `dabbler-platform` can remediate from without re-running verification.
2. The **first cross-target remediation backlog** — `aggregate_remediation_reports`
   over the Set 072 harvester remediation report **and** this set's platform report,
   written as `remediation-backlog.{json,md}`, validated by `validate_remediation_backlog`
   (the first run of the S3 aggregator on real, independently-produced inputs). Findings
   that recur across targets are *not* expected (different codebases) — the value is
   exercising the cross-target path and the `MixedTargetError` guard's contrapositive
   (two reports, **one** logical aggregation per target; a deliberate two-target backlog
   is out of scope — the aggregator is one-target-by-construction, so the cross-target
   record is a **side-by-side comparison artifact**, not a single mixed backlog).
3. A **provider×surface telemetry record** for the platform run + a **side-by-side
   comparison** with the harvester run (Gemini-pull verdict, push-blindness on the diff
   shape, false-positive rate, per-cell findings), captured as a durable analysis note.
4. A **synthesis update** to `docs/verification-surface-strategy.md` §8 recording the
   **second datapoint** and the **Gemini-pull replication verdict** (replicated /
   did-not-replicate / inconclusive — whichever the data shows; a non-replication is an
   equally valid, recorded datapoint), and `ai_router/docs/pull-verifier.md` if warranted.
5. **Conditional, gated on recurrence:** if the platform run **also** surfaces the
   pull-template instruction-tension meta-finding (Set 072 harvester observed it once),
   that is the 2nd context — fix the `path-aware-critique.md` / `verification.md`
   instruction tension (a prompt-only change, framing strength preserved per L-069-2 —
   `classify_framing_strength` must still return `ADVERSARIAL`), with a release. If it
   does **not** recur, record the single observation and ship no template change / no
   release.
6. A lesson if warranted, `change-log.md`, the routed next-session-set recommendation,
   dogfood per `pathAwareCritique: advisory`, and an `ai_router` PyPI release **only if**
   item 5's template fix lands (otherwise no version bump — this is an
   application/telemetry set).

### Scope (in)

- One `run_verification_matrix` invocation against `../dabbler-platform` over an
  operator/orchestrator-chosen **code-focused** `--base`/`--head` range, written under
  `docs/session-sets/073-cross-target-verification-telemetry/platform-run/`.
- A cross-target **side-by-side** record (harvester vs platform) + a single-target
  aggregation per target where it adds signal (exercising the real aggregator path).
- The §8 synthesis update with the second datapoint + the Gemini-pull replication verdict.
- The conditional pull-template instruction-tension fix **iff** it recurs on platform
  (framing preserved; a regression test that `classify_framing_strength == ADVERSARIAL`).
- Tests only if code changes (item 5); otherwise this is a run+analyze+document set.

### Non-goals (out)

- **Changing the live `router-config.yaml` default pull provider.** Even a replicated
  Gemini-pull-not-silent result is N=2; the default-change decision stays held for a
  later set on accumulated telemetry (§5.1).
- **Weakening framing or the equal-arms steelman default** (L-069-2). The matrix varies
  provider, not framing; both arms stay strong adversarial.
- **A two-target *mixed* backlog.** The aggregator is one-target-by-construction
  (`MixedTargetError`); the cross-target view is a side-by-side comparison, not a merged
  backlog handed to either repo.
- **Greenfield finding-power testing** (the other Set 072 next-set candidate) — a
  separate future track; this set is the cheaper, lower-risk cross-target replication.
- **Remediating `dabbler-platform`'s findings in this repo.** Per the consumer-handoff
  model, canonical produces the remediation report; `dabbler-platform` consumes it on its
  own schedule. This set does not edit platform code.
- **Explorer / extension UI; any Marketplace bump.**

### Standards

- **Code-focused diff ranges (Set 072 harvester lesson).** Choose a `--base`/`--head`
  that is dominated by source changes, not generated/golden output the push arm elides.
  Record the chosen range and *why* in the run note.
- **Run load-bearing cells resiliently.** The Gemini-pull cell is the load-bearing
  acceptance check; run sequentially / be ready to re-run on a transient provider 529
  (L-067-1 producer-skip handles a skip gracefully, but a skipped load-bearing cell is
  not a datapoint — re-run it).
- **Honest replication verdict.** A non-replication (Gemini-pull silent or degraded on
  platform) is a *valid, recorded* datapoint, not a failure — record it and keep the
  default-pull-provider decision held either way.
- **Produce↔validate parity (L-066-1)** on every emitted artifact; **fix every sibling
  site** and **dogfood-as-evidence** (the two promoted Conventions) apply if any code lands.

---

## Sessions

### Session 1 of 2: Platform matrix run + cross-target telemetry record

**Steps:**
1. Register; read Set 072's `change-log.md`, `verification-surface-strategy.md` §8, the
   harvester run artifacts (`docs/session-sets/072-verification-tuning/harvester-run/`),
   and `verification_only_app.py` (`run_verification_matrix`, `CellTelemetry`,
   `build_remediation_report`, `aggregate_remediation_reports`).
2. **Choose a code-focused diff range** in `../dabbler-platform` (`git -C
   ../dabbler-platform log` + `diff --stat` to find a source-dominated change; avoid
   generated/golden/`.db`/`pack-output` noise). Record the range + rationale.
3. **Run the matrix** against `../dabbler-platform` with the best-guess matrix incl. the
   **Gemini-pull-under-strong-framing cell** (`push:anthropic --cell pull:openai --cell
   pull:google`, orchestrator stamped), writing under `platform-run/`. Confirm per-cell
   telemetry is present + complete, both validators round-trip, and **the Gemini-pull
   cell returns a verdict (not silence)** — re-run that cell if a transient 529 skips it.
4. **Cross-target record:** run `aggregate_remediation_reports` per target where it adds
   signal (exercising the real aggregator on independently-produced reports), and author
   a **side-by-side comparison note** (`cross-target-comparison.md`): Gemini-pull verdict
   harvester vs platform, diff shape + push-blindness, false-positive rate, per-cell
   findings. Validate the backlog(s).
5. Cross-provider verification (gated); `disposition.json`; commit + push; `close_session`.

**Creates:** `platform-run/verification-matrix-report.json`,
`platform-run/remediation-report.{json,md}`, `cross-target-comparison.md`
(+ any `remediation-backlog.{json,md}` produced).
**Touches:** none in `ai_router` (a pure run+record session).
**Ends with:** a validated platform matrix run with complete per-cell telemetry, a
non-silent (or recorded-silent) Gemini-pull verdict, and a side-by-side harvester-vs-
platform comparison note; session **VERIFIED**.
**Progress keys:** `platform-matrix-run`, `gemini-pull-replication-recorded`, `cross-target-comparison`, `s1-verified`.

### Session 2 of 2: Synthesis + (conditional) template fix + close

**Steps:**
1. Register; read S1's run + comparison note.
2. **Update `docs/verification-surface-strategy.md` §8** with the **second datapoint**
   and the **Gemini-pull replication verdict** (replicated / did-not-replicate /
   inconclusive); note the live default-pull-provider decision stays held regardless
   (§5.1). Update `ai_router/docs/pull-verifier.md` if warranted.
3. **Conditional template fix (gated on recurrence).** If the platform run *also*
   surfaced the pull-template instruction-tension meta-finding (2nd context), fix the
   tension in `prompt-templates/path-aware-critique.md` (and `verification.md` if
   shared) — a prompt-only change, **framing preserved** (a test pins
   `classify_framing_strength == ADVERSARIAL`); bump `ai_router` patch and ship the
   **PyPI release** per the publish runbook (operator pushes the tag on a green-Test
   SHA). If it did **not** recur, record the single observation and ship no change / no
   release.
4. Author a lesson if warranted; `change-log.md`; route the next-session-set
   recommendation via `route(task_type="analysis")` (candidate: a third target, or the
   greenfield finding-power track, or the default-pull-provider decision set if the
   replication holds); cross-provider verification.
5. **Dogfood** (`pathAwareCritique: advisory`) per L-070-1 (final round as the gate
   artifact; adjudicate every finding); `disposition.json`; commit + push;
   `close_session`; set closes.

**Creates:** the §8 synthesis update, `change-log.md`, the dogfood artifact, a lesson
(if warranted), and — only if item 3 fires — the template fix + a regression test.
**Touches:** `docs/verification-surface-strategy.md`, `ai_router/docs/pull-verifier.md`,
`docs/planning/lessons-learned.md` (if a lesson is authored), and — conditionally —
`ai_router/prompt-templates/*.md`, `ai_router/CHANGELOG.md`, version metadata.
**Ends with:** the second cross-target datapoint + the Gemini-pull replication verdict
are documented; any recurrence-gated template fix is released; set closed.
**Progress keys:** `synthesis-second-datapoint`, `replication-verdict-recorded`, `template-fix-or-noop`, `change-log-written`, `s2-verified`.

---

## End-of-set deliverables

- A **validated verification-only matrix run against `dabbler-platform`** over a
  code-focused diff range, with complete per-cell telemetry, a consumer-consumable
  `remediation-report.{json,md}`, and a recorded **Gemini-pull verdict** (S1).
- The **first cross-target telemetry record** — a side-by-side harvester-vs-platform
  comparison + the real aggregator exercised on independently-produced reports (S1).
- The **§8 synthesis update** with the second datapoint and the **Gemini-pull
  replication verdict** (whichever way it falls), the live default-pull-provider
  decision recorded as still held (S2).
- A **conditional, recurrence-gated pull-template instruction-tension fix** + PyPI
  release **iff** the meta-finding recurs (else a recorded no-op), `change-log.md`, the
  dogfood artifact, and the routed next-set recommendation (S2).

A second real datapoint on how verification **provider interacts with verification
surface** — turning the Set 072 N=1 Gemini-pull observation into a replication test on
an independent built target, exercising the cross-target aggregation path on real data,
and producing a usable remediation report `dabbler-platform` acts on directly — while
holding every not-yet-earned decision (the live default pull provider, RETIRE) exactly
where Set 072 left it.

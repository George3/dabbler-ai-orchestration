# Change Log — Set 073 (Cross-Target Verification Telemetry: Second External Target `dabbler-platform`)

> **What this set delivered.** Set 072 shipped the provider×surface matrix
> instrument + the verification-only application mode and ran it **once**, on
> `../dabbler-access-harvester` — producing one load-bearing observation
> (**Gemini-pull, the field study's "single weakest pull configuration," returned a
> verdict, not silence, under strong framing**) but at **N=1**, which supports no
> provider×surface *interaction* conclusion. Set 073 ran the **same matrix** against
> a **second, independent built target** (`../dabbler-platform`) over a deliberately
> **code-focused** diff range, turning one datapoint into two; exercised the
> cross-run aggregator on **real, independently-produced** inputs for the first time;
> emitted a consumer-consumable remediation report `dabbler-platform` can act on; and
> recorded the **Gemini-pull replication verdict** in the settled strategy. It is an
> **application/telemetry set: no `ai_router` code changed and no release** — the
> conditional pull-template fix did not fire because its recurrence gate did not trip.
>
> **Settled strategy:** [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md) § 9.
> **S1 evidence:** [`cross-target-comparison.md`](cross-target-comparison.md) + [`platform-run/`](platform-run/).
> **Release:** **none** (no version bump; no PyPI publish; no extension / Marketplace change).

---

## Session 1 of 2 — Platform matrix run + cross-target telemetry record

**Status:** CLOSED, VERIFIED (gpt-5-4 R1 ISSUES_FOUND, 1 Minor → fixed, non-blocking per L-071-1). No code change. No release.

### Delivered

- **Code-focused diff range chosen** in `../dabbler-platform`: `82a95ab..d66c449`
  (`crud-scaffolding-remediation` S2, the `Dabbler.CrudSlice` wrapper) —
  source-dominated (9 new `.cs` files: a new `tools/Dabbler.CrudSlice` CLI + its
  tests + 2 consuming `src/` files; no `.db`/`.nupkg`/golden/pack-output files
  dominant). Applies the Set 072 harvester lesson (avoid golden-output-dominated
  ranges the push arm elides).
- **Matrix run** `push:anthropic × {pull:openai, pull:google}` (mirrors the
  harvester matrix exactly, incl. the load-bearing
  Gemini-pull-under-strong-framing cell), orchestrator `anthropic/claude-opus-4-8`,
  both arms strong `adversarial-devils-advocate` framing (L-069-2 held). 2 cells,
  0 skipped → `platform-run/verification-matrix-report.json` +
  `remediation-report.{json,md}`. Per-cell telemetry present + complete; both
  `validate_matrix_report` (`expected_target=dabbler-platform`) and
  `validate_remediation_report` round-trip (`report-ok`).
- **The load-bearing acceptance check passed:** the Gemini-pull cell
  (`pull=google/gemini-2.5-pro`) returned `VERIFIED` — a verdict, NOT silence. The
  Set 072 harvester result **replicates on a second independent target (N=2)**.
  Honest nuance recorded: replication is of the *verdict-not-silence* property —
  Gemini-pull returned 0 findings while GPT-pull returned 2 Major contract-drift
  findings over the same repo, so the *finding-yield* gap is not refuted.
- **Per-cell results.** Cell A (`pull=gpt-5.4`): push `ISSUES_FOUND` 1 Major + pull
  `ISSUES_FOUND` 2 Major. Cell B (`pull=gemini`): both `VERIFIED`, 0 findings. The 2
  GPT-pull Majors are real repo-state contract-drift findings (a dead
  `docs/ai-led-session-workflow.md` SSOT link; `platform-overview.md` omitting the
  packaged `Dabbler.Api.Querying`) = genuine **consumer-handoff value**.
- **Cross-target record.** Ran `aggregate_remediation_reports` on the real platform
  report → `platform-run/remediation-backlog.{json,md}` (`runCount=1`, 3 findings,
  all `corroboration=1`), validates `report-ok`; demonstrated the
  **`MixedTargetError` contrapositive** (harvester + platform together correctly
  refused). Authored `cross-target-comparison.md` (side-by-side telemetry table, the
  replication observation + nuance, the diff-shape / push-blindness contrast, the
  per-cell findings + false-positive read, the aggregator exercise).
- **Key S2 input established:** the Set 072 pull-template instruction-tension
  **meta-finding did NOT recur** on platform → it is a single observation (N=1), so
  S2's conditional recurrence-gated pull-template fix **does not fire**.

### R1 adjudication

gpt-5-4 R1 returned 1 finding: `cross-target-comparison.md` §4 overstated the
adjudication of the platform push-only Completeness finding. Classified **Minor**
(doc-accuracy, no merge/code impact → non-blocking per L-071-1; effectively
VERIFIED). Fixed (rephrased §4 item 1 + its echo per L-065-1 to leave
materiality/triage to dabbler-platform) and not re-verified (a confirming re-verify
of a pure overstatement-removal wording fix is the L-071-1 nit-churn the discipline
forbids).

---

## Session 2 of 2 — Synthesis + (conditional) template fix + close

**Status:** CLOSED, VERIFIED. **No code change. No release** (the conditional
pull-template fix did not fire).

### Delivered

- **Synthesis.** `docs/verification-surface-strategy.md` **§ 9** (the second
  cross-target datapoint; the **Gemini-pull replication verdict** — *non-silent
  REPLICATED (N=2), finding-yield gap not refuted*; the push-blindness contrast
  across targets; the cross-target aggregator exercised on real inputs + the
  `MixedTargetError` contrapositive; the consumer-handoff value). The live
  `router-config.yaml` default pull provider is recorded as **still held** (§5.1 /
  §8.3 / §9.1) — N=2 on one property does not move it, and the finding-yield read
  cautions against promoting Gemini to the default pull slot on this evidence.
- **Conditional template fix — NO-OP (recorded).** The recurrence gate did not trip:
  the Set 072 pull-template instruction-tension meta-finding did **not** recur on
  platform (GPT-pull emitted substantive contract-drift findings instead), so it is a
  single observation (N=1). Per spec item 5, Set 073 records the single observation
  (§9.3) and ships **no template change and no release**.
  `classify_framing_strength` stays `ADVERSARIAL` — nothing touched the templates.
- **`pull-verifier.md` not updated** — its per-set sections are as-built-**code**
  records; Set 073 shipped no code, so the telemetry datapoint lives in strategy §9.
- **Next-session-set recommendation** (routed analysis): see `disposition.json`.

---

## End-of-set deliverables (all shipped)

- A **validated verification-only matrix run against `dabbler-platform`** over a
  code-focused diff range, complete per-cell telemetry, a consumer-consumable
  `remediation-report.{json,md}`, and a recorded **Gemini-pull verdict** (S1).
- The **first cross-target telemetry record** — `cross-target-comparison.md`
  (side-by-side harvester vs platform) + the real S3 aggregator exercised on
  independently-produced inputs, with the `MixedTargetError` guard confirmed (S1).
- The **§ 9 synthesis update** with the second datapoint and the **Gemini-pull
  replication verdict** (non-silent replicated, N=2; finding-yield gap not refuted),
  the live default-pull-provider decision recorded as **still held** (S2).
- A **recorded no-op** on the conditional, recurrence-gated pull-template fix (the
  meta-finding did not recur), this change-log, the advisory end-of-set dogfood
  artifact, and the routed next-set recommendation (S2).

A second real datapoint on how verification **provider interacts with verification
surface** — the Set 072 N=1 Gemini-pull observation turned into a replication test on
an independent built target (non-silence replicated; finding-yield gap not refuted),
the cross-target aggregation path exercised on real data, and a usable remediation
report `dabbler-platform` acts on directly — while holding every not-yet-earned
decision (the live default pull provider, RETIRE) exactly where Set 072 left it.

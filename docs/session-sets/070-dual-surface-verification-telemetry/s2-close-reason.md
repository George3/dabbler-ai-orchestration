# Set 070 Session 2 of 3 — close reason

**Orchestrator:** claude / anthropic / claude-opus-4-8 / high
**Verdict:** VERIFIED (gpt-5-4, R1 ISSUES → R2 ISSUES → R3 VERIFIED)
**Suite:** full ai_router GREEN — 2063 passed / 5 skipped (S1 baseline 1988/5;
S2 adds 75 net tests; the 5 skips are the Set 069 S4 real-Podman-on-Windows
by-design skips). **No release** this session (the ai_router bump + PyPI publish
is S3).

## Delivered (all in `ai_router/dual_surface_verify.py`, extending the S1 runner)

1. **Provenance merge** — `merge_findings` / `MergedFinding` / `MergeResult`.
   Two findings merge to `both` **only** when they share a non-empty, explicit
   `defectKey` — **never** on free-text wording (the Set 069 S6 floor-ratchet
   lesson: a description is not an identity). The safe direction is enforced: an
   unkeyed defect both arms caught becomes **two** single-surface entries
   (over-split, conservative — it never *hides* a push-unique catch, which would
   bias RETIRE toward retiring push), and the result honestly flags
   `provenance_complete=False` + per-surface unkeyed counts. Intra-arm duplicate
   keys fold to one contributor set (no double-count); severity = most-severe
   across contributors; both arms' wording preserved.

2. **Comparison artifact + validator + JSON Schema** — `build_comparison_artifact`,
   `validate_comparison_artifact`, `docs/dual-surface-comparison.schema.json` +
   `docs/dual-surface-comparison-schema-example.json`. Pure-Python validator in
   **L-066-1 parity** with the schema: closed top-level / contributor /
   merged-finding key sets, `int`-not-`bool` guards (`schemaVersion`,
   `pushUnkeyed`, `pullUnkeyed`), typed optionals, **and** the cross-field
   provenance invariants the schema cannot express (a `both` finding's
   contributors must cover both surfaces *and* carry a `defectKey`; a
   `push-only`/`pull-only`'s contributors are exactly that surface;
   `provenanceComplete=true` is inconsistent with any unkeyed finding **or** a
   nonzero unkeyed count). The example validates under both jsonschema and the
   Python validator.

3. **Fair-shake scoring** — `score_comparison` (push-unique / pull-unique / shared
   **high-severity** tally, reported as an **upper bound** when provenance is
   incomplete), `score_against_benchmark` (the RETIRE telemetry over the Set 069
   pre-registered seeded+holdout benchmark via
   `replacement_gate.validate_benchmark_registration`; ground truth = `defectKey`
   is a registered case; **underpowered → INCONCLUSIVE** even when
   push_unique>0; unkeyed high-sev excluded from the real tally; the gated push
   layer is **never retired** here — the verdict is a recommendation toward the
   operator-confirmed decision), and `aggregate_retire_telemetry` (refuses to pool
   `sampled` with `opt-in` — the honesty standard has teeth).

4. **Dual-surface verificationMode-pattern option + CLI** — `dualSurfaceMode`
   (`off`/`sampled`/`opt-in`) recorded once-at-set-start + immutable in the
   activity log (mirrors Set 057 verification_mode / Set 066 pathAwareCritique;
   distinct entry kind so it overloads neither enum); `read`/`has`/`unreadable`/
   `record`/`resolve_and_record`/spec-seed readers that **never raise** on a
   corrupt/malformed log; `should_run_dual_surface` with the random draw
   **injected** (hermetic, deterministic) — `off` never runs, `opt-in` only on
   explicit request, `sampled` fires when `sample_value < sample_rate` (tagged
   `sampled`) but a deliberate opt-in under sampled mode is the **operational**
   `opt-in` tag, never folded into the unbiased telemetry. CLI
   `python -m ai_router.dual_surface_verify record-mode / read-mode / score`.

## Verification arc (cross-provider, gpt-5-4, routed_gate → REQUIRED)

- **R1 ISSUES_FOUND ×3** (all real, no false positives): (1, High) the validator
  accepted `provenanceComplete=true` with nonzero unkeyed *counts* when no unkeyed
  *finding* was present → `score_comparison` would clear the upper-bound honesty
  warning → fixed with an unconditional count-consistency check + score derives
  completeness from flag **and** counts; (2, Med) `record-mode` could crash on a
  malformed activity log → hardened `record_dual_surface_mode` (controlled
  ValueError on unparseable/non-object, repair non-list entries) + `main`
  pre-checks unreadable and broadens its except; (3, Med) two tests didn't
  exercise the behavior they named → fixed.
- **R2 ISSUES_FOUND ×2** — Fix 2 was an **incomplete class-fix** (L-069-1): the
  *readers* (`read_`/`has_`) and the `stepNumber` `int()` cast could still
  `TypeError` on a non-list `entries` / a malformed `stepNumber`. Hardened every
  reader (guard `entries` is a list before iterating) + filtered prior
  `stepNumber`s through `_is_int_not_bool` + added `TypeError` belt-and-suspenders
  in the CLI, with the exact malformed-shape regressions R2 named.
- **R3 VERIFIED** — confirmed no remaining traceback path and that the new tests
  traverse the previously-broken CLI path, not just the writer in isolation.

(The R2 first attempt failed with an Anthropic 529 because `max_tier=2` had been
pinned, which dropped the verifier to a same-provider tier-2 model — a misapply of
L-064-7, which is for *wording-only* re-verifies; a substantive re-verify must stay
on the R1 verifier's tier. Re-run at tier 3 kept it on gpt-5-4. Noted for the
lesson refinement.)

## Deferred residual (explicitly recorded per L-069-1)

The same non-list-`entries` iteration pattern exists in the **pre-existing** sibling
readers `ai_router/path_aware_critique.py` (~lines 145, 209) and
`ai_router/dedicated_verification.py` (~lines 178, 243). They are out of S2's scope
(S2 owns `dual_surface_verify.py`); hardening them is a candidate follow-up
(S3 or a separate pass), recorded here as a decision, not an oversight.

## Metered spend

verify R1 $0.307 + R2 (failed 529, retried) ≈ $0 + R2-rerun $0.249 + R3 $0.188 +
next-orch analysis (routed) — total ≈ **$0.74 + next-orch**.

Session 2 **VERIFIED**.

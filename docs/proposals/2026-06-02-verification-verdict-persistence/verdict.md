# Verdict — verificationVerdict Persistence (S1 design-lock)

> **Set:** `054-verification-verdict-persistence`, Session 1
> **Date:** 2026-06-02
> **Consensus input:** `proposal.md` (Claude Opus 4.8 dispositions)
> **Cross-provider reviewer:** `gpt-5-4` (OpenAI) — raw in `consensus-review.md`
> **Round-1 overall:** `CONSENSUS-DISAGREE` (4 substantive objections)
> **Outcome:** design revised; 3 objections accepted, 1 partially accepted.
> This file is the **authoritative locked design**; where it differs from
> `proposal.md`, this file wins.

---

## How the consensus changed the design

The cross-provider reviewer agreed with **Q1, Q4, Q6, Q7, Q8, Q9, Q10**
outright and disagreed with **Q2, Q3, Q5**, plus raised four RISKS. The
disagreements were sound and materially improve the design. Net change:
**the verdict domain on disk collapses to `VERIFIED` / `ISSUES_FOUND` /
`null` — there is no `"manual"` or `"skipped"` verdict token.** Method and
provenance stay where they belong (`verification_method`, the attestation
event). This is more honest (the field means "the pass/fail outcome", not
"how it was checked") and removes an internal inconsistency the reviewer
caught.

### Objection-by-objection resolution

**Q2 — fallback / `--force` (ACCEPTED).** Reviewer: don't special-case
`--force` to `null`; force bypasses *gates*, not *evidence*, so a forced
close after a real API verification would erase a recoverable verdict.
Correct. **New precedence (final):**
1. `disposition.verification_verdict` present & non-empty → use it
   **verbatim** (wins even under `--force`, because the disposition is the
   evidence and force only skips gates).
2. else if `verification_method == "api"` → derive from
   `disposition.status`: `completed` → `"VERIFIED"`;
   `failed` / `requires_review` → `"ISSUES_FOUND"`.
3. else → `null` (manual / skipped / no-disposition `--force` — no pass/fail
   source exists; do not invent one).

**Q5 — manual / `--no-router` token (ACCEPTED).** Reviewer: `"manual"` is a
*method*, not a *verdict*; keep `verificationVerdict` `null` and let
`verification_method=manual` + the attestation event carry provenance.
Correct. **Final:** the manual / `--no-router` paths record
`verificationVerdict: null` unless the operator supplied an explicit
`VERIFIED` / `ISSUES_FOUND` in `disposition.verification_verdict` (then that
wins, per Q2 step 1). The schema-doc `:994` fix therefore becomes "records
`null`; `verification_method` records `manual`" — *more* honest than the
doc's current (false) `"manual"` claim.

**Q3 — enum vs free string (PARTIALLY ACCEPTED).** Reviewer: persist only
exact `VERIFIED` / `ISSUES_FOUND` / `null`; loose prefix-strings make the
state file and events non-queryable. Agreed on the *goal* (canonical,
queryable). **Final, with one bound:**
- The automated path is **canonical by construction**:
  `parse_verification_response()` only ever returns `"VERIFIED"` or
  `"ISSUES_FOUND"`. The orchestrator writes that token into the
  disposition, so a routine close always persists a canonical token. No
  "garbage" can arrive through the normal path.
- `validate_disposition` treats a present `verification_verdict` whose
  prefix is not `VERIFIED` / `ISSUES_FOUND` as a **warning, not an error**.
- We do **not silently drop or rewrite** a non-canonical value. Reason:
  `session-state-schema.md:219` documents — and this set *keeps* — the
  reader contract that the writer does not enforce an enum and operators
  may ship deliberate extension tokens (`ISSUES_FOUND_RESOLVED_IN_FLIGHT`)
  that carry real mid-session disposition; normalizing-on-write would
  destroy that operator intent and contradict a doc line we are not
  changing. The residual risk (a non-canonical string on disk) is bounded
  to **deliberate hand-edits**, which the existing contract already
  permits and prefix-matching readers already handle.

This is the one place the lock diverges from the reviewer; the rationale is
recorded so S3 verification can weigh it.

### RISKS dispositioned

- **R1 (`--force` erases verdict)** — fixed by the Q2 revision above
  (explicit disposition verdict wins under force).
- **R2 (`skipped` vs `null` inconsistency)** — fixed: there is no
  `"skipped"` (or `"manual"`) verdict token; skipped/manual → `null`.
  Verdict domain is `VERIFIED` / `ISSUES_FOUND` / `null` only.
- **R3 (garbage strings via soft validation)** — bounded, not eliminated;
  see Q3 resolution. Automated source is canonical-by-construction.
- **R4 (idempotent re-close must not clobber a stored verdict)** —
  **ACCEPTED as a first-class invariant** (see below). The existing
  writer guard already provides it; S2 must preserve it and add the
  regression test.

---

## Locked invariant (new, from R4)

> **The close path overwrites `sessions[N].verificationVerdict` only when a
> non-null verdict is threaded.** `_flip_state_to_closed` already writes the
> field only `if verification_verdict is not None`
> (`session_state.py:1201-1202`); the `resolve_close_verdict()` helper
> returning `None` therefore **leaves any previously-stored verdict
> untouched**. Combined with `close_session`'s existing
> `_is_already_closed` short-circuit (returns `noop_already_closed` *before*
> reading the disposition or flipping state, `close_session.py:1298`), a
> re-close or a `--repair --apply` re-flip with a missing/stale disposition
> can never replace a real stored verdict with `null` or a re-derived value.
> S2 must keep both guards and add an explicit regression test.

---

## Final locked dispositions (all 10)

| Q | Decision |
|---|---|
| Q1 | `disposition.verification_verdict` is the sole source. **No `--verdict` flag.** |
| Q2 | Precedence: **explicit verbatim (wins under `--force`) → api-status-derived → `null`.** No force special-case. |
| Q3 | Domain on disk: `VERIFIED` / `ISSUES_FOUND` / `null`. Canonical-by-construction on the automated path; soft-warn (never drop) on non-canonical explicit values. |
| Q4 | **No** blocking gate. Soft stderr note on fallback. No new `GATE_CHECKS` entry. |
| Q5 | manual / `--no-router` → `null` (+ `verification_method=manual` + attestation). **No `"manual"` verdict token.** |
| Q6 | Events carry the **resolved** verdict, omit-null: `verdict=<token>` on `closeout_succeeded`; `verification_completed` drops the hardcoded `"manual_attestation"` for the resolved token (omit when `null`). |
| Q7 | Doc-only (S3): workflow Step 6/8 instruct recording the parsed verdict in the disposition. Verifier template unchanged. `write_disposition` call sites unaffected (optional field). |
| Q8 | **No TS change. PyPI-only.** Extension only reads/derives/preserves the field; no writer originates a verdict; Explorer does not surface it. |
| Q9 | **No backfill.** Historical `null`s accepted (nothing recoverable). |
| Q10 | PyPI `dabbler-ai-router` **minor** bump; additive, backward-compatible. Consumer guidance folds into the URL-referenced workflow doc; no separate notice file. |

---

## Locked change list

**S2 — code (`ai_router/`):**
- `disposition.py`: add `verification_verdict: Optional[str] = None` to
  `Disposition`; (de)serialize in `disposition_to_dict` /
  `disposition_from_dict`; in `validate_disposition`, when present and
  non-empty, **warn** (do not error) if its prefix is not `VERIFIED` /
  `ISSUES_FOUND`. Optional ⇒ old dispositions validate unchanged.
- `close_session.py`: add `resolve_close_verdict(disposition, method)`
  implementing the Q2 precedence; thread its result into
  `_flip_state_to_closed(..., verification_verdict=verdict)`; add `verdict`
  to the `closeout_succeeded` event (**omit-null**); replace the
  `verification_completed` event's `"manual_attestation"` literal with the
  resolved token (omit-null). Emit a one-line soft stderr note when the
  helper derives (rather than reads) the verdict.
- `session_state.py`: no signature change (writer already accepts
  `verification_verdict`); **preserve** the `if ... is not None` overwrite
  guard (the R4 invariant).
- Tests: disposition round-trip + validation (canonical, extension-token
  warning, absent-field); `resolve_close_verdict` for every branch
  (explicit / explicit-under-force / api-completed / api-failed /
  api-requires-review / manual / skipped / force-no-disposition);
  threading lands the token in `sessions[N].verificationVerdict`;
  **R4 regression**: re-close / repair-reflip with missing disposition
  leaves a stored non-null verdict intact; events payload carries the
  resolved verdict and omits it when null.

**S3 — docs + release:**
- `session-state-schema.md:219` — real source (set by `close_session` from
  `disposition.verification_verdict` with the Q2 fallback); keep the
  enum-not-enforced / prefix-match reader clause.
- `session-state-schema.md:994` — `--no-router` records `null` +
  `verification_method=manual` (not `"manual"`).
- `ai-led-session-workflow.md` Step 6/8 — orchestrator records the parsed
  verdict in `disposition.json`; correct the stale `mark_session_complete`
  / orchestrator-clearing prose (locate by content).
- `ai_router/docs/close-out.md` — verdict rows / manual-flag matrix.
- `ai_router/CHANGELOG.md` + set `change-log.md` + `CLAUDE.md` walk;
  `pyproject.toml` minor bump; publish **held** for operator tag-push.

**Out of scope (explicit):** `--verdict` flag · blocking gate · Explorer
verdict badge · TS edits · historical backfill · `verification_method`
taxonomy change · changing the writer's enum-non-enforcement contract.

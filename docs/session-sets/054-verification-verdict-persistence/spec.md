# verificationVerdict Persistence — Audit & Fix Spec

> **Purpose:** `verificationVerdict` in `session-state.json` is **never
> populated by the router's close machinery**. It stays at the `null`
> that `start_session` writes — in this repo and in every consumer that
> closes via `python -m ai_router.close_session`. The Step-6 verifier
> already produces a structured `{"verdict": "VERIFIED" | "ISSUES_FOUND"}`,
> but that value is dropped on the floor at close-out. Wire the verdict
> through the existing `disposition.json` handoff so `close_session`
> persists it, and reconcile the docs that already (falsely) claim this
> works.
> **Created:** 2026-06-02
> **Session Set:** `docs/session-sets/054-verification-verdict-persistence/`
> **Prerequisite:** None (Sets 051 / 052 / 053 are closed).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
```

> Rationale: router-internal Python (the `disposition.json` contract +
> `close_session` wiring) plus doc reconciliation. **No UI behavior
> change in this set** — surfacing the verdict in the Session Set
> Explorer is an explicit non-goal (see below) and would flip
> `requiresUAT`. Quality bar: existing suite stays green, new unit tests
> cover the verdict path, and cross-provider verification blesses the
> verdict-source design before any PyPI release.

---

## Project Overview

### Motivation

A 2026-06-02 trace (operator-reported "verificationVerdict is never
populated in consumer repos") confirmed a real, long-standing gap.
`verificationVerdict` is a per-session v4 field initialized to `null` by
`start_session` and meant to record the end-of-session verification
outcome. The close machinery never writes it.

**Empirical evidence (this repo, Full-tier, dogfoods the router):**

- Sets **049 / 050 / 051** — *every* session closed via `close_session`:
  `verificationVerdict: null`.
- Set **047** — only session 4 is non-null
  (`"ISSUES_FOUND_RESOLVED_IN_FLIGHT"`), and that is a hand-edit (note the
  non-canonical token). The schema doc even cites this hand-edit as if it
  were normal operator behavior — corroborating that the field is, in
  practice, *only* ever set by hand.
- Consumer repos run the identical `close_session.py` via pip, so the
  conclusion holds for them by construction.

**Root cause — three layers:**

1. **The close path drops the verdict.**
   `ai_router/close_session.py` (success path) calls
   `_flip_state_to_closed(session_set_dir, forced=bool(args.force))` —
   it omits the optional `verification_verdict` argument.
   `ai_router/session_state.py:_flip_state_to_closed` only writes the
   field `if verification_verdict is not None`, so it stays `null`.
   `git log -L` confirms this call has been verdict-less since **Set 014
   Session 1** — this is *not* a v4 regression; it never worked.
2. **There is no channel to supply a verdict.** `close_session` has no
   `--verdict` flag, and `disposition.json` — the structured
   verifier→close-out handoff the script reads — has **no verdict field**
   (`ai_router/disposition.py`: only `status` ∈ {completed, failed,
   requires_review} and `verification_method` ∈ {api, manual, skipped}).
   The Step-6 verifier *does* compute `{"verdict": ...}`
   (`ai_router/prompt-templates/verification.md`), but it is never
   captured into the disposition and thus never reaches the state file.
3. **`--no-router` is the same.** It sets a local `method="manual"` and
   emits an event, but never threads a verdict to the flip — despite the
   schema doc claiming it records `verificationVerdict: "manual"`.

**Docs assert behavior the code does not have (must be reconciled):**

- `docs/session-state-schema.md:219` — "Set by `close_session` after gate
  checks." **False.**
- `docs/session-state-schema.md:994` — "`--no-router` … records
  `verificationVerdict: "manual"`." **False.**
- `docs/ai-led-session-workflow.md:353` — describes `mark_session_complete`
  recording the verdict; that is **not** the path `close_session` runs,
  and the surrounding text is also stale (orchestrator-clearing was
  retired in Set 049).

### Confirmed (do NOT re-litigate)

- **Not a v4 regression.** The verdict-less flip call dates to Set 014 S1.
  v4 (Set 047) only formalized the per-session field and documented the
  (unfulfilled) contract.
- **The writer wiring already exists.** `_flip_state_to_closed` accepts
  `verification_verdict` and `mark_session_complete` threads it through.
  The problem is the *caller* (`close_session`) drops it AND there is no
  *source* — not that the state writer is incapable.
- **`mark_session_complete` is not the close path.** Set 014 deliberately
  chose the gate-bypass `_flip_state_to_closed` for `close_session`'s
  success path; re-routing through `mark_session_complete` is out of
  scope (it would re-run the gate the ledger already recorded).
- **The verdict is computed, not missing.** The verifier emits
  `{"verdict": "VERIFIED" | "ISSUES_FOUND", "issues": [...]}`. This set is
  about *capture + persist*, not *compute*.

### Non-goals

- **No `--verdict` CLI flag as the primary mechanism.** A flag re-creates
  the "agent forgot the flag" failure mode the gate checks exist to
  prevent. In-band via `disposition.json` is the recommended source. (A
  flag may be added as an *override* only if S1 explicitly bundles it.)
- **No surfacing of the verdict in the Session Set Explorer** (a
  VERIFIED / ISSUES_FOUND badge). That is a UI change → `requiresUAT`,
  and is a separate follow-on if wanted. Keeps this set UAT-free.
- **No mandatory backfill** of historical `null` verdicts. Most closed
  sets have no verdict recorded anywhere to recover. Optional, S1-gated.
- **No change to the `verification_method` taxonomy** (api / manual /
  skipped). The verdict is orthogonal to the method.

---

## Open design questions (S1 audit)

1. **Verdict source.** Confirm `disposition.verification_verdict`
   (in-band, gate-checkable, durable) as the primary mechanism vs. a
   `--verdict` flag. *(Recommendation: disposition field.)*
2. **Fallback when the field is absent** (old dispositions, or a session
   that didn't write it): derive from `disposition.status`
   (`completed` → `VERIFIED`; `failed` / `requires_review` →
   `ISSUES_FOUND`), or leave `null` and emit a warning? Interaction with
   `verification_method: "skipped"` and `--force`.
3. **Enum vs. free string.** `session-state.md:219` says the writer does
   not enforce an enum and operators have shipped extension tokens
   (`ISSUES_FOUND_RESOLVED_IN_FLIGHT`). Validate as canonical-prefix
   (`VERIFIED*` / `ISSUES_FOUND*`) or accept any non-empty string?
4. **Gate check.** Add `check_verdict_present` (mirroring
   `check_next_orchestrator_present`) so a missing verdict *blocks* close,
   or keep it soft (fall back + warn)? How does it interact with
   `--force` / `--manual-verify` / `skipped` / `--no-router`?
5. **`--no-router` token.** Record `verificationVerdict: "manual"` (per
   the schema doc) or the `--reason-file` text; reconcile with the events
   ledger's existing `verdict="manual_attestation"` string.
6. **Events emission.** Should `closeout_succeeded` (and the manual
   `verification_completed`) carry the *real* verdict instead of the
   placeholder `"manual_attestation"`?
7. **Step-6 workflow change.** The orchestrator must copy the verifier's
   `verdict` into `disposition.json` at verification time. Which doc /
   template, and do `write_disposition` call sites need updating?
8. **TS surface.** Does the extension *write* the verdict anywhere
   (`tools/dabbler-ai-orchestration/src/utils/sessionState.ts` v4 writer
   mirror), or only *read* it for rendering? Confirm the TS change is
   read-only / none (which keeps this PyPI-only).
9. **Backfill.** Reconstruct historical verdicts from the events ledger
   (the manual path recorded some) or accept the existing nulls as
   historical? If backfill, one-shot migrator or leave to `--repair`?
10. **Consumer impact / release.** Confirm a PyPI `dabbler-ai-router`
    minor bump and whether consumer-repo instruction files need a note
    that orchestrators now record the verdict in `disposition.json`.

---

## S1 Audit Lock (2026-06-02)

Session 1 re-verified the 3-layer diagnosis against the current tree and
ran a cross-provider design consensus (reviewer: `gpt-5-4` / OpenAI;
round-1 `CONSENSUS-DISAGREE`, 4 objections, 3 accepted + 1 partial). The
full record is in
`docs/proposals/2026-06-02-verification-verdict-persistence/`
(`proposal.md`, raw `consensus-review.md`, authoritative `verdict.md`).
**`verdict.md` is the locked design; this block is its summary.**

**Headline change from the consensus:** the verdict domain on disk is
**`VERIFIED` / `ISSUES_FOUND` / `null` only** — there is *no* `"manual"` or
`"skipped"` verdict token. Method/provenance stay in `verification_method`
and the attestation event; the verdict field means strictly "the pass/fail
outcome."

**Locked dispositions:**

- **Q1** — sole source is `disposition.verification_verdict`. No `--verdict`
  flag.
- **Q2** — `resolve_close_verdict` precedence: **explicit verbatim (wins
  even under `--force`) → `api`-status-derived
  (`completed`→`VERIFIED`, `failed`/`requires_review`→`ISSUES_FOUND`) →
  `null`.** No `--force` special-case (force bypasses gates, not evidence).
- **Q3** — domain `VERIFIED`/`ISSUES_FOUND`/`null`; canonical *by
  construction* on the automated path (`parse_verification_response` only
  emits those two); `validate_disposition` **warns** (never errors, never
  drops) on a non-canonical explicit value, preserving the documented
  `:219` prefix-match / enum-non-enforcement reader contract.
- **Q4** — no blocking gate; soft stderr note on fallback.
- **Q5** — manual / `--no-router` record `null` (+ `verification_method=
  manual` + attestation), unless an explicit `VERIFIED`/`ISSUES_FOUND` was
  supplied.
- **Q6** — events carry the **resolved** verdict, omit-null
  (`closeout_succeeded.verdict`; `verification_completed` drops the
  hardcoded `"manual_attestation"`).
- **Q7** — doc-only (S3); verifier template unchanged; `write_disposition`
  call sites unaffected (optional field).
- **Q8** — **no TS change; PyPI-only** (extension only reads/derives the
  field; no writer originates a verdict).
- **Q9** — no backfill; historical `null`s accepted.
- **Q10** — PyPI `dabbler-ai-router` minor bump, additive/backward-
  compatible; consumer guidance folds into the URL-referenced workflow doc.

**Locked invariant (R4):** the close path overwrites
`sessions[N].verificationVerdict` **only when a non-null verdict is
threaded** (the writer's existing `if ... is not None` guard); a
re-close/repair-reflip with a missing/stale disposition resolves to `null`
and leaves any stored verdict intact (reinforced by `_is_already_closed`'s
pre-flip short-circuit). S2 keeps both guards + adds the regression test.

**Out of scope (explicit):** `--verdict` flag · blocking gate · Explorer
verdict badge · TS edits · historical backfill · `verification_method`
taxonomy change · changing the writer's enum-non-enforcement contract.

---

## Sessions

### Session 1 of 3: Audit & design-lock

**Steps:**
1. Register the set; re-confirm the diagnosis fresh against current code
   (the Motivation findings are *inputs*, re-verify the file:line claims
   and the `git log -L` origin).
2. Confirm `disposition.json` carries no verdict today and that the
   verifier template emits one; map the exact data path from verifier
   output → disposition → `close_session` → `_flip_state_to_closed`.
3. Cross-provider consensus on the open questions (verdict source,
   fallback semantics, enum vs. free string, gate disposition, events
   emission, backfill, `--no-router` token). Produce `proposal.md` +
   verdict.
4. Lock the exact `disposition` schema + `close_session` + workflow
   change list for S2 and the doc-reconciliation list for S3.

**Creates:** `docs/proposals/2026-06-02-verification-verdict-persistence/proposal.md` + verdict.
**Touches:** this `spec.md` (scope-lock).
**Ends with:** an audit-locked design — verdict source, fallback rule,
gate disposition, events policy, backfill yes/no, TS-surface confirmation.
**Progress keys:** S1 audit verdict committed; change list locked.

### Session 2 of 3: Implement the verdict path

**Steps:**
1. Add `verification_verdict` to the `Disposition` dataclass +
   `disposition_to_dict` / `disposition_from_dict` + `validate_disposition`
   (per S1's enum decision).
2. Thread it through `close_session.run()` →
   `_flip_state_to_closed(..., verification_verdict=...)`, with S1's
   fallback derivation; record S1's token on the `--no-router` path.
3. Update events emission (`closeout_succeeded` / manual
   `verification_completed`) per S1; add `check_verdict_present` if S1
   blessed it.
4. TS parity only if S1 found a TS writer that emits the field.
5. Tests: disposition schema + validation; `close_session` verdict
   threading + fallback + `--no-router` + idempotent re-close; events
   payload. Confirm the suite is green.

**Touches:** `ai_router/disposition.py`, `ai_router/close_session.py`,
`ai_router/session_state.py` (events / flip wiring), `ai_router/gate_checks.py`
(if gate added), tests; `sessionState.ts` only if S1 requires it.
**Ends with:** `close_session` persists the verifier's verdict to
`session-state.json`; suite green.
**Progress keys:** disposition field + threading landed; tests green.

### Session 3 of 3: Workflow, docs, version bump, close-out

**Steps:**
1. Update `docs/ai-led-session-workflow.md` (Step 6 / 8 / 9): orchestrator
   records the verifier's verdict in `disposition.json`; correct the
   stale `mark_session_complete` / orchestrator-clearing language.
2. Reconcile `docs/session-state-schema.md` (lines 219 + 994),
   `ai_router/docs/close-out.md` verdict rows, and any verification
   template note — so the docs match the new code instead of overstating
   it.
3. `ai_router/CHANGELOG.md` + `change-log.md` + `CLAUDE.md` versioning
   walk; PyPI `dabbler-ai-router` minor bump.
4. Cross-provider verification; close-out; publish **held** for
   operator-initiated tag-push (PyPI `v<X.Y.Z>`).

**Creates:** `change-log.md`.
**Touches:** `docs/ai-led-session-workflow.md`, `docs/session-state-schema.md`,
`ai_router/docs/close-out.md`, `ai_router/CHANGELOG.md`, `pyproject.toml`,
`CLAUDE.md`.
**Ends with:** docs reconciled with code; version bumped; publish queued.
**Progress keys:** docs reconciled; version bumped; close-out verdict recorded.

---

## End-of-set deliverables

- `disposition.json` carries `verification_verdict`; the verifier's
  verdict flows through to `session-state.json`'s per-session
  `verificationVerdict` on close.
- `close_session` persists the verdict (with the S1-locked fallback);
  the `--no-router` path records its token.
- (Per S1, if bundled) `check_verdict_present` gate / real-verdict events
  emission / historical backfill.
- Docs reconciled: `session-state-schema.md`, `close-out.md`, and
  `ai-led-session-workflow.md` no longer claim un-implemented behavior.
- `CHANGELOG` + `change-log` + PyPI `dabbler-ai-router` version bump;
  publish held for operator tag-push.

# Proposal — verificationVerdict Persistence

> **Set:** `054-verification-verdict-persistence`, Session 1 (audit & design-lock)
> **Created:** 2026-06-02
> **Author:** Claude Opus 4.8 (orchestrator)
> **Status:** Recommended dispositions for cross-provider consensus, then lock.

This proposal records the **re-verified diagnosis** and a **recommended
disposition for each of the 10 open S1 questions** in `spec.md`. It is the
input to the Session-1 cross-provider consensus; the captured verdict and
the final locked decisions live in `verdict.md` and the scope-lock block
appended to `spec.md`.

---

## 1. Re-verified diagnosis (fresh against current code, 2026-06-02)

All three root-cause layers in the spec's Motivation hold against the
current tree. File:line claims re-confirmed:

**Layer 1 — the close path drops the verdict.**
`ai_router/close_session.py:1621-1623` calls
`_flip_state_to_closed(session_set_dir, forced=bool(args.force))` — the
optional `verification_verdict` argument is omitted. The writer at
`ai_router/session_state.py:998-1000` declares
`verification_verdict: Optional[str] = None` and only assigns the field
`if verification_verdict is not None`
(`session_state.py:1201-1202`), so it stays at the `null` that
`start_session` wrote. Confirmed verdict-less since Set 014 S1 — **not a v4
regression**.

**Layer 2 — there is no channel to supply a verdict.** The `Disposition`
dataclass (`ai_router/disposition.py:95-101`) carries `status`, `summary`,
`verification_method`, `files_changed`, `verification_message_ids`,
`next_orchestrator`, `blockers` — **no verdict field**. `close_session` has
no `--verdict` flag.

**New, load-bearing finding (resolves the spec's "structured `{verdict}`"
overstatement):** the verifier template
(`ai_router/prompt-templates/verification.md`) emits **prose**, not JSON —
it starts with `**VERIFIED**` or `**ISSUES FOUND**` (note the *space*).
But `ai_router/verification.py:201 parse_verification_response()` already
**normalizes** that prose into the canonical token
`"VERIFIED"` / `"ISSUES_FOUND"` (underscore) and returns
`(verdict, issues)`. So the canonical verdict token **already exists in
code** at verification time — it is computed and then dropped on the floor,
never captured into the disposition or the state file. This is the single
most important fact for the design: we are wiring an *existing computed
token* through to persistence, not inventing a verdict.

**Layer 3 — `--no-router` is the same.** The `--no-router` / `--manual-verify`
paths set `method="manual"` and emit a `verification_completed` event with a
hardcoded `verdict="manual_attestation"` (`close_session.py:1480-1489`), but
never thread any verdict to `_flip_state_to_closed`. The schema doc's claim
of `verificationVerdict: "manual"` (`session-state-schema.md:994`) is
therefore **false**.

**Writer wiring already exists.** `mark_session_complete`
(`session_state.py:1279-1281`) accepts `verification_verdict` and threads it
(`:1431`) plus emits `verdict` on its event (`:1395-1396`). The problem is
exclusively the *caller* (`close_session`) + the *missing source* — not the
state writer.

**Doc claims to reconcile (S3):** `session-state-schema.md:219` ("Set by
`close_session` after gate checks" — false), `:994` (`--no-router` records
`"manual"` — false), and the stale `mark_session_complete` /
orchestrator-clearing language in `ai-led-session-workflow.md` (the spec's
`:353` reference has drifted; the actual Step-8 prose is the target — S3
locates it by content, not line number).

---

## 2. Data-path map (verifier → disposition → close → flip)

```
Step 6 verification (orchestrator):
   route(task_type="session-verification")  → raw prose verdict
   parse_verification_response(raw)          → ("VERIFIED"|"ISSUES_FOUND", issues)
                                                       │
Step 8 disposition authoring (orchestrator):           ▼
   Disposition(..., verification_verdict="VERIFIED")  ← NEW field
   write_disposition(dir, disposition)        → disposition.json
                                                       │
close_session.run():                                   ▼
   disposition = read_disposition(dir)
   verdict = resolve_verdict(disposition, method, ...) ← NEW helper (fallback)
   _flip_state_to_closed(dir, forced=..., verification_verdict=verdict)  ← THREAD IT
                                                       │
                                                       ▼
   session-state.json sessions[N].verificationVerdict = "VERIFIED"
   closeout_succeeded event carries verdict=<real>     ← NEW payload field
```

---

## 3. Recommended dispositions (10 open questions)

### Q1 — Verdict source: disposition field (confirm)
**Disposition: LOCK `disposition.verification_verdict` as the sole primary
mechanism. No `--verdict` CLI flag (not even as an override).**
The orchestrator already holds the canonical token from
`parse_verification_response()` and already writes `disposition.json` at
verification time, so the field is the natural, in-band, durable,
gate-checkable channel. A flag re-creates the "agent forgot the flag"
failure mode (spec non-goal). Keep the surface minimal; a flag can be added
later if a real need appears.

### Q2 — Fallback when the field is absent
**Disposition: honest tiered fallback in a new `resolve_close_verdict()`
helper, in this precedence:**
1. `disposition.verification_verdict` present and non-empty → use it
   verbatim.
2. Else if `verification_method == "skipped"` **or** `--force` → leave
   `null`. No verification ran; synthesizing a pass/fail would be
   dishonest.
3. Else if `verification_method == "manual"` (incl. `--manual-verify` /
   `--no-router`) → record `"manual"` (see Q5).
4. Else (`api`, no explicit verdict — e.g. an old disposition) → derive
   from `disposition.status`: `completed` → `"VERIFIED"`;
   `failed` / `requires_review` → `"ISSUES_FOUND"`.

Net effect: `null` survives **only** where verification genuinely produced
no pass/fail signal (skipped / forced). Every real close gets a verdict.

### Q3 — Enum vs free string
**Disposition: soft canonical-prefix validation, NOT a hard enum.**
Canonical tokens are `"VERIFIED"` and `"ISSUES_FOUND"` (underscore —
matching `parse_verification_response()` output), plus the method tokens
`"manual"` / `"skipped"`. `validate_disposition` accepts any non-empty
string whose prefix is `VERIFIED` or `ISSUES_FOUND` (case-insensitive) or
that equals `manual`/`skipped`; anything else is a **warning, not an
error** — preserving the existing writer contract
(`session-state-schema.md:219`: "the writer does not enforce an enum") and
extension tokens like `ISSUES_FOUND_RESOLVED_IN_FLIGHT`. The field is
optional (defaults to `None`), so old dispositions validate unchanged.

### Q4 — Gate check
**Disposition: keep it SOFT. Do NOT add a blocking `check_verdict_present`
gate.** The Q2 fallback always yields a sensible verdict on the real
`api`/`manual` paths, so a missing explicit verdict is recoverable, not a
close-blocking error. A hard gate would (a) re-create the agent-forgot
failure mode the spec rejects for the flag, and (b) wrongly block the
legitimately-null `skipped` / `--force` / `--no-router` paths. Emit a
single soft stderr note when the helper falls back to a derived/`manual`
verdict, mirroring the existing drift-advisory style. No new entry in
`GATE_CHECKS`.

### Q5 — `--no-router` / manual token
**Disposition: state file records `verificationVerdict: "manual"`** on the
`--manual-verify` / `--no-router` paths (greppable, honest, matches the
schema-doc intent). The free-text `--reason-file` narrative stays in the
attestation/event payload — it is **not** dumped into the verdict slot
(the verdict field is for pass/fail bucketing, not prose). An explicit
`disposition.verification_verdict` still wins over `"manual"` if one was
supplied.

### Q6 — Events emission
**Disposition: YES — make the events carry the real verdict.** Add
`verdict=<resolved>` to the `closeout_succeeded` payload (it already
carries `method` + orchestrator identity). Replace the
`verification_completed` event's hardcoded `verdict="manual_attestation"`
with the actual recorded token (`"manual"` or the supplied verdict), so a
forensic walk of `session-events.jsonl` answers "what was the verdict?"
without consulting the snapshot. Omit the key when the resolved verdict is
`null` (skipped/force) — omit-null, consistent with the orchestrator-block
contract.

### Q7 — Step-6 workflow change
**Disposition: doc-only (S3), verifier template unchanged.** Update
`ai-led-session-workflow.md` Step 6 (verification) + Step 8 (disposition
authoring) to instruct the orchestrator to set
`disposition.verification_verdict` to the canonical token from
`parse_verification_response()`. The template already emits the prose the
parser normalizes — no template edit. `write_disposition` call sites are
unaffected: the new field is optional with a default, so every existing
caller stays valid.

### Q8 — TS surface
**Disposition: read-only / NO TS change. Confirmed PyPI-only.** A workspace
sweep shows the extension only *reads/derives/preserves* the field:
`sessionGenPrompt.ts` scaffolds it to `null`; `progress.ts` /
`fileSystem.ts` derive the top-level value from `sessions[]`;
`cancelLifecycle.ts` / `migrateSessionStateV4.ts` carry it across
shape-changes; `types.ts` declares it. **No TS code originates a non-null
verdict** (the extension never closes a session or runs verification). The
Explorer also does not surface it (spec non-goal). So this set ships
**no `.ts` edits** and **no Marketplace release**.

### Q9 — Backfill
**Disposition: NO backfill.** Most historical closes have no verdict
recorded anywhere recoverable — the old `closeout_succeeded` events did not
carry it, and the manual path only ever stored `"manual_attestation"`.
Reconstruction would be fabrication. Accept the existing historical `null`s.
(A future `--repair` could derive verdicts where a real signal exists, but
that is explicitly out of scope here.)

### Q10 — Consumer impact / release
**Disposition: PyPI `dabbler-ai-router` MINOR bump; additive,
backward-compatible.** New optional disposition field + close-out behavior;
no breaking change (old dispositions without the field validate and close
exactly as before, via the Q2 fallback). Consumer instruction: fold the
"record the verifier's verdict in `disposition.json`" guidance into the
canonical `ai-led-session-workflow.md` (Step 6/8), which consumers already
reference by URL — **no separate cross-repo notice file** unless consensus
prefers one. The current schema-doc overstatements get corrected in the
same S3 pass so consumers stop reading un-implemented behavior.

---

## 4. Locked change list (for S2 implement / S3 docs)

**S2 — code (`ai_router/`):**
- `disposition.py`: add optional `verification_verdict: Optional[str] = None`
  to `Disposition`; serialize in `disposition_to_dict` /
  `disposition_from_dict`; soft canonical-prefix check in
  `validate_disposition` (warning-level, never blocks).
- `close_session.py`: add `resolve_close_verdict(disposition, method,
  forced)` helper implementing the Q2 precedence; thread its result into
  `_flip_state_to_closed(..., verification_verdict=verdict)`; add
  `verdict` to the `closeout_succeeded` event (omit-null); replace the
  `verification_completed` event's `"manual_attestation"` literal with the
  resolved token.
- `session_state.py`: no signature change needed (writer already accepts
  `verification_verdict`); confirm the per-session `sessions[N]` write path
  records it.
- Tests: disposition field round-trip + validation (incl. extension token
  + invalid-prefix warning); `close_session` threading for each Q2 branch
  (explicit / api-derived / manual / skipped / force / no-router);
  idempotent re-close keeps the verdict; events payload carries the verdict.

**S3 — docs + release:**
- `session-state-schema.md`: fix `:219` (describe the real source — set by
  `close_session` from `disposition.verification_verdict` with the Q2
  fallback) and `:994` (`--no-router` records `"manual"`, now true).
- `ai-led-session-workflow.md`: Step 6/8 — orchestrator records the
  parsed verdict in `disposition.json`; correct the stale
  `mark_session_complete` / orchestrator-clearing prose.
- `ai_router/docs/close-out.md`: verdict rows / manual-flag matrix.
- `ai_router/CHANGELOG.md` + set `change-log.md` + `CLAUDE.md` version walk;
  `pyproject.toml` minor bump; publish **held** for operator tag-push.

**Out of scope (explicit):** `--verdict` flag, blocking gate, Explorer
verdict badge, TS edits, historical backfill, `verification_method`
taxonomy change.

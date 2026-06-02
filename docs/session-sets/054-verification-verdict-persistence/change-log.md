# Change Log — 054-verification-verdict-persistence

## Summary

Wired the cross-provider verifier's pass/fail outcome through to
`session-state.json`'s per-session `verificationVerdict` field, closing a
long-standing gap (present since Set 014 S1, formalized as a contract in
Set 047, never implemented). The field was initialized to `null` by
`start_session` and remained `null` on every router-closed session across
all consumer repos.

## Root cause (confirmed in S1 audit)

Three compounding layers:

1. `close_session.py` omitted the optional `verification_verdict` arg on its
   `_flip_state_to_closed` call — the writer accepted it but the caller never
   passed it.
2. `Disposition` had no `verification_verdict` field — no channel to supply a
   verdict from the verifier's output to `close_session`.
3. The S1 cross-provider consensus collapsed the `--no-router` verdict to
   `null` (not `"manual"`) — method/provenance live in `verification_method`
   and the attestation event; the verdict field means strictly pass/fail.

## Implementation (S2)

- **`Disposition.verification_verdict`** — new optional field; omit-null on
  disk; non-canonical values warn to stderr (enum-non-enforcement contract
  preserved).
- **`CANONICAL_VERDICTS = ("VERIFIED", "ISSUES_FOUND")`** — module constant.
- **`resolve_close_verdict(disposition)`** — three-level precedence:
  explicit field wins → `api`-status-derived fallback → `null`.
- **`_flip_state_to_closed`** now receives the resolved verdict and writes it
  to `sessions[N].verificationVerdict`.
- **Events**: `closeout_succeeded.verdict` carries the resolved verdict
  (omit-null); `verification_completed` drops the hardcoded
  `"manual_attestation"` string.
- **31 new tests** covering disposition schema, verdict threading, fallback
  derivation, `--no-router` path, idempotent re-close, and event payloads.
  Full suite: 1060 pass.

## Doc reconciliation (S3)

- `docs/session-state-schema.md` — `verificationVerdict` description updated
  (source noted; false `--no-router: "manual"` claim corrected to `null`).
- `docs/disposition-schema.md` — `verification_verdict` field row added.
- `docs/ai-led-session-workflow.md` — Step 6 item 6 (record verdict in
  disposition); Step 8 disposition authoring updated; Lightweight Step 6
  corrected; Rule 16 stale API references fixed.
- `ai_router/docs/close-out.md` — Section 0 table (verdict source; Set 049
  orchestrator-preserve); Section 2 orchestrator paragraph; Section 3 step 9
  (`_flip_state_to_closed`, no orchestrator clear).

## Release

PyPI `dabbler-ai-router 0.15.0`. No VS Code Marketplace release (PyPI-only:
TS surface reads/derives `verificationVerdict` but does not write it).
Publish held for operator-initiated tag-push (`v0.15.0`).

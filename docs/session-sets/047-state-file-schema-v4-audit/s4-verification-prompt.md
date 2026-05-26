# Set 047 Session 4 — Writer-flip phase part 1 (Python) — Cross-Provider Verification

## What you're verifying

Set 047 Session 4 of the v4 state-file schema migration. This session
flipped all Python writers from emitting v3 on-disk shape (top-level
`currentSession` / `totalSessions` / `completedSessions` /
`orchestrator` / `startedAt` / `completedAt` / `verificationVerdict` /
`lifecycleState` derived from `sessions[]`) to emitting v4 on-disk
shape (per-session metadata is authoritative; top-level state
derives at read time via the Session-2 shim
`progress.normalize_to_v4_shape`).

Scope-locked spec: `docs/session-sets/047-state-file-schema-v4-audit/spec.md`
§3.1 (v4 schema shape) and §4 row for Session 4.

## What you're NOT verifying

- The Session-2 shim itself (`normalize_to_v4_shape`) — already verified
  in S2; only minor extensions in S4 (lifecycleState derivation,
  plan-less fallback, completedAt status-gated derivation).
- The Session-3 migrator (`migrate_v3_to_v4`) — already verified in S3.
- TypeScript writers — Session 5 scope.

## The four writer surfaces that changed

1. `register_session_start` (ai_router/session_state.py) — emits v4 with
   per-session orchestrator + startedAt on the in-progress session;
   preserves prior-completed sessions' per-session metadata across the
   rewrite via `_read_prior_v4_metadata`. Same-holder reattach
   detection updated to look at the prior in-progress session's per-
   session orchestrator (NOT the top-level field which v4 drops).
2. `_flip_state_to_closed` (ai_router/session_state.py) — emits v4
   with per-session `completedAt` + `verificationVerdict` on the
   closing session; per-session orchestrator on the just-closed
   session is PRESERVED as a historical record (no more top-level
   orchestrator clear — the H1/H3 check-in semantic is now implicit
   in status moving off `in-progress`).
3. `cancel_session_set` / `restore_session_set`
   (ai_router/session_lifecycle.py) — emit canonical v4 shape with
   the cancellation passthroughs (`preCancelStatus`, `forceClosed`)
   preserved.
4. `_not_started_payload` + `_backfill_payload`
   (ai_router/session_state.py) — emit v4 shape for synth + lazy
   backfill.

## Critical contracts to verify

### V4 on-disk shape (spec §3.1)

The on-disk file MUST have:
- `schemaVersion: 4`
- `sessionSetName`
- `status: "not-started" | "in-progress" | "complete" | "cancelled"`
- `sessions: [{number, title, status, startedAt, completedAt, orchestrator, verificationVerdict}, ...]`

The on-disk file MUST NOT have these top-level keys (the shim
re-derives them at read time):
- `currentSession`, `totalSessions`, `completedSessions`
- `startedAt`, `completedAt`, `verificationVerdict`
- `orchestrator`, `lifecycleState`

Passthrough top-level keys preserved when present:
- `preCancelStatus` (cancellation lifecycle)
- `forceClosed` (forensic FORCED marker)

### V3-input backward compatibility

A consumer that has a legacy v3 file on disk (top-level fields
present, schemaVersion=3 or earlier) must read transparently through
`read_session_state` — the shim's `normalize_to_v4_shape` produces
a derived top-level view that downstream code sees as if it were v3.

The writers (`register_session_start` / `_flip_state_to_closed` /
cancel / restore) accept v3 input and re-emit as v4 — they do NOT
require the input to already be v4.

### Per-session orchestrator semantic

Under v3 the top-level orchestrator block was cleared on every close
(H1/H3 check-in: "released between sessions"). Under v4 the per-
session orchestrator on a CLOSED session is preserved as a
historical record — "who closed which session" is part of the audit
trail. The check-in semantic ("no current holder between sessions")
is now implicit:
- No session is in-progress → the shim's derived top-level
  orchestrator returns `None`.
- The shim deliberately does NOT fall back to last_completed's
  orchestrator when deriving the top-level field — preserving the
  v3 H1/H3 "released" signal for downstream consumers.

### Same-holder reattach (Set 033 H4 + Set 036 Q5)

`register_session_start` reads the EXISTING state's in-progress
session orchestrator (top-level under v3, per-session under v4) to
decide:
- Same `(engine, provider, chatSessionId)` composite → preserve
  `checkedOutAt`, bump `lastActivityAt`.
- Different composite → fresh `checkedOutAt = now`.

The detection works against BOTH v3 input (top-level orchestrator
+ matching top-level currentSession) AND v4 input (per-session
orchestrator on the session_number record with status=in-progress).

### Plan-less carve-out

When the writer cannot determine a session total (no spec.md
`totalSessions`, no `### Session N` headings, no prior state), the
plan-less branch emits a v4 file with:
- `sessions[]` ABSENT (not empty array — absent)
- `orchestrator` + `startedAt` at top level (carve-out passthrough)

The shim recognizes this carve-out: when sessions[] is absent in
input AND status is in-progress, the shim's step-4 fallback uses
top-level orchestrator/startedAt. The derived `totalSessions` is
`None` (not 0) so the Explorer renders "0/?" per Set 046's fix.

## What to evaluate

Read the bundled files in order:

1. `ai_router/session_state.py` — the four writers + v4 helpers.
   Pay attention to:
   - `_read_prior_v4_metadata`, `_apply_v4_per_session_metadata`,
     `_strip_v4_dropped_top_level_keys` helpers.
   - `register_session_start`: same-holder detection, per-session
     metadata application, plan-less branch.
   - `_flip_state_to_closed`: total backfill (raw vs derived),
     metadata preservation, per-session orchestrator preservation,
     v4 on-disk shape composition.
   - `compute_effective_completed_sessions`: new sessions[]
     fallback + raw read.
   - `read_session_state` vs `read_raw_session_state`: the two-tier
     read contract (shim-routed for consumers, raw for writers).
2. `ai_router/session_lifecycle.py` — cancel/restore + the
   `_to_v4_on_disk_shape` projection helper.
3. `ai_router/progress.py` — the shim extensions: lifecycle
   derivation, plan-less totalSessions=None, status-gated
   completedAt, dropped last-completed-orchestrator fallback.
4. `ai_router/tests/test_session_state_v4_writers.py` — new v4
   writer-shape tests.
5. The updated test fixtures in test_session_state_v2/v3.py,
   test_chatsessionid_writer.py, test_checkout_writer.py,
   test_start_session.py, test_start_session_takeover_prompt.py,
   test_close_session_snapshot_flip.py, test_read_status.py,
   test_normalize_v4_shape.py, e2e/fixtures.py,
   e2e/test_register_session_start_regression.py.

## What I want from you

Return a verdict block in this format:

```
VERDICT: VERIFIED | ISSUES_FOUND

[If ISSUES_FOUND, enumerate as numbered must-fix items with
specific file:line references.]

## Critical (must-fix before this session can close)
1. ...

## Important (should-fix but does not block close)
1. ...

## Nice-to-have
1. ...

## Notes
[Any general observations, edge cases worth thinking about, or
follow-up items for Sessions 5-6.]
```

Particularly look for:

- Any case where the v4 writer accidentally re-introduces a v3
  top-level field (the spec §3.1 contract is firm).
- Any case where the writer fails to preserve prior per-session
  metadata across a rewrite (would silently lose audit history).
- The same-holder detection logic — does it correctly handle the
  v3-to-v4 transition window (existing files might be v3 OR v4)?
- The plan-less carve-out — is the contract clear that this is a
  documented exception to the "no top-level state" rule?
- Cancel/restore re-emitting v4 — does the `_to_v4_on_disk_shape`
  projection correctly normalize a legacy v3 input on cancel?
- The shim's deliberate decision to NOT fall back to last_completed
  orchestrator — does this break any downstream consumer the test
  suite covers?
- Test coverage gaps: which v4-emission edge cases are NOT covered
  by `test_session_state_v4_writers.py`?

Cost budget: this session has $9.12 of $10 NTE remaining. One
verification round is fine; don't recurse.

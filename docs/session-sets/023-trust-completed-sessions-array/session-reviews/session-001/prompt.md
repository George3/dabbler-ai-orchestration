# Set 023 Session 1 — ai_router writer fix (union-not-overwrite)

You are an independent verifier reviewing Session 1 of session set
`023-trust-completed-sessions-array` in `dabbler-ai-orchestration`.

## Decisions confirmed (do not re-litigate)

Set 022 (shipped 2026-05-15 as `ai_router 0.2.3` + extension v0.13.12)
made `completedSessions[]` the authoritative progress ledger on both
tiers. Migration of two pre-Set-022 sets on this repo (Set 004,
Set 006) surfaced a regression: `close_session --repair --apply`
Case 1 overwrote a hand-authored `completedSessions[]` with the
events-ledger reconstruction, *dropping* sessions the operator had
declared closed.

Set 023's design (decided 2026-05-15):

1. **Repair's `completedSessions[]` backfill is monotone-up only.**
   Take the union of (a) the snapshot's existing array and (b) the
   events-ledger reconstruction. Never drop a session number the
   operator hand-authored.
2. **Three apply outcomes, three message phrasings:**
   - `backfilled completedSessions=[…]` — snapshot's array was empty/absent.
   - `merged completedSessions=[…] (union of snapshot [...] and events [...])` — snapshot's array existed but differed.
   - `repair preserved completedSessions=[…]` (no rewrite) — snapshot's array already a superset.
3. **Idempotency:** a second `--repair --apply` on a clean shape produces no further snapshot writes.

This session implements those decisions. No new drift case added;
this tightens an existing case's apply behavior.

## Session 1 plan

**Goal:** Make `close_session --repair --apply` Case 1 preserve a
hand-authored `completedSessions[]`. Release as `ai_router 0.2.4`.

**Steps:**

1. Modify `_run_repair` Case 1 apply path in
   `ai_router/close_session.py`: replace the events-ledger
   overwrite with a union computation.
2. Distinguish the three message outcomes (backfilled / merged /
   preserved).
3. Add two regression tests + an idempotency assertion to
   `ai_router/tests/test_close_session_session4.py`.
4. Update `ai_router/docs/close-out.md` Section 5 drift-case-1
   description.
5. Bump to `ai_router 0.2.4`.
6. Cross-provider verification (this round).

## Test results

`python -m pytest ai_router/tests/` → **701 passed** (up from 699
before this session; the 2 new tests landed without regressions).

The two new tests:

- `test_repair_preserves_snapshot_completed_sessions_superset` —
  snapshot has `[1, 2, 3, 4]`, ledger has only forced session-3
  closeout. After `--apply`: snapshot's array preserved verbatim;
  message line includes `preserved completedSessions=[1, 2, 3, 4]`.
- `test_repair_merges_snapshot_completed_sessions_with_events` —
  snapshot has `[2]`, ledger has session-1 closeout. After
  `--apply`: snapshot becomes `[1, 2]`; message line reports the
  union framing explicitly. Plus idempotency assertion: second
  `--apply` produces no further snapshot rewrite.

The existing `test_repair_detects_mixed_mode_drift` continues to
pass — its assertion `completedSessions == [1, 2]` is preserved
under the new union code (existing was empty, so union of {} and
{1, 2} is [1, 2], reported as "backfilled" not "merged").

## Files in this session's commit

```diff
{{DIFF}}
```

## Your verification task

Evaluate per the structured verifier instructions:

1. **Correctness.** Does the union computation match the spec's
   "monotone-up only" framing? Are there shapes where it incorrectly
   *adds* a session number that should not be marked closed (e.g.,
   could the ledger after synthesis include a stale event for an
   unrelated session)? Is the idempotency invariant preserved (a
   second apply on a clean shape doesn't rewrite the snapshot)?

2. **Completeness.** Does the implementation cover all three message
   outcomes the spec enumerates? Is the "preserved" no-rewrite branch
   actually a no-op (no snapshot.write happens, mtime stable)?

3. **Defensive handling.** Does the new `existing_list` filter
   handle malformed snapshot arrays (non-int entries, booleans,
   negative numbers) the same way the previous code did? Does
   `read_session_state` being None still get handled by the
   `or {}` fallback?

4. **Doc/code alignment.** Does the close-out.md Section 5 update
   accurately describe what the code now does?

Output JSON only:

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {
      "category": "Correctness | Completeness | False Positive",
      "severity": "Critical | Major | Minor",
      "description": "...",
      "location": "<file path or section>"
    }
  ]
}
```

# Set 023 Session 1 — Round 1 verification review

**Verifier:** gpt-5-4 · **Verdict:** ISSUES_FOUND · **Cost:** $0.14014
**Elapsed:** 128s · **Tokens:** 7,981 in / 5,929 out

## Issues

### Issue 1 — Correctness (Major)

**Location:** `ai_router/close_session.py` (_run_repair Case 1 completedSessions merge/preserved block)

> The new `existing_list` sanitization changes the preserve/no-rewrite
> decision to operate on a filtered set, not the raw snapshot array.
> With malformed `completedSessions` values, repair can now emit
> `repair preserved completedSessions=[...]` and skip rewriting even
> though `session-state.json` still contains extra invalid entries.
> Example: snapshot `[1, -1]` or `[1, true]` with ledger
> reconstruction `[1]` now takes the preserved branch and leaves the
> malformed authoritative array in place.

**Real bug.** Fixed in round 2: split `existing_raw_list` (the
on-disk literal, used for the rewrite-needed check) from
`existing_clean` (sanitized, used for the union math). Added a
fourth "normalized" message branch for when a malformed array gets
cleaned up. New regression test
`test_repair_normalizes_malformed_snapshot_completed_sessions`
covers the round-1 example exactly.

### Issue 2 — Completeness (Minor)

**Location:** `ai_router/docs/close-out.md` Section 5 drift-case-1

> Section 5 says the repair uses the union of the snapshot's existing
> `completedSessions[]` and the events-ledger reconstruction, but the
> implementation actually unions only a sanitized positive-int subset
> of the snapshot array. The same section also says 'Two apply
> outcomes' while listing three.

**Real finding.** Fixed in round 2: section now enumerates four
outcomes (backfilled / merged / normalized / preserved) and notes
that the union math operates on a sanitized view of the snapshot.

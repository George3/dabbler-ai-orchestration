```markdown
VERDICT: ISSUES_FOUND

## Critical (must-fix before this session can close)
1. `register_session_start` no longer infers the session total from prior **v4** state. The fallback chain still only checks the dropped top-level `totalSessions`, so a prior v4 file with authoritative `sessions[]` but no spec/config/headings is misclassified as “plan-less” (or outright rejected once there are prior completed sessions), even though the prior ledger already proves the total. → Location → `ai_router/session_state.py:602-619` (`effective_total` fallback chain in `register_session_start`) → Fix → before falling through to spec/config/headings, add a raw-v4 fallback: if `existing["sessions"]` is a list, use `len(existing["sessions"])` as `effective_total`.

2. `_not_started_payload` ignores `### Session N` headings and only consults the config-block `totalSessions`, so headings-only specs incorrectly emit the plan-less carve-out. `_backfill_payload` inherits that mistake, which means legacy folders with headings + `activity-log.json` / `change-log.md` can still be backfilled as `not-started` instead of materializing canonical v4 `sessions[]`. → Location → `ai_router/session_state.py:1145-1161` (`_not_started_payload`) and `ai_router/session_state.py:1276-1309` (`_backfill_payload` branches that depend on `base["sessions"]`) → Fix → mirror the same headings fallback used in `register_session_start` when building the not-started base payload, so `sessions[]` is present whenever headings establish a plan.

3. `cancel_session_set` / `restore_session_set` destroy the documented plan-less carve-out. `_to_v4_on_disk_shape` blindly writes `sessions: []` whenever normalization returns an empty list, so a sessions-absent state becomes a zero-session state on disk. For a plan-less in-progress set, cancel→restore also drops the top-level `startedAt` / `orchestrator` needed for the carve-out, so the restored file no longer round-trips to the documented “unknown plan, still attributable” shape. → Location → `ai_router/session_lifecycle.py:197-209` (`_to_v4_on_disk_shape`) → Fix → preserve `sessions` as **absent** when the input had no `sessions[]` and normalization produced an empty ledger; for the in-progress carve-out, also carry top-level `startedAt` / `orchestrator` through cancel/restore so restore returns to the same plan-less shape.

## Important (should-fix but does not block close)
1. The e2e helper named `read_raw_state` is not raw; it calls the shimmed reader, so any e2e test using it cannot detect on-disk v4-shape regressions. → Location → `ai_router/tests/e2e/fixtures.py:486-494` → Fix → use `read_raw_session_state` (or direct JSON file reads) inside `read_raw_state`.

## Nice-to-have
1. Add explicit v4-writer coverage for: (a) `register_session_start(..., total_sessions=None)` with prior v4 `sessions[]` as the only total source, (b) synth/backfill from a headings-only spec with no config block, and (c) plan-less cancel→restore preserving `sessions` absence plus top-level `startedAt` / `orchestrator`.

## Notes
- I did not find a functional regression from the shim’s deliberate removal of the “last completed orchestrator” fallback; the updated tests now assert the derived top-level `orchestrator` is `None` between sessions.
- There is some comment drift in `session_state.py` still describing the old fallback behavior, but that is secondary to the three functional issues above.
```
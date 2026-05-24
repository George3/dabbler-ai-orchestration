REJECTED

*   **Issue:** The `harvest()` implementation does not emit the full event stream for a bound native session, only a `session_start` record. This contradicts the joiner spec. The hardened `read_copilot_session_events` parser is implemented but is not called by `harvest()`, leaving its per-event emission logic unused.
    *   **Location:** `ai_router/joiner/schema.py`, function `harvest()`.
    *   **Fix:** After identifying a `bound` launch (`len(candidates) == 1`), the implementation must iterate through the events of the bound native session (`candidates[0]`) and yield a `HarvestRecord` for each, as described in `joiner-spec.md` §4. This will require adding an `events()` method to the `NativeSession` class that uses the new per-event parsers (like `read_copilot_session_events`). The current logic that emits a `session_start` record for all native sessions (including bound ones) in a separate loop should be adjusted to avoid duplicating the `session_start` event for bound sessions.

*   **Issue:** The join algorithm in `harvest()` uses raw string equality for the engine name, while the spec implies canonicalized comparison to handle vendor variants (e.g., `claude` vs. `claude-code`).
    *   **Location:** `ai_router/joiner/schema.py`, function `harvest()`.
    *   **Fix:** The candidate filtering predicate should use `normalize_engine()` on both the launch record's engine and the native session's engine to ensure a robust join. Change `ns.engine == launch.engine` to `normalize_engine(ns.engine) == normalize_engine(launch.engine)`.

---
### Verification Details

#### A. dabbler-launch wrapper (ai_router/dabbler_launch.py)

1.  **Schema Compliance:** VERIFIED. `build_record()` emits every required field from `joiner-spec.md` §5.1. Nullable fields (`conv_id`, `binding_state`, `tool`, etc.) are correctly emitted as explicit `None`, which serializes to JSON `null`.
2.  **Append+Spawn Order:** VERIFIED. `run_launch()` calls `append_launch_record()` before `spawn_child()`. A crash between the two correctly results in an on-disk launch record that the joiner will see as "unbound," which matches the design intent.
3.  **Headless/Windows:** VERIFIED. For the "headless-only" commitment, `subprocess.run` with default stream inheritance is sufficient and correct on both POSIX and Windows. Complex TTY/console issues are out of scope for S3.
4.  **Engine Validation:** VERIFIED. Rejecting unknown engines at the writer side is the correct strictness. It prevents malformed records from being written, simplifying consumer logic. Normalization is a reader-side concern for the joiner, not a writer-side one.
5.  **--dry-run Flag:** VERIFIED. The flag correctly prevents the subprocess spawn while still writing the record and returning 0, matching its documented purpose.

#### B. Copilot OTel parser hardening (read_copilot_session_events in parsers.py)

1.  **Event Mapping:** VERIFIED. The mapping in `_COPILOT_EVENT_TYPE_TO_HARVEST` correctly implements the `HarvestRecord` schema from `joiner-spec.md` §5.1. Collapsing `turn.start` and `turn.end` into a single `turn` event is consistent with the spec, which does not model turn duration. The implementation matches the contract.
2.  **Sticky Context:** VERIFIED. The sticky context propagation is sound for an event stream. It correctly updates context (cwd, model, etc.) when a `session.start` or other context-bearing event is seen, and applies that context to subsequent events.
3.  **§7 Redaction:** VERIFIED. `_summarize_tool_args` correctly implements the redaction policy from §7. The heuristic keys are reasonable, and the fallback to `arg_keys` prevents leaking raw argument values, which is the primary privacy concern.
4.  **Streaming Contract:** VERIFIED. The function `read_copilot_session_events` uses `yield` within a line-by-line file read loop, correctly honoring the streaming generator contract.
5.  **Preservation of `_read_copilot_events`:** VERIFIED. Preserving the session-level `_read_copilot_events` is correct, as it is used by `scan_copilot_logs` to produce the `NativeSession` summary object needed for the first pass of the join algorithm. The new per-event parser is intended for a second pass after a session is bound (though this is not yet wired up).

#### C. harvest() wire-up (ai_router/joiner/schema.py)

1.  **Join Algorithm:** REJECTED. (See must-fix list). The implementation uses raw engine string equality, not `normalize_engine()`, a deviation from the spec's intent for robust matching.
2.  **Bound Native Emission:** REJECTED. (See must-fix list). The implementation correctly identifies a bound launch but fails to emit the corresponding native session's full event stream as specified in `joiner-spec.md` §4. It emits only a single `session_start` record for every native session, regardless of binding state.
3.  **Free-running Natives:** VERIFIED. The logic correctly emits `session_start` records for native sessions that are not claimed by any launch, matching the spec.
4.  **Filter Application:** VERIFIED. The `workspace_cwd` and `since` filters are applied correctly and consistently to both launches (on `launch_ts`) and natives (on `first_event_ts`) before the join logic is run.

#### D. Test coverage

1.  **Conflict/Join Mode Coverage:** VERIFIED. `test_dabbler_launch_join_e2e.py` explicitly covers the bound, unbound, ambiguous, and free-running cases defined in `joiner-spec.md` §4.
2.  **Wrapper L1 Compromise:** VERIFIED. Using `spawn=False` is a standard and acceptable compromise for L1 unit tests. It sufficiently tests the record-writing logic, which is the wrapper's primary responsibility in S3.
3.  **L2 e2e Completeness:** VERIFIED. The e2e test coverage is sufficient for S3 close-out. It validates the critical path from wrapper-write to joiner-read and binding-state assignment.

#### E. Backward compatibility (LaunchRecord field rename)

1.  **Reader compatibility:** VERIFIED. `scan_launch_log` correctly accepts both the old (`target_backend`, `launch_ts`) and new (`engine`, `ts`) field names, following the robust reader pattern.
2.  **v0 Test Pinning:** VERIFIED. The test pinning the v0 shape is a low-cost safety net that makes the backward-compatibility contract explicit. It is acceptable.

#### F. Cross-cutting / re-question

*   **Log rotation:** Unbounded log growth is tolerable for the expected scale. Log rotation is a valid feature request but not a must-fix for S3.
*   **`tool.call` vs. `tool.invoke`:** Conflating these is a reasonable default in the absence of a clear semantic distinction from the vendor. This is not a bug.
*   **TTY passthrough stub:** Correctly omitted. Adding stubs for deferred features is not required and would be dead code.
*   **`launch_id`:** Correctly included. It is a critical audit and debugging field, establishing a primary key for the launch event, even if the current join algorithm does not use it as a join key. It is not dead weight.
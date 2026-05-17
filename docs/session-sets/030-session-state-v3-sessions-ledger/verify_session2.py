"""Session 2 verification driver — Set 030.

Round A focuses on the Python writer changes in
``ai_router/session_state.py`` (the load-bearing path for
``register_session_start`` and ``_flip_state_to_closed``). Per memory
``feedback_split_large_verification_bundles``, the bundle is kept
focused on the writer functions + their helpers (~700 LOC); the
unchanged ~700 LOC of the same file (lifecycle enum, NextOrchestrator
validator, scaffolding helpers that haven't been touched) is omitted.

Per memory ``feedback_ai_router_route_result_handling``, the
RouteResult is dumped to JSON before any attribute access — past
sessions lost $0.34 on wrapper-crash bugs from accessing fields
directly.

Round A uses task_type='session-verification' which router-config
pins to gpt-5-4 (cross-provider verifier for a Claude orchestrator).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent

def read_files(paths):
    blocks = []
    for p in paths:
        rel = p.relative_to(REPO_ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        blocks.append(f"=== FILE: {rel} ({len(text.splitlines())} LOC) ===\n{text}")
    return "\n\n".join(blocks)


def read_lines(path, ranges):
    """Read a file and return only the requested 1-indexed line ranges.

    ranges: list of (start, end) tuples, inclusive. Returns a single
    string with section headers between non-contiguous slices so the
    verifier can see line numbers when citing issues.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel = path.relative_to(REPO_ROOT).as_posix()
    chunks = []
    for start, end in ranges:
        section = "\n".join(
            f"{i+1:>5}  {lines[i]}" for i in range(start - 1, min(end, len(lines)))
        )
        chunks.append(
            f"--- {rel} lines {start}-{min(end, len(lines))} ---\n{section}"
        )
    total_lines = sum(min(e, len(lines)) - s + 1 for s, e in ranges)
    return f"=== FILE: {rel} ({total_lines} LOC across {len(ranges)} slice(s)) ===\n" + "\n\n".join(chunks)


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


def run_round(label, system_summary, code_block, focus_prompt, out_path):
    print(f"\n{'='*60}\n[{label}] sending verification call...\n{'='*60}")
    result = ai_router.route(
        content=focus_prompt,
        task_type="session-verification",
        context=f"{system_summary}\n\n--- FILES ---\n{code_block}",
        session_set="030-session-state-v3-sessions-ledger",
        session_number=2,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


SYSTEM_SUMMARY = """
Set 030 Session 2 ships the Phase 2 dual-write writers per spec D5.
Writers in ai_router/session_state.py now emit BOTH the canonical v3
`sessions[]` ledger AND the legacy progress triple (currentSession /
totalSessions / completedSessions), with legacy fields derived from
sessions[] via _derive_legacy_fields(). Per spec D6, writer-side
invariant violations raise SessionStateInvariantError (re-exported
from ai_router.progress) BEFORE any file is written — no silent
recovery.

Session 2 deliverables in session_state.py:

1. SCHEMA_VERSION bumped from 2 to 3. _migrate_v1_to_v2_inplace gate
   was changed from `>= SCHEMA_VERSION` to literal `>= 2` so v2 files
   pass through unchanged on read (the v2->v3 promotion is the
   writer's job, not the reader's).

2. New helpers (lines ~150-380):
   - _existing_sessions_records(state) — tolerantly coerces a prior
     sessions[] on disk into SessionRecord objects, carrying titles
     forward across boundary writes.
   - _spec_titles_for_set(dir) — wraps progress.extract_session_titles_from_spec
     to return {number: title}.
   - _build_sessions_array(dir, total, completed_numbers,
     in_progress_number, prior_state) — single source of truth for v3
     sessions[]. Title resolution: prior sessions[] → spec.md →
     generic "Session N". Status assignment: in-progress > complete >
     not-started. Rule 1 validation built in.
   - _derive_legacy_fields(sessions) — derives (currentSession,
     totalSessions, completedSessions) from sessions[]. The ONLY
     materialization path for the legacy triple (spec D5).
   - _validate_sessions_or_raise(sessions, top_status,
     lifecycle_state) — writer-side wrapper around
     progress.validate_invariants. Fail-loud per spec D6.

3. register_session_start updated to dual-write:
   - Computes effective_total (arg > existing state > max-of-spec/completed/N).
   - Builds sessions[] via _build_sessions_array (session N in-progress,
     prior_completed marked complete, rest not-started).
   - Validates via _validate_sessions_or_raise BEFORE writing.
   - Writes v3 sessions[] + derived legacy triple.

4. _flip_state_to_closed updated:
   - Computes new_completed = old completed + currentSession.
   - is_last_session = forced OR (sessions_done AND change_log_present).
   - Under forced=True (incident recovery, spec D6): promotes EVERY
     session in the ledger to complete so rule 7 holds. The v2 writer
     left an internally-inconsistent state on disk in this case
     (top-status complete + currentSession + completedSessions
     missing later sessions); v3 makes the operator's "set is done"
     assertion explicit by reflecting it in sessions[].
   - Validates via _validate_sessions_or_raise BEFORE writing.
   - Writes v3 sessions[] + derived legacy triple.

5. _not_started_payload and _backfill_payload scaffolding helpers
   write v3 sessions[] when totalSessions is known.

Behavior change visible to legacy readers (spec problem statement):
currentSession is now derived strictly from sessions[]: it is the
single in-progress session's number, or null when no session is
in-flight. The v2 ambiguity ("in flight OR most-recently-closed") is
resolved by v3. Tests that asserted "close_session does not advance
currentSession" were updated to assert "currentSession is None after
close" — this is the exact behavior change the spec calls out as
intentional.

Test coverage: full pytest suite is 522 passed + 1 skipped (was 484
pre-Session-2). +38 tests across test_session_state_v2.py (updated
for v3 dual-write shape) and the new test_session_state_v3.py
(dual-write parity, scaffolding writes v3, writer invariant
enforcement, _build_sessions_array unit tests, _derive_legacy_fields
unit tests). TypeScript tsc --noEmit is clean. No production code
outside session_state.py was modified.
""".strip()


FOCUS_PROMPT = """
ROUND A — writer correctness in ai_router/session_state.py.

The 8 invariants the writers must satisfy (from
docs/session-sets/030-session-state-v3-sessions-ledger/spec.md):

  1. sessions[] required and non-empty for any set with a known plan.
  2. session numbers are positive ints, unique, contiguous starting at 1.
  3. At most one session may be 'in-progress'.
  4. No session may be 'complete' if an earlier session is
     'not-started' or 'in-progress'.
  5. Top-level status 'not-started' requires every session to be
     'not-started'.
  6. Top-level status 'in-progress' allows either exactly one
     in-progress session OR a between-sessions state (>=1 complete,
     >=1 not-started, 0 in-progress).
  7. Top-level status 'complete' requires every session to be
     'complete'.
  8. lifecycleState 'closed' pairs with top-level status 'complete' or
     'cancelled' only.

Verify:

A. **Dual-write parity.** Does register_session_start emit sessions[]
   AND legacy fields that are mathematically consistent? Specifically:
   does the on-disk currentSession always equal the single
   in-progress session's number (or None when no session is
   in-progress)? Does on-disk completedSessions always equal the
   sorted list of complete-status session numbers? Does totalSessions
   always equal len(sessions)? Identify any path where these can
   diverge.

B. **_flip_state_to_closed dual-write.** Same parity questions, plus:
   when forced=True triggers is_last_session=True mid-set (e.g., on a
   3-session set, force-close at session 2), does the resulting
   sessions[] have every session marked complete? Does the legacy
   completedSessions reflect [1, 2, 3] (not [1, 2])? Trace the
   `completed_for_array = list(range(1, total_sessions + 1))` branch
   and confirm it's reached on forced incident-recovery and ONLY on
   forced incident-recovery (a natural close at the last session
   should also flip the SET to complete, but only because every
   session was already in new_completed — no all-or-nothing promotion).

C. **Writer-side invariant enforcement.** Does
   _validate_sessions_or_raise run BEFORE the file is written in both
   register_session_start and _flip_state_to_closed? Identify any
   error path where the file gets written before validation, leaving
   an invalid state on disk. (Spec D6: fail loud, no silent recovery.)

D. **Title carry-forward.** _build_sessions_array's title resolution
   order is (1) existing sessions[] in prior_state, (2) spec.md
   headings via _spec_titles_for_set, (3) generic 'Session N'.
   Confirm titles already in prior_state survive across boundary
   writes — particularly the case where spec.md is renamed AFTER the
   first register_session_start (the original title must stick).

E. **Backfill on legacy v2 state files.** When register_session_start
   runs on a state file that was last written under v2 (no sessions[]
   on disk), does the effective_total fallback chain land on the
   right value? Trace:
   1. `total_sessions` argument (caller-supplied)
   2. existing `totalSessions` field on disk
   3. max(spec_titles.keys(), max(prior_completed), session_number)
   Identify any v2 file shape where this chain produces a total
   that's smaller than what the resulting sessions[] needs.

F. **Scaffolding writes.** Does _not_started_payload correctly omit
   sessions[] when totalSessions is unknown (no spec.md or no
   numeric totalSessions)? Per rule 1, "any set with a known plan"
   — a not-started set with no plan should not carry a (possibly
   empty) sessions[] array; rule 1 guards against an empty
   sessions[] specifically. Does _backfill_payload's change-log
   branch promote EVERY session in the array to complete (not just
   the highest-numbered one)? Does the activity-log-only branch
   correctly assume session 1 is in-progress?

G. **forced=True semantics.** The new incident-recovery semantic
   says "operator asserts the SET is done; promote all sessions to
   complete." Identify any operator-visible interaction this breaks
   that the v2 writer didn't break. Specifically: if the operator
   uses --force on session 2 of 5 and then later wants to RESUME
   sessions 3-5, can they? (Hint: the state would now be top-status
   complete + lifecycleState closed; register_session_start of
   session 3 against that state would have to handle "set is
   already complete.")

H. **Idempotent close.** Re-running mark_session_complete on a
   session that's already complete (currentSession was just closed,
   then close runs again before the next start) — does the writer
   produce a consistent state? The builder's `completed_numbers`
   set already includes currentSession, so the array doesn't change
   on re-run. Confirm this matches what the v2 writer did, with no
   regression in idempotency.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues with line numbers>.

Cite specific line numbers when flagging issues. Skip stylistic
nits. Focus on correctness — does the writer's on-disk output
satisfy the 8 invariants under every input shape the writer
accepts?
""".strip()


def main():
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    # Round B uses the same slice ranges since the same lines were
    # edited (the Round A fixes are localized to register_session_start,
    # _flip_state_to_closed, and _build_sessions_array).
    if len(sys.argv) > 1 and sys.argv[1] == "round-b":
        slices = [
            (1, 93),       # docstring + imports + SCHEMA_VERSION = 3
            (181, 407),    # _state_path + helpers including new
                           # out-of-range rejection in _build_sessions_array
            (408, 606),    # register_session_start (reordered:
                           # validate first, then event, then snapshot)
            (701, 896),    # _flip_state_to_closed (forced/natural paths
                           # split, totalSessions hard-requirement)
            (1067, 1100),  # _migrate_v1_to_v2_inplace (unchanged from
                           # Round A; included for context)
            (1214, 1295),  # _not_started_payload + synthesize_not_started_state
            (1376, 1450),  # _backfill_payload
        ]
        code_block = read_lines(
            REPO_ROOT / "ai_router" / "session_state.py", slices,
        )
        focus = (
            "ROUND B — confirm the four Round-A must-fix issues are "
            "addressed in the updated ai_router/session_state.py.\n\n"
            "Round A REJECTED with:\n"
            "  1. Silent truncation of out-of-range session numbers in "
            "_build_sessions_array; register_session_start trusting a "
            "smaller totalSessions.\n"
            "  2. _flip_state_to_closed promoting every session to "
            "complete on natural last-session close (not just under "
            "forced=True).\n"
            "  3. Unvalidated legacy-only fallback write in "
            "_flip_state_to_closed when totalSessions stays unknown.\n"
            "  4. work_started event appended before invariant "
            "validation in register_session_start, leaving the events "
            "ledger ahead of the snapshot on validation failure.\n\n"
            "For each issue, confirm:\n"
            "  - The fix is present at the cited locations.\n"
            "  - The fix doesn't introduce a new contradiction (e.g., "
            "rejecting valid mid-set inputs that the v2 writer "
            "accepted, or losing event-write ordering on the success "
            "path).\n"
            "  - The fix is consistent with spec D6 (fail loud, never "
            "silently recover).\n\n"
            "Additionally, look for any new issue introduced by the "
            "fixes that wasn't present in Round A. Report each as a "
            "must-fix bullet OR as a nice-to-have note.\n\n"
            "Verdict format:\n"
            "  - VERIFIED: all four Round A issues addressed; no new "
            "issues. (Nice-to-have notes optional.)\n"
            "  - REJECTED: <bulleted list of remaining issues or new "
            "issues with line numbers>.\n\n"
            "Skip stylistic nits. Cite specific line numbers."
        )
        run_round(
            "Round B",
            SYSTEM_SUMMARY
            + "\n\n--- Round B context ---\nRound A returned REJECTED "
            "with 4 must-fix issues. All four have been addressed in "
            "the updated session_state.py. Round B is the confirmation "
            "pass: verify the fixes are correct and no new issues were "
            "introduced.",
            code_block,
            focus,
            out_dir / "round-b-session-2-result.json",
        )
    elif len(sys.argv) > 1 and sys.argv[1] == "round-a":
        # Focused slice of session_state.py — only the lines Session 2
        # touched. Pinned with line numbers so the verifier can cite
        # precisely. Total ~770 LOC, under the gpt-5-4 read-bundle
        # ceiling (per memory feedback_split_large_verification_bundles).
        slices = [
            (1, 93),       # docstring + imports + SCHEMA_VERSION = 3
            (181, 380),    # _state_path + Session 2 helpers (_existing_sessions_records,
                           # _spec_titles_for_set, _build_sessions_array,
                           # _derive_legacy_fields, _validate_sessions_or_raise)
            (381, 536),    # register_session_start (full new body)
            (631, 813),    # _flip_state_to_closed (full new body)
            (984, 1017),   # _migrate_v1_to_v2_inplace (gate change to literal 2)
            (1131, 1213),  # _not_started_payload + synthesize_not_started_state
            (1293, 1367),  # _backfill_payload
        ]
        code_block = read_lines(
            REPO_ROOT / "ai_router" / "session_state.py", slices,
        )
        run_round(
            "Round A",
            SYSTEM_SUMMARY,
            code_block,
            FOCUS_PROMPT,
            out_dir / "round-a-session-2-result.json",
        )
    else:
        print("Usage: python verify_session2.py round-a", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

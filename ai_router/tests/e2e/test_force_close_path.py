"""End-to-end force-close path scenarios.

Tests the ``--force`` close-out bypass, covering three sub-scenarios:

1. **Guard test**: ``--force`` is rejected when
   ``AI_ROUTER_ALLOW_FORCE_CLOSE_OUT`` is not set. Asserts not only
   the error exit but also that state and events are untouched.

2. **Force-close on non-final session**: ``--force`` short-circuits
   ``is_last_session = True`` (``session_state._flip_state_to_closed``
   line 437) regardless of session count. Flips set to
   ``status: "complete"`` immediately. Events ledger records
   ``closeout_force_used`` pinned to the forced session.

3. **Force-close on final session**: exercises the same forensic markers
   on the literal last session of a set.

Note: the conftest ``_scrub_force_close_env`` autouse fixture ensures
``AI_ROUTER_ALLOW_FORCE_CLOSE_OUT`` is absent in every test. Force
tests that need the variable must inject it via
``drive_close_session(..., force=True)``, which calls
``env.pop("AI_ROUTER_ALLOW_FORCE_CLOSE_OUT")`` then sets it only when
``inject_force_env=True``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import (  # type: ignore[import-not-found]
    drive_close_session,
    drive_start_session,
    make_activity_log_entry,
    make_change_log,
    make_disposition,
    make_session_set,
    read_events,
    read_state,
)


pytestmark = pytest.mark.e2e


def test_force_close_rejected_without_env_var(tmp_path: Path) -> None:
    """--force is rejected unless AI_ROUTER_ALLOW_FORCE_CLOSE_OUT=1 is set.

    Confirms: (a) non-zero exit and error references the env-var name;
    (b) state is unchanged after the failed invocation (no forceClosed,
    no status flip, same currentSession); (c) events ledger has no
    force-related entries.
    """
    handle = make_session_set(
        tmp_path, slug="harness-force-guard", total_sessions=2
    )
    drive_start_session(handle, 1)

    state_before = read_state(handle)
    events_before = read_events(handle)

    proc = drive_close_session(
        handle,
        1,
        force=True,
        inject_force_env=False,
        commit_after=False,
    )
    assert proc.returncode != 0, (
        "expected non-zero exit when --force is used without env var"
    )
    combined = proc.stdout + proc.stderr
    assert "AI_ROUTER_ALLOW_FORCE_CLOSE_OUT" in combined, (
        f"expected env-var name in output; got stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )

    # State must be unchanged after a rejected close-out.
    state_after = read_state(handle)
    assert state_after.get("status") == "in-progress", (
        f"state.status should still be 'in-progress'; got {state_after.get('status')!r}"
    )
    assert state_after.get("currentSession") == 1
    assert not state_after.get("forceClosed"), "forceClosed must not be set"

    # Events ledger must not have any force-close entries.
    events_after = read_events(handle)
    assert len(events_after) == len(events_before), (
        "events ledger must not have new entries after a rejected close-out"
    )
    assert not any(e.event_type == "closeout_force_used" for e in events_after)
    assert not any(
        e.event_type == "closeout_succeeded" and e.session_number == 1
        for e in events_after
    )


def test_force_close_nonfinal_session(tmp_path: Path) -> None:
    """force-close on a non-final session flips status to complete immediately.

    Scenario: 3-session set. Session 1 normal. Session 2 force-closed
    WITHOUT a prior disposition (gates bypassed). Close-out must succeed,
    write ``forceClosed: true``, flip status to ``complete``, and record
    ``closeout_force_used`` pinned to session 2.
    """
    handle = make_session_set(
        tmp_path, slug="harness-force-nonfinal", total_sessions=3
    )

    # Session 1: normal run.
    drive_start_session(handle, 1)
    make_activity_log_entry(handle, 1)
    make_disposition(handle, 1, is_final=False)
    proc = drive_close_session(handle, 1)
    assert proc.returncode == 0, (
        f"close_session N=1: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert read_state(handle).get("completedSessions") == [1]

    # Capture session 1's events so we can verify history stability.
    events_after_s1 = read_events(handle)

    # Session 2: start, force-close without disposition.
    drive_start_session(handle, 2)
    state = read_state(handle)
    assert state.get("currentSession") == 2
    assert state.get("status") == "in-progress"

    proc = drive_close_session(handle, 2, force=True)
    assert proc.returncode == 0, (
        f"force close-session N=2: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )

    state = read_state(handle)

    # Forensic marker.
    assert state.get("forceClosed") is True, (
        f"expected forceClosed: true in state; got {state!r}"
    )
    # --force short-circuits is_last_session, so status flips to complete.
    assert state.get("status") == "complete", (
        f"expected status='complete'; got {state.get('status')!r}"
    )
    assert state.get("lifecycleState") == "closed"
    assert state.get("completedAt") is not None
    # Set 030 Session 2: forced-incident-recovery promotes every
    # session in the v3 ``sessions[]`` ledger to ``complete`` so rule 7
    # (top-status complete ⟹ every session complete) holds by
    # construction. The legacy ``completedSessions`` is derived from
    # ``sessions[]`` per spec D5, so it reflects [1, 2, 3] for the
    # 3-session set even though only sessions 1 and 2 went through
    # the work-and-close cycle. The ``closeout_force_used`` event
    # below preserves the forensic record of WHICH session triggered
    # the force.
    assert state.get("completedSessions") == [1, 2, 3], (
        f"expected completedSessions=[1, 2, 3] under v3 forced-recovery "
        f"semantics (operator asserts the SET is done); got "
        f"{state.get('completedSessions')!r}"
    )
    # v3 ledger reflects the operator's "set is done" assertion.
    sessions = state.get("sessions")
    assert isinstance(sessions, list)
    assert all(s["status"] == "complete" for s in sessions), (
        f"expected every session in sessions[] to be complete; got {sessions!r}"
    )

    # Events ledger: closeout_force_used pinned to session 2.
    events = read_events(handle)
    force_events = [e for e in events if e.event_type == "closeout_force_used"]
    assert len(force_events) == 1, (
        f"expected 1 closeout_force_used event; got "
        f"{[(e.session_number, e.event_type) for e in events]!r}"
    )
    assert force_events[0].session_number == 2, (
        f"closeout_force_used should be for session 2; got {force_events[0].session_number!r}"
    )

    # Session 1's work_started and closeout_succeeded must still be intact.
    s1_ws = [e for e in events if e.event_type == "work_started" and e.session_number == 1]
    s1_cs = [e for e in events if e.event_type == "closeout_succeeded" and e.session_number == 1]
    assert len(s1_ws) == 1, f"session 1 work_started missing after force; events={events!r}"
    assert len(s1_cs) == 1, f"session 1 closeout_succeeded missing after force; events={events!r}"

    # force-close produces its own closeout_succeeded.
    s2_cs = [e for e in events if e.event_type == "closeout_succeeded" and e.session_number == 2]
    assert len(s2_cs) == 1


def test_force_close_final_session(tmp_path: Path) -> None:
    """force-close on the literal last session writes the same forensic markers.

    Scenario: 2-session set. Session 1 normal. Session 2 is both the
    final session AND force-closed (so both the mathematical and the
    force short-circuits would flip status; verify the markers still land).
    """
    handle = make_session_set(
        tmp_path, slug="harness-force-final", total_sessions=2
    )

    # Session 1: normal run.
    drive_start_session(handle, 1)
    make_activity_log_entry(handle, 1)
    make_disposition(handle, 1, is_final=False)
    proc = drive_close_session(handle, 1)
    assert proc.returncode == 0
    assert read_state(handle).get("completedSessions") == [1]

    # Session 2: final session, force-closed without disposition or change-log.
    drive_start_session(handle, 2)
    proc = drive_close_session(handle, 2, force=True)
    assert proc.returncode == 0, (
        f"force close-session (final) N=2: stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )

    state = read_state(handle)
    assert state.get("forceClosed") is True
    assert state.get("status") == "complete"
    assert state.get("lifecycleState") == "closed"
    assert state.get("completedSessions") == [1, 2]

    events = read_events(handle)
    force_events = [e for e in events if e.event_type == "closeout_force_used"]
    assert len(force_events) == 1
    assert force_events[0].session_number == 2

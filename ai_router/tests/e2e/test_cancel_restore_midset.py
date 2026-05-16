"""End-to-end cancel/restore mid-set scenario.

A 4-session set runs sessions 1 and 2 to completion, then is cancelled
mid-session-3 via the production ``cancel_session_set`` helper (the
same code path triggered by the VS Code "Cancel lifecycle" command).
The set is subsequently restored and driven through sessions 3 and 4
to a normal close-out.

Key invariants asserted:

* After cancel: ``CANCELLED.md`` present, ``RESTORED.md`` absent,
  ``state.status == "cancelled"``, ``state.preCancelStatus`` captures
  the pre-cancel status.
* After restore: ``CANCELLED.md`` absent (renamed to ``RESTORED.md``),
  ``state.status`` is restored from ``preCancelStatus``,
  ``preCancelStatus`` is cleared.
* After the full 4-session run: ``completedSessions == [1, 2, 3, 4]``,
  ``status == "complete"``, ``RESTORED.md`` still present as the
  audit-trail artifact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import (  # type: ignore[import-not-found]
    cancel_set,
    drive_close_session,
    drive_start_session,
    make_activity_log_entry,
    make_change_log,
    make_disposition,
    make_session_set,
    read_events,
    read_state,
    restore_set,
)
from session_lifecycle import is_cancelled, was_restored  # type: ignore[import-not-found]


pytestmark = pytest.mark.e2e


def test_cancel_restore_midset(tmp_path: Path) -> None:
    total = 4
    handle = make_session_set(
        tmp_path, slug="harness-cancel-restore", total_sessions=total
    )

    # Sessions 1-2: normal run through to close.
    for n in (1, 2):
        drive_start_session(handle, n)
        make_activity_log_entry(handle, n)
        make_disposition(handle, n, is_final=False)
        proc = drive_close_session(handle, n)
        assert proc.returncode == 0, (
            f"close_session failed for N={n}: stdout={proc.stdout!r} "
            f"stderr={proc.stderr!r}"
        )

    assert read_state(handle).get("completedSessions") == [1, 2]

    # Session 3: start, then cancel before any close-out.
    drive_start_session(handle, 3)
    state = read_state(handle)
    assert state.get("status") == "in-progress"
    assert state.get("currentSession") == 3
    pre_cancel_status = state.get("status")  # "in-progress"

    cancel_set(handle, reason="pausing for business reasons")

    # After cancel: CANCELLED.md present, RESTORED.md absent.
    assert is_cancelled(str(handle.set_dir)), "is_cancelled() should return True"
    assert (handle.set_dir / "CANCELLED.md").is_file()
    assert not (handle.set_dir / "RESTORED.md").is_file()

    state = read_state(handle)
    assert state.get("status") == "cancelled"
    assert state.get("preCancelStatus") == pre_cancel_status, (
        f"preCancelStatus should capture '{pre_cancel_status}'; "
        f"got {state.get('preCancelStatus')!r}"
    )

    # Restore: rename CANCELLED.md → RESTORED.md, restore prior status.
    restore_set(handle, reason="back on track")

    assert not is_cancelled(str(handle.set_dir)), "is_cancelled() should return False after restore"
    assert was_restored(str(handle.set_dir)), "was_restored() should return True"
    assert (handle.set_dir / "RESTORED.md").is_file()
    assert not (handle.set_dir / "CANCELLED.md").is_file()

    state = read_state(handle)
    assert state.get("status") == "in-progress", (
        f"status after restore should be 'in-progress'; got {state.get('status')!r}"
    )
    assert "preCancelStatus" not in state, (
        f"preCancelStatus should be cleared after restore; state={state!r}"
    )

    # Complete session 3 from the restored in-progress state.
    make_activity_log_entry(handle, 3)
    make_disposition(handle, 3, is_final=False)
    proc = drive_close_session(handle, 3)
    assert proc.returncode == 0, (
        f"close_session failed for N=3 after restore: stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )
    assert read_state(handle).get("completedSessions") == [1, 2, 3]

    # Session 4: final session closes out the set.
    drive_start_session(handle, 4)
    make_activity_log_entry(handle, 4)
    make_disposition(handle, 4, is_final=True)
    make_change_log(handle, final_session_number=4)
    proc = drive_close_session(handle, 4)
    assert proc.returncode == 0, (
        f"close_session failed for N=4: stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )

    state = read_state(handle)
    assert state.get("completedSessions") == [1, 2, 3, 4]
    assert state.get("status") == "complete"
    assert state.get("lifecycleState") == "closed"
    assert state.get("completedAt") is not None

    # RESTORED.md is the permanent audit-trail artifact; CANCELLED.md was
    # renamed on restore and does not reappear.
    assert (handle.set_dir / "RESTORED.md").is_file()
    assert not (handle.set_dir / "CANCELLED.md").is_file()

    # Events ledger should record all four sessions' work_started and
    # closeout_succeeded entries without corruption from the cancel/restore.
    events = read_events(handle)
    for s in (1, 2, 3, 4):
        ws = [e for e in events if e.event_type == "work_started" and e.session_number == s]
        cs = [e for e in events if e.event_type == "closeout_succeeded" and e.session_number == s]
        assert len(ws) == 1, f"expected 1 work_started for session {s}; got {ws!r}"
        assert len(cs) == 1, f"expected 1 closeout_succeeded for session {s}; got {cs!r}"

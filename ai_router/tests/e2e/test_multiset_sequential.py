"""Three session sets driven sequentially inside one git repo.

All three sets live under the same ``docs/session-sets/`` root and
share the same git history. They are driven to completion in order:
A → B → C. After each set completes, the test asserts that the *other*
sets' state files are untouched (boundary-write hygiene: closing set A
must not mutate B's or C's state file).

Session counts mirror the operator's design-conversation framing (3,
4, and 3 sessions) so the fixture exercises the unequal-total-sessions
case in a single run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import json

from fixtures import (  # type: ignore[import-not-found]
    drive_close_session,
    drive_start_session,
    make_activity_log_entry,
    make_additional_set,
    make_change_log,
    make_disposition,
    make_session_set,
    read_state,
)


pytestmark = pytest.mark.e2e


def _read_raw_state(handle) -> dict:
    """Read session-state.json bytes without the schema-migration layer.

    Used for boundary-hygiene snapshots so we compare exactly what is
    on disk — if a session-set's state file is not touched, the raw dict
    must be identical byte-for-byte (modulo JSON key ordering which
    json.loads normalises). Any in-memory migration by read_state() that
    doesn't write back to disk would produce a false mismatch.
    """
    p = handle.set_dir / "session-state.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _drive_set_to_completion(handle, total: int) -> None:
    """Drive *handle* through *total* sessions to a normal close-out."""
    for n in range(1, total + 1):
        is_final = n == total
        drive_start_session(handle, n)
        make_activity_log_entry(handle, n)
        make_disposition(handle, n, is_final=is_final)
        if is_final:
            make_change_log(handle, final_session_number=n)
        proc = drive_close_session(handle, n)
        assert proc.returncode == 0, (
            f"close_session failed for set={handle.slug} N={n}: "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )


def test_multiset_sequential_boundary_hygiene(tmp_path: Path) -> None:
    # Three sets in the same repo.
    ha = make_session_set(tmp_path, slug="harness-multi-a", total_sessions=3)
    hb = make_additional_set(ha, "harness-multi-b", 4)
    hc = make_additional_set(ha, "harness-multi-c", 3)

    # Before any work: all three are not-started.
    assert read_state(ha).get("status") == "not-started"
    assert read_state(hb).get("status") == "not-started"
    assert read_state(hc).get("status") == "not-started"

    # Snapshot the full on-disk state of B and C before driving A.
    # After A completes, the snapshots must be byte-for-byte identical —
    # a regression that rewrites another set while preserving status alone
    # (e.g. touches currentSession or lifecycle fields) would still fail.
    snapshot_b = _read_raw_state(hb)
    snapshot_c = _read_raw_state(hc)

    # Drive set A to completion; B and C must be completely untouched.
    _drive_set_to_completion(ha, 3)
    assert read_state(ha).get("status") == "complete"
    assert _read_raw_state(hb) == snapshot_b, (
        "completing set A must not mutate set B's state file"
    )
    assert _read_raw_state(hc) == snapshot_c, (
        "completing set A must not mutate set C's state file"
    )

    # Snapshot C before driving B; also re-confirm A's final state.
    snapshot_c2 = _read_raw_state(hc)
    snapshot_a_done = _read_raw_state(ha)

    # Drive set B to completion; A must stay unchanged, C must be untouched.
    _drive_set_to_completion(hb, 4)
    assert read_state(hb).get("status") == "complete"
    assert _read_raw_state(hc) == snapshot_c2, (
        "completing set B must not mutate set C's state file"
    )
    assert _read_raw_state(ha) == snapshot_a_done, (
        "completing set B must not mutate set A's state file"
    )

    # Drive set C to completion.
    _drive_set_to_completion(hc, 3)
    assert read_state(hc).get("status") == "complete"

    # Final state: all three complete with correct completedSessions.
    assert read_state(ha).get("completedSessions") == [1, 2, 3]
    assert read_state(hb).get("completedSessions") == [1, 2, 3, 4]
    assert read_state(hc).get("completedSessions") == [1, 2, 3]

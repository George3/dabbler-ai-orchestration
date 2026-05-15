"""Set 023 Session 3 regression: ``print_session_set_status`` count
derivation must consult ``completedSessions[]`` (via the canonical
``compute_effective_completed_sessions`` helper), not the pre-Set-022
activity-log distinct-sessionNumber shape.

Failure shape the test pins:

A Full-tier set in the in-flight window — currentSession=2, session 1
closed, session 2 in flight — has activity-log entries for both
sessions 1 and 2. The pre-Set-022 derivation
``len({entry.sessionNumber for entry in entries})`` counts the
in-flight session 2 as completed, reporting 2/N. The Set 022 invariant
(``completedSessions[]`` is authoritative) and the TypeScript reader
both report 1/N. This test asserts the Python CLI agrees.

Mirror of the migration Set 022 Session 2 applied to the TypeScript
``readSessionSets``: "Activity log is a step log, not a count source."
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_ai_router():
    """Load ``ai_router`` from its package directory via importlib."""
    init = REPO_ROOT / "ai_router" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "ai_router_for_print_count_test",
        str(init),
        submodule_search_locations=[str(init.parent)],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ai_router_for_print_count_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ar():
    return _load_ai_router()


def _capture(ar, base_dir: Path) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        ar.print_session_set_status(str(base_dir))
    return buf.getvalue()


def test_in_flight_session_does_not_inflate_count(ar, tmp_path: Path) -> None:
    """A set with currentSession=2 (session 1 closed, session 2 in
    flight) reports 1/4 — not 2/4. The activity-log records both
    session numbers as having steps, but only session 1 is in
    ``completedSessions[]``.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "in-flight-shape"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 4,
            "entries": [
                {"dateTime": "2026-05-15T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-15T08:30:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-15T09:00:00-04:00", "sessionNumber": 2},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "in-progress",
            "currentSession": 2,
            "totalSessions": 4,
            "completedSessions": [1],
            "startedAt": "2026-05-15T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    assert "1/4" in out, out
    assert "2/4" not in out, out


def test_legacy_set_without_array_falls_back_via_helper(
    ar, tmp_path: Path
) -> None:
    """A pre-Set-022 set with no ``completedSessions[]`` and no events
    ledger falls through ``compute_effective_completed_sessions``'s
    last-resort ``currentSession - 1`` heuristic. currentSession=3 →
    sessions_completed=2, rendered as 2/5.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "legacy-no-array"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 5,
            "entries": [
                {"dateTime": "2026-05-10T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-11T08:00:00-04:00", "sessionNumber": 2},
                {"dateTime": "2026-05-12T08:00:00-04:00", "sessionNumber": 3},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "in-progress",
            "currentSession": 3,
            "totalSessions": 5,
            "startedAt": "2026-05-10T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    # Helper fallback: sessions_completed = currentSession - 1 = 2.
    assert "2/5" in out, out


def test_events_ledger_fallback_when_array_absent(
    ar, tmp_path: Path
) -> None:
    """Round-1 verifier finding: when the snapshot lacks
    ``completedSessions[]`` BUT a ``session-events.jsonl`` is present
    with `closeout_succeeded` events, the helper's events-ledger
    fallback supplies the count — not the activity-log distinct-
    sessionNumber count, not the last-resort `currentSession - 1`
    heuristic.

    Fixture: snapshot has currentSession=3, totalSessions=4, no
    ``completedSessions[]``. Events ledger records `closeout_succeeded`
    for sessions 1 and 2. Activity log records steps for sessions 1, 2,
    and 3 (session 3 is in flight). Expected count: 2 (from events
    ledger), not 3 (from activity-log distinct), not 2 from the
    last-resort heuristic (which would also produce 2, but via a
    different code path that emits a stderr warning the events-ledger
    branch suppresses).
    """
    base = tmp_path / "session-sets"
    set_dir = base / "events-fallback"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "session-events.jsonl").write_text(
        "\n".join([
            json.dumps({
                "timestamp": "2026-05-10T08:00:00.000000Z",
                "session_number": 1,
                "event_type": "work_started",
            }),
            json.dumps({
                "timestamp": "2026-05-10T09:00:00.000000Z",
                "session_number": 1,
                "event_type": "closeout_succeeded",
            }),
            json.dumps({
                "timestamp": "2026-05-11T08:00:00.000000Z",
                "session_number": 2,
                "event_type": "work_started",
            }),
            json.dumps({
                "timestamp": "2026-05-11T09:00:00.000000Z",
                "session_number": 2,
                "event_type": "closeout_succeeded",
            }),
            json.dumps({
                "timestamp": "2026-05-12T08:00:00.000000Z",
                "session_number": 3,
                "event_type": "work_started",
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 4,
            "entries": [
                {"dateTime": "2026-05-10T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-11T08:00:00-04:00", "sessionNumber": 2},
                {"dateTime": "2026-05-12T08:00:00-04:00", "sessionNumber": 3},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "in-progress",
            "currentSession": 3,
            "totalSessions": 4,
            # Deliberately no completedSessions[] — pre-Set-022 shape.
            "startedAt": "2026-05-10T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    # Events ledger says sessions 1 and 2 are closed → 2/4 rendered.
    assert "2/4" in out, out
    # Activity-log distinct count (the pre-fix path) would have shown 3/4.
    assert "3/4" not in out, out


def test_done_set_uses_array_length(ar, tmp_path: Path) -> None:
    """A done set with completedSessions=[1,2,3,4] renders 4/4, not
    whatever the activity-log entry count happens to be.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "shipped"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "change-log.md").write_text("# Changes\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 4,
            # Deliberately includes a stray entry for session 5 (e.g.,
            # an abandoned attempt that got rolled back). The count
            # must not include it because session 5 is not in
            # ``completedSessions[]``.
            "entries": [
                {"dateTime": "2026-05-01T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-02T08:00:00-04:00", "sessionNumber": 2},
                {"dateTime": "2026-05-03T08:00:00-04:00", "sessionNumber": 3},
                {"dateTime": "2026-05-04T08:00:00-04:00", "sessionNumber": 4},
                {"dateTime": "2026-05-05T08:00:00-04:00", "sessionNumber": 5},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "complete",
            "currentSession": 4,
            "totalSessions": 4,
            "completedSessions": [1, 2, 3, 4],
            "startedAt": "2026-05-01T08:00:00-04:00",
            "completedAt": "2026-05-04T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    # Done sets render as N/N (the existing render rule); the count
    # must be 4 (array length), not 5 (activity-log distinct sessions).
    assert "4/4" in out, out
    assert "5/5" not in out, out

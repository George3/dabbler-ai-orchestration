"""Layer-1 unit tests for ai_router.joiner.conflicts.

Set 049 retired the Set 045 / Set 033 coordination-conflict detectors
(engine-mismatch, bare-touch, stale-checkout-touch) along with the
rest of the H3 + H4 coordination layer. The writer-bypass detector
(D3) survives as a general writer-discipline check, decoupled from the
coordination framing.

The detector is a pure function of its inputs; tests don't need any
operator-machine state.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_router.joiner.conflicts import (
    detect_writer_bypass,
    scan_conflicts,
)
from ai_router.joiner.parsers import SessionStateView


# ---------------------------------------------------------------------------
# Helpers — synthetic state views.
# ---------------------------------------------------------------------------


def make_state_view(
    *,
    state_file: Path,
    workspace_root: Path,
    set_slug: str = "999-test-set",
) -> SessionStateView:
    """Build a minimal :class:`SessionStateView` for writer-bypass tests.

    The writer-bypass detector only reads ``state_file`` (mtime) and the
    sibling ``session-events.jsonl`` (timestamps), plus ``workspace_root``
    + ``set_slug`` for the report payload. Coordination-era fields
    (orchestrator_engine, last_activity, orchestrator_provider) are
    irrelevant to the predicate.
    """
    return SessionStateView(
        state_file=state_file,
        set_slug=set_slug,
        workspace_root=workspace_root,
        orchestrator_engine=None,
        orchestrator_provider=None,
        last_activity=None,
    )


# ---------------------------------------------------------------------------
# Writer-bypass — the sole surviving conflict mode.
# ---------------------------------------------------------------------------


class TestWriterBypass:
    def test_bypass_emits_when_no_nearby_event(self, tmp_path: Path):
        state_file = tmp_path / "session-state.json"
        events_file = tmp_path / "session-events.jsonl"
        state_file.write_text("{}", encoding="utf-8")
        # Force the state file mtime to a known wall-clock value.
        target = time.time()
        os.utime(state_file, (target, target))
        # Event ledger has a single record an hour earlier — well outside the ±2s window.
        early_iso = datetime.fromtimestamp(target - 3600, tz=timezone.utc).isoformat()
        events_file.write_text(json.dumps({"ts": early_iso, "kind": "work_started"}) + "\n", encoding="utf-8")

        state = make_state_view(
            state_file=state_file,
            workspace_root=tmp_path,
        )
        reports = detect_writer_bypass(state)
        assert len(reports) == 1
        assert reports[0].kind == "writer-bypass"
        assert reports[0].severity == "high"
        assert reports[0].evidence["delta_seconds"] > 100

    def test_no_bypass_when_event_within_tolerance(self, tmp_path: Path):
        state_file = tmp_path / "session-state.json"
        events_file = tmp_path / "session-events.jsonl"
        state_file.write_text("{}", encoding="utf-8")
        target = time.time()
        os.utime(state_file, (target, target))
        # Event within ±2s of state mtime.
        close_iso = datetime.fromtimestamp(target, tz=timezone.utc).isoformat()
        events_file.write_text(json.dumps({"ts": close_iso, "kind": "work_started"}) + "\n", encoding="utf-8")

        state = make_state_view(
            state_file=state_file,
            workspace_root=tmp_path,
        )
        reports = detect_writer_bypass(state)
        assert reports == []

    def test_no_bypass_when_events_file_missing(self, tmp_path: Path):
        state_file = tmp_path / "session-state.json"
        state_file.write_text("{}", encoding="utf-8")
        state = make_state_view(state_file=state_file, workspace_root=tmp_path)
        # No events.jsonl → skip rather than false-positive.
        assert detect_writer_bypass(state) == []

    def test_no_bypass_when_events_file_empty(self, tmp_path: Path):
        state_file = tmp_path / "session-state.json"
        events_file = tmp_path / "session-events.jsonl"
        state_file.write_text("{}", encoding="utf-8")
        events_file.write_text("", encoding="utf-8")
        state = make_state_view(state_file=state_file, workspace_root=tmp_path)
        assert detect_writer_bypass(state) == []


# ---------------------------------------------------------------------------
# scan_conflicts() — integration over the synthetic workspace layout.
# ---------------------------------------------------------------------------


def test_scan_conflicts_emits_writer_bypass_only(tmp_path: Path):
    """``scan_conflicts`` walks every state file under the workspace and
    only emits writer-bypass kinds post-Set-049. The retired detectors
    (engine-mismatch, bare-touch, stale-checkout-touch) are gone."""
    workspace = tmp_path / "workspace"
    set_dir = workspace / "docs" / "session-sets" / "999-test-set"
    set_dir.mkdir(parents=True)
    state = {
        "schemaVersion": 4,
        "sessionSetName": "999-test-set",
        "status": "in-progress",
        "sessions": [{"number": 1, "title": "Test", "status": "in-progress"}],
    }
    state_path = set_dir / "session-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    # Events ledger with an entry an hour off — forces writer-bypass.
    mtime = state_path.stat().st_mtime
    iso = datetime.fromtimestamp(mtime - 3600, tz=timezone.utc).isoformat()
    (set_dir / "session-events.jsonl").write_text(
        json.dumps({"ts": iso, "kind": "work_started"}) + "\n",
        encoding="utf-8",
    )

    reports = scan_conflicts(
        workspace_root=workspace,
        detected_at=datetime(2026, 5, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    kinds = {r.kind for r in reports}
    # Writer-bypass is the only kind the joiner emits post-rip.
    assert kinds == {"writer-bypass"}


def test_scan_conflicts_set_slug_filter_excludes_other_sets(tmp_path: Path):
    """``--set-slug`` restricts the scan to one set."""
    workspace = tmp_path / "workspace"
    set_a = workspace / "docs" / "session-sets" / "999-test-set"
    set_a.mkdir(parents=True)
    state_a = {
        "schemaVersion": 4,
        "sessionSetName": "999-test-set",
        "status": "in-progress",
        "sessions": [{"number": 1, "title": "Test", "status": "in-progress"}],
    }
    state_a_path = set_a / "session-state.json"
    state_a_path.write_text(json.dumps(state_a), encoding="utf-8")
    mtime_a = state_a_path.stat().st_mtime
    iso_a = datetime.fromtimestamp(mtime_a - 3600, tz=timezone.utc).isoformat()
    (set_a / "session-events.jsonl").write_text(
        json.dumps({"ts": iso_a, "kind": "work_started"}) + "\n",
        encoding="utf-8",
    )

    set_b = workspace / "docs" / "session-sets" / "111-other"
    set_b.mkdir(parents=True)
    state_b = {
        "schemaVersion": 4,
        "sessionSetName": "111-other",
        "status": "not-started",
        "sessions": [],
    }
    state_b_path = set_b / "session-state.json"
    state_b_path.write_text(json.dumps(state_b), encoding="utf-8")
    mtime_b = state_b_path.stat().st_mtime
    iso_b = datetime.fromtimestamp(mtime_b - 3600, tz=timezone.utc).isoformat()
    (set_b / "session-events.jsonl").write_text(
        json.dumps({"ts": iso_b, "kind": "work_started"}) + "\n",
        encoding="utf-8",
    )

    reports = scan_conflicts(
        set_slug="999-test-set",
        workspace_root=workspace,
        detected_at=datetime(2026, 5, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    slugs = {r.set_slug for r in reports}
    assert slugs == {"999-test-set"}

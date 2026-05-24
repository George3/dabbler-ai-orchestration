"""Layer-1 unit tests for ai_router.joiner.conflicts.

Synthetic fixtures exercise each of the three conflict modes:

- Mode A: engine-mismatch
- Mode B: bare-touch / stale-checkout-touch
- Mode C: writer-bypass

The detectors are pure functions of their inputs; tests don't need
any operator-machine state.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ai_router.joiner.conflicts import (
    DEFAULT_ENGINE_MISMATCH_WINDOW,
    DEFAULT_STALENESS_THRESHOLD,
    detect_bare_or_stale_touch,
    detect_engine_mismatch,
    detect_writer_bypass,
    scan_conflicts,
)
from ai_router.joiner.parsers import (
    NativeSession,
    SessionStateView,
    canonicalize_cwd,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic state views + native sessions.
# ---------------------------------------------------------------------------


def make_state_view(
    *,
    state_file: Path,
    workspace_root: Path,
    orchestrator_engine: str | None = "claude-code",
    last_activity: datetime | None = None,
    set_slug: str = "999-test-set",
) -> SessionStateView:
    if last_activity is None and orchestrator_engine is not None:
        last_activity = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
    return SessionStateView(
        state_file=state_file,
        set_slug=set_slug,
        workspace_root=workspace_root,
        orchestrator_engine=orchestrator_engine,
        orchestrator_provider="anthropic" if orchestrator_engine else None,
        last_activity=last_activity,
    )


def make_native_session(
    engine: str,
    cwd_canonical: str,
    first_event_ts: datetime,
    conv_id: str = "conv-test",
) -> NativeSession:
    return NativeSession(
        engine=engine,
        conv_id=conv_id,
        first_event_ts=first_event_ts,
        last_event_ts=first_event_ts + timedelta(minutes=1),
        cwd_canonical=cwd_canonical,
        source_file=f"/synthetic/{engine}/{conv_id}.jsonl",
        cwd_source="jsonl-field",
    )


# ---------------------------------------------------------------------------
# Mode A — engine-mismatch.
# ---------------------------------------------------------------------------


class TestEngineMismatch:
    def test_mismatch_within_window_emits_report(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine="claude-code",
            last_activity=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        native = make_native_session(
            engine="copilot",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=datetime(2026, 5, 24, 12, 1, 0, tzinfo=timezone.utc),
        )
        reports = detect_engine_mismatch(state, [native])
        assert len(reports) == 1
        r = reports[0]
        assert r.kind == "engine-mismatch"
        assert r.severity == "high"
        assert r.evidence["state_engine"] == "claude-code"
        assert r.evidence["native_engine"] == "copilot"

    def test_same_engine_no_conflict(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine="claude-code",
        )
        native = make_native_session(
            engine="claude",  # base form matches normalized "claude-code"
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=datetime(2026, 5, 24, 12, 0, 30, tzinfo=timezone.utc),
        )
        reports = detect_engine_mismatch(state, [native])
        assert reports == []

    def test_outside_window_no_conflict(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine="claude-code",
            last_activity=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        native = make_native_session(
            engine="copilot",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=datetime(2026, 5, 24, 13, 0, 0, tzinfo=timezone.utc),  # 1 hour later
        )
        reports = detect_engine_mismatch(state, [native])
        assert reports == []

    def test_no_checkout_skips_engine_mismatch(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine=None,
        )
        native = make_native_session(
            engine="copilot",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        # Mode A doesn't fire without an orchestrator_engine (Mode B handles that case).
        reports = detect_engine_mismatch(state, [native])
        assert reports == []

    def test_wrong_workspace_no_conflict(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace-a",
            orchestrator_engine="claude-code",
        )
        native = make_native_session(
            engine="copilot",
            cwd_canonical="c:/other/workspace",
            first_event_ts=datetime(2026, 5, 24, 12, 0, 30, tzinfo=timezone.utc),
        )
        reports = detect_engine_mismatch(state, [native])
        assert reports == []


# ---------------------------------------------------------------------------
# Mode B — bare-touch / stale-checkout-touch.
# ---------------------------------------------------------------------------


class TestBareOrStaleTouch:
    def test_bare_touch_emits_when_no_checkout(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine=None,
        )
        native = make_native_session(
            engine="claude",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        reports = detect_bare_or_stale_touch(state, [native])
        assert len(reports) == 1
        assert reports[0].kind == "bare-touch"
        assert reports[0].severity == "medium"

    def test_no_bare_touch_when_native_outside_workspace(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine=None,
        )
        native = make_native_session(
            engine="claude",
            cwd_canonical="c:/elsewhere",
            first_event_ts=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        reports = detect_bare_or_stale_touch(state, [native])
        assert reports == []

    def test_native_in_subdirectory_counts_as_touch(self, tmp_path: Path):
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine=None,
        )
        workspace_canon = canonicalize_cwd(str(tmp_path / "workspace"))
        native = make_native_session(
            engine="claude",
            cwd_canonical=workspace_canon + "/subdir",
            first_event_ts=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        reports = detect_bare_or_stale_touch(state, [native])
        assert len(reports) == 1
        assert reports[0].kind == "bare-touch"

    def test_stale_checkout_touch_emits_when_old_checkout(self, tmp_path: Path):
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine="claude-code",
            last_activity=now - timedelta(hours=5),  # very stale
        )
        native = make_native_session(
            engine="claude",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=now - timedelta(minutes=10),  # post-staleness-window
        )
        reports = detect_bare_or_stale_touch(state, [native], detected_at=now)
        assert len(reports) == 1
        assert reports[0].kind == "stale-checkout-touch"
        assert reports[0].evidence["checkout_age_seconds"] > 3600

    def test_fresh_checkout_no_stale_touch(self, tmp_path: Path):
        now = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        state = make_state_view(
            state_file=tmp_path / "state.json",
            workspace_root=tmp_path / "workspace",
            orchestrator_engine="claude-code",
            last_activity=now - timedelta(minutes=10),  # fresh
        )
        native = make_native_session(
            engine="claude",
            cwd_canonical=canonicalize_cwd(str(tmp_path / "workspace")),
            first_event_ts=now - timedelta(minutes=5),
        )
        reports = detect_bare_or_stale_touch(state, [native], detected_at=now)
        assert reports == []


# ---------------------------------------------------------------------------
# Mode C — writer-bypass.
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


@pytest.fixture
def synthetic_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build a workspace + one session set + an isolated Claude root.

    Returns (workspace_root, claude_root, copilot_root).
    """
    workspace = tmp_path / "workspace"
    set_dir = workspace / "docs" / "session-sets" / "999-test-set"
    set_dir.mkdir(parents=True)
    state = {
        "schemaVersion": 3,
        "sessionSetName": "999-test-set",
        "sessions": [{"number": 1, "title": "Test", "status": "in-progress"}],
        "currentSession": 1,
        "totalSessions": 1,
        "completedSessions": [],
        "status": "in-progress",
        "startedAt": "2026-05-24T08:00:00-04:00",
        "orchestrator": {
            "engine": "claude-code",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
            "checkedOutAt": "2026-05-24T08:00:00-04:00",
            "lastActivityAt": "2026-05-24T12:00:00-04:00",
        },
    }
    state_path = set_dir / "session-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    # Events ledger that brackets the state file mtime — avoids Mode C noise.
    mtime = state_path.stat().st_mtime
    iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    (set_dir / "session-events.jsonl").write_text(
        json.dumps({"ts": iso, "kind": "work_started"}) + "\n",
        encoding="utf-8",
    )

    # Claude root with a copilot-engine session in the workspace → engine-mismatch
    # (since the workspace's orchestrator is claude-code). We use a copilot
    # JSONL to keep the scenario obvious; the Claude scraper handles slug
    # decoding while the Copilot scraper handles events.jsonl.
    claude_root = tmp_path / "claude-root"
    claude_root.mkdir()
    copilot_root = tmp_path / "copilot-root"
    copilot_root.mkdir()

    return workspace, claude_root, copilot_root


def test_scan_conflicts_no_mismatch_when_native_matches_orchestrator(
    synthetic_workspace,
):
    workspace, claude_root, copilot_root = synthetic_workspace
    # Place a Claude session in the workspace within window → matches orchestrator → no conflict.
    workspace_slug = "c--" + str(workspace).replace(":", "").replace("\\", "-").replace("/", "-").lstrip("-")
    # Easier path: write a JSONL with the cwd field pointing at workspace.
    ws_dir = claude_root / "any-slug"
    ws_dir.mkdir()
    (ws_dir / "conv-1.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-05-24T12:01:00-04:00",
            "cwd": str(workspace),
        }) + "\n",
        encoding="utf-8",
    )
    reports = scan_conflicts(
        workspace_root=workspace,
        claude_root=claude_root,
        copilot_root=copilot_root,
        detected_at=datetime(2026, 5, 24, 16, 1, 0, tzinfo=timezone.utc),
    )
    # No engine-mismatch (claude session matches claude-code orchestrator)
    # No bare-touch (orchestrator IS present)
    # No stale-checkout (only 1 minute past last_activity)
    # No writer-bypass (events ledger brackets state mtime)
    assert all(r.kind != "engine-mismatch" for r in reports), [r.note for r in reports]


def test_scan_conflicts_finds_engine_mismatch_with_copilot_in_workspace(
    synthetic_workspace,
):
    workspace, claude_root, copilot_root = synthetic_workspace
    # Place a Copilot session in the workspace within window of the state file's
    # lastActivityAt — should fire Mode A (state says claude-code, native is copilot).
    sess = copilot_root / "conv-zzz"
    sess.mkdir()
    (sess / "events.jsonl").write_text(
        json.dumps({
            "type": "session.start",
            "timestamp": "2026-05-24T12:01:00-04:00",
            "data": {
                "sessionId": "conv-zzz",
                "startTime": "2026-05-24T12:01:00-04:00",
                "context": {"cwd": str(workspace)},
            },
        }) + "\n",
        encoding="utf-8",
    )
    reports = scan_conflicts(
        set_slug="999-test-set",
        workspace_root=workspace,
        claude_root=claude_root,
        copilot_root=copilot_root,
        detected_at=datetime(2026, 5, 24, 16, 1, 0, tzinfo=timezone.utc),
    )
    engine_mismatch = [r for r in reports if r.kind == "engine-mismatch"]
    assert len(engine_mismatch) == 1
    r = engine_mismatch[0]
    assert r.evidence["state_engine"] == "claude-code"
    assert r.evidence["native_engine"] == "copilot"
    assert r.evidence["native_conv_id"] == "conv-zzz"


def test_scan_conflicts_set_slug_filter_excludes_other_sets(
    synthetic_workspace,
):
    workspace, claude_root, copilot_root = synthetic_workspace
    # Build a SECOND session set with no orchestrator + a copilot native session
    # — should fire bare-touch if no filter, but the filter should exclude.
    other_set = workspace / "docs" / "session-sets" / "111-other"
    other_set.mkdir(parents=True)
    other_state = {
        "schemaVersion": 3,
        "sessionSetName": "111-other",
        "sessions": [],
        "totalSessions": 0,
        "completedSessions": [],
        "status": "not-started",
        "startedAt": "2026-05-24T08:00:00-04:00",
        "orchestrator": None,
    }
    (other_set / "session-state.json").write_text(json.dumps(other_state), encoding="utf-8")

    sess = copilot_root / "conv-other"
    sess.mkdir()
    (sess / "events.jsonl").write_text(
        json.dumps({
            "type": "session.start",
            "timestamp": "2026-05-24T12:01:00-04:00",
            "data": {
                "sessionId": "conv-other",
                "startTime": "2026-05-24T12:01:00-04:00",
                "context": {"cwd": str(workspace)},
            },
        }) + "\n",
        encoding="utf-8",
    )
    reports = scan_conflicts(
        set_slug="999-test-set",
        workspace_root=workspace,
        claude_root=claude_root,
        copilot_root=copilot_root,
        detected_at=datetime(2026, 5, 24, 16, 1, 0, tzinfo=timezone.utc),
    )
    # Filter should restrict to 999-test-set; no bare-touch should leak from 111-other.
    assert all(r.set_slug == "999-test-set" for r in reports)

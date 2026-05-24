"""Layer-1 unit tests for ai_router.joiner.coverage."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_router.joiner.coverage import coverage


@pytest.fixture
def workspace_with_set(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    set_dir = workspace / "docs" / "session-sets" / "999-test-set"
    set_dir.mkdir(parents=True)
    state = {
        "schemaVersion": 3,
        "sessionSetName": "999-test-set",
        "sessions": [],
        "totalSessions": 0,
        "completedSessions": [],
        "status": "not-started",
        "startedAt": "2026-05-24T08:00:00-04:00",
        "orchestrator": None,
    }
    (set_dir / "session-state.json").write_text(json.dumps(state), encoding="utf-8")
    return workspace


def test_coverage_returns_one_summary_per_set(workspace_with_set: Path, tmp_path: Path):
    summaries = coverage(
        workspace_root=workspace_with_set,
        claude_root=tmp_path / "empty-claude",
        copilot_root=tmp_path / "empty-copilot",
        launch_log=tmp_path / "no-launch.jsonl",
    )
    assert len(summaries) == 1
    s = summaries[0]
    assert s.set_slug == "999-test-set"
    assert s.wrapper_launched is False
    assert s.narration_present is False  # S4 will flip this
    assert s.native_log_bound is False
    assert s.bypass_inferred is False
    assert s.last_signal_ts is None


def test_coverage_detects_native_log_in_workspace(workspace_with_set: Path, tmp_path: Path):
    claude_root = tmp_path / "claude"
    ws_dir = claude_root / "any-slug"
    ws_dir.mkdir(parents=True)
    (ws_dir / "conv-x.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-05-24T08:00:00Z",
            "cwd": str(workspace_with_set),
        }) + "\n",
        encoding="utf-8",
    )
    summaries = coverage(
        workspace_root=workspace_with_set,
        claude_root=claude_root,
        copilot_root=tmp_path / "empty-copilot",
        launch_log=tmp_path / "no-launch.jsonl",
    )
    assert len(summaries) == 1
    s = summaries[0]
    assert s.native_log_bound is True
    assert s.wrapper_launched is False
    assert s.bypass_inferred is True  # native log present + no wrapper launch
    assert s.last_signal_ts is not None


def test_coverage_detects_wrapper_launch(workspace_with_set: Path, tmp_path: Path):
    launch_log = tmp_path / "launch-log.jsonl"
    launch_log.write_text(
        json.dumps({
            "launch_ts": "2026-05-24T08:00:00Z",
            "workspace_cwd": str(workspace_with_set),
            "set_slug": "999-test-set",
            "session_number": 1,
            "target_backend": "claude",
            "launch_id": "uuid-1",
            "effort": "high",
        }) + "\n",
        encoding="utf-8",
    )
    summaries = coverage(
        workspace_root=workspace_with_set,
        claude_root=tmp_path / "empty-claude",
        copilot_root=tmp_path / "empty-copilot",
        launch_log=launch_log,
    )
    s = summaries[0]
    assert s.wrapper_launched is True
    assert s.bypass_inferred is False  # wrapper present → not a bypass case

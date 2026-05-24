"""Layer-2 e2e: wrapper → launch log → joiner harvest() join round-trip.

The L1 tests in test_dabbler_launch.py exercise the writer side and
the L1 tests in test_joiner_parsers.py exercise the reader side.
This file ties them together: the wrapper's actual ``run_launch``
writes the canonical record, the joiner's ``harvest()`` then reads
it and produces the joined HarvestRecord stream with the expected
``binding_state``.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ai_router.dabbler_launch import LaunchInputs, run_launch
from ai_router.joiner.schema import harvest


def _write_claude_jsonl(claude_root: Path, slug: str, conv_id: str, ts: datetime, cwd: str) -> None:
    workspace = claude_root / slug
    workspace.mkdir(parents=True, exist_ok=True)
    jsonl = workspace / f"{conv_id}.jsonl"
    jsonl.write_text(
        json.dumps({"timestamp": ts.isoformat(), "cwd": cwd}) + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def workspace_cwd() -> str:
    return "C:/Users/foo/project"


@pytest.fixture
def workspace_canon(workspace_cwd: str) -> str:
    return "c:/users/foo/project"


@pytest.fixture
def launch_inputs(tmp_path: Path, workspace_cwd: str) -> LaunchInputs:
    return LaunchInputs(
        engine="claude",
        workspace_cwd=workspace_cwd,
        set_slug="045-log-harvest-implementation",
        session_number=3,
        effort="high",
        provider="anthropic",
        model="claude-opus-4-7",
        launch_log=tmp_path / "launch-log.jsonl",
        child_argv=[],
    )


class TestWrapperToJoinerBound:
    def test_wrapper_record_binds_to_native_session_within_window(
        self, tmp_path, launch_inputs, workspace_canon
    ):
        launch_ts = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        run_launch(launch_inputs, when=launch_ts, spawn=False)

        claude_root = tmp_path / "claude-projects"
        # Native first-event 5 s after launch — well inside the 30 s bind window.
        _write_claude_jsonl(
            claude_root,
            slug="C--Users-foo-project",
            conv_id="conv-bound",
            ts=launch_ts + timedelta(seconds=5),
            cwd="C:/Users/foo/project",
        )

        records = list(
            harvest(
                workspace_cwd=workspace_canon,
                claude_root=claude_root,
                copilot_root=tmp_path / "empty-copilot",
                launch_log=launch_inputs.launch_log,
            )
        )
        launches = [r for r in records if r.event_type == "launch"]
        natives = [r for r in records if r.event_type == "session_start"]
        assert len(launches) == 1
        assert launches[0].binding_state == "bound"
        assert launches[0].conv_id == "conv-bound"
        assert launches[0].set_slug == "045-log-harvest-implementation"
        # The native session_start is also emitted alongside the bound launch.
        assert len(natives) == 1
        assert natives[0].conv_id == "conv-bound"


class TestWrapperToJoinerUnbound:
    def test_wrapper_record_outside_window_is_unbound(
        self, tmp_path, launch_inputs, workspace_canon
    ):
        launch_ts = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        run_launch(launch_inputs, when=launch_ts, spawn=False)

        claude_root = tmp_path / "claude-projects"
        # Native event 10 minutes after launch — far outside the 30 s bind window.
        _write_claude_jsonl(
            claude_root,
            slug="C--Users-foo-project",
            conv_id="conv-far",
            ts=launch_ts + timedelta(minutes=10),
            cwd="C:/Users/foo/project",
        )

        records = list(
            harvest(
                workspace_cwd=workspace_canon,
                claude_root=claude_root,
                copilot_root=tmp_path / "empty-copilot",
                launch_log=launch_inputs.launch_log,
            )
        )
        launches = [r for r in records if r.event_type == "launch"]
        assert len(launches) == 1
        assert launches[0].binding_state == "unbound"
        assert launches[0].conv_id is None


class TestWrapperToJoinerAmbiguous:
    def test_two_native_candidates_within_window_yields_ambiguous(
        self, tmp_path, launch_inputs, workspace_canon
    ):
        launch_ts = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        run_launch(launch_inputs, when=launch_ts, spawn=False)

        claude_root = tmp_path / "claude-projects"
        _write_claude_jsonl(
            claude_root,
            slug="C--Users-foo-project-a",
            conv_id="conv-a",
            ts=launch_ts + timedelta(seconds=3),
            cwd="C:/Users/foo/project",
        )
        _write_claude_jsonl(
            claude_root,
            slug="C--Users-foo-project-b",
            conv_id="conv-b",
            ts=launch_ts + timedelta(seconds=10),
            cwd="C:/Users/foo/project",
        )

        records = list(
            harvest(
                workspace_cwd=workspace_canon,
                claude_root=claude_root,
                copilot_root=tmp_path / "empty-copilot",
                launch_log=launch_inputs.launch_log,
            )
        )
        launches = [r for r in records if r.event_type == "launch"]
        assert len(launches) == 1
        assert launches[0].binding_state == "ambiguous"
        assert launches[0].conv_id is None
        assert set(launches[0].bound_candidates or []) == {"conv-a", "conv-b"}


class TestFreeRunningNativeWithoutLaunch:
    def test_native_session_with_no_launch_is_emitted_without_binding(
        self, tmp_path, workspace_canon
    ):
        # No launch log at all — just a native session.
        claude_root = tmp_path / "claude-projects"
        _write_claude_jsonl(
            claude_root,
            slug="C--Users-foo-project",
            conv_id="conv-freerunning",
            ts=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
            cwd="C:/Users/foo/project",
        )

        records = list(
            harvest(
                workspace_cwd=workspace_canon,
                claude_root=claude_root,
                copilot_root=tmp_path / "empty-copilot",
                launch_log=tmp_path / "no-such-log.jsonl",
            )
        )
        launches = [r for r in records if r.event_type == "launch"]
        natives = [r for r in records if r.event_type == "session_start"]
        assert launches == []
        assert len(natives) == 1
        assert natives[0].conv_id == "conv-freerunning"
        assert natives[0].binding_state is None

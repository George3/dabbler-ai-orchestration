"""Layer-1 unit tests for the ai_router.joiner CLI."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_router.joiner.cli import main


def _build_empty_workspace(tmp_path: Path) -> Path:
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


def test_cli_conflicts_no_match(tmp_path, capsys):
    workspace = _build_empty_workspace(tmp_path)
    rc = main(["--conflicts", "--workspace", str(workspace), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out) == []


def test_cli_coverage_emits_json(tmp_path, capsys):
    workspace = _build_empty_workspace(tmp_path)
    rc = main(["--coverage", "--workspace", str(workspace), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["set_slug"] == "999-test-set"


def test_cli_coverage_human_readable(tmp_path, capsys):
    workspace = _build_empty_workspace(tmp_path)
    rc = main(["--coverage", "--workspace", str(workspace)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "999-test-set" in out
    assert "(no signal)" in out


def test_cli_harvest_runs(tmp_path, capsys):
    # Filter to a non-existent workspace so we get an empty stream regardless of operator's real logs.
    rc = main(["--harvest", "--workspace-cwd", "c:/nonexistent/path", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_requires_one_mode(tmp_path):
    with pytest.raises(SystemExit):
        main([])

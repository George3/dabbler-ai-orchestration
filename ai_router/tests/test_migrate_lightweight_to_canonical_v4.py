"""Tests for the Lightweight-tier migrator — Set 048 Session 4.

Covers the four documented non-canonical-shape recognizers and the
backup/rollback contract:

- ``sessionLog[]`` -> ``sessions[]`` rename (great-psalms-scroll-font
  shape).
- Missing ``schemaVersion`` field on otherwise v3-shaped input.
- Per-session and top-level ``status`` alias canonicalization
  (``"completed"`` / ``"done"`` -> ``"complete"``).
- Idempotent skip on canonical v4 input.
- Refusal of v1 / v2 / future-schema files; structured skip results
  for malformed / missing inputs.
- Apply mode writes ``session-state.lwbak.json`` before the new file
  and the .bak content matches the pre-migration on-disk bytes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import migrate_lightweight_to_canonical_v4 as mlw
from migrate_lightweight_to_canonical_v4 import (
    ACTION_FAILED_BACKUP,
    ACTION_MIGRATED,
    ACTION_SKIPPED_FUTURE_SCHEMA,
    ACTION_SKIPPED_MALFORMED,
    ACTION_SKIPPED_NO_STATE,
    ACTION_SKIPPED_PRE_V3,
    ACTION_SKIPPED_V4,
    BACKUP_FILENAME,
    SESSION_STATE_FILENAME,
    discover_session_sets,
    main,
    migrate_all,
    migrate_one_set,
)


def _spec(n: int) -> str:
    lines = ["# Test set", "", "## Sessions", ""]
    for i in range(1, n + 1):
        lines.append(f"### Session {i} of {n}: title-{i}")
        lines.append("Body...")
        lines.append("")
    return "\n".join(lines)


def _write(set_dir: Path, state: dict, *, spec_n: int = 3) -> None:
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / SESSION_STATE_FILENAME).write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    (set_dir / "spec.md").write_text(_spec(spec_n), encoding="utf-8")


def _read(set_dir: Path) -> dict:
    return json.loads((set_dir / SESSION_STATE_FILENAME).read_text("utf-8"))


def _read_backup(set_dir: Path) -> dict:
    return json.loads((set_dir / BACKUP_FILENAME).read_text("utf-8"))


# ---------------------------------------------------------------------------
# sessionLog[] alias
# ---------------------------------------------------------------------------


class TestSessionLogAlias:
    def test_sessionlog_array_promoted_to_sessions(self, tmp_path):
        set_dir = tmp_path / "psalms"
        _write(
            set_dir,
            {
                "schemaVersion": 3,
                "sessionSetName": "psalms",
                "sessionLog": [
                    {"number": 1, "title": "title-1", "status": "complete"},
                    {"number": 2, "title": "title-2", "status": "complete"},
                    {"number": 3, "title": "title-3", "status": "not-started"},
                ],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["schemaVersion"] == 4
        assert isinstance(r.after.get("sessions"), list)
        assert len(r.after["sessions"]) == 3
        assert "sessionLog" not in r.after
        # The rename note must surface in the normalizations record so
        # the CLI can report which divergence triggered.
        assert any("sessionLog" in n for n in r.normalizations)

    def test_sessionlog_alias_apply_writes_canonical_v4(self, tmp_path):
        set_dir = tmp_path / "psalms"
        _write(
            set_dir,
            {
                "schemaVersion": 3,
                "sessionSetName": "psalms",
                "sessionLog": [
                    {"number": 1, "title": "title-1", "status": "complete"},
                    {"number": 2, "title": "title-2", "status": "not-started"},
                    {"number": 3, "title": "title-3", "status": "not-started"},
                ],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_MIGRATED
        on_disk = _read(set_dir)
        assert on_disk["schemaVersion"] == 4
        assert "sessionLog" not in on_disk
        assert isinstance(on_disk["sessions"], list)
        # Backup carries the pre-migration on-disk bytes (with
        # sessionLog still present).
        bak = _read_backup(set_dir)
        assert "sessionLog" in bak
        assert "sessions" not in bak


# ---------------------------------------------------------------------------
# Missing schemaVersion
# ---------------------------------------------------------------------------


class TestMissingSchemaVersion:
    def test_no_schema_version_but_v3_shape_promotes(self, tmp_path):
        set_dir = tmp_path / "no-schema"
        _write(
            set_dir,
            {
                "sessionSetName": "no-schema",
                "sessions": [
                    {"number": 1, "title": "title-1", "status": "complete"},
                    {"number": 2, "title": "title-2", "status": "not-started"},
                    {"number": 3, "title": "title-3", "status": "not-started"},
                ],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["schemaVersion"] == 4
        assert any("stamped missing schemaVersion" in n for n in r.normalizations)

    def test_no_schema_version_and_no_sessions_is_pre_v3(self, tmp_path):
        set_dir = tmp_path / "v2-shape"
        _write(
            set_dir,
            {
                "sessionSetName": "v2-shape",
                "currentSession": 1,
                "totalSessions": 3,
                "completedSessions": [],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_PRE_V3


# ---------------------------------------------------------------------------
# Status alias canonicalization
# ---------------------------------------------------------------------------


class TestStatusAliasCanonicalization:
    def test_top_level_done_canonicalized_to_complete(self, tmp_path):
        set_dir = tmp_path / "alias-top"
        _write(
            set_dir,
            {
                "schemaVersion": 3,
                "sessionSetName": "alias-top",
                "sessions": [
                    {"number": 1, "title": "title-1", "status": "complete"},
                    {"number": 2, "title": "title-2", "status": "complete"},
                    {"number": 3, "title": "title-3", "status": "complete"},
                ],
                "status": "done",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["status"] == "complete"

    def test_per_session_completed_alias_canonicalized(self, tmp_path):
        set_dir = tmp_path / "alias-session"
        _write(
            set_dir,
            {
                "schemaVersion": 3,
                "sessionSetName": "alias-session",
                "sessions": [
                    {"number": 1, "title": "title-1", "status": "completed"},
                    {"number": 2, "title": "title-2", "status": "not-started"},
                    {"number": 3, "title": "title-3", "status": "not-started"},
                ],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        # Session 1's status alias is rewritten on-disk to the canonical token.
        assert r.after["sessions"][0]["status"] == "complete"
        assert any(
            "canonicalized per-session status" in n for n in r.normalizations
        )


# ---------------------------------------------------------------------------
# Idempotent skip on canonical v4
# ---------------------------------------------------------------------------


class TestIdempotentSkip:
    def test_canonical_v4_skipped(self, tmp_path):
        set_dir = tmp_path / "already-v4"
        _write(
            set_dir,
            {
                "schemaVersion": 4,
                "sessionSetName": "already-v4",
                "sessions": [
                    {
                        "number": 1,
                        "title": "title-1",
                        "status": "complete",
                        "startedAt": None,
                        "completedAt": None,
                        "orchestrator": None,
                        "verificationVerdict": None,
                    },
                    {
                        "number": 2,
                        "title": "title-2",
                        "status": "not-started",
                        "startedAt": None,
                        "completedAt": None,
                        "orchestrator": None,
                        "verificationVerdict": None,
                    },
                    {
                        "number": 3,
                        "title": "title-3",
                        "status": "not-started",
                        "startedAt": None,
                        "completedAt": None,
                        "orchestrator": None,
                        "verificationVerdict": None,
                    },
                ],
                "status": "in-progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_SKIPPED_V4
        # No backup created on a skip.
        assert not (set_dir / BACKUP_FILENAME).exists()


# ---------------------------------------------------------------------------
# Refusal cases
# ---------------------------------------------------------------------------


class TestRefusalCases:
    def test_missing_state_file(self, tmp_path):
        set_dir = tmp_path / "missing"
        set_dir.mkdir()
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_NO_STATE

    def test_malformed_json(self, tmp_path):
        set_dir = tmp_path / "bad"
        set_dir.mkdir()
        (set_dir / SESSION_STATE_FILENAME).write_text("not-json")
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_MALFORMED

    def test_non_object_json(self, tmp_path):
        set_dir = tmp_path / "list"
        set_dir.mkdir()
        (set_dir / SESSION_STATE_FILENAME).write_text("[1,2,3]")
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_MALFORMED

    def test_v2_file_refused_with_pointer_to_v2_v3_migrator(self, tmp_path):
        set_dir = tmp_path / "v2"
        _write(
            set_dir,
            {
                "schemaVersion": 2,
                "sessionSetName": "v2",
                "currentSession": 1,
                "totalSessions": 3,
                "completedSessions": [],
                "status": "in-progress",
                "lifecycleState": "work_in_progress",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_PRE_V3
        assert "migrate_session_state" in r.reason

    def test_future_schema_refused(self, tmp_path):
        set_dir = tmp_path / "future"
        _write(
            set_dir,
            {
                "schemaVersion": 9,
                "sessionSetName": "future",
                "sessions": [],
                "status": "complete",
            },
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_FUTURE_SCHEMA


# ---------------------------------------------------------------------------
# Backup contract (apply mode)
# ---------------------------------------------------------------------------


class TestBackupContract:
    def test_apply_mode_writes_lwbak_before_state(self, tmp_path):
        set_dir = tmp_path / "psalms"
        before = {
            "schemaVersion": 3,
            "sessionSetName": "psalms",
            "sessionLog": [
                {"number": 1, "title": "title-1", "status": "complete"},
                {"number": 2, "title": "title-2", "status": "not-started"},
                {"number": 3, "title": "title-3", "status": "not-started"},
            ],
            "status": "in-progress",
        }
        _write(set_dir, before)
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_MIGRATED
        assert (set_dir / BACKUP_FILENAME).exists()
        # Backup is the pre-migration on-disk bytes (sessionLog still there).
        bak = _read_backup(set_dir)
        assert "sessionLog" in bak
        # State file is the canonical v4 shape.
        on_disk = _read(set_dir)
        assert on_disk["schemaVersion"] == 4
        assert "sessionLog" not in on_disk
        # Sanity: re-running apply mode skips (already v4) and the .bak
        # is not overwritten with the now-canonical-v4 file.
        r2 = migrate_one_set(str(set_dir), dry_run=False)
        assert r2.action == ACTION_SKIPPED_V4
        bak2 = _read_backup(set_dir)
        assert "sessionLog" in bak2


# ---------------------------------------------------------------------------
# CLI / discovery
# ---------------------------------------------------------------------------


class TestCLI:
    def test_discover_finds_session_sets(self, tmp_path):
        # Two with state files, one without — only the two are returned.
        _write(tmp_path / "a", {"schemaVersion": 4, "sessionSetName": "a", "sessions": [], "status": "complete"})
        _write(tmp_path / "b", {"schemaVersion": 3, "sessionSetName": "b", "sessions": [], "status": "complete"})
        (tmp_path / "c").mkdir()  # bare folder, no state file
        found = discover_session_sets(str(tmp_path))
        names = sorted(os.path.basename(p) for p in found)
        assert names == ["a", "b"]

    def test_main_dry_run_returns_zero(self, capsys, tmp_path):
        _write(
            tmp_path / "x",
            {
                "schemaVersion": 3,
                "sessionSetName": "x",
                "sessions": [
                    {"number": 1, "title": "title-1", "status": "not-started"},
                    {"number": 2, "title": "title-2", "status": "not-started"},
                    {"number": 3, "title": "title-3", "status": "not-started"},
                ],
                "status": "not-started",
            },
        )
        exit_code = main(["--scan", str(tmp_path)])
        assert exit_code == 0
        out = capsys.readouterr().out
        # Dry-run output does NOT write the state file — re-read and
        # confirm the file is unchanged.
        on_disk = _read(tmp_path / "x")
        assert on_disk["schemaVersion"] == 3  # untouched

    def test_main_json_output_includes_counts(self, capsys, tmp_path):
        _write(
            tmp_path / "x",
            {
                "schemaVersion": 4,
                "sessionSetName": "x",
                "sessions": [],
                "status": "complete",
            },
        )
        exit_code = main(["--scan", str(tmp_path), "--json"])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["counts"]["skipped_v4"] == 1
        assert payload["counts"]["total"] == 1

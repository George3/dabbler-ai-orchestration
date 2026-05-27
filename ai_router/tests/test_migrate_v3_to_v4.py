"""Tests for the bulk v3 → v4 migrator — Set 047 Session 3.

Covers:

- Happy path: a canonical v3 file is rewritten in v4 shape; round-trip
  through ``normalize_to_v4_shape`` reads identically before vs. after.
- Per-session metadata promotion: top-level ``orchestrator`` /
  ``startedAt`` / ``completedAt`` / ``verificationVerdict`` are
  promoted onto the appropriate ``sessions[]`` entry by the shim and
  preserved by the migrator's strip step.
- On-disk shape: derived top-level fields (currentSession,
  totalSessions, completedSessions, orchestrator, startedAt,
  completedAt, verificationVerdict, lifecycleState) are DROPPED;
  preserved keys are exactly {schemaVersion, sessionSetName, status,
  sessions, [preCancelStatus, forceClosed]}.
- Idempotence: a v4 file is returned as ``ACTION_SKIPPED_V4`` without
  touching disk; back-to-back apply-mode runs converge.
- Refusal cases:
    * v1/v2 files return ``ACTION_SKIPPED_NOT_V3`` with an actionable
      pointer to the v2 → v3 migrator.
    * Broken v3 (schemaVersion=3 but missing/non-list sessions[])
      returns ``ACTION_SKIPPED_MALFORMED``.
    * Future schema (schemaVersion > 4) returns
      ``ACTION_SKIPPED_FUTURE_SCHEMA``.
    * Non-object / non-JSON / missing state files return structured
      skip results, never raise.
- Backup behavior (apply mode):
    * The .bak file is created BEFORE the state file is replaced.
    * The .bak content matches the pre-migration state.
    * Re-running apply mode overwrites the .bak with the now-v4 file's
      pre-migration content (which, on the second run, is itself v4 —
      the second run skips and does NOT overwrite the .bak).
- Status alias canonicalization: a v3 file with ``"completed"`` /
  ``"done"`` at top level is normalized to ``"complete"`` in the v4
  output.
- Passthrough fields (``preCancelStatus`` / ``forceClosed``) ride
  along when present in the source; absent when not.
- ``discover_session_sets`` and ``migrate_all`` interact correctly
  with ``--only`` filtering.
- CLI ``main()`` returns 0 on success, 1 when any set would violate
  or any backup fails, and emits JSON when ``--json`` is passed.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

import migrate_v3_to_v4 as mv4
import progress
from migrate_v3_to_v4 import (
    ACTION_FAILED_BACKUP,
    ACTION_MIGRATED,
    ACTION_SKIPPED_FUTURE_SCHEMA,
    ACTION_SKIPPED_MALFORMED,
    ACTION_SKIPPED_NO_STATE,
    ACTION_SKIPPED_NOT_V3,
    ACTION_SKIPPED_V4,
    ACTION_SWEPT_ORCHESTRATOR,
    ACTION_WOULD_VIOLATE,
    BACKUP_FILENAME,
    SESSION_STATE_FILENAME,
    SWEEP_BACKUP_FILENAME,
    MigrationResult,
    build_v4_on_disk_shape,
    discover_session_sets,
    main,
    migrate_all,
    migrate_one_set,
)
from migrate_v3_to_v4 import _strip_retired_orchestrator_keys, _sweep_orchestrator_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(n: int) -> str:
    lines = ["# Test set", "", "## Sessions", ""]
    for i in range(1, n + 1):
        lines.append(f"### Session {i} of {n}: title-{i}")
        lines.append("Body...")
        lines.append("")
    return "\n".join(lines)


def _v3_state(
    *,
    name: str = "set",
    total: int = 3,
    completed: int = 0,
    in_progress: int | None = None,
    orchestrator: dict | None = None,
    started: str | None = None,
    finished: str | None = None,
    verdict: str | None = None,
    top_status: str = "in-progress",
    lifecycle: str | None = "work_in_progress",
    extra: dict | None = None,
) -> dict:
    """Build a canonical v3 state dict for fixture writes."""
    sessions = []
    for n in range(1, total + 1):
        if n <= completed:
            status = "complete"
        elif in_progress is not None and n == in_progress:
            status = "in-progress"
        else:
            status = "not-started"
        sessions.append({"number": n, "title": f"title-{n}", "status": status})
    state: dict = {
        "schemaVersion": 3,
        "sessionSetName": name,
        "sessions": sessions,
        "status": top_status,
        "lifecycleState": lifecycle,
        "currentSession": in_progress,
        "totalSessions": total,
        "completedSessions": list(range(1, completed + 1)),
        "startedAt": started,
        "completedAt": finished,
        "verificationVerdict": verdict,
        "orchestrator": orchestrator,
    }
    if extra:
        state.update(extra)
    return state


def _write_state(set_dir: Path, state: dict, *, spec_n: int = 3) -> None:
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / SESSION_STATE_FILENAME).write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    (set_dir / "spec.md").write_text(_spec(spec_n), encoding="utf-8")


def _read_state(set_dir: Path) -> dict:
    return json.loads((set_dir / SESSION_STATE_FILENAME).read_text(encoding="utf-8"))


def _read_backup(set_dir: Path) -> dict:
    return json.loads((set_dir / BACKUP_FILENAME).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path + shape contract
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_in_progress_v3_migrates_to_v4_shape(self, tmp_path):
        set_dir = tmp_path / "in-flight"
        orch = {
            "engine": "claude",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
        }
        _write_state(
            set_dir,
            _v3_state(
                name="in-flight",
                total=3,
                completed=1,
                in_progress=2,
                orchestrator=orch,
                started="2026-05-26T09:00:00-04:00",
            ),
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        out = r.after
        assert out["schemaVersion"] == 4
        assert out["sessionSetName"] == "in-flight"
        assert out["status"] == "in-progress"
        # Derived top-level fields are dropped from the on-disk shape.
        for dropped in (
            "lifecycleState",
            "currentSession",
            "totalSessions",
            "completedSessions",
            "startedAt",
            "completedAt",
            "verificationVerdict",
            "orchestrator",
        ):
            assert dropped not in out, f"v4 on-disk should not carry {dropped!r}"
        assert len(out["sessions"]) == 3
        # The in-progress session received the orchestrator + startedAt.
        s2 = out["sessions"][1]
        assert s2["status"] == "in-progress"
        assert s2["orchestrator"] == orch
        assert s2["startedAt"] == "2026-05-26T09:00:00-04:00"
        # Other sessions carry the v4 metadata keys defaulted to null.
        s1 = out["sessions"][0]
        assert s1["status"] == "complete"
        assert s1["orchestrator"] is None
        assert s1["startedAt"] is None
        assert s1["completedAt"] is None
        assert s1["verificationVerdict"] is None

    def test_completed_v3_migrates_with_orchestrator_on_last_session(self, tmp_path):
        set_dir = tmp_path / "all-done"
        orch = {"engine": "claude", "provider": "anthropic", "model": "claude-opus-4-7", "effort": "high"}
        _write_state(
            set_dir,
            _v3_state(
                name="all-done",
                total=3,
                completed=3,
                in_progress=None,
                top_status="complete",
                lifecycle="closed",
                orchestrator=orch,
                started="2026-05-25T09:00:00-04:00",
                finished="2026-05-26T17:00:00-04:00",
                verdict="VERIFIED",
            ),
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        out = r.after
        assert out["status"] == "complete"
        # No in-progress session → the orchestrator + completedAt +
        # verificationVerdict land on the most-recently-completed
        # session (session 3).
        s3 = out["sessions"][2]
        assert s3["status"] == "complete"
        assert s3["orchestrator"] == orch
        assert s3["completedAt"] == "2026-05-26T17:00:00-04:00"
        assert s3["verificationVerdict"] == "VERIFIED"

    def test_status_alias_canonicalized(self, tmp_path):
        set_dir = tmp_path / "alias"
        state = _v3_state(name="alias", total=2, completed=2, top_status="completed", lifecycle="closed")
        _write_state(set_dir, state, spec_n=2)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["status"] == "complete"

    def test_passthrough_fields_preserved(self, tmp_path):
        set_dir = tmp_path / "passthrough"
        state = _v3_state(
            name="passthrough",
            total=2,
            completed=2,
            top_status="complete",
            lifecycle="closed",
            extra={"preCancelStatus": "in-progress", "forceClosed": True},
        )
        _write_state(set_dir, state, spec_n=2)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["preCancelStatus"] == "in-progress"
        assert r.after["forceClosed"] is True

    def test_round_trip_through_shim_equivalent(self, tmp_path):
        """The shim's read view over the v4 output must equal its read
        view over the v3 input — that's the contract that lets v3-era
        readers consume v4 files transparently."""
        set_dir = tmp_path / "round-trip"
        state = _v3_state(
            name="round-trip",
            total=3,
            completed=2,
            in_progress=3,
            orchestrator={"engine": "claude", "provider": "anthropic", "model": "claude-opus-4-7", "effort": "high"},
            started="2026-05-26T10:00:00-04:00",
        )
        _write_state(set_dir, state)
        spec_path = set_dir / "spec.md"
        before = progress.normalize_to_v4_shape(state, spec_path)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        after = progress.normalize_to_v4_shape(r.after, spec_path)
        # The two normalized views should be observationally
        # equivalent — sessions[] and derived top-level fields all
        # match.
        assert before["sessions"] == after["sessions"]
        assert before["currentSession"] == after["currentSession"]
        assert before["completedSessions"] == after["completedSessions"]
        assert before["orchestrator"] == after["orchestrator"]
        assert before["startedAt"] == after["startedAt"]
        assert before["completedAt"] == after["completedAt"]
        assert before["verificationVerdict"] == after["verificationVerdict"]
        assert before["status"] == after["status"]


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


class TestIdempotence:
    def test_v4_file_skipped(self, tmp_path):
        set_dir = tmp_path / "already-v4"
        state = {
            "schemaVersion": 4,
            "sessionSetName": "already-v4",
            "status": "complete",
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
            ],
        }
        _write_state(set_dir, state, spec_n=1)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_V4
        assert "already v4" in r.reason

    def test_apply_then_skip(self, tmp_path):
        set_dir = tmp_path / "apply-then-skip"
        _write_state(set_dir, _v3_state(name="apply-then-skip", total=2, completed=2, top_status="complete", lifecycle="closed"), spec_n=2)
        r1 = migrate_one_set(str(set_dir), dry_run=False)
        assert r1.action == ACTION_MIGRATED
        assert (set_dir / BACKUP_FILENAME).is_file()
        # Second run: the state file is now v4 → skipped.
        r2 = migrate_one_set(str(set_dir), dry_run=False)
        assert r2.action == ACTION_SKIPPED_V4
        # The .bak from the first run is untouched (the skip path
        # doesn't write).
        assert _read_backup(set_dir)["schemaVersion"] == 3


# ---------------------------------------------------------------------------
# Refusal cases
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_v2_file_skipped_not_v3(self, tmp_path):
        set_dir = tmp_path / "v2"
        state = {
            "schemaVersion": 2,
            "sessionSetName": "v2",
            "currentSession": 2,
            "totalSessions": 3,
            "completedSessions": [1],
            "status": "in-progress",
        }
        _write_state(set_dir, state)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_NOT_V3
        assert "migrate_session_state" in r.reason

    def test_schemaversion_missing_skipped_not_v3(self, tmp_path):
        set_dir = tmp_path / "no-schema"
        state = {"sessionSetName": "no-schema", "status": "not-started"}
        _write_state(set_dir, state)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_NOT_V3

    def test_broken_v3_missing_sessions_skipped_malformed(self, tmp_path):
        set_dir = tmp_path / "broken-v3"
        state = {
            "schemaVersion": 3,
            "sessionSetName": "broken-v3",
            "status": "in-progress",
            # sessions[] intentionally absent
        }
        _write_state(set_dir, state)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_MALFORMED
        assert "sessions[]" in r.reason

    def test_future_schema_skipped(self, tmp_path):
        set_dir = tmp_path / "future"
        state = {"schemaVersion": 99, "sessionSetName": "future", "status": "in-progress", "sessions": []}
        _write_state(set_dir, state)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_FUTURE_SCHEMA

    def test_missing_state_file(self, tmp_path):
        set_dir = tmp_path / "empty"
        set_dir.mkdir()
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_NO_STATE

    def test_unparseable_json(self, tmp_path):
        set_dir = tmp_path / "bad-json"
        set_dir.mkdir()
        (set_dir / SESSION_STATE_FILENAME).write_text("{ not json", encoding="utf-8")
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_MALFORMED

    def test_non_object_top_level(self, tmp_path):
        set_dir = tmp_path / "array-top"
        set_dir.mkdir()
        (set_dir / SESSION_STATE_FILENAME).write_text("[]", encoding="utf-8")
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SKIPPED_MALFORMED
        # Python json reports list, JS reports array — the migrator
        # uses type(state).__name__ so the token here is "list".
        assert "list" in r.reason and "expected object" in r.reason

    def test_invariant_violation_surfaces_would_violate(self, tmp_path):
        """A v3 file with status=complete but a not-started session
        violates rule 7. The shim raises SessionStateInvariantError,
        which the migrator converts to ACTION_WOULD_VIOLATE."""
        set_dir = tmp_path / "violating"
        state = {
            "schemaVersion": 3,
            "sessionSetName": "violating",
            "status": "complete",
            "lifecycleState": "closed",
            "sessions": [
                {"number": 1, "title": "title-1", "status": "complete"},
                {"number": 2, "title": "title-2", "status": "not-started"},
            ],
            "currentSession": None,
            "totalSessions": 2,
            "completedSessions": [1],
        }
        _write_state(set_dir, state, spec_n=2)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_WOULD_VIOLATE


# ---------------------------------------------------------------------------
# Backup behavior + apply mode
# ---------------------------------------------------------------------------


class TestBackupAndApply:
    def test_apply_writes_backup_with_original_v3_content(self, tmp_path):
        set_dir = tmp_path / "backup"
        original = _v3_state(name="backup", total=2, completed=2, top_status="complete", lifecycle="closed")
        _write_state(set_dir, original, spec_n=2)
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_MIGRATED
        assert r.backup_path == str(set_dir / BACKUP_FILENAME)
        bak = _read_backup(set_dir)
        assert bak["schemaVersion"] == 3
        assert bak["sessionSetName"] == "backup"
        # State file is now v4.
        live = _read_state(set_dir)
        assert live["schemaVersion"] == 4
        # Backup is byte-equivalent in CONTENT (re-emitted JSON) to
        # the parsed original.
        assert bak == original

    def test_dry_run_does_not_touch_disk(self, tmp_path):
        set_dir = tmp_path / "dry"
        original = _v3_state(name="dry", total=2, completed=1, in_progress=2)
        _write_state(set_dir, original)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        # Backup must NOT exist.
        assert not (set_dir / BACKUP_FILENAME).exists()
        # State file unchanged.
        assert _read_state(set_dir)["schemaVersion"] == 3

    def test_backup_write_failure_aborts(self, monkeypatch, tmp_path):
        set_dir = tmp_path / "backup-fail"
        _write_state(set_dir, _v3_state(name="backup-fail", total=2, completed=2, top_status="complete", lifecycle="closed"), spec_n=2)

        original_replace = os.replace

        def _failing_replace(src, dst):
            # Fail only on the .bak write; allow any other replaces.
            if dst.endswith(BACKUP_FILENAME):
                raise OSError("simulated backup write failure")
            return original_replace(src, dst)

        monkeypatch.setattr(os, "replace", _failing_replace)
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_FAILED_BACKUP
        # The state file must be untouched.
        assert _read_state(set_dir)["schemaVersion"] == 3
        # No .bak landed → backup_path is None so callers can
        # distinguish the "no rollback needed" subcase.
        assert r.backup_path is None

    def test_state_write_failure_after_backup_signals_rollback_subcase(
        self, monkeypatch, tmp_path
    ):
        """The OTHER `failed-backup` subtype: backup landed, then
        state-file write failed. The S3 verifier flagged the
        rollback-doc / message conflation between these two subcases
        — distinguish them with backup_path set vs None."""
        set_dir = tmp_path / "state-fail"
        _write_state(
            set_dir,
            _v3_state(
                name="state-fail",
                total=2,
                completed=2,
                top_status="complete",
                lifecycle="closed",
            ),
            spec_n=2,
        )

        state_path = str(set_dir / SESSION_STATE_FILENAME)
        backup_path = str(set_dir / BACKUP_FILENAME)
        original_replace = os.replace

        def _state_replace_fails(src, dst):
            # Allow the backup write; fail the state-file replacement.
            if dst == state_path:
                raise OSError("simulated state-file write failure")
            return original_replace(src, dst)

        monkeypatch.setattr(os, "replace", _state_replace_fails)
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_FAILED_BACKUP
        # backup_path is SET so the operator-facing message can route
        # to the rollback procedure (vs. the no-bak subcase).
        assert r.backup_path == backup_path
        # The .bak landed.
        assert os.path.isfile(backup_path)
        assert _read_backup(set_dir)["schemaVersion"] == 3

    def test_done_alias_canonicalized(self, tmp_path):
        """Coverage for the `"done"` status alias (the existing alias
        test only covers `"completed"`). The shim canonicalizes both
        to `"complete"`; the migrator's status canonicalization on
        the way out should produce `"complete"` on disk."""
        set_dir = tmp_path / "done-alias"
        state = _v3_state(name="done-alias", total=2, completed=2, top_status="done", lifecycle="closed")
        _write_state(set_dir, state, spec_n=2)
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        assert r.after["status"] == "complete"


# ---------------------------------------------------------------------------
# build_v4_on_disk_shape — pure-function unit tests
# ---------------------------------------------------------------------------


class TestBuildV4OnDiskShape:
    def test_drops_every_derived_key(self):
        normalized = {
            "schemaVersion": 4,
            "sessionSetName": "x",
            "status": "in-progress",
            "sessions": [{"number": 1, "title": "t", "status": "in-progress"}],
            "currentSession": 1,
            "totalSessions": 1,
            "completedSessions": [],
            "orchestrator": {"engine": "claude"},
            "startedAt": "2026-05-26T09:00:00-04:00",
            "completedAt": None,
            "verificationVerdict": None,
            "lifecycleState": "work_in_progress",
        }
        out = build_v4_on_disk_shape(normalized, {"schemaVersion": 3})
        assert set(out.keys()) == {"schemaVersion", "sessionSetName", "status", "sessions"}

    def test_passthrough_only_when_present_in_original(self):
        normalized = {
            "schemaVersion": 4,
            "sessionSetName": "x",
            "status": "cancelled",
            "sessions": [],
        }
        # forceClosed absent in original → not in output
        out_a = build_v4_on_disk_shape(normalized, {"schemaVersion": 3})
        assert "forceClosed" not in out_a
        # forceClosed present in original → passes through
        out_b = build_v4_on_disk_shape(normalized, {"schemaVersion": 3, "forceClosed": True})
        assert out_b["forceClosed"] is True

    def test_status_canonicalized(self):
        normalized = {
            "schemaVersion": 4,
            "sessionSetName": "x",
            "status": "completed",
            "sessions": [],
        }
        out = build_v4_on_disk_shape(normalized, {"schemaVersion": 3})
        assert out["status"] == "complete"


# ---------------------------------------------------------------------------
# discover_session_sets + migrate_all
# ---------------------------------------------------------------------------


class TestDiscoveryAndBulk:
    def test_discover_lists_sets_with_state_files(self, tmp_path):
        # Two sets with state files, one set without, one non-directory.
        for name in ("set-a", "set-b", "set-c"):
            d = tmp_path / name
            d.mkdir()
        _write_state(tmp_path / "set-a", _v3_state(name="set-a", total=1))
        _write_state(tmp_path / "set-b", _v3_state(name="set-b", total=1))
        (tmp_path / "stray.txt").write_text("not a set")
        sets = discover_session_sets(str(tmp_path))
        names = [os.path.basename(p) for p in sets]
        assert names == ["set-a", "set-b"]

    def test_migrate_all_with_only_filter(self, tmp_path):
        for name in ("set-a", "set-b"):
            _write_state(tmp_path / name, _v3_state(name=name, total=1, completed=1, top_status="complete", lifecycle="closed"), spec_n=1)
        results = migrate_all(str(tmp_path), dry_run=True, set_filter=["set-a"])
        assert len(results) == 1
        assert os.path.basename(results[0].set_dir) == "set-a"

    def test_discover_returns_empty_for_missing_root(self, tmp_path):
        sets = discover_session_sets(str(tmp_path / "does-not-exist"))
        assert sets == []


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


class TestCLI:
    def test_main_returns_zero_on_dry_run_with_migrations(self, tmp_path, capsys):
        _write_state(tmp_path / "set-a", _v3_state(name="set-a", total=1, completed=1, top_status="complete", lifecycle="closed"), spec_n=1)
        exit_code = main(["--scan", str(tmp_path)])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Summary" in out

    def test_main_returns_one_when_would_violate(self, tmp_path, capsys):
        set_dir = tmp_path / "violating"
        state = {
            "schemaVersion": 3,
            "sessionSetName": "violating",
            "status": "complete",
            "lifecycleState": "closed",
            "sessions": [
                {"number": 1, "title": "t1", "status": "complete"},
                {"number": 2, "title": "t2", "status": "not-started"},
            ],
            "totalSessions": 2,
            "completedSessions": [1],
            "currentSession": None,
        }
        _write_state(set_dir, state, spec_n=2)
        exit_code = main(["--scan", str(tmp_path)])
        assert exit_code == 1

    def test_main_json_output_shape(self, tmp_path, capsys):
        _write_state(tmp_path / "set-a", _v3_state(name="set-a", total=2, completed=2, top_status="complete", lifecycle="closed"), spec_n=2)
        exit_code = main(["--scan", str(tmp_path), "--json"])
        assert exit_code == 0
        text = capsys.readouterr().out
        data = json.loads(text)
        assert data["scan_root"] == str(tmp_path)
        assert data["dry_run"] is True
        assert data["counts"]["migrated"] == 1
        assert len(data["results"]) == 1

    def test_main_apply_writes_v4_and_backup(self, tmp_path):
        set_dir = tmp_path / "applied"
        _write_state(set_dir, _v3_state(name="applied", total=2, completed=2, top_status="complete", lifecycle="closed"), spec_n=2)
        exit_code = main(["--scan", str(tmp_path), "--in-place"])
        assert exit_code == 0
        assert _read_state(set_dir)["schemaVersion"] == 4
        assert _read_backup(set_dir)["schemaVersion"] == 3

    def test_main_only_filter(self, tmp_path):
        for name in ("set-a", "set-b"):
            _write_state(tmp_path / name, _v3_state(name=name, total=1, completed=1, top_status="complete", lifecycle="closed"), spec_n=1)
        exit_code = main(["--scan", str(tmp_path), "--in-place", "--only", "set-a"])
        assert exit_code == 0
        assert _read_state(tmp_path / "set-a")["schemaVersion"] == 4
        # set-b untouched.
        assert _read_state(tmp_path / "set-b")["schemaVersion"] == 3


# ---------------------------------------------------------------------------
# Set 049 T4: orchestrator-block sweep+normalize
# ---------------------------------------------------------------------------


def _v4_state_with_stale_orchestrator_keys() -> dict:
    """Build a v4 state whose orchestrator blocks carry the 3 Set-049-retired keys."""
    return {
        "schemaVersion": 4,
        "sessionSetName": "swept-fixture",
        "status": "in-progress",
        "sessions": [
            {
                "number": 1,
                "title": "title-1",
                "status": "complete",
                "startedAt": "2026-05-26T09:00:00-04:00",
                "completedAt": "2026-05-26T10:00:00-04:00",
                "orchestrator": {
                    "engine": "claude",
                    "provider": "anthropic",
                    "model": "claude-opus-4-7",
                    "effort": "high",
                    "chatSessionId": "sess-abc",
                    "checkedOutAt": "2026-05-26T09:00:00-04:00",
                    "lastActivityAt": "2026-05-26T10:00:00-04:00",
                },
                "verificationVerdict": None,
            },
            {
                "number": 2,
                "title": "title-2",
                "status": "in-progress",
                "startedAt": "2026-05-26T10:30:00-04:00",
                "completedAt": None,
                "orchestrator": {
                    "engine": "codex",
                    "provider": "openai",
                    "model": "gpt-5.4",
                    "effort": "medium",
                    "chatSessionId": None,
                    "checkedOutAt": "2026-05-26T10:30:00-04:00",
                    "lastActivityAt": "2026-05-26T10:30:00-04:00",
                },
                "verificationVerdict": None,
            },
        ],
    }


class TestStripRetiredOrchestratorKeys:
    def test_returns_unchanged_on_clean_block(self):
        block = {
            "engine": "claude",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
        }
        new_block, changed = _strip_retired_orchestrator_keys(block)
        assert changed is False
        assert new_block == block

    def test_strips_all_three_retired_keys(self):
        block = {
            "engine": "claude",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
            "chatSessionId": "sess-abc",
            "checkedOutAt": "2026-05-26T09:00:00-04:00",
            "lastActivityAt": "2026-05-26T10:00:00-04:00",
        }
        new_block, changed = _strip_retired_orchestrator_keys(block)
        assert changed is True
        assert new_block == {
            "engine": "claude",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
        }

    def test_strips_when_retired_keys_are_null(self):
        # The retired keys are stripped regardless of value — including None.
        # On-disk omit-null contract: missing key, not key with null value.
        block = {
            "engine": "claude",
            "provider": "anthropic",
            "chatSessionId": None,
            "checkedOutAt": None,
            "lastActivityAt": None,
        }
        new_block, changed = _strip_retired_orchestrator_keys(block)
        assert changed is True
        assert new_block == {"engine": "claude", "provider": "anthropic"}

    def test_preserves_unknown_keys(self):
        # Forward-compat: unknown keys are preserved (they may be added by a
        # later schema without the migrator's awareness).
        block = {"engine": "claude", "chatSessionId": "x", "futureField": "v"}
        new_block, changed = _strip_retired_orchestrator_keys(block)
        assert changed is True
        assert new_block == {"engine": "claude", "futureField": "v"}

    def test_non_dict_input_roundtrips(self):
        for value in (None, [], "string", 42):
            new_value, changed = _strip_retired_orchestrator_keys(value)
            assert changed is False
            assert new_value is value


class TestSweepOrchestratorBlocks:
    def test_sweeps_top_level_legacy_orchestrator(self):
        state = {
            "schemaVersion": 3,
            "orchestrator": {
                "engine": "claude",
                "chatSessionId": "sess-abc",
                "checkedOutAt": "ts",
                "lastActivityAt": "ts",
            },
        }
        new_state, changed = _sweep_orchestrator_blocks(state)
        assert changed is True
        assert new_state["orchestrator"] == {"engine": "claude"}
        # Input was not mutated.
        assert "chatSessionId" in state["orchestrator"]

    def test_sweeps_per_session_orchestrator_blocks(self):
        state = _v4_state_with_stale_orchestrator_keys()
        new_state, changed = _sweep_orchestrator_blocks(state)
        assert changed is True
        for entry in new_state["sessions"]:
            for retired in ("chatSessionId", "checkedOutAt", "lastActivityAt"):
                assert retired not in entry["orchestrator"]
        # Input was not mutated.
        assert "chatSessionId" in state["sessions"][0]["orchestrator"]

    def test_clean_state_returns_unchanged(self):
        state = {
            "schemaVersion": 4,
            "sessions": [
                {
                    "number": 1,
                    "orchestrator": {"engine": "claude", "provider": "anthropic"},
                }
            ],
        }
        new_state, changed = _sweep_orchestrator_blocks(state)
        assert changed is False
        assert new_state is state

    def test_no_orchestrator_blocks_returns_unchanged(self):
        state = {
            "schemaVersion": 4,
            "sessions": [
                {"number": 1, "orchestrator": None},
                {"number": 2},
            ],
        }
        new_state, changed = _sweep_orchestrator_blocks(state)
        assert changed is False
        assert new_state is state

    def test_idempotent_across_calls(self):
        state = _v4_state_with_stale_orchestrator_keys()
        once, changed_1 = _sweep_orchestrator_blocks(state)
        twice, changed_2 = _sweep_orchestrator_blocks(once)
        assert changed_1 is True
        assert changed_2 is False
        assert twice is once


class TestMigrateOneSetSweep:
    def test_v4_with_stale_keys_returns_swept_dry_run(self, tmp_path):
        set_dir = tmp_path / "stale-v4"
        set_dir.mkdir()
        state = _v4_state_with_stale_orchestrator_keys()
        (set_dir / SESSION_STATE_FILENAME).write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
        (set_dir / "spec.md").write_text(_spec(2), encoding="utf-8")
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_SWEPT_ORCHESTRATOR
        assert r.backup_path is None
        # The dry-run after view has the keys stripped...
        for entry in r.after["sessions"]:
            for retired in ("chatSessionId", "checkedOutAt", "lastActivityAt"):
                assert retired not in entry["orchestrator"]
        # ...but the on-disk file is untouched.
        on_disk = json.loads((set_dir / SESSION_STATE_FILENAME).read_text(encoding="utf-8"))
        assert "chatSessionId" in on_disk["sessions"][0]["orchestrator"]
        # And no sweep backup file was created.
        assert not (set_dir / SWEEP_BACKUP_FILENAME).exists()

    def test_v4_with_stale_keys_applies_sweep_with_backup(self, tmp_path):
        set_dir = tmp_path / "stale-v4"
        set_dir.mkdir()
        state = _v4_state_with_stale_orchestrator_keys()
        (set_dir / SESSION_STATE_FILENAME).write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
        (set_dir / "spec.md").write_text(_spec(2), encoding="utf-8")
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_SWEPT_ORCHESTRATOR
        assert r.backup_path == str(set_dir / SWEEP_BACKUP_FILENAME)
        # State file: keys stripped.
        on_disk = json.loads((set_dir / SESSION_STATE_FILENAME).read_text(encoding="utf-8"))
        for entry in on_disk["sessions"]:
            for retired in ("chatSessionId", "checkedOutAt", "lastActivityAt"):
                assert retired not in entry["orchestrator"]
        # Backup file: pre-sweep state (still carries the retired keys).
        bak = json.loads(
            (set_dir / SWEEP_BACKUP_FILENAME).read_text(encoding="utf-8")
        )
        assert "chatSessionId" in bak["sessions"][0]["orchestrator"]
        # No v3-style .bak file was created (we're sweeping a v4 file).
        assert not (set_dir / BACKUP_FILENAME).exists()

    def test_v4_clean_returns_skipped_v4(self, tmp_path):
        set_dir = tmp_path / "clean-v4"
        set_dir.mkdir()
        state = {
            "schemaVersion": 4,
            "sessionSetName": "clean",
            "status": "in-progress",
            "sessions": [
                {
                    "number": 1,
                    "title": "title-1",
                    "status": "in-progress",
                    "startedAt": "2026-05-26T09:00:00-04:00",
                    "completedAt": None,
                    "orchestrator": {
                        "engine": "claude",
                        "provider": "anthropic",
                        "model": "claude-opus-4-7",
                        "effort": "high",
                    },
                    "verificationVerdict": None,
                },
            ],
        }
        (set_dir / SESSION_STATE_FILENAME).write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
        (set_dir / "spec.md").write_text(_spec(1), encoding="utf-8")
        r = migrate_one_set(str(set_dir), dry_run=False)
        assert r.action == ACTION_SKIPPED_V4
        # No sweep backup written.
        assert not (set_dir / SWEEP_BACKUP_FILENAME).exists()

    def test_apply_then_rerun_is_idempotent(self, tmp_path):
        set_dir = tmp_path / "stale-v4"
        set_dir.mkdir()
        state = _v4_state_with_stale_orchestrator_keys()
        (set_dir / SESSION_STATE_FILENAME).write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
        (set_dir / "spec.md").write_text(_spec(2), encoding="utf-8")
        # First apply: sweep + backup.
        r1 = migrate_one_set(str(set_dir), dry_run=False)
        assert r1.action == ACTION_SWEPT_ORCHESTRATOR
        # Second apply: clean v4, no-op.
        r2 = migrate_one_set(str(set_dir), dry_run=False)
        assert r2.action == ACTION_SKIPPED_V4

    def test_v3_with_stale_top_level_orchestrator_strips_on_migrate(self, tmp_path):
        # A v3 file whose top-level orchestrator carries the retired keys.
        # After v3→v4 promotion + sweep, the resulting per-session
        # orchestrator block should NOT carry them.
        set_dir = tmp_path / "stale-v3"
        orchestrator_with_stale = {
            "engine": "claude",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
            "chatSessionId": "sess-old",
            "checkedOutAt": "2026-05-20T09:00:00-04:00",
            "lastActivityAt": "2026-05-20T10:00:00-04:00",
        }
        _write_state(
            set_dir,
            _v3_state(
                name="stale-v3",
                total=2,
                completed=0,
                in_progress=1,
                orchestrator=orchestrator_with_stale,
                started="2026-05-20T09:00:00-04:00",
            ),
            spec_n=2,
        )
        r = migrate_one_set(str(set_dir), dry_run=True)
        assert r.action == ACTION_MIGRATED
        # The in-progress session received the promoted orchestrator,
        # but the retired keys must not have ridden along.
        s1 = r.after["sessions"][0]
        assert s1["orchestrator"]["engine"] == "claude"
        for retired in ("chatSessionId", "checkedOutAt", "lastActivityAt"):
            assert retired not in s1["orchestrator"]

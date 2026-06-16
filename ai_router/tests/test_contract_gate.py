"""Set 068 S5 - the contract-test / CDC gate (deterministic verification floor).

Covers the policy attribute (mirrors path_aware_critique), the manifest +
floor-result pure-Python validators (L-066-1 discipline), the floor producer
(drives the S1 cage against a real throwaway git repo - no metered calls), the
coverage / residual split, and the posture-agnostic close-out validator.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import contract_gate as cg  # conftest puts ai_router/ on sys.path


NONE = cg.CONTRACT_GATE_NONE
ADVISORY = cg.CONTRACT_GATE_ADVISORY
REQUIRED = cg.CONTRACT_GATE_REQUIRED


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _set_dir(tmp_path, name="068-contract", *, with_log=True):
    d = tmp_path / name
    d.mkdir()
    (d / "spec.md").write_text(
        "# spec\n\n## Session Set Configuration\n\n```yaml\ntier: full\n```\n",
        encoding="utf-8",
    )
    if with_log:
        (d / "activity-log.json").write_text(
            json.dumps({"entries": []}, indent=2), encoding="utf-8"
        )
    return d


def _manifest(set_name="068-contract", level=REQUIRED, command=None, classes=None):
    return {
        "schemaVersion": 1,
        "sessionSetName": set_name,
        "contractGate": level,
        "command": command if command is not None else [sys.executable, "-c", "pass"],
        "defectClasses": classes
        if classes is not None
        else [
            {
                "id": "DC1",
                "description": "probeable, covered",
                "probeable": True,
                "coveredBy": ["test_dc1"],
            },
            {
                "id": "DC2",
                "description": "non-probeable residual",
                "probeable": False,
                "coveredBy": [],
            },
        ],
    }


def _floor_result(set_name="068-contract", level=REQUIRED, command=None,
                  passed=True):
    cmd = command or [sys.executable, "-c", "pass"]
    return {
        "schemaVersion": 1,
        "sessionSetName": set_name,
        "contractGate": level,
        "ref": "HEAD",
        "command": cmd,
        "ran": True,
        "passed": passed,
        "exitCode": 0 if passed else 1,
        "timedOut": False,
        "wallSeconds": 0.1,
        "worktreeCreated": True,
        "worktreeRemoved": True,
        "producedAt": "2026-06-15T00:00:00+00:00",
        "output": "",
    }


@pytest.fixture
def git_repo(tmp_path):
    """A throwaway one-commit git repo (the cage's source ref)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def _git(*args):
        subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True
        )

    _git("init", "-q")
    _git("config", "user.email", "t@example.invalid")
    _git("config", "user.name", "Test")
    (repo / "hello.txt").write_text("hi\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")
    return repo


# ---------------------------------------------------------------------------
# Policy attribute (mirrors path_aware_critique)
# ---------------------------------------------------------------------------


class TestPolicyAttribute:
    def test_default_is_none(self, tmp_path):
        d = _set_dir(tmp_path)
        assert cg.read_contract_gate(d) == NONE

    def test_record_then_read(self, tmp_path):
        d = _set_dir(tmp_path)
        cg.record_contract_gate(d, REQUIRED)
        assert cg.read_contract_gate(d) == REQUIRED
        assert cg.has_contract_gate_record(d) is True

    def test_record_unknown_value_raises(self, tmp_path):
        d = _set_dir(tmp_path)
        with pytest.raises(ValueError):
            cg.record_contract_gate(d, "bogus")

    def test_record_missing_log_raises(self, tmp_path):
        d = _set_dir(tmp_path, with_log=False)
        with pytest.raises(FileNotFoundError):
            cg.record_contract_gate(d, REQUIRED)

    def test_resolve_seeds_from_spec_once_then_immutable(self, tmp_path):
        d = _set_dir(tmp_path, with_log=False)
        (d / "spec.md").write_text(
            "# spec\n\n## Session Set Configuration\n\n"
            "```yaml\ntier: full\ncontractGate: required\n```\n",
            encoding="utf-8",
        )
        first = cg.resolve_and_record_contract_gate(d)
        assert first == REQUIRED
        assert cg.read_contract_gate(d) == REQUIRED
        # immutable: a later resolve is a no-op even with a different cli choice
        second = cg.resolve_and_record_contract_gate(d, cli_choice=NONE)
        assert second is None
        assert cg.read_contract_gate(d) == REQUIRED

    def test_resolve_no_seed_records_nothing(self, tmp_path):
        d = _set_dir(tmp_path)
        assert cg.resolve_and_record_contract_gate(d) is None
        assert cg.read_contract_gate(d) == NONE

    def test_resolve_bad_cli_choice_raises(self, tmp_path):
        d = _set_dir(tmp_path)
        with pytest.raises(ValueError):
            cg.resolve_and_record_contract_gate(d, cli_choice="bogus")

    def test_unreadable_record_detected(self, tmp_path):
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text("{ corrupt", encoding="utf-8")
        assert cg.contract_gate_record_unreadable(d) is True
        # collapses to none rather than raising
        assert cg.read_contract_gate(d) == NONE

    def test_unreadable_false_when_absent_or_clean(self, tmp_path):
        d = _set_dir(tmp_path, with_log=False)
        assert cg.contract_gate_record_unreadable(d) is False
        (d / "activity-log.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8"
        )
        assert cg.contract_gate_record_unreadable(d) is False

    @pytest.mark.parametrize(
        "blob", ["[]", '{"entries": "bad"}', '"a string"', "42"]
    )
    def test_malformed_but_parseable_log_is_flagged_not_raised(
        self, tmp_path, blob
    ):
        # gpt-5-4 S5 verification, Major: a JSON-parseable but wrong-shape log
        # must (a) never raise from the readers, and (b) be flagged unreadable so
        # close_session warns loudly instead of silently disarming the gate.
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text(blob, encoding="utf-8")
        assert cg.read_contract_gate(d) == NONE  # no raise
        assert cg.has_contract_gate_record(d) is False  # no raise
        assert cg.contract_gate_record_unreadable(d) is True

    def test_empty_object_log_is_legitimate_none_not_flagged(self, tmp_path):
        # {} is a degenerate-but-valid log: no record -> none, NOT corrupt.
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text("{}", encoding="utf-8")
        assert cg.read_contract_gate(d) == NONE
        assert cg.contract_gate_record_unreadable(d) is False

    def test_non_dict_entries_tolerant_read_but_flagged(self, tmp_path):
        # gpt-5-4 S5 R2, Major 2: reads stay tolerant (a real record after junk
        # still reads) but the non-dict element is surfaced as corruption.
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text(
            json.dumps({"entries": [
                "junk",
                42,
                {"kind": cg.CONTRACT_GATE_ENTRY_KIND, "choice": REQUIRED},
            ]}),
            encoding="utf-8",
        )
        assert cg.read_contract_gate(d) == REQUIRED
        assert cg.has_contract_gate_record(d) is True
        assert cg.contract_gate_record_unreadable(d) is True

    def test_invalid_utf8_is_flagged_not_raised(self, tmp_path):
        # gpt-5-4 S5 R2, Major 1: invalid UTF-8 bytes (UnicodeDecodeError, a
        # ValueError that is NOT a JSONDecodeError) must be caught, not raised.
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_bytes(b'{"entries": [\xff\xfe]}')
        assert cg.read_contract_gate(d) == NONE
        assert cg.has_contract_gate_record(d) is False
        assert cg.contract_gate_record_unreadable(d) is True

    def test_record_into_malformed_log_raises_controlled(self, tmp_path):
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError):
            cg.record_contract_gate(d, REQUIRED)

    def test_record_into_non_dict_entry_log_raises_controlled(self, tmp_path):
        d = _set_dir(tmp_path)
        (d / "activity-log.json").write_text(
            json.dumps({"entries": ["junk"]}), encoding="utf-8"
        )
        with pytest.raises(ValueError):
            cg.record_contract_gate(d, REQUIRED)


# ---------------------------------------------------------------------------
# Manifest validator
# ---------------------------------------------------------------------------


class TestManifestValidator:
    def test_valid(self):
        r = cg.validate_contract_manifest(_manifest())
        assert r.ok
        assert r.probeable_total == 1
        assert r.probeable_covered == 1
        assert r.uncovered_probeable_ids == ()
        assert r.residual_ids == ("DC2",)
        assert r.command[0] == sys.executable

    def test_missing_file(self, tmp_path):
        r = cg.validate_contract_manifest(tmp_path / "nope.json")
        assert not r.ok and r.code == cg.ARTIFACT_MISSING_FILE

    def test_unreadable(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text("{ corrupt", encoding="utf-8")
        r = cg.validate_contract_manifest(p)
        assert not r.ok and r.code == cg.ARTIFACT_UNREADABLE

    def test_invalid_utf8_is_unreadable_not_a_crash(self, tmp_path):
        # Invalid UTF-8 raises UnicodeDecodeError (a ValueError, NOT an OSError
        # or JSONDecodeError); the validators promise never-raising, so it must
        # come back as ARTIFACT_UNREADABLE, not crash close-out (Set 068 S6
        # whole-set critique, GPT-5.4, Major).
        p = tmp_path / "m.json"
        p.write_bytes(b"\x80\x81not-utf8")
        r = cg.validate_contract_manifest(p)
        assert not r.ok and r.code == cg.ARTIFACT_UNREADABLE
        # the floor-result validator shares _load_json_artifact -> same guard
        r2 = cg.validate_contract_floor_result(p)
        assert not r2.ok and r2.code == cg.ARTIFACT_UNREADABLE

    def test_not_an_object(self):
        r = cg.validate_contract_manifest([1, 2])
        assert not r.ok and r.code == cg.ARTIFACT_NOT_AN_OBJECT

    @pytest.mark.parametrize("bad_version", [1.0, True, 2, "1", None])
    def test_schema_version_must_be_supported_int(self, bad_version):
        m = _manifest()
        m["schemaVersion"] = bad_version
        r = cg.validate_contract_manifest(m)
        assert not r.ok
        assert any("schemaVersion" in x for x in r.reasons)

    def test_missing_command(self):
        m = _manifest()
        del m["command"]
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("command" in x for x in r.reasons)

    def test_command_must_be_str_argv(self):
        m = _manifest(command=["python", 3])
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("command" in x for x in r.reasons)

    def test_empty_defect_classes(self):
        m = _manifest(classes=[])
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("defectClasses" in x for x in r.reasons)

    def test_duplicate_ids(self):
        m = _manifest(classes=[
            {"id": "X", "description": "a", "probeable": True, "coveredBy": ["t"]},
            {"id": "X", "description": "b", "probeable": True, "coveredBy": ["t"]},
        ])
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("duplicate" in x for x in r.reasons)

    def test_non_bool_probeable(self):
        m = _manifest(classes=[
            {"id": "X", "description": "a", "probeable": "yes", "coveredBy": ["t"]},
        ])
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("probeable" in x for x in r.reasons)

    def test_bad_covered_by(self):
        m = _manifest(classes=[
            {"id": "X", "description": "a", "probeable": True, "coveredBy": [1]},
        ])
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("coveredBy" in x for x in r.reasons)

    def test_unknown_top_level_key(self):
        m = _manifest()
        m["surprise"] = 1
        r = cg.validate_contract_manifest(m)
        assert not r.ok and any("unknown top-level" in x for x in r.reasons)

    def test_uncovered_probeable_is_structurally_valid_but_flagged(self):
        # A probeable class with no covering test is schema-valid (so ok=True)
        # but recorded in uncovered_probeable_ids - the GATE turns this into a
        # failure, not the manifest validator.
        m = _manifest(classes=[
            {"id": "U", "description": "uncovered", "probeable": True,
             "coveredBy": []},
            {"id": "R", "description": "residual", "probeable": False},
        ])
        r = cg.validate_contract_manifest(m)
        assert r.ok
        assert r.uncovered_probeable_ids == ("U",)
        assert r.probeable_total == 1 and r.probeable_covered == 0
        assert r.residual_ids == ("R",)

    def test_covered_by_absent_for_residual_ok(self):
        m = _manifest(classes=[
            {"id": "R", "description": "residual", "probeable": False},
        ])
        r = cg.validate_contract_manifest(m)
        assert r.ok and r.residual_ids == ("R",)


# ---------------------------------------------------------------------------
# Floor-result validator
# ---------------------------------------------------------------------------


class TestFloorResultValidator:
    def test_valid_passing(self):
        r = cg.validate_contract_floor_result(_floor_result())
        assert r.ok and r.passed is True

    def test_valid_failing(self):
        r = cg.validate_contract_floor_result(_floor_result(passed=False))
        assert r.ok and r.passed is False

    def test_passed_mismatch_rejected(self):
        # records passed=True but exitCode=1 -> incoherent/tampered.
        fr = _floor_result(passed=True)
        fr["exitCode"] = 1
        r = cg.validate_contract_floor_result(fr)
        assert not r.ok and any("does not agree" in x for x in r.reasons)

    def test_timeout_is_not_passed(self):
        fr = _floor_result(passed=False)
        fr.update(exitCode=None, timedOut=True, passed=False)
        r = cg.validate_contract_floor_result(fr)
        assert r.ok and r.passed is False and r.timed_out is True

    def test_leaked_worktree_is_not_passed(self):
        fr = _floor_result(passed=True)
        fr["worktreeRemoved"] = False
        fr["passed"] = False  # derived: leaked -> not passed
        r = cg.validate_contract_floor_result(fr)
        assert r.ok and r.passed is False

    def test_bool_field_type_checked(self):
        fr = _floor_result()
        fr["ran"] = "yes"
        r = cg.validate_contract_floor_result(fr)
        assert not r.ok and any("ran" in x for x in r.reasons)

    def test_exit_code_bool_rejected(self):
        fr = _floor_result()
        fr["exitCode"] = True
        r = cg.validate_contract_floor_result(fr)
        assert not r.ok and any("exitCode" in x for x in r.reasons)

    @pytest.mark.parametrize("bad_version", [1.0, True, 2])
    def test_schema_version_guard(self, bad_version):
        fr = _floor_result()
        fr["schemaVersion"] = bad_version
        r = cg.validate_contract_floor_result(fr)
        assert not r.ok


# ---------------------------------------------------------------------------
# Producer (drives the S1 cage; real git repo, no metered calls)
# ---------------------------------------------------------------------------


class TestProducer:
    def test_produces_passing_floor(self, tmp_path, git_repo):
        d = _set_dir(tmp_path)
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(_manifest(command=[sys.executable, "-c", "pass"])),
            encoding="utf-8",
        )
        res = cg.produce_contract_floor(d, repo_root=git_repo)
        assert res.ok and res.passed
        # the saved artifact validates and reports passed
        fr = cg.validate_contract_floor_result(res.result_path)
        assert fr.ok and fr.passed
        # provenance: the cage ran and tore down
        assert res.raw["worktreeCreated"] and res.raw["worktreeRemoved"]

    def test_produces_failing_floor(self, tmp_path, git_repo):
        d = _set_dir(tmp_path)
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(_manifest(
                command=[sys.executable, "-c", "import sys; sys.exit(1)"]
            )),
            encoding="utf-8",
        )
        res = cg.produce_contract_floor(d, repo_root=git_repo)
        assert not res.ok and not res.passed
        fr = cg.validate_contract_floor_result(res.result_path)
        assert fr.ok and fr.passed is False and fr.exit_code == 1

    def test_no_manifest_raises(self, tmp_path, git_repo):
        d = _set_dir(tmp_path)
        with pytest.raises(cg.ContractGateError):
            cg.produce_contract_floor(d, repo_root=git_repo)

    def test_invalid_manifest_raises(self, tmp_path, git_repo):
        d = _set_dir(tmp_path)
        bad = _manifest()
        del bad["command"]
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(bad), encoding="utf-8"
        )
        with pytest.raises(cg.ContractGateError):
            cg.produce_contract_floor(d, repo_root=git_repo)

    def test_not_a_git_repo_records_unran_floor(self, tmp_path):
        # The cage reports not-a-repo as a raw error -> floor did not pass.
        d = _set_dir(tmp_path)
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(_manifest()), encoding="utf-8"
        )
        not_repo = tmp_path / "plain"
        not_repo.mkdir()
        res = cg.produce_contract_floor(d, repo_root=not_repo)
        assert not res.passed
        assert any("cage error" in r for r in res.reasons)


# ---------------------------------------------------------------------------
# Close-out gate validator (posture-agnostic)
# ---------------------------------------------------------------------------


def _armed_set(tmp_path, level=REQUIRED, *, manifest=None, floor=None,
               name="068-contract"):
    d = _set_dir(tmp_path, name)
    cg.record_contract_gate(d, level)
    if manifest is not None:
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    if floor is not None:
        (d / cg.CONTRACT_FLOOR_RESULT_FILENAME).write_text(
            json.dumps(floor), encoding="utf-8"
        )
    return d


class TestCloseOutGate:
    def test_none_is_noop(self, tmp_path):
        d = _set_dir(tmp_path)
        r = cg.validate_contract_gate(d)
        assert r.applicable is False and r.ok is True

    def test_happy_path(self, tmp_path):
        d = _armed_set(
            tmp_path, manifest=_manifest(), floor=_floor_result()
        )
        r = cg.validate_contract_gate(d)
        assert r.ok
        assert r.residual_ids == ("DC2",)
        assert "reserved for the path-aware" in r.reason

    def test_missing_manifest_fails(self, tmp_path):
        d = _armed_set(tmp_path, floor=_floor_result())
        r = cg.validate_contract_gate(d)
        assert r.applicable and not r.ok and "no contract-manifest" in r.reason

    def test_manifest_identity_mismatch_fails(self, tmp_path):
        d = _armed_set(
            tmp_path,
            manifest=_manifest(set_name="some-other-set"),
            floor=_floor_result(),
        )
        r = cg.validate_contract_gate(d)
        assert not r.ok and "does not match this set" in r.reason

    def test_manifest_level_mismatch_fails(self, tmp_path):
        d = _armed_set(
            tmp_path,
            level=REQUIRED,
            manifest=_manifest(level=ADVISORY),
            floor=_floor_result(),
        )
        r = cg.validate_contract_gate(d)
        assert not r.ok and "does not match the recorded policy" in r.reason

    def test_uncovered_probeable_fails(self, tmp_path):
        m = _manifest(classes=[
            {"id": "U", "description": "uncovered", "probeable": True,
             "coveredBy": []},
        ])
        d = _armed_set(tmp_path, manifest=m, floor=_floor_result())
        r = cg.validate_contract_gate(d)
        assert not r.ok and "no covering contract test" in r.reason

    def test_missing_floor_fails(self, tmp_path):
        d = _armed_set(tmp_path, manifest=_manifest())
        r = cg.validate_contract_gate(d)
        assert not r.ok and "has not been run" in r.reason

    def test_floor_command_mismatch_fails(self, tmp_path):
        d = _armed_set(
            tmp_path,
            manifest=_manifest(command=[sys.executable, "-c", "pass"]),
            floor=_floor_result(command=[sys.executable, "-c", "other"]),
        )
        r = cg.validate_contract_gate(d)
        assert not r.ok and "does not match this set/manifest" in r.reason

    def test_floor_set_name_mismatch_fails(self, tmp_path):
        d = _armed_set(
            tmp_path,
            manifest=_manifest(),
            floor=_floor_result(set_name="some-other-set"),
        )
        r = cg.validate_contract_gate(d)
        assert not r.ok and "does not match this set" in r.reason

    def test_non_passing_floor_fails(self, tmp_path):
        d = _armed_set(
            tmp_path, manifest=_manifest(), floor=_floor_result(passed=False)
        )
        r = cg.validate_contract_gate(d)
        assert not r.ok and "did not pass" in r.reason

    def test_advisory_happy_path_ok(self, tmp_path):
        d = _armed_set(
            tmp_path,
            level=ADVISORY,
            manifest=_manifest(level=ADVISORY),
            floor=_floor_result(level=ADVISORY),
        )
        r = cg.validate_contract_gate(d)
        assert r.ok and r.applicable

    def test_no_residual_reported(self, tmp_path):
        m = _manifest(classes=[
            {"id": "DC1", "description": "covered", "probeable": True,
             "coveredBy": ["t"]},
        ])
        d = _armed_set(tmp_path, manifest=m, floor=_floor_result())
        r = cg.validate_contract_gate(d)
        assert r.ok and r.residual_ids == ()
        assert "no non-probeable residual" in r.reason


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_validate_none_exit_zero(self, tmp_path, capsys):
        d = _set_dir(tmp_path)
        rc = cg.main(["validate", "--session-set-dir", str(d)])
        assert rc == 0
        assert "contractGate=none" in capsys.readouterr().out

    def test_validate_required_missing_exit_one(self, tmp_path, capsys):
        d = _armed_set(tmp_path)
        rc = cg.main(["validate", "--session-set-dir", str(d)])
        assert rc == 1

    def test_run_produces_and_exits_by_pass(self, tmp_path, git_repo, capsys):
        d = _set_dir(tmp_path)
        (d / cg.CONTRACT_MANIFEST_FILENAME).write_text(
            json.dumps(_manifest(command=[sys.executable, "-c", "pass"])),
            encoding="utf-8",
        )
        rc = cg.main([
            "run", "--session-set-dir", str(d), "--repo-root", str(git_repo)
        ])
        assert rc == 0
        assert "PASSED" in capsys.readouterr().out
        assert (d / cg.CONTRACT_FLOOR_RESULT_FILENAME).is_file()

    def test_run_missing_manifest_exit_two(self, tmp_path, git_repo, capsys):
        d = _set_dir(tmp_path)
        rc = cg.main([
            "run", "--session-set-dir", str(d), "--repo-root", str(git_repo)
        ])
        assert rc == 2
        assert "ERROR" in capsys.readouterr().out

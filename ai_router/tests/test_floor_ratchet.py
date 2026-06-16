"""Set 069 S5 - the quality-gated ceiling->floor ratchet.

Covers the admission gate (the six quality gates + the never-auto-merge and
rubber-stamp-guard safety properties), the builder from a REPRODUCED finding, the
pure-Python artifact validator (L-066-1 parity with the JSON Schema), the
mandatory coverage check, and the CLI. No metered calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

import floor_ratchet as fr  # conftest puts ai_router/ on sys.path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "docs" / "candidate-falsifier.schema.json"
EXAMPLE = REPO_ROOT / "docs" / "candidate-falsifier-schema-example.json"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _good_candidate(**overrides):
    """A candidate that passes every mechanical gate (sign-off still pending)."""
    cand = {
        "id": "CF1",
        "defect": {"findingRef": "openai:0", "description": "a real bug",
                   "severity": "Major"},
        "falsifier": {"templateId": "validator-on-bad-bytes",
                      "args": {"module": "ai_router.contract_gate"}},
        "entrypoint": {"kind": "public_api", "ref": "ai_router.contract_gate"},
        "contractKind": fr.CONTRACT_PUBLIC,
        "failsOnOld": {"ref": "old", "failed": True},
        "passesOnFixed": {"ref": "new", "passed": True},
        "flakeCheck": {"runs": 5, "agreeing": 5, "stable": True},
        "owner": "denmi",
        "humanSignoff": {"status": fr.SIGNOFF_PENDING},
    }
    cand.update(overrides)
    return cand


def _approve(cand, by="denmi"):
    cand = json.loads(json.dumps(cand))
    cand["humanSignoff"] = {"status": fr.SIGNOFF_APPROVED, "by": by}
    return cand


# ---------------------------------------------------------------------------
# Schema <-> validator parity (L-066-1)
# ---------------------------------------------------------------------------


class TestSchemaParity:
    def test_files_exist(self):
        assert SCHEMA.is_file() and EXAMPLE.is_file()

    def test_schema_is_valid(self):
        schema = _load(SCHEMA)
        jsonschema.validators.validator_for(schema).check_schema(schema)

    def test_example_conforms_to_schema(self):
        jsonschema.validate(_load(EXAMPLE), _load(SCHEMA))

    def test_example_passes_python_validator(self):
        art = _load(EXAMPLE)
        res = fr.validate_candidate_falsifiers_artifact(
            art, expected_set_name="069-automated-pull-critique-capabilities")
        assert res.ok and res.code == fr.CANDIDATE_OK
        statuses = {d.candidate_id: d.status for d in res.decisions}
        assert statuses == {"CF1": fr.ADMIT_ADMITTED, "CF2": fr.ADMIT_WAIVED}

    def test_schemaversion_float_and_bool_rejected_like_schema(self):
        # L-066-1: 1.0 / True pass `in (1,)` in Python but the schema's integer
        # rejects them. The Python validator must too.
        for bad in (1.0, True):
            art = _good_artifact()
            art["schemaVersion"] = bad
            res = fr.validate_candidate_falsifiers_artifact(art)
            assert not res.ok and res.code == fr.CANDIDATE_BAD_SCHEMA_VERSION

    def test_flake_runs_bool_rejected(self):
        # flakeCheck.runs must be a true integer; True must not satisfy it.
        cand = _approve(_good_candidate(flakeCheck={"runs": True, "agreeing": True,
                                                    "stable": True}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED


def _good_artifact(**overrides):
    art = {
        "schemaVersion": 1,
        "sessionSetName": "069-x",
        "candidates": [_good_candidate()],
    }
    art.update(overrides)
    return art


# ---------------------------------------------------------------------------
# The admission gate - the six quality gates
# ---------------------------------------------------------------------------


class TestAdmissionGate:
    def test_pending_when_gates_pass_but_no_signoff(self):
        d = fr.admission_decision(_good_candidate())
        assert d.status == fr.ADMIT_PENDING and not d.admitted
        assert any("sign-off" in r for r in d.reasons)

    def test_admitted_when_gates_pass_and_approved(self):
        d = fr.admission_decision(_approve(_good_candidate()))
        assert d.status == fr.ADMIT_ADMITTED and d.admitted
        assert d.reasons == ()

    def test_approved_without_by_is_not_admitted(self):
        cand = _good_candidate()
        cand["humanSignoff"] = {"status": fr.SIGNOFF_APPROVED}
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("approver" in r for r in d.reasons)

    def test_fails_on_old_required(self):
        cand = _approve(_good_candidate(failsOnOld={"ref": "old", "failed": False}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("failsOnOld" in r for r in d.reasons)

    def test_passes_on_fixed_must_differ_from_old_ref(self):
        cand = _approve(_good_candidate(
            failsOnOld={"ref": "same", "failed": True},
            passesOnFixed={"ref": "same", "passed": True}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("differential" in r for r in d.reasons)

    def test_incidental_contract_rejected_even_with_public_entrypoint(self):
        cand = _approve(_good_candidate(contractKind=fr.CONTRACT_INCIDENTAL))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("incidental" in r for r in d.reasons)

    def test_agent_harness_entrypoint_rejected(self):
        cand = _approve(_good_candidate(
            entrypoint={"kind": "agent_harness", "ref": "x"}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("public surface" in r for r in d.reasons)

    def test_flake_runs_below_minimum_rejected(self):
        cand = _approve(_good_candidate(
            flakeCheck={"runs": 2, "agreeing": 2, "stable": True}))
        d = fr.admission_decision(cand, min_flake_runs=3)
        assert d.status == fr.ADMIT_REJECTED
        assert any("minimum" in r for r in d.reasons)

    def test_flake_not_stable_rejected(self):
        cand = _approve(_good_candidate(
            flakeCheck={"runs": 5, "agreeing": 5, "stable": False}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("flaked" in r for r in d.reasons)

    def test_flake_no_majority_rejected(self):
        cand = _approve(_good_candidate(
            flakeCheck={"runs": 4, "agreeing": 2, "stable": True}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("majority" in r for r in d.reasons)

    def test_missing_owner_rejected(self):
        cand = _approve(_good_candidate(owner="  "))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED
        assert any("owner" in r for r in d.reasons)

    def test_rubber_stamp_guard_approval_cannot_override_failing_gate(self):
        # The safety property: a human can approve, but the gate still refuses to
        # admit a falsifier that does not actually fail-on-old.
        cand = _approve(_good_candidate(failsOnOld={"ref": "old", "failed": False}))
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_REJECTED and not d.admitted

    def test_min_flake_runs_floor_ignores_garbage(self):
        # A nonsense min is replaced by the default, never crashes.
        d = fr.admission_decision(_approve(_good_candidate()), min_flake_runs=0)
        assert d.status == fr.ADMIT_ADMITTED

    def test_non_dict_candidate_never_raises(self):
        for bad in (None, 7, "x", []):
            d = fr.admission_decision(bad)
            assert d.status == fr.ADMIT_PENDING and not d.admitted


class TestWaiver:
    def test_waiver_with_note_is_clean(self):
        cand = _good_candidate(humanSignoff={"status": fr.SIGNOFF_WAIVED,
                                             "by": "denmi", "note": "incidental"})
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_WAIVED and not d.admitted and d.reasons == ()

    def test_waiver_without_note_flags(self):
        cand = _good_candidate(humanSignoff={"status": fr.SIGNOFF_WAIVED})
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_WAIVED
        assert any("note" in r for r in d.reasons)

    def test_waiver_short_circuits_failing_gates(self):
        # A waiver does not require the mechanical gates to pass - it is an
        # explicit decision not to promote.
        cand = _good_candidate(
            failsOnOld={"ref": "old", "failed": False},
            humanSignoff={"status": fr.SIGNOFF_WAIVED, "note": "won't fix"})
        d = fr.admission_decision(cand)
        assert d.status == fr.ADMIT_WAIVED


# ---------------------------------------------------------------------------
# Artifact validation
# ---------------------------------------------------------------------------


class TestArtifactValidation:
    def test_good_artifact_ok(self):
        res = fr.validate_candidate_falsifiers_artifact(_good_artifact())
        assert res.ok and len(res.decisions) == 1

    def test_not_an_object(self):
        res = fr.validate_candidate_falsifiers_artifact([1, 2])
        assert not res.ok and res.code == fr.CANDIDATE_NOT_AN_OBJECT

    def test_identity_mismatch(self):
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(), expected_set_name="some-other-set")
        assert not res.ok and res.code == fr.CANDIDATE_IDENTITY_MISMATCH

    def test_empty_candidates_rejected(self):
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[]))
        assert not res.ok and res.code == fr.CANDIDATE_BAD_STRUCTURE

    def test_duplicate_ids_rejected(self):
        art = _good_artifact(candidates=[_good_candidate(), _good_candidate()])
        res = fr.validate_candidate_falsifiers_artifact(art)
        assert not res.ok and any("duplicated" in r for r in res.reasons)

    def test_falsifier_both_ids_rejected(self):
        cand = _good_candidate(falsifier={"commandId": "a", "templateId": "b"})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("exactly one" in r for r in res.reasons)

    def test_falsifier_neither_id_rejected(self):
        cand = _good_candidate(falsifier={"args": {}})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("commandId OR a templateId" in r
                                  for r in res.reasons)

    def test_bad_contract_kind_rejected(self):
        cand = _good_candidate(contractKind="nonsense")
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("contractKind" in r for r in res.reasons)

    def test_bad_signoff_status_rejected(self):
        cand = _good_candidate(humanSignoff={"status": "maybe"})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("humanSignoff.status" in r for r in res.reasons)

    def test_severity_wrong_type_rejected(self):
        cand = _good_candidate()
        cand["defect"]["severity"] = 7
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("severity" in r for r in res.reasons)

    def test_unknown_top_level_key_rejected(self):
        # The schema closes the top-level object; an extra key (e.g. a smuggled
        # verdict) must be rejected (L-066-1).
        art = _good_artifact()
        art["verdict"] = "admitted"
        res = fr.validate_candidate_falsifiers_artifact(art)
        assert not res.ok and any("top-level" in r for r in res.reasons)

    def test_wrong_typed_notes_rejected(self):
        res = fr.validate_candidate_falsifiers_artifact(_good_artifact(notes=7))
        assert not res.ok and any("notes" in r for r in res.reasons)

    @pytest.mark.parametrize("bad_kind", ["agent_harness", "arbitrary", ""])
    def test_entrypoint_kind_enum_enforced_structurally(self, bad_kind):
        cand = _good_candidate(entrypoint={"kind": bad_kind, "ref": "x"})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("entrypoint.kind" in r for r in res.reasons)

    def test_flakecheck_runs_bool_rejected_structurally(self):
        cand = _good_candidate(flakeCheck={"runs": True, "agreeing": 3,
                                           "stable": True})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("flakeCheck.runs" in r for r in res.reasons)

    def test_flakecheck_stable_int_rejected_structurally(self):
        cand = _good_candidate(flakeCheck={"runs": 5, "agreeing": 5, "stable": 1})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("flakeCheck.stable" in r for r in res.reasons)

    def test_failson_old_failed_wrong_type_rejected(self):
        cand = _good_candidate(failsOnOld={"ref": "old", "failed": "yes"})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("failsOnOld.failed" in r for r in res.reasons)

    def test_signoff_note_wrong_type_rejected(self):
        cand = _good_candidate(humanSignoff={"status": "waived", "note": 7})
        res = fr.validate_candidate_falsifiers_artifact(
            _good_artifact(candidates=[cand]))
        assert not res.ok and any("humanSignoff.note" in r for r in res.reasons)


# ---------------------------------------------------------------------------
# Builder from a reproduced finding
# ---------------------------------------------------------------------------


def _repro_finding():
    return {
        "description": "unicode crash",
        "severity": "Major",
        "evidenceTier": "REPRODUCED",
        "transcript": {
            "pinnedRef": "abc123",
            "templateId": "validator-on-bad-bytes",
            "args": {"module": "ai_router.contract_gate"},
            "pristineCheckout": True,
            "exitCode": 1,
            "rawOutput": "Traceback...",
            "outputHash": "sha256:x",
            "entrypoint": {"kind": "public_api", "ref": "ai_router.contract_gate"},
            "replay": {"pristineCheckout": True, "outputHash": "sha256:x"},
        },
    }


class TestBuilder:
    def test_builds_pending_candidate_from_transcript(self):
        cand = fr.build_candidate_from_finding(
            _repro_finding(), candidate_id="CF1", finding_ref="openai:0",
            owner="denmi",
            fails_on_old={"ref": "old", "failed": True},
            passes_on_fixed={"ref": "new", "passed": True},
            flake_check={"runs": 5, "agreeing": 5, "stable": True})
        assert cand["humanSignoff"] == {"status": fr.SIGNOFF_PENDING}
        assert cand["falsifier"]["templateId"] == "validator-on-bad-bytes"
        assert cand["entrypoint"]["kind"] == "public_api"
        assert cand["defect"]["severity"] == "Major"
        # pending until a human approves - never auto-merged
        assert fr.admission_decision(cand).status == fr.ADMIT_PENDING

    def test_builder_never_mints_approval(self):
        cand = fr.build_candidate_from_finding(
            _repro_finding(), candidate_id="CF1", finding_ref="x", owner="denmi")
        assert cand["humanSignoff"]["status"] == fr.SIGNOFF_PENDING

    def test_builder_rejects_non_reproduced_finding(self):
        f = _repro_finding()
        f["evidenceTier"] = "ASSERTED"
        with pytest.raises(ValueError):
            fr.build_candidate_from_finding(
                f, candidate_id="x", finding_ref="x", owner="o")

    def test_builder_rejects_finding_without_transcript(self):
        f = {"description": "x", "evidenceTier": "REPRODUCED"}
        with pytest.raises(ValueError):
            fr.build_candidate_from_finding(
                f, candidate_id="x", finding_ref="x", owner="o")


# ---------------------------------------------------------------------------
# Mandatory coverage
# ---------------------------------------------------------------------------


def _critique_with_reproduced():
    finding = _repro_finding()
    return {
        "schemaVersion": 1,
        "sessionSetName": "069-x",
        "pathAwareCritique": "required",
        "critiques": [
            {"provider": "openai", "model": "m", "verdict": "ISSUES_FOUND",
             "findings": [finding]},
            {"provider": "google", "model": "m", "verdict": "VERIFIED",
             "summary": "looks fine"},
        ],
    }


class TestCoverage:
    def test_reproduced_findings_extracted(self):
        repro = fr.reproduced_findings(_critique_with_reproduced())
        assert len(repro) == 1 and repro[0][0] == "openai:0"

    def test_covered_by_findingref_passes(self):
        crit = _critique_with_reproduced()
        cand = fr.build_candidate_from_finding(
            crit["critiques"][0]["findings"][0],
            candidate_id="CF1", finding_ref="openai:0", owner="denmi")
        art = {"schemaVersion": 1, "sessionSetName": "069-x",
               "candidates": [cand]}
        cov = fr.check_floor_ratchet_coverage(crit, art)
        assert cov.ok and cov.pending == 1 and cov.uncovered == ()

    def test_uncovered_reproduced_defect_flagged(self):
        crit = _critique_with_reproduced()
        art = {"schemaVersion": 1, "sessionSetName": "069-x",
               "candidates": [_good_candidate(defect={
                   "findingRef": "unrelated:9", "description": "x"})]}
        cov = fr.check_floor_ratchet_coverage(crit, art)
        assert not cov.ok and "openai:0" in cov.uncovered

    def test_no_reproduced_defects_is_vacuously_covered(self):
        crit = {"schemaVersion": 1, "sessionSetName": "069-x",
                "pathAwareCritique": "required",
                "critiques": [{"provider": "openai", "model": "m",
                               "verdict": "VERIFIED", "summary": "clean"}]}
        cov = fr.check_floor_ratchet_coverage(crit, {})
        assert cov.ok

    def test_reproduced_defect_with_no_artifact_flagged(self):
        cov = fr.check_floor_ratchet_coverage(_critique_with_reproduced(), {})
        assert not cov.ok
        assert cov.reasons and "no valid" in cov.reasons[0]

    def test_rejected_candidate_does_not_satisfy_coverage(self):
        # A candidate a human approved but that fails a mechanical gate is
        # REJECTED, and a rejected candidate must NOT cover its finding (it is
        # broken, not done).
        crit = _critique_with_reproduced()
        rejected = _approve(_good_candidate(
            defect={"findingRef": "openai:0", "description": "x"},
            failsOnOld={"ref": "old", "failed": False}))  # fails a gate
        art = {"schemaVersion": 1, "sessionSetName": "069-x",
               "candidates": [rejected]}
        cov = fr.check_floor_ratchet_coverage(crit, art)
        assert not cov.ok and "openai:0" in cov.uncovered
        assert cov.rejected == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def test_validate_admitted(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        (d / fr.CANDIDATE_FALSIFIER_FILENAME).write_text(
            json.dumps(_good_artifact(
                sessionSetName="069-x",
                candidates=[_approve(_good_candidate())])),
            encoding="utf-8")
        rc = fr.main(["--session-set-dir", str(d)])
        out = capsys.readouterr().out
        assert rc == 0 and "admitted" in out

    def test_validate_rejected_returns_nonzero(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        bad = _approve(_good_candidate(failsOnOld={"ref": "o", "failed": False}))
        (d / fr.CANDIDATE_FALSIFIER_FILENAME).write_text(
            json.dumps(_good_artifact(sessionSetName="069-x", candidates=[bad])),
            encoding="utf-8")
        rc = fr.main(["--session-set-dir", str(d)])
        assert rc == 1
        assert "rejected" in capsys.readouterr().out

    def test_missing_artifact_is_not_an_error(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        rc = fr.main(["--session-set-dir", str(d)])
        assert rc == 0 and "no candidate-falsifiers.json" in capsys.readouterr().out

    def test_unreadable_artifact_bad_bytes(self, tmp_path, capsys):
        # L-069-1: a malformed-bytes artifact is reported, never crashes the CLI.
        d = tmp_path / "069-x"
        d.mkdir()
        (d / fr.CANDIDATE_FALSIFIER_FILENAME).write_bytes(b"\xff\xfe not json")
        rc = fr.main(["--session-set-dir", str(d)])
        assert rc == 2 and "unreadable" in capsys.readouterr().out

"""Set 069 S5 - the measured replacement gate (benchmark + scoreboard).

Covers the two pure-Python validators (L-066-1 parity with the JSON Schemas),
the derived scoring (recall / precision / replay-success / false-REPRODUCED), the
honesty rules (underpowered forces meets=False; the manual run is never retired),
and the CLI. No metered calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

import replacement_gate as rg  # conftest puts ai_router/ on sys.path

REPO_ROOT = Path(__file__).resolve().parents[2]
REG_SCHEMA = REPO_ROOT / "docs" / "benchmark-registration.schema.json"
SB_SCHEMA = REPO_ROOT / "docs" / "replacement-scoreboard.schema.json"
REG_EXAMPLE = REPO_ROOT / "docs" / "benchmark-registration-schema-example.json"
SB_EXAMPLE = REPO_ROOT / "docs" / "replacement-scoreboard-schema-example.json"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _registration(**overrides):
    reg = {
        "schemaVersion": 1,
        "name": "bench",
        "registeredAt": "2026-06-16",
        "minCasesForPower": 3,
        "thresholds": {"recall": 0.8, "precision": 0.8, "replaySuccess": 0.8,
                       "maxFalseReproducedRate": 0.1},
        "cases": [
            {"id": "S1", "kind": "seeded", "defectClass": "a", "description": "x"},
            {"id": "S2", "kind": "seeded", "defectClass": "b", "description": "y"},
            {"id": "H1", "kind": "holdout", "defectClass": "c", "description": "z",
             "sourceRef": "0.22.0"},
        ],
    }
    reg.update(overrides)
    return reg


def _scoreboard(**overrides):
    sb = {
        "schemaVersion": 1,
        "benchmarkName": "bench",
        "scoredAt": "2026-06-16",
        "spuriousDetections": 0,
        "outcomes": [
            {"caseId": "S1", "detected": True, "replayed": True,
             "falseReproduced": False},
            {"caseId": "S2", "detected": True, "replayed": True,
             "falseReproduced": False},
            {"caseId": "H1", "detected": True, "replayed": True,
             "falseReproduced": False},
        ],
        "telemetry": {"escapedDefectRate": 0.0, "falsePositiveChurn": 0,
                      "predicateShouldHaveFiredMisses": 0,
                      "timing": {"introStageCatches": 3, "endOfSetCatches": 0}},
    }
    sb.update(overrides)
    return sb


# ---------------------------------------------------------------------------
# Schema parity
# ---------------------------------------------------------------------------


class TestSchemaParity:
    def test_files_exist(self):
        for p in (REG_SCHEMA, SB_SCHEMA, REG_EXAMPLE, SB_EXAMPLE):
            assert p.is_file()

    def test_schemas_valid(self):
        for p in (REG_SCHEMA, SB_SCHEMA):
            schema = _load(p)
            jsonschema.validators.validator_for(schema).check_schema(schema)

    def test_examples_conform(self):
        jsonschema.validate(_load(REG_EXAMPLE), _load(REG_SCHEMA))
        jsonschema.validate(_load(SB_EXAMPLE), _load(SB_SCHEMA))

    def test_examples_pass_python_validators(self):
        assert rg.validate_benchmark_registration(_load(REG_EXAMPLE)).ok
        assert rg.validate_scoreboard(_load(SB_EXAMPLE)).ok

    def test_example_score_is_underpowered_and_honest(self):
        s = rg.score_benchmark(_load(REG_EXAMPLE), _load(SB_EXAMPLE))
        assert s.ok and s.underpowered and not s.meets_thresholds
        assert s.cadence_recommendation == rg.CADENCE_MANUAL_MANDATORY

    def test_schemaversion_float_bool_rejected(self):
        for bad in (1.0, True):
            assert rg.validate_benchmark_registration(
                _registration(schemaVersion=bad)).code == \
                rg.REPLACEMENT_BAD_SCHEMA_VERSION
            assert rg.validate_scoreboard(
                _scoreboard(schemaVersion=bad)).code == \
                rg.REPLACEMENT_BAD_SCHEMA_VERSION

    def test_threshold_out_of_unit_range_rejected(self):
        reg = _registration()
        reg["thresholds"]["recall"] = 1.5
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("[0, 1]" in r for r in res.reasons)

    def test_minpower_bool_rejected(self):
        res = rg.validate_benchmark_registration(_registration(minCasesForPower=True))
        assert not res.ok


# ---------------------------------------------------------------------------
# Registration validation
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_good(self):
        assert rg.validate_benchmark_registration(_registration()).ok

    def test_not_an_object(self):
        assert rg.validate_benchmark_registration(5).code == \
            rg.REPLACEMENT_NOT_AN_OBJECT

    def test_identity_mismatch(self):
        res = rg.validate_benchmark_registration(
            _registration(), expected_name="other")
        assert not res.ok and res.code == rg.REPLACEMENT_IDENTITY_MISMATCH

    def test_missing_thresholds(self):
        reg = _registration()
        del reg["thresholds"]
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("thresholds" in r for r in res.reasons)

    def test_holdout_required(self):
        reg = _registration(cases=[
            {"id": "S1", "kind": "seeded", "defectClass": "a", "description": "x"}])
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("holdout" in r for r in res.reasons)

    def test_duplicate_case_ids(self):
        reg = _registration(cases=[
            {"id": "S1", "kind": "seeded", "defectClass": "a", "description": "x"},
            {"id": "S1", "kind": "holdout", "defectClass": "b", "description": "y"}])
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("duplicated" in r for r in res.reasons)

    def test_bad_case_kind(self):
        reg = _registration(cases=[
            {"id": "S1", "kind": "weird", "defectClass": "a", "description": "x"},
            {"id": "H1", "kind": "holdout", "defectClass": "b", "description": "y"}])
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("kind" in r for r in res.reasons)

    def test_probeable_wrong_type(self):
        reg = _registration()
        reg["cases"][0]["probeable"] = "yes"
        res = rg.validate_benchmark_registration(reg)
        assert not res.ok and any("probeable" in r for r in res.reasons)

    def test_unknown_top_level_key_rejected(self):
        res = rg.validate_benchmark_registration(_registration(verdict="pass"))
        assert not res.ok and any("top-level" in r for r in res.reasons)

    def test_wrong_typed_notes_rejected(self):
        res = rg.validate_benchmark_registration(_registration(notes=7))
        assert not res.ok and any("notes" in r for r in res.reasons)


# ---------------------------------------------------------------------------
# Scoreboard validation
# ---------------------------------------------------------------------------


class TestScoreboard:
    def test_good(self):
        assert rg.validate_scoreboard(_scoreboard()).ok

    def test_missing_telemetry(self):
        sb = _scoreboard()
        del sb["telemetry"]
        res = rg.validate_scoreboard(sb)
        assert not res.ok and any("telemetry" in r for r in res.reasons)

    def test_outcome_non_bool_detected(self):
        sb = _scoreboard()
        sb["outcomes"][0]["detected"] = "true"
        res = rg.validate_scoreboard(sb)
        assert not res.ok and any("detected" in r for r in res.reasons)

    def test_telemetry_rate_out_of_range(self):
        sb = _scoreboard()
        sb["telemetry"]["escapedDefectRate"] = 2.0
        res = rg.validate_scoreboard(sb)
        assert not res.ok and any("escapedDefectRate" in r for r in res.reasons)

    def test_telemetry_predicate_misses_bool_rejected(self):
        sb = _scoreboard()
        sb["telemetry"]["predicateShouldHaveFiredMisses"] = True
        res = rg.validate_scoreboard(sb)
        assert not res.ok

    def test_missing_timing(self):
        sb = _scoreboard()
        del sb["telemetry"]["timing"]
        res = rg.validate_scoreboard(sb)
        assert not res.ok and any("timing" in r for r in res.reasons)

    def test_spurious_negative_rejected(self):
        res = rg.validate_scoreboard(_scoreboard(spuriousDetections=-1))
        assert not res.ok

    def test_scoreboard_rejects_smuggled_verdict_field(self):
        # The C.1 loophole: a scoreboard must NOT carry a hand-written verdict.
        for key in ("verdict", "meets_thresholds", "cadence_recommendation"):
            sb = _scoreboard()
            sb[key] = True
            res = rg.validate_scoreboard(sb)
            assert not res.ok and any("top-level" in r for r in res.reasons)

    def test_scoreboard_wrong_typed_notes_rejected(self):
        res = rg.validate_scoreboard(_scoreboard(notes=7))
        assert not res.ok and any("notes" in r for r in res.reasons)

    def test_negative_timing_rejected(self):
        sb = _scoreboard()
        sb["telemetry"]["timing"]["introStageCatches"] = -1
        res = rg.validate_scoreboard(sb)
        assert not res.ok and any("introStageCatches" in r for r in res.reasons)


# ---------------------------------------------------------------------------
# Scoring - the derived verdict
# ---------------------------------------------------------------------------


class TestScoring:
    def test_perfect_powered_meets_and_recommends_backstop(self):
        reg = _registration(minCasesForPower=3)
        s = rg.score_benchmark(reg, _scoreboard())
        assert s.ok and not s.underpowered
        assert s.recall == 1.0 and s.precision == 1.0 and s.replay_success == 1.0
        assert s.false_reproduced_rate == 0.0
        assert s.meets_thresholds
        assert s.cadence_recommendation == rg.CADENCE_MANUAL_BACKSTOP

    def test_underpowered_forces_not_met(self):
        reg = _registration(minCasesForPower=100)
        s = rg.score_benchmark(reg, _scoreboard())
        assert s.underpowered and not s.meets_thresholds
        assert s.cadence_recommendation == rg.CADENCE_MANUAL_MANDATORY
        assert any("underpowered" in r for r in s.reasons)

    def test_precision_counts_spurious_detections(self):
        reg = _registration(minCasesForPower=3)
        sb = _scoreboard(spuriousDetections=1)
        s = rg.score_benchmark(reg, sb)
        # 3 detected / (3 + 1 spurious) = 0.75
        assert s.precision == 0.75 and not s.meets_thresholds

    def test_replay_success_below_threshold_fails(self):
        reg = _registration(minCasesForPower=3)
        sb = _scoreboard()
        sb["outcomes"][2]["replayed"] = False  # 2/3 replayed
        s = rg.score_benchmark(reg, sb)
        assert round(s.replay_success, 3) == 0.667 and not s.meets_thresholds

    def test_false_reproduced_rate_caps_meets(self):
        reg = _registration(minCasesForPower=3)
        sb = _scoreboard()
        sb["outcomes"][0]["falseReproduced"] = True  # 1/3 falsely REPRODUCED
        s = rg.score_benchmark(reg, sb)
        assert round(s.false_reproduced_rate, 3) == 0.333
        assert not s.meets_thresholds

    def test_no_detections_metrics_are_none_not_zero(self):
        reg = _registration(minCasesForPower=3)
        sb = _scoreboard(outcomes=[
            {"caseId": "S1", "detected": False, "replayed": False,
             "falseReproduced": False},
            {"caseId": "S2", "detected": False, "replayed": False,
             "falseReproduced": False},
            {"caseId": "H1", "detected": False, "replayed": False,
             "falseReproduced": False}])
        s = rg.score_benchmark(reg, sb)
        assert s.recall == 0.0
        assert s.precision is None and s.replay_success is None
        assert s.false_reproduced_rate is None
        assert not s.meets_thresholds

    def test_unregistered_caseid_rejected(self):
        reg = _registration(minCasesForPower=3)
        sb = _scoreboard()
        sb["outcomes"].append({"caseId": "ZZ", "detected": True, "replayed": True,
                               "falseReproduced": False})
        s = rg.score_benchmark(reg, sb)
        assert not s.ok and any("not a registered case" in r for r in s.reasons)

    def test_name_mismatch_rejected(self):
        s = rg.score_benchmark(_registration(), _scoreboard(benchmarkName="other"))
        assert not s.ok

    def test_invalid_registration_propagates(self):
        s = rg.score_benchmark({"schemaVersion": 9}, _scoreboard())
        assert not s.ok and s.cadence_recommendation == rg.CADENCE_MANUAL_MANDATORY


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def _write(self, d, reg, sb):
        (d / rg.BENCHMARK_REGISTRATION_FILENAME).write_text(
            json.dumps(reg), encoding="utf-8")
        (d / rg.REPLACEMENT_SCOREBOARD_FILENAME).write_text(
            json.dumps(sb), encoding="utf-8")

    def test_score_meets(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        self._write(d, _registration(minCasesForPower=3), _scoreboard())
        rc = rg.main(["--session-set-dir", str(d)])
        out = capsys.readouterr().out
        assert rc == 0 and rg.CADENCE_MANUAL_BACKSTOP in out

    def test_score_underpowered(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        self._write(d, _registration(minCasesForPower=100), _scoreboard())
        rc = rg.main(["--session-set-dir", str(d)])
        out = capsys.readouterr().out
        assert rc == 0 and rg.CADENCE_MANUAL_MANDATORY in out

    def test_missing_artifacts(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        rc = rg.main(["--session-set-dir", str(d)])
        assert rc == 0 and "missing artifact" in capsys.readouterr().out

    def test_unreadable_bad_bytes(self, tmp_path, capsys):
        d = tmp_path / "069-x"
        d.mkdir()
        (d / rg.BENCHMARK_REGISTRATION_FILENAME).write_bytes(b"\xff\xfe x")
        (d / rg.REPLACEMENT_SCOREBOARD_FILENAME).write_text("{}", encoding="utf-8")
        rc = rg.main(["--session-set-dir", str(d)])
        assert rc == 2 and "unreadable" in capsys.readouterr().out

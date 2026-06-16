"""Set 068 S5 - JSON Schema <-> pure-Python validator parity for the contract gate.

Per L-066-1 a pure-Python validator that mirrors a JSON Schema drifts looser
unless every schema-constrained field (required AND optional) is parity-tested.
This module pins, for BOTH artifacts (contract-manifest.json,
contract-floor-result.json):

- the schema is itself a valid JSON Schema;
- the shipped example conforms to the schema AND passes the Python validator
  (the dual-validation drift guard);
- the structural guardrails (required fields, closed envelope, types);
- the documented Python-only semantic rules JSON Schema cannot express
  (manifest: uncovered-probeable + the gate's coverage rule; floor-result: the
  derived 'passed' must agree with the recorded flag).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

import contract_gate as cg  # conftest puts ai_router/ on sys.path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCHEMA = REPO_ROOT / "docs" / "contract-manifest.schema.json"
FLOOR_SCHEMA = REPO_ROOT / "docs" / "contract-floor-result.schema.json"
MANIFEST_EXAMPLE = REPO_ROOT / "docs" / "contract-manifest-schema-example.json"
FLOOR_EXAMPLE = REPO_ROOT / "docs" / "contract-floor-result-schema-example.json"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _validator(schema_path):
    schema = _load(schema_path)
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


@pytest.fixture(scope="module")
def manifest_validator():
    return _validator(MANIFEST_SCHEMA)


@pytest.fixture(scope="module")
def floor_validator():
    return _validator(FLOOR_SCHEMA)


def _schema_ok(validator, env) -> bool:
    try:
        validator.validate(env)
        return True
    except jsonschema.ValidationError:
        return False


# ---------------------------------------------------------------------------
# Files exist + example fixtures conform to both validators
# ---------------------------------------------------------------------------


class TestArtifactFilesExist:
    def test_schema_files_exist(self):
        assert MANIFEST_SCHEMA.is_file() and FLOOR_SCHEMA.is_file()

    def test_example_files_exist(self):
        assert MANIFEST_EXAMPLE.is_file() and FLOOR_EXAMPLE.is_file()


class TestExampleFixtures:
    def test_manifest_example_conforms_to_schema(self, manifest_validator):
        manifest_validator.validate(_load(MANIFEST_EXAMPLE))

    def test_manifest_example_passes_python_validator(self):
        res = cg.validate_contract_manifest(_load(MANIFEST_EXAMPLE))
        assert res.ok and res.code == cg.ARTIFACT_VALID
        assert res.probeable_total == 2 and res.probeable_covered == 2
        assert res.residual_ids == ("DC3",)

    def test_floor_example_conforms_to_schema(self, floor_validator):
        floor_validator.validate(_load(FLOOR_EXAMPLE))

    def test_floor_example_passes_python_validator(self):
        res = cg.validate_contract_floor_result(_load(FLOOR_EXAMPLE))
        assert res.ok and res.passed is True


# ---------------------------------------------------------------------------
# Manifest envelope parity
# ---------------------------------------------------------------------------


class TestManifestParity:
    def _malformations(self):
        out = []
        base = _load(MANIFEST_EXAMPLE)

        a = json.loads(json.dumps(base)); a["bogus"] = 1
        out.append(("extra-top-key", a))
        b = json.loads(json.dumps(base)); del b["command"]
        out.append(("missing-command", b))
        c = json.loads(json.dumps(base)); c["command"] = []
        out.append(("empty-command", c))
        d = json.loads(json.dumps(base)); d["schemaVersion"] = 2
        out.append(("bad-version", d))
        e = json.loads(json.dumps(base)); e["contractGate"] = "bogus"
        out.append(("bad-level", e))
        f = json.loads(json.dumps(base)); f["defectClasses"] = []
        out.append(("empty-classes", f))
        g = json.loads(json.dumps(base)); g["defectClasses"][0]["probeable"] = "yes"
        out.append(("non-bool-probeable", g))
        h = json.loads(json.dumps(base)); del h["defectClasses"][0]["id"]
        out.append(("class-missing-id", h))
        return out

    def test_malformations_rejected_by_both(self, manifest_validator):
        for label, env in self._malformations():
            assert not _schema_ok(manifest_validator, env), \
                f"{label}: schema unexpectedly accepted"
            assert not cg.validate_contract_manifest(env).ok, \
                f"{label}: python validator unexpectedly accepted"

    def test_clean_accepted_by_both(self, manifest_validator):
        env = _load(MANIFEST_EXAMPLE)
        assert _schema_ok(manifest_validator, env)
        assert cg.validate_contract_manifest(env).ok

    def test_uncovered_probeable_is_python_semantic_only(self, manifest_validator):
        # The "a probeable class must name a covering test" rule is enforced by
        # the GATE, not the schema (JSON Schema cannot express it). A manifest
        # with an uncovered probeable class is schema-valid AND manifest-valid;
        # the gate (validate_contract_gate) is what fails it.
        env = _load(MANIFEST_EXAMPLE)
        env["defectClasses"][0]["coveredBy"] = []
        assert _schema_ok(manifest_validator, env)
        res = cg.validate_contract_manifest(env)
        assert res.ok and "DC1" in res.uncovered_probeable_ids


# ---------------------------------------------------------------------------
# Floor-result envelope parity
# ---------------------------------------------------------------------------


class TestFloorParity:
    def _malformations(self):
        out = []
        base = _load(FLOOR_EXAMPLE)

        a = json.loads(json.dumps(base)); a["bogus"] = 1
        out.append(("extra-top-key", a))
        b = json.loads(json.dumps(base)); del b["ran"]
        out.append(("missing-ran", b))
        c = json.loads(json.dumps(base)); c["ran"] = "yes"
        out.append(("non-bool-ran", c))
        d = json.loads(json.dumps(base)); d["schemaVersion"] = 2
        out.append(("bad-version", d))
        e = json.loads(json.dumps(base)); e["exitCode"] = "0"
        out.append(("string-exit-code", e))
        return out

    def test_malformations_rejected_by_both(self, floor_validator):
        for label, env in self._malformations():
            assert not _schema_ok(floor_validator, env), \
                f"{label}: schema unexpectedly accepted"
            assert not cg.validate_contract_floor_result(env).ok, \
                f"{label}: python validator unexpectedly accepted"

    def test_clean_accepted_by_both(self, floor_validator):
        env = _load(FLOOR_EXAMPLE)
        assert _schema_ok(floor_validator, env)
        assert cg.validate_contract_floor_result(env).ok

    def test_passed_mismatch_is_python_semantic_only(self, floor_validator):
        # 'passed must agree with the derived criterion' is a Python-only rule
        # (JSON Schema cannot cross-check fields). A schema-valid result that
        # records passed=true with exitCode=1 passes the schema but fails the
        # Python validator.
        env = _load(FLOOR_EXAMPLE)
        env["exitCode"] = 1  # but passed still true
        assert _schema_ok(floor_validator, env)
        res = cg.validate_contract_floor_result(env)
        assert not res.ok and any("does not agree" in r for r in res.reasons)

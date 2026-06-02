"""Tests for the root-level structured verifier-findings artifact.

Set 055 locked a docs/schema/example contract for `sN-issues.json`
with **no runtime reader**. These tests therefore validate the static
contract rather than any importable write path:

- the JSON Schema at ``docs/session-issues.schema.json`` is itself a
  valid schema,
- the shipped example fixture
  (``docs/session-issues-schema-example.json``) conforms to it and
  honors the locked invariant ("presence means issues found"),
- the documented optionality holds: a minimal envelope with bare
  verifier issues is valid, and the ``resolution_*`` annotations are
  genuinely optional,
- the guardrails hold: no empty-issues file, top-level envelope is
  closed, issue objects tolerate extra verifier-emitted keys.

The fixture test is the drift guard: if the example or the schema
changes incompatibly, this fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "session-issues.schema.json"
EXAMPLE_PATH = REPO_ROOT / "docs" / "session-issues-schema-example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validator(schema):
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _minimal_envelope() -> dict:
    """The smallest valid findings artifact: five envelope fields and
    a single bare verifier issue with no resolution annotations."""
    return {
        "schemaVersion": 1,
        "sessionNumber": 2,
        "verificationRound": 1,
        "verificationVerdict": "ISSUES_FOUND",
        "issues": [{"description": "A real finding."}],
    }


class TestArtifactFilesExist:
    def test_schema_file_exists(self):
        assert SCHEMA_PATH.is_file()

    def test_example_file_exists(self):
        assert EXAMPLE_PATH.is_file()


class TestExampleFixture:
    def test_example_conforms_to_schema(self, validator):
        payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        validator.validate(payload)

    def test_example_honors_presence_means_issues_invariant(self):
        """A persisted artifact must be findings-bearing: a non-VERIFIED
        verdict and at least one issue."""
        payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        assert payload["verificationVerdict"] != "VERIFIED"
        assert len(payload["issues"]) >= 1

    def test_example_demonstrates_both_annotated_and_bare_issues(self):
        """The example proves the optional fields are optional by
        carrying one annotated and one bare issue."""
        payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        has_annotated = any("resolution_status" in i for i in payload["issues"])
        has_bare = any("resolution_status" not in i for i in payload["issues"])
        assert has_annotated and has_bare


class TestEnvelopeContract:
    def test_minimal_envelope_passes(self, validator):
        validator.validate(_minimal_envelope())

    def test_resolution_fields_are_optional(self, validator):
        env = _minimal_envelope()
        env["issues"][0].update(
            {
                "resolution_status": "fixed",
                "resolution_notes": "Addressed in-flight.",
                "resolved_in_round": 2,
            }
        )
        validator.validate(env)

    def test_empty_issues_rejected(self, validator):
        """No empty issue file: the artifact exists only for
        findings-bearing rounds, so issues must be non-empty."""
        env = _minimal_envelope()
        env["issues"] = []
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(env)

    def test_missing_required_envelope_field_rejected(self, validator):
        for field in (
            "schemaVersion",
            "sessionNumber",
            "verificationRound",
            "verificationVerdict",
            "issues",
        ):
            env = _minimal_envelope()
            del env[field]
            with pytest.raises(jsonschema.ValidationError):
                validator.validate(env)

    def test_unknown_top_level_key_rejected(self, validator):
        """The envelope is closed — stray top-level keys (e.g. an
        accidental issue array dumped at the root) are rejected."""
        env = _minimal_envelope()
        env["disposition"] = {"status": "completed"}
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(env)

    def test_schema_version_must_be_one(self, validator):
        env = _minimal_envelope()
        env["schemaVersion"] = 2
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(env)


class TestIssueObjectContract:
    def test_issue_requires_description(self, validator):
        env = _minimal_envelope()
        env["issues"][0] = {"category": "bug", "severity": "Major"}
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(env)

    def test_issue_tolerates_extra_verifier_keys(self, validator):
        """Verifier-emitted fields are preserved verbatim, so the issue
        object keeps additionalProperties open."""
        env = _minimal_envelope()
        env["issues"][0]["evidence"] = "line 42 in foo.py"
        validator.validate(env)

    def test_category_and_severity_are_loose_strings(self, validator):
        env = _minimal_envelope()
        env["issues"][0].update({"category": "unknown", "severity": "unknown"})
        validator.validate(env)

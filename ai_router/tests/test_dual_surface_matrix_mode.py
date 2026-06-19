"""Set 072 (S1) - tests for the dual-surface MATRIX-mode seam.

Hermetic: both arms are injected fakes and the git-diff dispatch is stubbed, so
**no metered LLM call and no real git invocation** happen. What is exercised is
the matrix seam's contract:

- the equal-arms steelman DEFAULT is unchanged - a provider/model divergence with
  NO per-arm params still raises ``UnequalArmsError`` and the attestation records
  ``mode == "equal-arms"``;
- setting per-arm providers engages matrix mode - intentional divergence does NOT
  raise, ``mode == "matrix"``, ``intentionalDivergence == True``, and both arms
  still ran at strong adversarial framing (the matrix varies *provider*, not
  framing - L-069-2);
- the framing gate STILL fires in matrix mode (a weakened push template raises);
- ``_arms_held_equal`` (the RETIRE-evidence boundary) rejects a matrix artifact;
- the comparison artifact round-trips at schemaVersion 2 carrying ``mode``, while
  a legacy schemaVersion-1 artifact (no ``mode``) still validates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dual_surface_verify as dsv
from pull_verifier import (
    Finding,
    PullCritique,
    PullResult,
    PullTrace,
    STOP_VERDICT,
    ToolCallRecord,
)

STRONG_PULL_INSTRUCTION = (
    "You are an adversarial reviewer. Be a genuine devil's advocate: assume the "
    "work is flawed and try to prove it. Read the files yourself."
)
STRONG_PUSH_TEMPLATE = (
    "You are an adversarial verifier. Be a devil's advocate: assume the work is "
    "flawed and try to prove it. {original_task} {task_type} {original_response} "
    "Start with VERIFIED or ISSUES FOUND."
)
WEAK_PUSH_TEMPLATE = (
    "You are a verifier. Evaluate it objectively. {original_task} {task_type} "
    "{original_response} Start with VERIFIED or ISSUES FOUND."
)

# A minimal config carrying BOTH providers either arm might run in matrix mode.
_CONFIG = {"providers": {"anthropic": {}, "google": {}, "openai": {}}, "pull_verifier": {}}


def _set_dir(tmp_path: Path) -> Path:
    d = tmp_path / "072-set"
    d.mkdir(exist_ok=True)
    (d / "spec.md").write_text("# spec\n", encoding="utf-8")
    return d


def _fake_push(content: str, *, provider=None, model=None):
    """Push-arm fake; by default ECHOES the provider/model it was asked to run."""
    calls = {}

    def run(**kw):
        calls.update(kw)
        return dsv._PushRaw(
            content=content,
            provider=provider if provider is not None else kw.get("provider", ""),
            model=model if model is not None else kw.get("model", ""),
            input_tokens=120,
            output_tokens=40,
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


def _critique(verdict="VERIFIED", findings=()):
    return PullCritique(
        provider="anthropic",
        model="claude-sonnet-4-6",
        verdict=verdict,
        summary="reviewed the diff",
        findings=tuple(findings),
    )


def _fake_pull(critique, *, provider=None, model=None):
    """Pull-arm fake; by default ECHOES the provider/model it was asked to run."""
    calls = {}

    def run(sandbox, instruction, **kw):
        calls["sandbox"] = sandbox
        calls["instruction"] = instruction
        calls.update(kw)
        trace = PullTrace(stop_reason=STOP_VERDICT, cost_usd=0.012)
        trace.tool_calls.append(
            ToolCallRecord(
                turn=0, name="read_file", args={}, raw=True,
                elided=False, result_chars=42, error=False,
            )
        )
        return PullResult(
            provider=provider if provider is not None else kw.get("provider", "anthropic"),
            model=model if model is not None else kw.get("model", "claude-sonnet-4-6"),
            critique=critique,
            trace=trace,
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


@pytest.fixture(autouse=True)
def _stub_diff(monkeypatch):
    monkeypatch.setattr(
        dsv,
        "_dispatch_get_diff",
        lambda cfg: ("[unified diff]\n+changed a line\n", False, False),
    )


def _run(tmp_path, **overrides):
    set_dir = overrides.pop("set_dir", None) or _set_dir(tmp_path)
    kw = dict(
        base_ref="HEAD~1",
        head_ref="",
        provider="anthropic",
        model="claude-sonnet-4-6",
        sandbox_dir=str(tmp_path),
        push_template=STRONG_PUSH_TEMPLATE,
        pull_template=STRONG_PULL_INSTRUCTION,
        config=_CONFIG,
    )
    kw.update(overrides)
    return dsv.run_dual_surface(set_dir, **kw)


# ---------------------------------------------------------------------------
# The equal-arms DEFAULT is byte-for-byte unchanged
# ---------------------------------------------------------------------------

def test_equal_arms_default_records_equal_arms_mode(tmp_path):
    """With NO per-arm params the run is equal-arms; attestation says so and the
    new mode field threads onto the run + its dict."""
    push = _fake_push("VERIFIED - tried to break it; could not.")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(tmp_path, run_push=push, run_pull=pull)
    assert run.mode == dsv.RUN_MODE_EQUAL_ARMS
    assert run.attestation["mode"] == dsv.RUN_MODE_EQUAL_ARMS
    assert run.attestation["intentionalDivergence"] is False
    # The per-arm requested identities collapse to the single scalar.
    assert run.attestation["requestedPushProvider"] == "anthropic"
    assert run.attestation["requestedPullProvider"] == "anthropic"
    assert run.to_dict()["mode"] == dsv.RUN_MODE_EQUAL_ARMS


def test_equal_arms_provider_divergence_still_raises(tmp_path):
    """A provider divergence with NO per-arm params is an ACCIDENT and must still
    raise (the steelman default is unchanged)."""
    push = _fake_push("VERIFIED")
    # The pull fake reports a provider the runner did not request.
    pull = _fake_pull(_critique("VERIFIED"), provider="openai")
    with pytest.raises(dsv.UnequalArmsError):
        _run(tmp_path, run_push=push, run_pull=pull)
    # And with require_equal False it completes, recording equal-arms mode.
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED"), provider="openai"),
        require_equal=False,
    )
    assert run.mode == dsv.RUN_MODE_EQUAL_ARMS
    assert run.attestation["providerEqual"] is False


# ---------------------------------------------------------------------------
# Matrix mode: intentional divergence is recorded, not raised
# ---------------------------------------------------------------------------

def test_matrix_mode_intentional_divergence_does_not_raise(tmp_path):
    """push=anthropic / pull=google -> matrix mode: no raise, divergence recorded,
    both arms still strong adversarial framing."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(
        tmp_path,
        run_push=push,
        run_pull=pull,
        push_provider="anthropic",
        pull_provider="google",
    )
    assert run.mode == dsv.RUN_MODE_MATRIX
    assert run.attestation["mode"] == dsv.RUN_MODE_MATRIX
    assert run.attestation["intentionalDivergence"] is True
    # Each arm ran its OWN resolved identity.
    assert run.attestation["pushProvider"] == "anthropic"
    assert run.attestation["pullProvider"] == "google"
    assert run.attestation["requestedPullModel"] == "gemini-2.5-pro"  # google default pin
    assert pull.calls["provider"] == "google"
    assert pull.calls["model"] == "gemini-2.5-pro"
    # The matrix varies provider, NOT framing - both arms stayed strong adversarial.
    assert run.attestation["bothAdversarial"] is True
    assert run.framing_equal is True


def test_matrix_mode_single_arm_override_engages_matrix(tmp_path):
    """Setting only ONE per-arm param still engages matrix mode (the other arm
    falls back to the scalar)."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(tmp_path, run_push=push, run_pull=pull, pull_provider="google")
    assert run.mode == dsv.RUN_MODE_MATRIX
    assert run.attestation["pushProvider"] == "anthropic"  # fell back to scalar
    assert run.attestation["pullProvider"] == "google"
    assert run.attestation["intentionalDivergence"] is True


def test_matrix_mode_equal_providers_no_divergence(tmp_path):
    """Per-arm params that happen to be EQUAL still mark matrix mode, but record
    intentionalDivergence False (honest)."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(
        tmp_path,
        run_push=push,
        run_pull=pull,
        push_provider="anthropic",
        pull_provider="anthropic",
    )
    assert run.mode == dsv.RUN_MODE_MATRIX
    assert run.attestation["intentionalDivergence"] is False


# ---------------------------------------------------------------------------
# Framing is STILL enforced in matrix mode (the matrix varies provider, not framing)
# ---------------------------------------------------------------------------

def test_matrix_mode_still_enforces_framing(tmp_path):
    """A weakened push template raises EVEN in matrix mode - matrix never relaxes
    the L-069-2 framing gate."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    with pytest.raises(dsv.UnequalArmsError):
        _run(
            tmp_path,
            run_push=push,
            run_pull=pull,
            push_template=WEAK_PUSH_TEMPLATE,
            push_provider="anthropic",
            pull_provider="google",
        )
    # The refusal is the framing gate (before any metered call) - arms never ran.
    assert push.calls == {}
    assert pull.calls == {}


# ---------------------------------------------------------------------------
# _arms_held_equal rejects a matrix artifact as RETIRE evidence
# ---------------------------------------------------------------------------

def _comparison_from_run(run):
    merge = dsv.merge_findings(
        [f for f in run.push.issues], [f for f in run.pull.findings]
    )
    return dsv.build_comparison_artifact(
        run, merge, run_tag=dsv.RUN_TAG_OPT_IN, compared_at="2026-06-19T00:00:00Z"
    )


def test_matrix_artifact_rejected_as_retire_evidence(tmp_path):
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED")),
        push_provider="anthropic",
        pull_provider="google",
    )
    artifact = _comparison_from_run(run)
    # Structurally valid (schemaVersion 2, mode matrix) ...
    result = dsv.validate_comparison_artifact(artifact)
    assert result.ok, result.reasons
    assert artifact["schemaVersion"] == dsv.COMPARISON_SCHEMA_VERSION_CURRENT
    assert artifact["mode"] == dsv.RUN_MODE_MATRIX
    # ... but NOT scoreable RETIRE telemetry: the scorer rejects it on the posture.
    held_equal, reasons = dsv._arms_held_equal(artifact)
    assert held_equal is False
    assert any("matrix" in r for r in reasons)
    assert dsv.score_comparison(artifact).ok is False


def test_equal_arms_artifact_is_scoreable(tmp_path):
    """The equal-arms artifact stays valid RETIRE telemetry (matrix rejection did
    not over-reach)."""
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED")),
    )
    artifact = _comparison_from_run(run)
    assert dsv.validate_comparison_artifact(artifact).ok
    held_equal, _ = dsv._arms_held_equal(artifact)
    assert held_equal is True
    assert dsv.score_comparison(artifact).ok is True


# ---------------------------------------------------------------------------
# Schema-version 2 + legacy-1 acceptance
# ---------------------------------------------------------------------------

def test_legacy_schema_version_1_without_mode_still_validates(tmp_path):
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED")),
    )
    artifact = _comparison_from_run(run)
    # Downgrade to a pre-Set-072 envelope: schemaVersion 1, no mode field.
    artifact["schemaVersion"] = 1
    del artifact["mode"]
    assert dsv.validate_comparison_artifact(artifact).ok


def test_schema_version_2_requires_mode(tmp_path):
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED")),
    )
    artifact = _comparison_from_run(run)
    del artifact["mode"]  # schemaVersion stays 2
    result = dsv.validate_comparison_artifact(artifact)
    assert result.ok is False
    assert any("mode" in r for r in result.reasons)


def test_bad_mode_value_rejected(tmp_path):
    run = _run(
        tmp_path,
        run_push=_fake_push("VERIFIED"),
        run_pull=_fake_pull(_critique("VERIFIED")),
    )
    artifact = _comparison_from_run(run)
    artifact["mode"] = "bogus-posture"
    result = dsv.validate_comparison_artifact(artifact)
    assert result.ok is False
    assert any("mode" in r for r in result.reasons)

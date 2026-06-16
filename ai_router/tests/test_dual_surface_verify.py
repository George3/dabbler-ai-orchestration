"""Set 070 (S1) — tests for the dual-surface two-arm runner.

Hermetic: both arms are injected fakes (``run_push`` / ``run_pull``) and the
git-diff resolution is monkeypatched, so **no metered LLM call and no real git
invocation** happen. What is exercised is the runner's contract:

- provider + model + framing held EQUAL across arms (the steelman invariant);
- each arm's framing strength derived from the ACTUAL template text (L-069-2);
- a weak/unequal framing REFUSED by default (``UnequalArmsError``);
- both arms' RAW verdicts returned with NO merge (S1 scope);
- push verdict parsed via ``parse_verification_response``; pull findings lifted
  from the forced critique.
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
    STOP_NO_VERDICT,
    STOP_VERDICT,
    ToolCallRecord,
)

# A strong-framing pull instruction used where we don't want to depend on the
# shipped template file being read off disk.
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


def _set_dir(tmp_path: Path) -> Path:
    d = tmp_path / "070-set"
    d.mkdir(exist_ok=True)
    (d / "spec.md").write_text("# spec\n", encoding="utf-8")
    return d


def _fake_push(content: str, *, provider=None, model=None):
    """A push-arm fake. By default it ECHOES the provider/model it was asked to
    run (the honest contract); pass provider=/model= to simulate an arm that ran
    a *different* identity than requested."""
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


def _critique(verdict="ISSUES_FOUND", findings=()):
    return PullCritique(
        provider="anthropic",
        model="claude-sonnet-4-6",
        verdict=verdict,
        summary="reviewed the diff",
        findings=tuple(findings),
    )


def _fake_pull(critique, *, with_probe=True, stop=STOP_VERDICT):
    calls = {}

    def run(sandbox, instruction, **kw):
        calls["sandbox"] = sandbox
        calls["instruction"] = instruction
        calls.update(kw)
        trace = PullTrace(stop_reason=stop, cost_usd=0.012)
        if with_probe:
            trace.tool_calls.append(
                ToolCallRecord(
                    turn=0, name="read_file", args={}, raw=True,
                    elided=False, result_chars=42, error=False,
                )
            )
        return PullResult(
            provider=kw.get("provider", "anthropic"),
            model=kw.get("model", "claude-sonnet-4-6"),
            critique=critique,
            trace=trace,
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


@pytest.fixture(autouse=True)
def _stub_diff(monkeypatch):
    """Replace the git-diff dispatch with a fixed snippet (no real git)."""
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
        # pull_template is the SINGLE pull source: it is both classified and
        # (after rendering) executed, so there is no second value to drift.
        pull_template=STRONG_PULL_INSTRUCTION,
        config={"providers": {"anthropic": {}}, "pull_verifier": {}},
    )
    kw.update(overrides)
    return dsv.run_dual_surface(set_dir, **kw)


# ---------------------------------------------------------------------------
# Happy path: equal arms, both raw verdicts, NO merge
# ---------------------------------------------------------------------------

def test_runs_both_arms_equal_and_returns_raw_verdicts(tmp_path):
    push = _fake_push("ISSUES FOUND\n\n- **Issue 1:** off-by-one\n  - **Severity:** Major\n")
    pull = _fake_pull(
        _critique(
            "ISSUES_FOUND",
            findings=[Finding(description="cross-file drift", severity="Major", category="contract-drift")],
        )
    )
    run = _run(tmp_path, run_push=push, run_pull=pull)

    # Both arms ran; both raw verdicts present.
    assert run.push.verdict == "ISSUES_FOUND"
    assert run.pull.verdict == "ISSUES_FOUND"
    assert run.push.issues  # parsed push issues
    assert run.pull.findings and run.pull.findings[0]["description"] == "cross-file drift"
    # Equal-arms attestation.
    assert run.framing_equal is True
    assert run.attestation["bothAdversarial"] is True
    assert run.attestation["providerEqual"] and run.attestation["modelEqual"]
    # Provenance — honest WORKTREE label since head_ref is empty.
    assert run.provider == "anthropic" and run.model == "claude-sonnet-4-6"
    assert run.committed_ref == "HEAD~1..WORKTREE"
    # NO merge in S1: the run carries no merged/provenance-tagged finding set.
    assert not hasattr(run, "merged")
    d = run.to_dict()
    assert d["kind"] == "dual_surface_run" and "push" in d and "pull" in d


def test_both_arms_pinned_to_same_provider_and_model(tmp_path):
    push = _fake_push("VERIFIED — tried to break it; could not.")
    pull = _fake_pull(_critique("VERIFIED"))
    _run(tmp_path, run_push=push, run_pull=pull, provider="anthropic", model="claude-opus-4-8")

    assert push.calls["provider"] == "anthropic"
    assert push.calls["model"] == "claude-opus-4-8"
    assert pull.calls["provider"] == "anthropic"
    assert pull.calls["model"] == "claude-opus-4-8"


def test_push_arm_fed_the_committed_diff_snippet(tmp_path):
    push = _fake_push("VERIFIED — checked it.")
    pull = _fake_pull(_critique("VERIFIED"))
    _run(tmp_path, run_push=push, run_pull=pull)
    # The push prompt embeds the (stubbed) diff snippet — snippet-fed surface.
    assert "+changed a line" in push.calls["prompt"]


# ---------------------------------------------------------------------------
# The equal-framing invariant (L-069-2)
# ---------------------------------------------------------------------------

def test_weak_push_framing_refused_by_default(tmp_path):
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    with pytest.raises(dsv.UnequalArmsError):
        _run(tmp_path, run_push=push, run_pull=pull, push_template=WEAK_PUSH_TEMPLATE)
    # The refusal happens BEFORE any arm runs (no metered call wasted).
    assert push.calls == {}
    assert pull.calls == {}


def test_unequal_framing_allowed_when_require_equal_false(tmp_path):
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(
        tmp_path,
        run_push=push,
        run_pull=pull,
        push_template=WEAK_PUSH_TEMPLATE,
        require_equal=False,
    )
    assert run.framing_equal is False
    assert run.attestation["pushFraming"]["strength"] == dsv.FRAMING_WEAK
    assert run.attestation["pullFraming"]["strength"] == dsv.FRAMING_ADVERSARIAL
    assert run.attestation["bothAdversarial"] is False


def test_provider_mismatch_refused_post_arm(tmp_path):
    """If an arm actually ran a DIFFERENT provider than requested, the attestation
    must catch it and refuse (equality is measured, not assumed)."""
    # The pull fake reports a provider different from the requested one.
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    # Override the pull fake to report a mismatching provider.
    def mismatching_pull(sandbox, instruction, **kw):
        res = pull(sandbox, instruction, **kw)
        return PullResult(provider="openai", model=res.model, critique=res.critique, trace=res.trace)
    with pytest.raises(dsv.UnequalArmsError):
        _run(tmp_path, run_push=push, run_pull=mismatching_pull)


def test_push_arm_omitting_identity_falsifies_equality(tmp_path):
    """A push fake that does not echo its identity cannot prove equality — the
    attestation reports providerEqual False (and refuses by default)."""
    push = _fake_push("VERIFIED", provider="", model="")  # omits identity
    pull = _fake_pull(_critique("VERIFIED"))
    with pytest.raises(dsv.UnequalArmsError):
        _run(tmp_path, run_push=push, run_pull=pull)
    # With require_equal False the run completes and records the falsification.
    push2 = _fake_push("VERIFIED", provider="", model="")
    run = _run(tmp_path, run_push=push2, run_pull=_fake_pull(_critique("VERIFIED")), require_equal=False)
    assert run.attestation["providerEqual"] is False
    assert run.attestation["pushProvider"] == ""


def test_committed_ref_uses_head_ref_when_pinned(tmp_path):
    """A pinned head_ref is recorded verbatim (no WORKTREE substitution)."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(tmp_path, run_push=push, run_pull=pull, base_ref="abc123", head_ref="def456")
    assert run.committed_ref == "abc123..def456"


def test_pull_framing_not_spoofable_by_interpolation(tmp_path):
    """Framing is classified from the UNFILLED pull template body, so adversarial
    markers spliced in via placeholder interpolation (the change summary, file
    list) cannot mask a weak template body."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    # Weak body; the only adversarial markers would be interpolated content, which
    # classification never sees -> classified weak -> refuse.
    weak_pull_template = "=== PROMPT ===\nEvaluate it objectively. {change_summary}"
    with pytest.raises(dsv.UnequalArmsError):
        _run(
            tmp_path,
            run_push=push,
            run_pull=pull,
            push_template=STRONG_PUSH_TEMPLATE,
            pull_template=weak_pull_template,
        )


def test_default_templates_are_both_adversarial(tmp_path):
    """With ALL templates defaulting to the shipped files, framing is equal-strong
    and the template labels are the truthful shipped filenames."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    set_dir = _set_dir(tmp_path)
    # No push_template / pull_template / pull_instruction overrides -> real files.
    run = dsv.run_dual_surface(
        set_dir,
        base_ref="HEAD~1",
        provider="anthropic",
        model="claude-sonnet-4-6",
        sandbox_dir=str(tmp_path),
        config={"providers": {"anthropic": {}}, "pull_verifier": {}},
        run_push=push,
        run_pull=pull,
    )
    assert run.push.framing.strength == dsv.FRAMING_ADVERSARIAL
    assert run.pull.framing.strength == dsv.FRAMING_ADVERSARIAL
    assert run.push.framing.template == "verification.md"
    assert run.pull.framing.template == "path-aware-critique.md"


def test_pull_executed_instruction_rendered_from_classified_template(tmp_path):
    """The instruction the pull arm RUNS is rendered from the SAME template that
    was classified — one source of truth, so no classify-vs-execute drift. A
    weak custom pull_template both classifies weak AND would execute weak."""
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    set_dir = _set_dir(tmp_path)
    # A pull template whose PROMPT BODY is weak (after the marker).
    weak_template = "preamble\n=== PROMPT ===\nEvaluate it objectively. {change_summary}"
    with pytest.raises(dsv.UnequalArmsError):
        dsv.run_dual_surface(
            set_dir,
            base_ref="HEAD~1",
            provider="anthropic",
            model="claude-sonnet-4-6",
            sandbox_dir=str(tmp_path),
            push_template=STRONG_PUSH_TEMPLATE,
            pull_template=weak_template,
            config={"providers": {"anthropic": {}}, "pull_verifier": {}},
            run_push=push,
            run_pull=pull,
        )
    # And the instruction the pull arm receives is the rendered (filled) body of
    # that very template — captured on the fake.
    run = dsv.run_dual_surface(
        set_dir,
        base_ref="HEAD~1",
        provider="anthropic",
        model="claude-sonnet-4-6",
        sandbox_dir=str(tmp_path),
        push_template=STRONG_PUSH_TEMPLATE,
        pull_template=weak_template,
        require_equal=False,
        config={"providers": {"anthropic": {}}, "pull_verifier": {}},
        run_push=_fake_push("VERIFIED"),
        run_pull=pull,
    )
    assert "Evaluate it objectively." in pull.calls["instruction"]
    assert run.pull.framing.strength == dsv.FRAMING_WEAK


# ---------------------------------------------------------------------------
# Arm-level edge cases
# ---------------------------------------------------------------------------

def test_pull_arm_no_verdict_marks_not_ok(tmp_path):
    push = _fake_push("VERIFIED")
    pull = _fake_pull(None, with_probe=True, stop=STOP_NO_VERDICT)
    run = _run(tmp_path, run_push=push, run_pull=pull)
    assert run.pull.verdict == "NO_VERDICT"
    assert run.pull.ok is False
    assert run.pull.findings == []


def test_pull_arm_zero_probe_is_not_ok(tmp_path):
    push = _fake_push("VERIFIED")
    # A verdict with zero probe calls is a FAILED pull run (tool-contract §5).
    pull = _fake_pull(_critique("VERIFIED"), with_probe=False)
    run = _run(tmp_path, run_push=push, run_pull=pull)
    assert run.pull.ok is False


def test_push_verified_parses_clean(tmp_path):
    push = _fake_push("VERIFIED — I tried to break it and could not.")
    pull = _fake_pull(_critique("VERIFIED"))
    run = _run(tmp_path, run_push=push, run_pull=pull)
    assert run.push.verdict == "VERIFIED"
    assert run.push.issues == []


def test_diff_error_raises_dual_surface_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        dsv, "_dispatch_get_diff", lambda cfg: ("ERROR: get_diff: bad ref", True, False)
    )
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    with pytest.raises(dsv.DualSurfaceError):
        _run(tmp_path, run_push=push, run_pull=pull)


def test_missing_set_dir_raises(tmp_path):
    push = _fake_push("VERIFIED")
    pull = _fake_pull(_critique("VERIFIED"))
    with pytest.raises(dsv.DualSurfaceError):
        _run(tmp_path, set_dir=tmp_path / "does-not-exist", run_push=push, run_pull=pull)


# ---------------------------------------------------------------------------
# Framing classifier unit coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Be a devil's advocate: assume the work is flawed.", dsv.FRAMING_ADVERSARIAL),
        ("Please find every defect in this code.", dsv.FRAMING_MODERATE),
        ("Evaluate it objectively and report.", dsv.FRAMING_WEAK),
        ("Summarize the change.", dsv.FRAMING_UNKNOWN),
    ],
)
def test_classify_framing_strength(text, expected):
    assert dsv.classify_framing_strength(text) == expected

"""Tests for the Set 067 S4 path-aware-critique producer.

The producer drives the pull verifier across >= 2 providers and assembles the
Set 066 ``path-aware-critique.json`` artifact. These tests inject a FAKE
``run_pull`` so no metered API call is ever made; they assert the multi-provider
invariant (refuse a single-provider artifact), the envelope shape (validates
against the Set 066 runtime validator), level/identity stamping, the write/
dry-run paths, instruction building from the template + disposition, and the
CLI surface.
"""

from __future__ import annotations

import json

import pytest

import pull_critique as pc  # conftest puts ai_router/ on sys.path
import pull_verifier as pv
from path_aware_critique import (
    record_path_aware_critique,
    validate_path_aware_critique_artifact,
    validate_path_aware_critique_gate,
)


# --- Fakes ------------------------------------------------------------------


def _fake_result(provider, model, *, ok=True, verdict="VERIFIED", summary="ok",
                 findings=(), zero_calls=False, stop="verdict", crit=True):
    """Build a PullResult as the adapter would return it."""
    trace = pv.PullTrace(stop_reason=stop)
    if not zero_calls:
        trace.tool_calls.append(
            pv.ToolCallRecord(
                turn=0, name="read_file", args={"path": "x"}, raw=True,
                elided=False, result_chars=10, error=False,
            )
        )
    critique = None
    if crit:
        critique = pv.PullCritique(
            provider=provider,
            model=model,
            verdict=verdict,
            summary=summary,
            findings=tuple(
                pv.Finding(description=d, severity="Major", category="correctness")
                for d in findings
            ),
        )
    return pv.PullResult(
        provider=provider, model=model, critique=critique, trace=trace
    )


def _runner(mapping):
    """Return a run_pull that yields a scripted PullResult per provider."""
    def run_pull(sandbox, instruction, *, provider, model, config):
        return mapping[provider]
    return run_pull


def _make_set(tmp_path, slug="099-demo-set", level="required"):
    set_dir = tmp_path / slug
    set_dir.mkdir()
    (set_dir / "spec.md").write_text(
        "# Demo Set Spec\n\nbody\n", encoding="utf-8"
    )
    (set_dir / "disposition.json").write_text(
        json.dumps(
            {"summary": "did a thing", "files_changed": ["a.py", "b.py"]}
        ),
        encoding="utf-8",
    )
    # The durable record (so read_path_aware_critique returns `level`).
    (set_dir / "activity-log.json").write_text(
        json.dumps({"sessionSetName": slug, "entries": []}), encoding="utf-8"
    )
    record_path_aware_critique(set_dir, level, session_number=1)
    return set_dir


# --- The multi-provider invariant ------------------------------------------


def test_two_distinct_providers_produces_valid_artifact(tmp_path):
    set_dir = _make_set(tmp_path)
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4", findings=["bug a"]),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, run_pull=run
    )
    assert res.ok
    assert res.written_to == set_dir / "path-aware-critique.json"
    # The written file passes the SAME validator the close-out gate uses.
    result = validate_path_aware_critique_artifact(res.written_to)
    assert result.ok, result.reasons
    assert sorted(result.providers) == ["google", "openai"]
    # Identity stamping: name = dir name, level = recorded policy.
    assert res.artifact["sessionSetName"] == "099-demo-set"
    assert res.artifact["pathAwareCritique"] == "required"
    assert res.artifact["schemaVersion"] == 1


def test_single_distinct_provider_refused(tmp_path):
    set_dir = _make_set(tmp_path)
    # Two runs but the SAME provider -> not multi-provider.
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("openai", "gpt-5.4"),  # adapter stamped openai
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, run_pull=run
    )
    assert not res.ok
    assert res.written_to is None
    assert not (set_dir / "path-aware-critique.json").exists()
    assert any("single-provider" in r for r in res.reasons)


def test_failed_provider_run_is_skipped_not_fatal(tmp_path):
    set_dir = _make_set(tmp_path)
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result(
                "google", "gemini-2.5-pro", zero_calls=True
            ),  # zero probes -> ok=False -> skipped
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, run_pull=run
    )
    # Only one usable verdict -> single provider -> refused, but the run
    # completed (the zero-probe failure was skipped, not raised).
    assert not res.ok
    assert any("zero tool calls" in s for s in res.skipped)


def test_raising_provider_is_skipped(tmp_path):
    set_dir = _make_set(tmp_path)

    def run_pull(sandbox, instruction, *, provider, model, config):
        if provider == "google":
            raise RuntimeError("boom")
        return _fake_result("openai", "gpt-5.4")

    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, run_pull=run_pull
    )
    assert not res.ok
    assert any("RuntimeError" in s and "boom" in s for s in res.skipped)


# --- write vs dry-run -------------------------------------------------------


def test_dry_run_does_not_write(tmp_path):
    set_dir = _make_set(tmp_path)
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, write=False, run_pull=run
    )
    assert res.ok
    assert res.written_to is None
    assert not (set_dir / "path-aware-critique.json").exists()


def test_explicit_level_override_allowed_only_on_dry_run(tmp_path):
    # An explicit level that disagrees with the recorded policy is honored in
    # the ARTIFACT, but only a dry run may stamp it (writing it would fail the
    # gate's identity check), so write must be False.
    set_dir = _make_set(tmp_path, level="required")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, level="advisory", write=False, run_pull=run
    )
    assert res.artifact["pathAwareCritique"] == "advisory"
    assert res.ok  # dry run: structurally valid, nothing written
    assert res.written_to is None


def test_write_mode_refuses_level_mismatching_recorded_policy(tmp_path):
    # The gate-identity guard: in write mode the stamped level must equal the
    # recorded policy, or the artifact would be written-but-gate-rejected.
    set_dir = _make_set(tmp_path, level="required")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, level="advisory", run_pull=run
    )
    assert not res.ok
    assert res.written_to is None
    assert not (set_dir / "path-aware-critique.json").exists()
    assert any("recorded" in r and "advisory" in r for r in res.reasons)


def test_level_defaults_to_recorded_policy(tmp_path):
    set_dir = _make_set(tmp_path, level="advisory")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(
        set_dir, sandbox_dir=tmp_path, run_pull=run
    )
    assert res.artifact["pathAwareCritique"] == "advisory"


# --- instruction building ---------------------------------------------------


def test_build_instruction_fills_template(tmp_path):
    set_dir = _make_set(tmp_path)
    instr = pc.build_instruction(set_dir)
    # Placeholders are gone; set specifics + template body are present.
    assert "{set_title}" not in instr
    assert "{change_summary}" not in instr
    assert "{files_changed}" not in instr
    assert "099-demo-set" in instr
    assert "did a thing" in instr
    assert "a.py" in instr
    # The template's load-bearing anti-bias instruction survives.
    assert "the repository wins" in instr


def test_build_instruction_without_disposition(tmp_path):
    set_dir = tmp_path / "100-bare"
    set_dir.mkdir()
    (set_dir / "spec.md").write_text("# Bare Spec\n", encoding="utf-8")
    instr = pc.build_instruction(set_dir)
    assert "100-bare" in instr
    # No disposition -> graceful fallbacks, not a crash.
    assert "No file list recorded" in instr or "No close-time summary" in instr


def test_build_instruction_non_string_summary_does_not_raise(tmp_path):
    # A malformed disposition with a non-string (truthy) summary must not crash
    # build_instruction in str.replace (S4 dogfood finding 3).
    set_dir = tmp_path / "101-bad-disp"
    set_dir.mkdir()
    (set_dir / "spec.md").write_text("# Bad Disp Spec\n", encoding="utf-8")
    (set_dir / "disposition.json").write_text(
        json.dumps({"summary": {"oops": "a dict"}, "files_changed": [123]}),
        encoding="utf-8",
    )
    instr = pc.build_instruction(set_dir)  # must not raise
    assert "No close-time summary" in instr


def test_session_name_resolved_from_dot_invocation(tmp_path, monkeypatch):
    # Invoked as "." from inside the set, Path(".").name is "" -> the producer
    # must resolve() first so sessionSetName is the real set name, not empty
    # (S4 dogfood finding 1).
    set_dir = _make_set(tmp_path, slug="102-dot-set")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    monkeypatch.chdir(set_dir)
    res = pc.produce_path_aware_critique(".", sandbox_dir=tmp_path, run_pull=run)
    assert res.artifact["sessionSetName"] == "102-dot-set"
    assert res.ok


def test_produced_artifact_passes_the_real_close_out_gate(tmp_path):
    # End-to-end: a produced artifact must satisfy the ACTUAL close-out gate
    # (validate_path_aware_critique_gate), not just the structural validator
    # (S4 dogfood finding 2 - the earlier tests only checked envelope validity).
    set_dir = _make_set(tmp_path, level="required")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4", findings=["bug a"]),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    res = pc.produce_path_aware_critique(set_dir, sandbox_dir=tmp_path, run_pull=run)
    assert res.ok and res.written_to is not None
    gate = validate_path_aware_critique_gate(set_dir)
    assert gate.applicable and gate.ok, gate.reason


def test_producer_and_gate_agree_on_non_canonical_path(tmp_path, monkeypatch):
    # The producer resolves the path to stamp sessionSetName; the gate must
    # resolve too, so a "." invocation that WRITES also PASSES the gate -- the
    # two never disagree on a non-canonical path (S4 dogfood finding 1).
    set_dir = _make_set(tmp_path, slug="103-agree-set", level="required")
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    monkeypatch.chdir(set_dir)
    res = pc.produce_path_aware_critique(".", sandbox_dir=tmp_path, run_pull=run)
    assert res.ok and res.written_to is not None
    gate = validate_path_aware_critique_gate(".")  # same non-canonical path
    assert gate.applicable and gate.ok, gate.reason


# --- CLI --------------------------------------------------------------------


def test_cli_dry_run(tmp_path, monkeypatch, capsys):
    set_dir = _make_set(tmp_path)
    run = _runner(
        {
            "openai": _fake_result("openai", "gpt-5.4"),
            "google": _fake_result("google", "gemini-2.5-pro"),
        }
    )
    # Patch the module-level default so the CLI uses the fake.
    monkeypatch.setattr(pc, "pull_route", run)
    real = pc.produce_path_aware_critique

    def patched(*a, **k):
        k.setdefault("run_pull", run)
        return real(*a, **k)

    monkeypatch.setattr(pc, "produce_path_aware_critique", patched)
    rc = pc._main([str(set_dir), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ok=True" in out
    assert "dry-run" in out
    assert not (set_dir / "path-aware-critique.json").exists()


def test_parse_providers():
    assert pc._parse_providers(None) == pc.DEFAULT_PROVIDERS
    assert pc._parse_providers(["openai"]) == (("openai", None),)
    assert pc._parse_providers(["openai:gpt-5.4", "google"]) == (
        ("openai", "gpt-5.4"),
        ("google", None),
    )

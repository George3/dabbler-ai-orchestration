"""Tests for the Set 067 first-party pull-verifier adapter (S1).

Covers the load-bearing invariants from
``docs/session-sets/067-pull-verifier-adapter-experiment-a/tool-contract.md``:
the loop terminates at every cap; sandbox escape is refused; the servant
returns raw ground truth and a summarizing servant is a hard failure; the
verdict is forced to the Set 066 critique-entry shape; the trace records real
tool use; and a zero-probe run is flagged as failed.

No metered API calls: a FakeBinding drives a scripted agentic loop.
"""

from __future__ import annotations

import json

import pytest

import pull_verifier as pv  # conftest puts ai_router/ on sys.path


# --- A minimal router config (no real provider call is ever made here) ------
CONFIG = {
    "providers": {
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://example.invalid/messages",
            "api_version": "2023-06-01",
            "timeout_seconds": 5,
        }
    },
    "models": {},  # pricing falls back to _FALLBACK_PRICING for the default model
}


def _tc(name, inp, tid="t1"):
    return pv.NeutralToolCall(id=tid, name=name, input=inp)


def _resp(text="", tool_calls=None, it=10, ot=10, stop="tool_use"):
    return pv.BindingResponse(
        text=text,
        tool_calls=tool_calls or [],
        input_tokens=it,
        output_tokens=ot,
        stop_reason=stop,
    )


class FakeBinding(pv.ProviderBinding):
    """Scripted provider binding - no network. provider_name=anthropic so the
    config/pricing resolution paths are exercised against the real registry."""

    provider_name = "anthropic"

    def __init__(self, queue=None, default=None, force_response=None):
        self.queue = list(queue or [])
        self.default = default
        self.force_response = force_response
        self.force_flags = []

    def request(self, *, force_verdict, **kw):
        self.force_flags.append(force_verdict)
        if force_verdict and self.force_response is not None:
            return self.force_response
        if self.queue:
            return self.queue.pop(0)
        if self.default is not None:
            return self.default
        raise AssertionError("FakeBinding ran out of responses")


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "a.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("needle here\nhay\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("inner\n", encoding="utf-8")
    return tmp_path


# ===========================================================================
# Sandbox confinement
# ===========================================================================


class TestSafe:
    def test_in_sandbox_path_ok(self, sandbox):
        assert pv._safe(sandbox, "a.py") == (sandbox / "a.py").resolve()

    def test_subdir_path_ok(self, sandbox):
        assert pv._safe(sandbox, "sub/c.py") == (sandbox / "sub" / "c.py").resolve()

    def test_dotdot_escape_refused(self, sandbox):
        with pytest.raises(pv.SandboxEscape):
            pv._safe(sandbox, "../outside.txt")

    def test_absolute_escape_refused(self, sandbox, tmp_path):
        outside = tmp_path.parent / "evil.txt"
        with pytest.raises(pv.SandboxEscape):
            pv._safe(sandbox, str(outside))

    def test_empty_path_refused(self, sandbox):
        with pytest.raises(pv.SandboxEscape):
            pv._safe(sandbox, "")


# ===========================================================================
# Deterministic servant returns raw ground truth
# ===========================================================================


class TestServantRawContent:
    def test_read_file_returns_raw_bytes(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("read_file", {"path": "a.py"}, sandbox)
        assert r.raw is True
        assert r.content == "alpha\nbeta\ngamma\n"
        assert r.elided is False

    def test_grep_returns_raw_lines(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "needle"}, sandbox)
        assert r.raw is True
        assert r.content == "b.txt:1:needle here"

    def test_grep_no_matches(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "zzzz"}, sandbox)
        assert r.content == "(no matches)"

    def test_list_dir_marks_directories(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("list_dir", {}, sandbox)
        assert "a.py" in r.content.splitlines()
        assert "sub/" in r.content.splitlines()

    def test_read_missing_file_is_raw_error(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("read_file", {"path": "nope.py"}, sandbox)
        assert r.content.startswith("ERROR: ")
        assert r.raw is True

    def test_escape_is_raw_error_not_crash(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("read_file", {"path": "../x"}, sandbox)
        assert r.content.startswith("ERROR: ")
        assert "escapes sandbox" in r.content

    def test_large_file_is_elided_raw_slice(self, sandbox):
        big = "x" * (pv._RESULT_BYTE_CAP + 500)
        (sandbox / "big.txt").write_text(big, encoding="utf-8")
        servant = pv.DeterministicServant()
        r = servant.run("read_file", {"path": "big.txt"}, sandbox)
        assert r.elided is True
        assert r.content.startswith("x" * 100)  # raw head slice, not a summary
        assert "elided" in r.content
        assert r.bytes_total == len(big)

    def test_elision_caps_bytes_not_chars(self, sandbox):
        # Multibyte content: 'e-acute' is 2 UTF-8 bytes, so this text is ~2x the
        # cap in BYTES while only ~1x in chars. A char-based cap would overshoot.
        text = "é" * pv._RESULT_BYTE_CAP
        (sandbox / "multi.txt").write_text(text, encoding="utf-8")
        servant = pv.DeterministicServant()
        r = servant.run("read_file", {"path": "multi.txt"}, sandbox)
        assert r.elided is True
        head = r.content.split("\n[... elided")[0]
        assert len(head.encode("utf-8")) <= pv._RESULT_BYTE_CAP
        assert r.bytes_total == len(text.encode("utf-8"))


class TestGrepConfinement:
    def test_grep_skips_symlink_to_outside_file(self, sandbox, tmp_path):
        outside = tmp_path.parent / "secret.txt"
        outside.write_text("SECRETTOKEN should not leak\n", encoding="utf-8")
        link = sandbox / "leak.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted on this host")
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "SECRETTOKEN"}, sandbox)
        assert "SECRETTOKEN" not in r.content  # outside content never read
        assert r.content == "(no matches)"

    def test_grep_does_not_descend_symlinked_dir(self, sandbox, tmp_path):
        outside_dir = tmp_path.parent / "outside_dir"
        outside_dir.mkdir(exist_ok=True)
        (outside_dir / "hidden.txt").write_text(
            "SECRETTOKEN in dir\n", encoding="utf-8"
        )
        link = sandbox / "linkdir"
        try:
            link.symlink_to(outside_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted on this host")
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "SECRETTOKEN"}, sandbox)
        assert "SECRETTOKEN" not in r.content

    def test_grep_still_finds_real_in_tree_files(self, sandbox):
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "inner"}, sandbox)
        assert "sub/c.py:1:inner" in r.content  # real subdir file still walked

    def test_broken_symlink_does_not_abort_grep(self, sandbox):
        # A broken in-tree symlink must be skipped (is_file() False), not read,
        # so it cannot turn the whole recursive grep into an ERROR.
        link = sandbox / "broken.txt"
        try:
            link.symlink_to(sandbox / "nonexistent-target.txt")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted on this host")
        servant = pv.DeterministicServant()
        r = servant.run("grep", {"pattern": "inner"}, sandbox)
        assert not r.content.startswith("ERROR: ")
        assert "sub/c.py:1:inner" in r.content  # real files still searched


# ===========================================================================
# The deterministic-servant guardrail (anti-bias property)
# ===========================================================================


class _SummarizingServant(pv.DeterministicServant):
    """A BAD servant that paraphrases - must be caught by the guard."""

    def run(self, name, args, sandbox):
        return pv.ToolResult(
            content="(summary: the file looks fine)",
            raw=True,
            elided=False,
            bytes_total=0,
        )


class _NotRawServant(pv.DeterministicServant):
    """A BAD servant that fails to flag its result raw."""

    def run(self, name, args, sandbox):
        gt = pv._CANONICAL[name](sandbox, args)
        return pv.ToolResult(
            content=gt.content, raw=False, elided=gt.elided, bytes_total=0
        )


class _FakeErrorServant(pv.DeterministicServant):
    """A BAD servant that hides readable content behind a fake ERROR prefix."""

    def run(self, name, args, sandbox):
        return pv.ToolResult(
            content="ERROR: (summary disguised as an error)",
            raw=True,
            elided=False,
            bytes_total=0,
        )


class _FabricatedErrorTextServant(pv.DeterministicServant):
    """A BAD servant that injects model text into a genuinely-failing probe."""

    def run(self, name, args, sandbox):
        return pv.ToolResult(
            content="ERROR: model says this file probably has an auth bypass",
            raw=True,
            elided=False,
            bytes_total=0,
        )


class TestServantGuardrail:
    def test_fake_error_over_readable_file_is_hard_failure(self, sandbox):
        bad = _FakeErrorServant()
        r = bad.run("read_file", {"path": "a.py"}, sandbox)
        with pytest.raises(pv.DeterministicServantViolation):
            pv._guard_raw_ground_truth("read_file", {"path": "a.py"}, r, sandbox)

    def test_fabricated_error_text_on_failing_probe_caught(self, sandbox):
        # Even when canonical ALSO fails (missing file), an injected error
        # string must not pass: the error text itself must match ground truth.
        bad = _FabricatedErrorTextServant()
        r = bad.run("read_file", {"path": "missing.py"}, sandbox)
        with pytest.raises(pv.DeterministicServantViolation):
            pv._guard_raw_ground_truth(
                "read_file", {"path": "missing.py"}, r, sandbox
            )

    def test_genuine_error_passes_guard(self, sandbox):
        # An ERROR for a path that canonical also fails on is legitimate.
        good = pv.DeterministicServant()
        r = good.run("read_file", {"path": "missing.py"}, sandbox)
        assert r.content.startswith("ERROR: ")
        pv._guard_raw_ground_truth(
            "read_file", {"path": "missing.py"}, r, sandbox
        )

    def test_summarizing_servant_is_hard_failure(self, sandbox):
        bad = _SummarizingServant()
        r = bad.run("read_file", {"path": "a.py"}, sandbox)
        with pytest.raises(pv.DeterministicServantViolation):
            pv._guard_raw_ground_truth("read_file", {"path": "a.py"}, r, sandbox)

    def test_not_raw_flag_is_hard_failure(self, sandbox):
        bad = _NotRawServant()
        r = bad.run("read_file", {"path": "a.py"}, sandbox)
        with pytest.raises(pv.DeterministicServantViolation):
            pv._guard_raw_ground_truth("read_file", {"path": "a.py"}, r, sandbox)

    def test_good_servant_passes_guard(self, sandbox):
        good = pv.DeterministicServant()
        r = good.run("read_file", {"path": "a.py"}, sandbox)
        pv._guard_raw_ground_truth("read_file", {"path": "a.py"}, r, sandbox)

    def test_summarizing_servant_caught_in_full_loop(self, sandbox):
        binding = FakeBinding(
            queue=[_resp(tool_calls=[_tc("read_file", {"path": "a.py"})])]
        )
        with pytest.raises(pv.DeterministicServantViolation):
            pv.pull_route(
                sandbox,
                "review",
                binding=binding,
                servant=_SummarizingServant(),
                config=CONFIG,
            )


# ===========================================================================
# Forced verdict schema
# ===========================================================================


class TestVerdictSchema:
    def test_valid_verdict_parsed(self):
        c = pv._parse_verdict(
            "anthropic",
            "claude-sonnet-4-6",
            {
                "verdict": "ISSUES_FOUND",
                "summary": "found a bug",
                "findings": [
                    {"description": "off by one", "severity": "major"}
                ],
            },
        )
        assert c.verdict == "ISSUES_FOUND"
        assert c.findings[0].description == "off by one"
        assert c.findings[0].severity == "major"

    def test_missing_verdict_rejected(self):
        with pytest.raises(pv.VerdictSchemaError):
            pv._parse_verdict("anthropic", "m", {"summary": "x"})

    def test_empty_verdict_rejected(self):
        with pytest.raises(pv.VerdictSchemaError):
            pv._parse_verdict("anthropic", "m", {"verdict": "  ", "summary": "x"})

    def test_finding_without_description_rejected(self):
        with pytest.raises(pv.VerdictSchemaError):
            pv._parse_verdict(
                "anthropic",
                "m",
                {"verdict": "V", "summary": "s", "findings": [{"severity": "x"}]},
            )

    def test_trivial_verdict_rejected(self):
        # Empty summary AND no findings -> would fail the Set 066 per-entry rule.
        with pytest.raises(pv.VerdictSchemaError):
            pv._parse_verdict(
                "a", "m", {"verdict": "VERIFIED", "summary": "  ", "findings": []}
            )

    def test_verdict_with_findings_but_no_summary_ok(self):
        # Set 066 allows summary OR findings; findings alone is content-non-trivial.
        c = pv._parse_verdict(
            "a",
            "m",
            {
                "verdict": "ISSUES_FOUND",
                "summary": "",
                "findings": [{"description": "real bug"}],
            },
        )
        assert c.summary == ""
        assert len(c.findings) == 1

    def test_critique_entry_matches_set066_shape(self):
        c = pv._parse_verdict(
            "anthropic",
            "claude-sonnet-4-6",
            {"verdict": "VERIFIED", "summary": "ok", "findings": []},
        )
        entry = c.to_critique_entry()
        assert set(entry) >= {"provider", "model", "verdict", "summary", "findings"}
        assert entry["provider"] == "anthropic"


# ===========================================================================
# The loop driver - termination, caps, trace
# ===========================================================================


class TestLoopTermination:
    def test_probe_then_verdict_is_ok(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(tool_calls=[_tc("read_file", {"path": "a.py"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "looks fine"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.ok is True
        assert result.critique.verdict == "VERIFIED"
        assert result.trace.stop_reason == pv.STOP_VERDICT
        assert result.trace.tool_call_count == 1
        assert result.trace.zero_tool_calls is False
        assert result.trace.tool_calls[0].name == "read_file"
        assert result.trace.tool_calls[0].raw is True

    def test_zero_probe_verdict_is_failed_run(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "no probe"},
                            "v1",
                        )
                    ]
                )
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.critique is not None
        assert result.trace.zero_tool_calls is True
        assert result.ok is False  # a verdict with no probe is NOT ok

    def test_text_only_turn_nudges_then_verdict(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(text="I think it's fine."),  # no tool use -> nudge
                _resp(tool_calls=[_tc("grep", {"pattern": "needle"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "checked"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.ok is True
        assert result.trace.tool_call_count == 1

    def test_max_turns_without_verdict(self, sandbox):
        # Binding always probes, never submits, ignores force -> max-turns.
        binding = FakeBinding(
            default=_resp(tool_calls=[_tc("read_file", {"path": "a.py"})])
        )
        result = pv.pull_route(
            sandbox,
            "review",
            binding=binding,
            config=CONFIG,
            caps=pv.PullCaps(max_turns=3),
        )
        assert result.critique is None
        assert result.ok is False
        assert result.trace.stop_reason == pv.STOP_MAX_TURNS
        assert result.trace.api_turns == 3

    def test_force_verdict_on_final_turn(self, sandbox):
        # Binding probes by default but honors force on the last turn.
        forced = _resp(
            tool_calls=[
                _tc(
                    "submit_verdict",
                    {"verdict": "ISSUES_FOUND", "summary": "forced"},
                    "v1",
                )
            ]
        )
        binding = FakeBinding(
            default=_resp(tool_calls=[_tc("read_file", {"path": "a.py"})]),
            force_response=forced,
        )
        result = pv.pull_route(
            sandbox,
            "review",
            binding=binding,
            config=CONFIG,
            caps=pv.PullCaps(max_turns=3),
        )
        assert result.ok is True
        assert result.critique.verdict == "ISSUES_FOUND"
        assert result.trace.stop_reason == pv.STOP_VERDICT
        # The last request must have been issued with force_verdict=True.
        assert binding.force_flags[-1] is True


class TestCaps:
    def test_token_budget_cap(self, sandbox):
        binding = FakeBinding(
            default=_resp(
                tool_calls=[_tc("read_file", {"path": "a.py"})], it=30, ot=30
            )
        )
        result = pv.pull_route(
            sandbox,
            "review",
            binding=binding,
            config=CONFIG,
            caps=pv.PullCaps(token_budget=50, max_turns=10),
        )
        assert result.trace.stop_reason == pv.STOP_TOKEN_BUDGET
        assert result.trace.api_turns == 1  # second turn blocked by budget

    def test_cost_ceiling_cap(self, sandbox):
        # sonnet fallback pricing 3/15 per 1M: 1000 in + 1000 out = $0.018/turn.
        # The ceiling is a POST-HOC stop (tool-contract section 5): the loop
        # stops once incurred spend crosses it, so it bounds the number of
        # further calls rather than the exact spend of the in-flight one.
        binding = FakeBinding(
            default=_resp(
                tool_calls=[_tc("read_file", {"path": "a.py"})], it=1000, ot=1000
            )
        )
        result = pv.pull_route(
            sandbox,
            "review",
            binding=binding,
            config=CONFIG,
            caps=pv.PullCaps(cost_ceiling_usd=0.01, max_turns=10),
        )
        assert result.trace.stop_reason == pv.STOP_COST_CEILING
        assert result.trace.api_turns == 1  # stopped after the first crossing

    def test_cost_accounting_accumulates(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(
                    tool_calls=[_tc("read_file", {"path": "a.py"})],
                    it=1000,
                    ot=1000,
                ),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ],
                    it=500,
                    ot=500,
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.trace.input_tokens == 1500
        assert result.trace.output_tokens == 1500
        # (1500*3 + 1500*15) / 1e6 = 0.027
        assert abs(result.trace.cost_usd - 0.027) < 1e-9


class TestTraceInstrumentation:
    def test_trace_records_elided_flag(self, sandbox):
        big = "y" * (pv._RESULT_BYTE_CAP + 100)
        (sandbox / "big.txt").write_text(big, encoding="utf-8")
        binding = FakeBinding(
            queue=[
                _resp(tool_calls=[_tc("read_file", {"path": "big.txt"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.trace.tool_calls[0].elided is True

    def test_escaping_probe_records_error(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(tool_calls=[_tc("read_file", {"path": "../escape"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        rec = result.trace.tool_calls[0]
        assert rec.error is True
        assert rec.name == "read_file"
        # The escape was raw-errored, not crashed: the loop still produced a verdict.
        assert result.trace.stop_reason == pv.STOP_VERDICT

    def test_result_serializes_to_dict(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(tool_calls=[_tc("read_file", {"path": "a.py"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        d = result.to_dict()
        # Round-trips through JSON (the CLI / S4 producer relies on this).
        s = json.dumps(d)
        assert json.loads(s)["ok"] is True
        assert d["trace"]["tool_call_count"] == 1


# ===========================================================================
# Provider binding registry + Anthropic wire translation (no network)
# ===========================================================================


class TestPricing:
    def test_pricing_reads_from_config_models(self):
        cfg = {
            "models": {
                "x": {
                    "model_id": "claude-sonnet-4-6",
                    "input_cost_per_1m": 1.0,
                    "output_cost_per_1m": 2.0,
                }
            }
        }
        assert pv._pricing_for("claude-sonnet-4-6", cfg) == (1.0, 2.0)

    def test_pricing_falls_back_when_absent(self):
        assert pv._pricing_for("claude-sonnet-4-6", None) == (3.00, 15.00)

    def test_pricing_uses_config_over_fallback(self, sandbox):
        # pull_route must use config pricing, not the conservative fallback.
        cfg = {
            "providers": {"anthropic": {"api_key_env": "X"}},
            "models": {
                "s": {
                    "model_id": "claude-sonnet-4-6",
                    "input_cost_per_1m": 100.0,
                    "output_cost_per_1m": 100.0,
                }
            },
        }
        binding = FakeBinding(
            queue=[
                _resp(
                    tool_calls=[_tc("read_file", {"path": "a.py"})],
                    it=1000,
                    ot=0,
                ),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ],
                    it=0,
                    ot=0,
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=cfg)
        # 1000 in-tokens at $100/1M = $0.1 (would be $0.003 on fallback pricing).
        assert abs(result.trace.cost_usd - 0.1) < 1e-9


class TestBindingRegistry:
    def test_anthropic_binding_available(self):
        b = pv._get_binding("anthropic")
        assert isinstance(b, pv.AnthropicBinding)

    def test_openai_binding_available(self):
        b = pv._get_binding("openai")
        assert isinstance(b, pv.OpenAIBinding)

    def test_gemini_binding_available(self):
        b = pv._get_binding("google")
        assert isinstance(b, pv.GeminiBinding)

    def test_unbound_provider_raises(self):
        # cohere has no binding; the registry still raises a clear error.
        with pytest.raises(NotImplementedError):
            pv._get_binding("cohere")

    def test_unknown_provider_raises(self):
        with pytest.raises(NotImplementedError):
            pv._get_binding("nope")


class TestAnthropicWireTranslation:
    def test_to_messages_roundtrips_tool_use(self):
        transcript = [
            {"role": "user", "text": "review"},
            {
                "role": "assistant",
                "text": "let me look",
                "tool_calls": [_tc("read_file", {"path": "a.py"}, "tu1")],
            },
            {
                "role": "tool",
                "results": [
                    {"id": "tu1", "name": "read_file", "content": "alpha"}
                ],
            },
        ]
        msgs = pv.AnthropicBinding._to_messages(transcript)
        assert msgs[0] == {"role": "user", "content": "review"}
        assert msgs[1]["role"] == "assistant"
        assert any(b["type"] == "tool_use" for b in msgs[1]["content"])
        assert msgs[2]["content"][0]["type"] == "tool_result"
        assert msgs[2]["content"][0]["tool_use_id"] == "tu1"

    def test_from_response_extracts_tool_calls_and_usage(self):
        data = {
            "content": [
                {"type": "text", "text": "thinking"},
                {
                    "type": "tool_use",
                    "id": "x",
                    "name": "grep",
                    "input": {"pattern": "p"},
                },
            ],
            "usage": {"input_tokens": 11, "output_tokens": 22},
            "stop_reason": "tool_use",
        }
        r = pv.AnthropicBinding._from_response(data)
        assert r.text == "thinking"
        assert r.tool_calls[0].name == "grep"
        assert r.input_tokens == 11
        assert r.output_tokens == 22

    def test_to_anthropic_tool_shapes_input_schema(self):
        tool = pv._verdict_tool_schema()
        shaped = pv.AnthropicBinding._to_anthropic_tool(tool)
        assert shaped["name"] == "submit_verdict"
        assert "input_schema" in shaped
        assert shaped["input_schema"]["type"] == "object"

    def test_verdict_schema_required_aligns_with_parser(self):
        # Schema requires only 'verdict'; the Set 066 content rule (summary OR
        # findings) is enforced by _parse_verdict, so schema and parser agree.
        tool = pv._verdict_tool_schema()
        assert tool["parameters"]["required"] == ["verdict"]


# ===========================================================================
# pull_route guards
# ===========================================================================


class TestPullRouteGuards:
    def test_missing_sandbox_raises(self, tmp_path):
        with pytest.raises(pv.PullVerifierError):
            pv.pull_route(
                tmp_path / "does-not-exist",
                "review",
                binding=FakeBinding(),
                config=CONFIG,
            )

    def test_result_stamps_provider_and_model(self, sandbox):
        binding = FakeBinding(
            queue=[
                _resp(tool_calls=[_tc("read_file", {"path": "a.py"})]),
                _resp(
                    tool_calls=[
                        _tc(
                            "submit_verdict",
                            {"verdict": "VERIFIED", "summary": "ok"},
                            "v1",
                        )
                    ]
                ),
            ]
        )
        result = pv.pull_route(sandbox, "review", binding=binding, config=CONFIG)
        assert result.provider == "anthropic"
        assert result.model == "claude-sonnet-4-6"
        assert result.critique.provider == "anthropic"
        assert result.critique.model == "claude-sonnet-4-6"


# ===========================================================================
# S2: OpenAI binding wire translation (Chat Completions tool_calls)
# ===========================================================================


# A canned multi-turn neutral transcript reused across binding-parity tests.
PARITY_TRANSCRIPT = [
    {"role": "user", "text": "review the repo"},
    {
        "role": "assistant",
        "text": "let me read it",
        "tool_calls": [pv.NeutralToolCall(id="c1", name="read_file", input={"path": "a.py"})],
    },
    {
        "role": "tool",
        "results": [{"id": "c1", "name": "read_file", "content": "alpha\nbeta"}],
    },
]


class TestOpenAIWireTranslation:
    def test_to_input_items_sends_only_new_non_assistant_entries(self):
        # Assistant turns live server-side (previous_response_id); only the
        # user message + the tool results become input items.
        items, upto = pv.OpenAIBinding._to_input_items(PARITY_TRANSCRIPT, 0)
        assert upto == 3
        assert items[0] == {"role": "user", "content": "review the repo"}
        # the assistant turn is skipped; the tool result becomes a
        # function_call_output keyed by the SAME call_id the model emitted.
        assert items[1] == {
            "type": "function_call_output",
            "call_id": "c1",
            "output": "alpha\nbeta",
        }
        assert len(items) == 2

    def test_to_input_items_resumes_from_offset(self):
        # On turn 2 the binding has already sent transcript[:2]; only the new
        # tool entry at index 2 is translated.
        items, upto = pv.OpenAIBinding._to_input_items(PARITY_TRANSCRIPT, 2)
        assert upto == 3
        assert items == [
            {"type": "function_call_output", "call_id": "c1", "output": "alpha\nbeta"}
        ]

    def test_to_openai_tool_flattens_function(self):
        # Responses API flattens function tools (no nested "function" key).
        tool = pv._verdict_tool_schema()
        shaped = pv.OpenAIBinding._to_openai_tool(tool)
        assert shaped["type"] == "function"
        assert shaped["name"] == "submit_verdict"
        assert shaped["parameters"]["type"] == "object"

    def test_from_response_extracts_function_call_and_usage(self):
        data = {
            "id": "resp_1",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "thinking out loud"}],
                },
                {
                    "type": "function_call",
                    "call_id": "call_42",
                    "name": "grep",
                    "arguments": '{"pattern": "needle"}',
                },
            ],
            "usage": {"input_tokens": 33, "output_tokens": 44},
            "status": "completed",
        }
        r = pv.OpenAIBinding._from_response(data)
        assert r.text == "thinking out loud"
        assert r.tool_calls[0].id == "call_42"
        assert r.tool_calls[0].name == "grep"
        assert r.tool_calls[0].input == {"pattern": "needle"}
        assert r.input_tokens == 33
        assert r.output_tokens == 44
        assert r.stop_reason == "end_turn"

    def test_from_response_maps_incomplete_to_max_tokens(self):
        data = {
            "output": [],
            "usage": {},
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
        }
        r = pv.OpenAIBinding._from_response(data)
        assert r.stop_reason == "max_tokens"

    def test_from_response_tolerates_bad_arguments_json(self):
        data = {
            "output": [
                {
                    "type": "function_call",
                    "call_id": "c",
                    "name": "grep",
                    "arguments": "{not json",
                }
            ],
            "usage": {},
            "status": "completed",
        }
        r = pv.OpenAIBinding._from_response(data)
        assert r.text == ""
        assert r.tool_calls[0].input == {}  # malformed args -> empty dict, no crash

    def test_request_uses_responses_api_and_chains_previous_id(self, monkeypatch):
        calls = []

        class _Resp:
            def __init__(self, rid):
                self._rid = rid

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "id": self._rid,
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "x"}],
                        }
                    ],
                    "usage": {},
                    "status": "completed",
                }

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                calls.append({"url": url, "body": json})
                return _Resp(f"resp_{len(calls)}")

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        cfg = {"api_key_env": "OPENAI_API_KEY", "base_url": "https://x.invalid/v1"}
        b = pv.OpenAIBinding()
        # Turn 1.
        b.request(
            system="s",
            transcript=[{"role": "user", "text": "go"}],
            tools=pv._all_tool_schemas(),
            force_verdict=False,
            max_output_tokens=24000,
            model="gpt-5.4",
            config=cfg,
            generation_params={"reasoning_effort": "medium"},
        )
        assert calls[0]["url"].endswith("/responses")
        b0 = calls[0]["body"]
        assert "previous_response_id" not in b0  # first turn has no prior id
        assert b0["max_output_tokens"] == 24000
        assert b0["reasoning"] == {"effort": "medium"}
        assert b0["store"] is True
        # Turn 2 (forced) - chains the prior response id, sends only new items.
        b.request(
            system="s",
            transcript=[
                {"role": "user", "text": "go"},
                {
                    "role": "assistant",
                    "text": "",
                    "tool_calls": [_tc("read_file", {"path": "a.py"}, "c1")],
                },
                {"role": "tool", "results": [{"id": "c1", "name": "read_file", "content": "x"}]},
            ],
            tools=pv._all_tool_schemas(),
            force_verdict=True,
            max_output_tokens=24000,
            model="gpt-5.4",
            config=cfg,
        )
        b1 = calls[1]["body"]
        assert b1["previous_response_id"] == "resp_1"
        # Only the new tool result is resent; the assistant turn is server-side.
        assert b1["input"] == [
            {"type": "function_call_output", "call_id": "c1", "output": "x"}
        ]
        assert b1["tool_choice"] == {"type": "function", "name": "submit_verdict"}

    def test_stateful_offset_advances_across_text_only_nudge(self, monkeypatch):
        # The adversarial path: a text-only assistant turn makes the driver
        # append a user NUDGE (not a tool result). The stateful cursor must
        # advance across that extra user turn and never resend the user msg.
        calls = []

        class _Resp:
            def __init__(self, rid):
                self._rid = rid

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "id": self._rid,
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "x"}]}
                    ],
                    "usage": {},
                    "status": "completed",
                }

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                calls.append(json)
                return _Resp(f"resp_{len(calls)}")

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        cfg = {"api_key_env": "OPENAI_API_KEY", "base_url": "https://x.invalid/v1"}
        b = pv.OpenAIBinding()
        tools = pv._all_tool_schemas()
        kw = dict(system="s", tools=tools, force_verdict=False, max_output_tokens=100, model="gpt-5.4", config=cfg)
        # Turn 1: initial user message.
        t1 = [{"role": "user", "text": "go"}]
        b.request(transcript=t1, **kw)
        # Turn 2: assistant returned text only -> driver appended a user nudge.
        t2 = t1 + [
            {"role": "assistant", "text": "hmm", "tool_calls": []},
            {"role": "user", "text": "use the tools then submit_verdict"},
        ]
        b.request(transcript=t2, **kw)
        # Turn 3: now a real tool call + result.
        t3 = t2 + [
            {"role": "assistant", "text": "", "tool_calls": [_tc("read_file", {"path": "a.py"}, "c9")]},
            {"role": "tool", "results": [{"id": "c9", "name": "read_file", "content": "alpha"}]},
        ]
        b.request(transcript=t3, **kw)

        # Turn 1 sent the user message, no chaining id.
        assert calls[0]["input"] == [{"role": "user", "content": "go"}]
        assert "previous_response_id" not in calls[0]
        # Turn 2 sent ONLY the nudge (assistant turn is server-side), chained.
        assert calls[1]["input"] == [
            {"role": "user", "content": "use the tools then submit_verdict"}
        ]
        assert calls[1]["previous_response_id"] == "resp_1"
        # Turn 3 sent ONLY the new tool result.
        assert calls[2]["input"] == [
            {"type": "function_call_output", "call_id": "c9", "output": "alpha"}
        ]
        assert calls[2]["previous_response_id"] == "resp_2"

    def test_offset_not_advanced_on_request_failure(self, monkeypatch):
        # Failure-atomicity: a failed request must NOT advance the cursor, so a
        # retry resends the same items rather than skipping them.
        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                raise RuntimeError("boom")

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        b = pv.OpenAIBinding()
        before = b._sent_upto
        with pytest.raises(RuntimeError):
            b.request(
                system="s",
                transcript=[{"role": "user", "text": "go"}],
                tools=pv._all_tool_schemas(),
                force_verdict=False,
                max_output_tokens=100,
                model="gpt-5.4",
                config={"api_key_env": "OPENAI_API_KEY"},
            )
        assert b._sent_upto == before  # cursor unchanged on failure
        assert b._response_id is None

    def test_offset_not_advanced_on_parse_failure(self, monkeypatch):
        # Failure-atomicity part 2: a malformed-but-JSON response that raises
        # during _from_response() parsing must ALSO leave the cursor untouched
        # (parse-before-commit ordering), so a retry resends, not skips.
        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id": "resp_1", "output": [], "usage": {}, "status": "ok"}

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                return _Resp()

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        b = pv.OpenAIBinding()
        # Force the parse step to blow up AFTER json() has returned.
        monkeypatch.setattr(
            b, "_from_response", lambda data: (_ for _ in ()).throw(ValueError("bad"))
        )
        before = b._sent_upto
        with pytest.raises(ValueError):
            b.request(
                system="s",
                transcript=[{"role": "user", "text": "go"}],
                tools=pv._all_tool_schemas(),
                force_verdict=False,
                max_output_tokens=100,
                model="gpt-5.4",
                config={"api_key_env": "OPENAI_API_KEY"},
            )
        assert b._sent_upto == before  # cursor NOT advanced past a parse failure
        assert b._response_id is None

    def test_from_response_skips_non_dict_output_items(self):
        # A null/garbage output item must not crash the parser.
        data = {
            "id": "r",
            "output": [None, {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}],
            "usage": {},
            "status": "completed",
        }
        r = pv.OpenAIBinding._from_response(data)
        assert r.text == "ok"


# ===========================================================================
# S2: Gemini binding wire translation (function_declarations)
# ===========================================================================


class TestGeminiWireTranslation:
    def test_to_contents_roundtrips_function_call_and_response(self):
        contents = pv.GeminiBinding._to_contents(PARITY_TRANSCRIPT)
        assert contents[0] == {"role": "user", "parts": [{"text": "review the repo"}]}
        assert contents[1]["role"] == "model"
        # model turn carries a functionCall part (no id on the wire).
        fc = [p for p in contents[1]["parts"] if "functionCall" in p][0]
        assert fc["functionCall"]["name"] == "read_file"
        assert fc["functionCall"]["args"] == {"path": "a.py"}
        # tool results go back in a user turn as functionResponse parts.
        assert contents[2]["role"] == "user"
        fr = contents[2]["parts"][0]["functionResponse"]
        assert fr["name"] == "read_file"
        assert fr["response"] == {"result": "alpha\nbeta"}

    def test_to_decl_flattens_tool(self):
        tool = pv._verdict_tool_schema()
        decl = pv.GeminiBinding._to_decl(tool)
        assert decl["name"] == "submit_verdict"
        assert decl["parameters"]["type"] == "object"

    def test_from_response_extracts_function_call_and_usage(self):
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "let me look"},
                            {
                                "functionCall": {
                                    "name": "list_dir",
                                    "args": {"path": "."},
                                }
                            },
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 5,
                "thoughtsTokenCount": 7,
            },
        }
        r = pv.GeminiBinding._from_response(data)
        assert r.text == "let me look"
        assert r.tool_calls[0].name == "list_dir"
        assert r.tool_calls[0].input == {"path": "."}
        assert r.tool_calls[0].id  # a synthesized non-empty id for result routing
        assert r.input_tokens == 12
        # thoughts folded into output so the budget/cost caps see honest spend.
        assert r.output_tokens == 12  # 5 candidates + 7 thoughts
        assert r.stop_reason == "end_turn"

    def test_from_response_maps_max_tokens_finish(self):
        data = {
            "candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}],
            "usageMetadata": {},
        }
        r = pv.GeminiBinding._from_response(data)
        assert r.stop_reason == "max_tokens"

    def test_multiple_same_name_calls_get_distinct_ids_and_positional_responses(self):
        # Gemini has no wire id; two read_file calls in one turn must parse to
        # DISTINCT synthesized ids, and their functionResponse parts must go
        # back in the same order (positional matching).
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"functionCall": {"name": "read_file", "args": {"path": "a.py"}}},
                            {"functionCall": {"name": "read_file", "args": {"path": "b.py"}}},
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {},
        }
        r = pv.GeminiBinding._from_response(data)
        assert len(r.tool_calls) == 2
        assert r.tool_calls[0].id != r.tool_calls[1].id  # distinct
        assert r.tool_calls[0].input == {"path": "a.py"}
        assert r.tool_calls[1].input == {"path": "b.py"}
        # The driver builds tool results in call order; _to_contents must emit
        # functionResponse parts in that same order.
        transcript = [
            {"role": "user", "text": "go"},
            {
                "role": "assistant",
                "text": "",
                "tool_calls": list(r.tool_calls),
            },
            {
                "role": "tool",
                "results": [
                    {"id": r.tool_calls[0].id, "name": "read_file", "content": "AAA"},
                    {"id": r.tool_calls[1].id, "name": "read_file", "content": "BBB"},
                ],
            },
        ]
        contents = pv.GeminiBinding._to_contents(transcript)
        responses = [
            p["functionResponse"] for p in contents[2]["parts"] if "functionResponse" in p
        ]
        assert [fr["response"]["result"] for fr in responses] == ["AAA", "BBB"]

    def test_gemini3_uses_thinking_level_not_budget(self, monkeypatch):
        captured = {}

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "candidates": [
                        {"content": {"parts": [{"text": "x"}]}, "finishReason": "STOP"}
                    ],
                    "usageMetadata": {},
                }

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, json=None):
                captured["body"] = json
                return _Resp()

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        pv.GeminiBinding().request(
            system="s",
            transcript=[{"role": "user", "text": "go"}],
            tools=pv._all_tool_schemas(),
            force_verdict=False,
            max_output_tokens=24000,
            model="gemini-3-pro",
            config={"api_key_env": "GEMINI_API_KEY", "base_url": "https://g.invalid/v1beta"},
            generation_params={"thinking_level": "high"},
        )
        thinking = captured["body"]["generationConfig"]["thinkingConfig"]
        assert thinking == {"thinkingLevel": "HIGH"}  # uppercased; not thinkingBudget
        assert "thinkingBudget" not in thinking

    def test_force_verdict_sets_tool_config_and_bounded_thinking(self, monkeypatch):
        captured = {}

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "candidates": [
                        {"content": {"parts": [{"text": "x"}]}, "finishReason": "STOP"}
                    ],
                    "usageMetadata": {},
                }

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, json=None):
                captured["url"] = url
                captured["body"] = json
                return _Resp()

        import httpx

        monkeypatch.setattr(httpx, "Client", _Client)
        b = pv.GeminiBinding()
        b.request(
            system="s",
            transcript=[{"role": "user", "text": "go"}],
            tools=pv._all_tool_schemas(),
            force_verdict=True,
            max_output_tokens=24000,
            model="gemini-2.5-pro",
            config={
                "api_key_env": "GEMINI_API_KEY",
                "base_url": "https://g.invalid/v1beta",
            },
            generation_params={"thinking_budget": 8192},
        )
        assert "generateContent" in captured["url"]
        body = captured["body"]
        fcc = body["tool_config"]["function_calling_config"]
        assert fcc["mode"] == "ANY"
        assert fcc["allowed_function_names"] == ["submit_verdict"]
        assert body["generationConfig"]["maxOutputTokens"] == 24000
        assert body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 8192


# ===========================================================================
# S2: tool-call parity across the three providers
# ===========================================================================


class TestToolCallParity:
    def test_all_bindings_expose_the_same_logical_toolset(self):
        tools = pv._all_tool_schemas()
        names = {t["name"] for t in tools}
        anthropic = {pv.AnthropicBinding._to_anthropic_tool(t)["name"] for t in tools}
        openai = {pv.OpenAIBinding._to_openai_tool(t)["name"] for t in tools}
        gemini = {pv.GeminiBinding._to_decl(t)["name"] for t in tools}
        assert names == anthropic == openai == gemini
        assert names == {"read_file", "grep", "list_dir", "submit_verdict"}

    def test_all_bindings_preserve_tool_parameter_schema(self):
        verdict = pv._verdict_tool_schema()
        a = pv.AnthropicBinding._to_anthropic_tool(verdict)["input_schema"]
        o = pv.OpenAIBinding._to_openai_tool(verdict)["parameters"]
        g = pv.GeminiBinding._to_decl(verdict)["parameters"]
        assert a == o == g == verdict["parameters"]

    def test_all_bindings_parse_the_same_neutral_tool_call(self):
        # Each provider expresses a read_file({path: a.py}) call in its own
        # native response shape; all three _from_response parsers must yield
        # the SAME neutral (name, input) the driver dispatches on.
        anthropic_resp = {
            "content": [
                {"type": "tool_use", "id": "x", "name": "read_file", "input": {"path": "a.py"}}
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "stop_reason": "tool_use",
        }
        openai_resp = {
            "id": "r",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "x",
                    "name": "read_file",
                    "arguments": '{"path": "a.py"}',
                }
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "status": "completed",
        }
        gemini_resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "read_file", "args": {"path": "a.py"}}}]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
        }
        a = pv.AnthropicBinding._from_response(anthropic_resp).tool_calls[0]
        o = pv.OpenAIBinding._from_response(openai_resp).tool_calls[0]
        g = pv.GeminiBinding._from_response(gemini_resp).tool_calls[0]
        assert (a.name, a.input) == ("read_file", {"path": "a.py"})
        assert (o.name, o.input) == ("read_file", {"path": "a.py"})
        assert (g.name, g.input) == ("read_file", {"path": "a.py"})


# ===========================================================================
# S2: executor config block resolution (router-config.yaml pull_verifier:)
# ===========================================================================


class TestExecutorConfig:
    def test_caps_from_config_reads_block(self):
        cfg = {
            "pull_verifier": {
                "caps": {
                    "max_turns": 20,
                    "max_output_tokens": 24000,
                    "token_budget": 500000,
                    "cost_ceiling_usd": 2.5,
                }
            }
        }
        caps = pv.caps_from_config(cfg)
        assert caps.max_turns == 20
        assert caps.max_output_tokens == 24000
        assert caps.token_budget == 500000
        assert caps.cost_ceiling_usd == 2.5

    def test_caps_from_config_falls_back_to_defaults(self):
        # No block at all -> the exact S1 PullCaps defaults (backward compatible).
        caps = pv.caps_from_config({})
        assert caps == pv.PullCaps()

    def test_caps_from_config_partial_block_merges_defaults(self):
        caps = pv.caps_from_config({"pull_verifier": {"caps": {"max_turns": 3}}})
        assert caps.max_turns == 3
        assert caps.max_output_tokens == pv.PullCaps().max_output_tokens

    def test_resolve_model_reads_executor_pin(self):
        cfg = {"pull_verifier": {"models": {"openai": "gpt-5.4-mini"}}}
        assert pv._resolve_model("openai", None, cfg) == "gpt-5.4-mini"

    def test_resolve_model_explicit_wins_over_pin(self):
        cfg = {"pull_verifier": {"models": {"openai": "gpt-5.4-mini"}}}
        assert pv._resolve_model("openai", "gpt-5.4", cfg) == "gpt-5.4"

    def test_resolve_model_falls_back_to_default_models(self):
        assert pv._resolve_model("google", None, {}) == "gemini-2.5-pro"

    def test_resolve_gen_params_reads_block(self):
        cfg = {
            "pull_verifier": {
                "generation_params": {"openai": {"reasoning_effort": "high"}}
            }
        }
        assert pv._resolve_gen_params("openai", cfg) == {"reasoning_effort": "high"}

    def test_resolve_gen_params_empty_when_absent(self):
        assert pv._resolve_gen_params("openai", {}) == {}

    def test_real_router_config_resolves_executor_block(self):
        # The shipped router-config.yaml must carry a valid pull_verifier block
        # with all three provider pins + caps that the resolvers can read.
        cfg = pv._load_router_config()
        block = pv._executor_block(cfg)
        assert block, "router-config.yaml is missing the pull_verifier block"
        assert set(block["models"]) == {"anthropic", "openai", "google"}
        caps = pv.caps_from_config(cfg)
        # The shipped caps bump max_output_tokens for GPT-5.4 reasoning headroom.
        assert caps.max_output_tokens >= 24000
        for prov in ("anthropic", "openai", "google"):
            assert pv._resolve_model(prov, None, cfg)

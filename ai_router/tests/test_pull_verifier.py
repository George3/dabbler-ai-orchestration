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

    def test_unbound_provider_raises(self):
        with pytest.raises(NotImplementedError):
            pv._get_binding("openai")

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

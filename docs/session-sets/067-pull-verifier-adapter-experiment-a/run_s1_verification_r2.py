"""Set 067 S1 cross-provider verification - ROUND 2 (post-remediation).

Round 1 (gpt-5.4) returned ISSUES_FOUND: 1 Critical + 3 Major + 1 Minor caveat.
All were remediated. This round re-presents the updated adapter + tests +
contract and asks the same verifier to confirm each R1 finding is resolved and
that the fixes introduced no new defect. Same verifier (gpt-5.4) for continuity;
substantive re-verify (real code changes), so normal review (no max_tier pin).
Persists raw output BEFORE printing (L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

contract = (HERE / "tool-contract.md").read_text(encoding="utf-8")
module = (REPO / "ai_router" / "pull_verifier.py").read_text(encoding="utf-8")
tests = (REPO / "ai_router" / "tests" / "test_pull_verifier.py").read_text(
    encoding="utf-8"
)
r1 = (HERE / "s1-verification.md").read_text(encoding="utf-8")

FIXES = """\
ROUND-1 FINDINGS AND THE FIXES APPLIED (confirm each is genuinely resolved in
the code below, and that no fix introduced a new defect):

[Critical] grep sandbox breakout -> FIXED. New _within_sandbox() (real-path
prefix check) + _walk_files() using os.walk(followlinks=False). grep now never
descends symlinked dirs and confines EVERY discovered file before reading; a
file whose real path leaves the sandbox is SKIPPED (not read, not relabelled).
Tests: TestGrepConfinement (symlinked file, symlinked dir, real-in-tree still found).

[Major] over-broad error exemption in the servant guard -> FIXED. Introduced
_canonical_result() that produces the FULL canonical ToolResult for BOTH success
and error outcomes. DeterministicServant.run and _guard_raw_ground_truth both
derive from it and require field-for-field equality (content/raw/elided/
bytes_total). A fabricated 'ERROR: <model text>' on a failing probe now mismatches
the canonical error string and raises. Test: test_fabricated_error_text_on_failing_probe_caught.

[Major] char-cap vs byte-cap elision -> FIXED. _elide() now encodes to UTF-8,
caps on BYTES, decodes a codepoint-aligned prefix (errors='ignore'), and reports
dropped BYTES. Test: test_elision_caps_bytes_not_chars (uses 2-byte chars).

[Major] config=None pricing bug -> FIXED. pull_route() now loads config once and
passes the SAME resolved config to both _provider_config and _pricing_for. Test:
test_pricing_uses_config_over_fallback.

[Major, the overshoot half of finding 4] token/cost ceilings overshoot by one
in-flight call -> ACCEPTED AS INHERENT, not 'fixed'. Token usage is unknown until
a call returns (same as route()/the spike), so these are POST-HOC stop conditions.
tool-contract.md section 5 now states this explicitly and the test documents it
(stops after the first crossing; bounds the number of further calls). Confirm
this resolution is honest and the contract wording matches the code.

[Minor] tool-schema/parser summary inconsistency -> FIXED. _parse_verdict now
rejects a trivial verdict (empty summary AND no findings), so every emitted entry
satisfies the Set 066 per-entry content rule (non-empty summary OR >=1 finding).
Tests: test_trivial_verdict_rejected, test_verdict_with_findings_but_no_summary_ok.
"""

CONVENTIONS = """\
CONVENTIONS (unchanged from R1; do NOT re-litigate scope): Set 067 S1 ships
ONLY the Anthropic binding (OpenAI/Gemini = S2), no release (S4), read-only
toolset (run_test = Set 068), and unit tests use a FakeBinding (no metered call).
Full pytest suite is GREEN (1446 prior + 62 pull_verifier tests). Review this as
production code.
"""

SYSTEM_PROMPT = (
    "You are the same independent cross-provider verifier (gpt-5.4) re-reviewing "
    "Set 067 Session 1 after remediation. For EACH round-1 finding, state "
    "RESOLVED or NOT-RESOLVED with a one-line reason citing the code. Then scan "
    "for any NEW defect the fixes introduced (especially in _walk_files, "
    "_canonical_result, _elide). Be concrete. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[{"severity":'
    '"Critical|Major|Minor","claim":"<what>","problem":"<why>","fix":"<how>"}]}. '
    "Return verdict VERIFIED only if every round-1 finding is resolved and you "
    "find no new Critical/Major defect."
)

USER = f"""{CONVENTIONS}

{FIXES}

=== ROUND-1 VERIFICATION (for reference) ===
{r1}

=== UPDATED DELIVERABLE 1: tool-contract.md ===
{contract}

=== UPDATED DELIVERABLE 2: ai_router/pull_verifier.py ===
{module}

=== UPDATED DELIVERABLE 3: ai_router/tests/test_pull_verifier.py ===
{tests}

Confirm each round-1 finding is resolved and scan for new defects. Return your
per-finding dispositions, any new findings, then the JSON verdict block."""


def main():
    cfg = yaml.safe_load(
        (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
    )
    pcfg = cfg["providers"]["openai"]
    model = next(
        m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4"
    )
    result = providers.call_model(
        provider_name="openai",
        model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT,
        user_message=USER,
        max_tokens=28000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s1-verification-round-2.md"
    out.write_text(
        "# Set 067 S1 -- Cross-provider verification (gpt-5.4) ROUND 2\n\n"
        "> Independent verifier: gpt-5.4 (openai). Post-remediation re-review.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(
        json.dumps(
            {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": round(in_cost + out_cost, 6),
                "stop_reason": result.stop_reason,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

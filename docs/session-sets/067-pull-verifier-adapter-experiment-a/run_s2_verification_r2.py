"""Set 067 S2 cross-provider session-verification -- ROUND 2.

Confirms the three Round-1 Minor findings (all by gpt-5.4) are resolved:
  1. OpenAI _sent_upto cursor advanced before the HTTP call succeeded
     (retry-desync robustness hole) -> now staged in new_upto and committed
     only after a successful response.
  2. No OpenAI-binding test pinned the text-only-nudge stateful-offset path
     -> added test_stateful_offset_advances_across_text_only_nudge (+ a
     failure-atomicity test).
  3. Gemini id-less multi-same-name positional matching and the gemini-3
     thinking_level branch untested -> added two Gemini tests.

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

module = (REPO / "ai_router" / "pull_verifier.py").read_text(encoding="utf-8")
tests = (REPO / "ai_router" / "tests" / "test_pull_verifier.py").read_text(
    encoding="utf-8"
)
r1 = (HERE / "s2-verification.md").read_text(encoding="utf-8")

SYSTEM_PROMPT = (
    "You are the same independent cross-provider verifier (gpt-5.4) from Round "
    "1 of Set 067 Session 2. You returned ISSUES_FOUND with three Minor "
    "findings. The orchestrator has applied fixes. Confirm whether each finding "
    "is resolved and whether the fixes introduced any new defect. Be concrete. "
    'End with a JSON verdict block: {"verdict":"VERIFIED"|"ISSUES_FOUND",'
    '"issues":[...]}.'
)

USER = f"""This is Round 2. Suite is GREEN (pull_verifier: 84 tests, up from 80;
full ai_router suite passes). Below are your Round-1 findings, then the UPDATED
adapter + tests. Confirm resolution of all three findings; flag any regression.

=== YOUR ROUND-1 REVIEW (verbatim) ===
{r1}

=== WHAT CHANGED ===
Finding 1 (OpenAI failure-atomicity): OpenAIBinding.request now stages
`input_items, new_upto = self._to_input_items(...)`, performs the HTTP call,
and ONLY after a successful response assigns `self._response_id = ...` and
`self._sent_upto = new_upto`. A failed request leaves the cursor untouched.

Finding 2 (OpenAI nudge offset test): added
TestOpenAIWireTranslation.test_stateful_offset_advances_across_text_only_nudge
(3 sequential request() calls on ONE OpenAIBinding instance: initial user ->
text-only assistant + user nudge -> tool call + result, asserting each turn
sends ONLY the new items and chains previous_response_id) AND
test_offset_not_advanced_on_request_failure (cursor unchanged when the HTTP
call raises).

Finding 3 (Gemini): added
TestGeminiWireTranslation.test_multiple_same_name_calls_get_distinct_ids_and_positional_responses
(two same-name read_file calls in one turn -> distinct synthesized ids, and
_to_contents emits functionResponse parts in results order) AND
test_gemini3_uses_thinking_level_not_budget (a gemini-3-pro request body uses
thinkingConfig.thinkingLevel, not thinkingBudget).

=== UPDATED DELIVERABLE 1: ai_router/pull_verifier.py ===
{module}

=== UPDATED DELIVERABLE 2: ai_router/tests/test_pull_verifier.py ===
{tests}

Confirm each finding is resolved and return the JSON verdict block."""


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
    out = HERE / "s2-verification-round-2.md"
    out.write_text(
        "# Set 067 S2 -- Cross-provider verification (gpt-5.4) -- Round 2\n\n"
        "> Independent verifier: gpt-5.4 (openai). Confirms the three Round-1\n"
        "> Minor findings are resolved.\n\n"
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

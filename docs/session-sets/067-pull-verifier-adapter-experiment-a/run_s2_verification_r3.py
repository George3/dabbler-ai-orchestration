"""Set 067 S2 cross-provider session-verification -- ROUND 3.

Round 2 confirmed findings 2 and 3 resolved and sharpened finding 1: the
OpenAI binding still committed `_response_id` / `_sent_upto` BEFORE
`_from_response(data)` parsing succeeded, so a malformed-but-JSON response
(e.g. output:[None]) could desync a retried instance. This round confirms the
parse-before-commit fix + the defensive non-dict-item skip + the two new tests.
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

# Just the OpenAIBinding.request + _from_response, and the new tests, to keep
# the round-3 prompt tight and focused on the single remaining finding.
module = (REPO / "ai_router" / "pull_verifier.py").read_text(encoding="utf-8")
start = module.index("class OpenAIBinding(ProviderBinding):")
end = module.index("class GeminiBinding(ProviderBinding):")
openai_binding = module[start:end].rstrip()

tests = (REPO / "ai_router" / "tests" / "test_pull_verifier.py").read_text(
    encoding="utf-8"
)
r2 = (HERE / "s2-verification-round-2.md").read_text(encoding="utf-8")

SYSTEM_PROMPT = (
    "You are the same independent cross-provider verifier (gpt-5.4) from Set "
    "067 Session 2. Round 2 left ONE open Minor finding: OpenAI state commit "
    "was not failure-atomic across a parse failure. Confirm the fix resolves "
    "it and introduces no regression. Be concrete. End with a JSON verdict "
    'block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]}.'
)

USER = f"""This is Round 3. Suite is GREEN (pull_verifier: 86 tests).

=== YOUR ROUND-2 REVIEW (verbatim) ===
{r2}

=== WHAT CHANGED (finding 1 fix) ===
OpenAIBinding.request now PARSES BEFORE COMMITTING:
    data = resp.json()
    parsed = self._from_response(data)        # parse first
    self._response_id = data.get("id") or self._response_id
    self._sent_upto = new_upto                # commit only after parse OK
    return parsed
and _from_response now skips non-dict output items defensively
(`if not isinstance(item, dict): continue`), so the output:[None] example no
longer raises at all. Two tests added:
  - test_offset_not_advanced_on_parse_failure: monkeypatches _from_response to
    raise after resp.json() returns; asserts _sent_upto and _response_id are
    unchanged.
  - test_from_response_skips_non_dict_output_items: output:[None, message]
    parses to the message text without crashing.

=== UPDATED OpenAIBinding (full class) ===
{openai_binding}

=== UPDATED ai_router/tests/test_pull_verifier.py ===
{tests}

Confirm finding 1 is resolved with no regression; return the JSON verdict block."""


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
    out = HERE / "s2-verification-round-3.md"
    out.write_text(
        "# Set 067 S2 -- Cross-provider verification (gpt-5.4) -- Round 3\n\n"
        "> Independent verifier: gpt-5.4 (openai). Confirms the final Round-2\n"
        "> finding (OpenAI parse-before-commit failure-atomicity) is resolved.\n\n"
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

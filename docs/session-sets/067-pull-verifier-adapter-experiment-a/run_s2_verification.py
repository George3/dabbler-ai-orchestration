"""Set 067 S2 cross-provider session-verification.

Independent verifier: gpt-5.4 (openai) -- cross-provider for the Claude
orchestrator. Reviews the S2 additions: the OpenAI (Responses-API function-tool)
and Gemini (function_declarations) bindings behind the same pull_route loop
driver, the router-config.yaml pull_verifier executor block + its resolvers,
and whether the new tests pin those bindings. Persists raw output BEFORE
printing (L-064-3).

Usage:
    .venv/Scripts/python.exe docs/session-sets/067-.../run_s2_verification.py
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
checker = (HERE / "run_s2_headless_check.py").read_text(encoding="utf-8")
headless = (HERE / "s2-headless-results.json").read_text(encoding="utf-8")
# Just the executor block of the YAML, to keep the prompt focused.
yaml_text = (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
start = yaml_text.index("# --- Pull-verifier executor (Set 067) ---")
end = yaml_text.index("# --- Metrics ---", start)
executor_block = yaml_text[start:end].rstrip()

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; they are the agreed
baseline, in-scope-by-design, or explicit later-session / Set-068 non-goals):

SUITE BASELINE: the full ai_router pytest suite is GREEN at session close
(1486 passed, 1 skipped -- the skip is a symlink-unsupported host guard). No
pre-existing failures are introduced. The pull_verifier suite is 80 tests.
Do not ask for test counts; assume green.

RELEASE CONTRACT: Session 2 of 4 ships NO release. The PyPI ai_router bump ships
in Session 4. S2 adds the OpenAI + Gemini bindings, the router-config executor
block + resolvers, and their tests, behind the seam S1 already shipped.

BY-DESIGN SCOPE (Set 067 S2 only -- the rest is later sessions or Set 068):
- The loop DRIVER (pull_route), the deterministic-servant guardrail, _safe
  sandbox confinement, the caps, the forced-verdict parser, and the trace were
  all shipped + cross-provider VERIFIED in S1. Do NOT re-litigate them unless S2
  changed their behavior. S2's job is the two new bindings + config wiring.
- The 3-provider "headless capability check" (run_s2_headless_check.py) is the
  small metered live test the spec asks for. It ran live: all three providers
  drove the read-only loop, issued real probe tool calls, and returned
  schema-valid ISSUES_FOUND verdicts; all three also caught the seeded defect.
  s2-headless-results.json is the saved raw evidence. It is a capability check,
  NOT Experiment A (the controlled capability study is Session 3).
- Experiment A (S3), the optional artifact-producer CLI (S4), and the run_test
  execution tool + disposable-worktree sandbox (Set 068) are all out of scope.
- This is FIRST-PARTY production code. Review it as production.

DESIGN NOTE you should validate, not flag as surprising:
- The OpenAI binding uses the RESPONSES API, not chat/completions, because
  gpt-5.4 returns HTTP 400 ("use /v1/responses instead") for function tools
  combined with reasoning_effort on chat/completions (confirmed empirically).
  It keeps reasoning items SERVER-SIDE via previous_response_id chaining
  (store=true) and sends only the entries new since the last response each turn
  (the user message or the function_call_output results). This makes the binding
  STATEFUL for one pull_route run (one fresh instance per run). Assess whether
  this chaining is correct and safe, not whether statefulness is unusual.

FOCUS your review on:
1. OPENAI BINDING CORRECTNESS: is the previous_response_id chaining correct?
   Does _to_input_items correctly send ONLY new, non-assistant entries (never
   resending a server-side function_call, which would trip the "function_call
   without reasoning item" error)? Is the _sent_upto offset advanced correctly
   so nothing is dropped or double-sent across turns? Is function_call /
   function_call_output round-tripping (call_id matching) correct? Are malformed
   tool-call arguments and the incomplete->max_tokens stop mapping handled?
   Could the stateful offset desync if the driver appends a user nudge turn
   (text-only response) instead of a tool result?
2. GEMINI BINDING CORRECTNESS: functionCall (model turn) <-> functionResponse
   (user turn) is matched POSITIONALLY by name with no wire id (Gemini gives
   none); synthesized ids are internal-only. Is that matching sound when a
   single turn issues multiple probes (e.g. two read_file calls)? Is
   thoughtsTokenCount correctly folded into output_tokens (cost/budget honesty)?
   Is the bounded thinkingBudget applied, and the gemini-3 thinking_level branch
   correct? finishReason mapping?
3. DRIVER UNCHANGED / PURE ADDITION: did S2 keep pull_route provider-agnostic?
   Is the binding interface change (adding generation_params) backward-safe for
   the S1 AnthropicBinding + the FakeBinding test double? Does AnthropicBinding's
   newly-added effort/thinking application match providers.py semantics and not
   regress S1 behavior?
4. EXECUTOR CONFIG WIRING: do caps_from_config / _resolve_model /
   _resolve_gen_params read the pull_verifier block correctly? Is the no-block
   path EXACTLY the S1 PullCaps defaults (backward compatible)? Does an explicit
   caps= still win over the config block? Is max_output_tokens=24000 a sound
   choice given the gpt-5.4 reasoning-eats-the-output-budget failure mode?
5. COST/TOKEN ACCOUNTING across all three providers: are input/output tokens
   read from the right fields per provider so the cost_ceiling + token_budget
   caps see honest spend (OpenAI input_tokens/output_tokens; Gemini
   prompt/candidates+thoughts)?
6. TEST QUALITY: do the new tests actually PIN 1-5 (Responses-API shape,
   chaining, positional Gemini matching, thoughts-folding, config resolution,
   parity), or are any vacuous? Anything a binding does that no test covers?
"""

BIAS_CAUTIONS = (
    "Bias cautions: this code was authored by an AI agent (Claude Opus 4.8) that "
    "maintains the workflow under study and has a stake in shipping the adapter. "
    "Its self-review may miss a hole in its own binding logic -- especially the "
    "stateful OpenAI chaining and the id-less Gemini positional matching, which "
    "are the two places a subtle multi-turn desync could hide. Be adversarial "
    "there. If the right question differs from the one posed, answer that too."
)

SYSTEM_PROMPT = (
    "You are a senior software-verification reviewer giving an independent "
    "cross-provider verification of a completed implementation session (Set 067, "
    "Session 2: the OpenAI + Gemini pull-verifier bindings + config wiring). You "
    "did not author it. Be rigorous and concrete: cite the specific function / "
    "line / claim. Distinguish a real correctness or safety defect from a style "
    'nit. End with a JSON verdict block: {"verdict":"VERIFIED"|"ISSUES_FOUND",'
    '"issues":[{"severity":"Critical|Major|Minor","claim":"<what>","problem":'
    '"<why>","fix":"<how>"}]}.'
)

USER = f"""{BIAS_CAUTIONS}

{CONVENTIONS}

=== DELIVERABLE 1: ai_router/pull_verifier.py (the adapter; S2 added the OpenAI
    + Gemini bindings, the executor-config resolvers, and generation_params
    threading; the S1-verified driver/guardrail/sandbox/caps are unchanged) ===
{module}

=== DELIVERABLE 2: router-config.yaml -- the new pull_verifier executor block ===
{executor_block}

=== DELIVERABLE 3: ai_router/tests/test_pull_verifier.py (80 tests) ===
{tests}

=== DELIVERABLE 4: run_s2_headless_check.py (the metered live capability check) ===
{checker}

=== DELIVERABLE 5: s2-headless-results.json (the SAVED RAW live-run evidence) ===
{headless}

Review per the FOCUS list. Return your findings then the JSON verdict block."""


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
    out = HERE / "s2-verification.md"
    out.write_text(
        "# Set 067 S2 -- Cross-provider verification (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude\n"
        "> orchestrator. Round 1.\n\n"
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

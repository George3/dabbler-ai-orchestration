"""Set 067 S1 cross-provider session-verification.

Independent verifier: gpt-5.4 (openai) -- cross-provider for the Claude
orchestrator. Reviews the S1 pull-verifier adapter (production code + tests +
the pinned tool contract) for correctness, the load-bearing invariants
(deterministic-servant guardrail, sandbox confinement, caps, forced verdict,
zero-tool-call flagging), and whether the tests actually pin those invariants.
Persists raw output BEFORE printing (L-064-3).

Usage:
    .venv/Scripts/python.exe docs/session-sets/067-.../run_s1_verification.py
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

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; they are the agreed
baseline, in-scope-by-design, or explicit Set-068 non-goals):

SUITE BASELINE: the full ai_router pytest suite is GREEN at session close
(1407 pre-existing tests + 40 new pull_verifier tests = 1447 passing). No
pre-existing failures are introduced. Do not ask for test counts; assume green.

RELEASE CONTRACT: Session 1 of 4 ships NO release. The PyPI ai_router bump ships
in Session 4. S1 only adds the library module + tests + the pinned tool contract
and exports the seam from ai_router/__init__.py.

BY-DESIGN SCOPE (Set 067 S1 only -- the rest is later sessions or Set 068):
- ONLY the Anthropic tool_use binding is implemented this session. OpenAI
  (tool_calls) and Gemini (function_declarations) bindings + router-config.yaml
  executor wiring are SESSION 2. _BINDINGS deliberately raises NotImplementedError
  for non-anthropic providers -- that is the intended S1 state, not a gap.
- NO live/metered API call is made in the unit tests by design: a FakeBinding
  drives a scripted loop. A 3-provider headless metered capability check is S2.
- The read-only toolset is read_file / grep / list_dir ONLY. The run_test
  execution tool + its disposable-worktree sandbox are explicitly Set 068.
- Experiment A (the capability study) is Session 3; the conditional artifact
  producer CLI is Session 4. S1 ships only a diagnostic _main() CLI.
- This is FIRST-PARTY production code now (unlike the Set 065 ~150-LOC throwaway
  spike) -- review it as production: correctness, safety, the invariants.

FOCUS your review on:
1. DETERMINISTIC-SERVANT GUARDRAIL (the load-bearing anti-bias property): does
   _guard_raw_ground_truth actually make a summarizing/paraphrasing servant a
   HARD failure? Can a bad servant slip a model-touched view past it? Consider
   the ERROR-result exemption and the elision path -- are they sound, or do they
   open a hole (e.g. a servant prefixing "ERROR: " to a summary to dodge the
   equality check)?
2. SANDBOX CONFINEMENT: does _safe correctly refuse ../ escapes, absolute-path
   escapes, and symlink escapes? Any path that escapes the sandbox? Is the
   read-only guarantee real (no write tool reachable)?
3. CAPS: are max_turns / token_budget / cost_ceiling each enforced and each
   reported via the right stop_reason? Any off-by-one (e.g. one extra API call
   past a ceiling)? Is force_verdict on the final turn correct?
4. FORCED VERDICT: does _parse_verdict correctly enforce the Set 066 critique
   entry shape (non-empty verdict; findings require non-empty description)? Does
   a single emitted critique entry satisfy the per-entry rules of Set 066's
   validate_path_aware_critique_artifact?
5. ZERO-TOOL-CALL ACCOUNTING: is submit_verdict correctly excluded from
   tool_call_count so a no-probe run is flagged ok=False (a failed run, not a
   fast one)?
6. SEAM CORRECTNESS: is pull_route genuinely parallel to route() and never
   nested in it / never calling route()? Is the loop driver provider-agnostic
   so the S2 bindings are a pure addition?
7. TEST QUALITY: do the 40 tests actually PIN invariants 1-6, or are any
   vacuous / tautological? Anything an invariant claims that no test covers?
"""

BIAS_CAUTIONS = (
    "Bias cautions: this code was authored by an AI agent (Claude Opus 4.8) that "
    "maintains the workflow under study and has a stake in shipping the adapter. "
    "Its self-review may miss a hole in the very guardrail it is proud of. Be "
    "adversarial about the deterministic-servant property in particular. If the "
    "right question to ask differs from the one posed, answer that too."
)

SYSTEM_PROMPT = (
    "You are a senior software-verification reviewer giving an independent "
    "cross-provider verification of a completed implementation session (Set 067, "
    "Session 1: the first-party pull-verifier adapter). You did not author it. Be "
    "rigorous and concrete: cite the specific function / line / claim. Distinguish "
    "a real correctness or safety defect from a style nit. End with a JSON verdict "
    'block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[{"severity":'
    '"Critical|Major|Minor","claim":"<what>","problem":"<why>","fix":"<how>"}]}.'
)

USER = f"""{BIAS_CAUTIONS}

{CONVENTIONS}

=== DELIVERABLE 1: tool-contract.md (the pinned S1 design contract) ===
{contract}

=== DELIVERABLE 2: ai_router/pull_verifier.py (the adapter) ===
{module}

=== DELIVERABLE 3: ai_router/tests/test_pull_verifier.py (the tests) ===
{tests}

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
    out = HERE / "s1-verification.md"
    out.write_text(
        "# Set 067 S1 -- Cross-provider verification (gpt-5.4)\n\n"
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

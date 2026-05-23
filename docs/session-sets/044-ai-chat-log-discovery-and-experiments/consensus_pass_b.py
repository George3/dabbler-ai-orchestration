"""Set 044 Session 5 - Pass B devil's-advocate consensus driver.

Per docs/ai-led-session-workflow.md Section "Prompt-framing discipline":
Pass B runs after Pass A returns material disagreement. The Pass A
disagreement was on S6 GO/NO-GO (2 GO vs 1 NO-GO) and a 2-1 split
on joiner location.

Pass B steelmans a SPECIFIC contrarian hypothesis: that the Pass A
"wrapper-first, GO on S6" convergence is the very framing-bias the
preamble was supposed to mitigate. The wrapper was foregrounded in
proposal.md Section 8.7 with several positive framings ("no AI cooperation
required," "natural home for cross-cutting concerns," "small,"
"cross-provider by construction") that may have pulled Pass A
reviewers toward endorsement.

Same 3 providers as Pass A; same bundle plus Pass A verdicts;
devil's-advocate focus prompt. Outputs to:
  verification-output/pass-b-gpt-5-4.json
  verification-output/pass-b-gemini-pro.json
  verification-output/pass-b-opus-4-6.json

Per memory feedback_ai_router_route_result_handling: dump
RouteResult to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent
OUT_DIR = SET_DIR / "verification-output"

PROVIDERS = [
    ("gpt-5-4",    "pass-b-gpt-5-4.json"),
    ("gemini-pro", "pass-b-gemini-pro.json"),
    ("opus",       "pass-b-opus-4-6.json"),
]


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


def read_pass_a_response(filename: str) -> str:
    path = OUT_DIR / filename
    if not path.exists():
        return f"=== PASS A RESPONSE: {filename} (missing) ==="
    data = json.loads(path.read_text(encoding="utf-8"))
    text = data.get("response") or data.get("text") or data.get("content") or "<no text>"
    model = data.get("model_id") or data.get("model_name") or data.get("model") or "?"
    return f"=== PASS A RESPONSE: {filename} (model={model}) ===\n{text}"


SYSTEM_SUMMARY = """
Set 044 Pass B devil's-advocate consensus call.

Pass A (just completed) routed proposal.md v0 to three providers
(gpt-5-4, gemini-pro, claude-opus-4-6) at max effort, with the
canonical bias-cautions preamble.

Pass A converged strongly on:
  - ENDORSE-WITH-REVISIONS the harvest direction
  - PROMOTE the operator-floated wrapper (proposal Section 8.7) to
    PRIMARY ARCHITECTURE; narration becomes fallback
  - Drop per-turn narration permanently
  - Wrapper lives in ai_router/, headless-first, ungated-default
  - Forward-compatible with Sets 042-043 (chat interface)
  - Retire Sets 038-041

Pass A diverged on:
  - S6 GO/NO-GO: GPT-5-4 said NO-GO (defer to Set 045 because the
    architecture-correct S6 is too big for one session); Gemini Pro
    and Opus 4.6 said GO with a wrapper-shipped scope
  - Joiner location: Python (GPT-5-4, Gemini Pro) vs TypeScript in
    extension (Opus 4.6)

Cumulative Set 044 spend going into Pass B: $1.10 of $15.00 NTE.

Per workflow.md Prompt-framing discipline Section #2 "Devil's-advocate
two-pass pattern":
  > "Pass B - an auto-generated counter-prompt that steelmans a
  > SPECIFIC contrarian hypothesis [...] Not 'be contrarian' -
  > that produces theatrically negative reviews that look
  > insightful but waste budget."

The contrarian hypothesis below is specific and steelmans real
concerns that Pass A may have underweighted due to authoring-agent
framing in proposal.md Section 8.7. The Pass A reviewers were
shown the wrapper through a deliberately favorable lens (multiple
positive framings, listed before drawbacks); Pass B asks them to
engage with the same wrapper through a deliberately unfavorable
lens to test whether their Pass A endorsement holds up.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt was authored by an AI agent that may
have an opinion on the answer. Its framing may inadvertently
constrain you toward agreeing with the contrarian hypothesis below
just because it's been packaged as a steelman. Before defending
the contrarian position, briefly check whether the contrarian is
ACTUALLY correct, or whether you should refute it. If your Pass A
position holds up under this counter-prompt, say so clearly. The
purpose of Pass B is robustness-testing, not position reversal.

== CONTEXT ==

You are seeing the Pass A responses from all three providers
(yourself and the other two) attached as evidence. Pass A
converged on a "wrapper-first, narration-fallback, GO on S6"
recommendation. Pass B's job is to steelman a SPECIFIC contrarian
hypothesis to test whether that convergence is robust or whether
it was driven by the way proposal.md Section 8.7 framed the wrapper.

== THE CONTRARIAN HYPOTHESIS YOU ARE ASKED TO STEELMAN ==

"The Pass A wrapper-first convergence is premature and possibly
incorrect. Specifically:

(A) The wrapper is launch-adapters-in-disguise. The proposal
    correctly identified that Sets 037-041's per-provider TypeScript
    LaunchAdapter / LaunchPlan / BeginSessionRequest architecture was
    over-engineered for the actual problem. But the wrapper merely
    RELOCATES the launch-adapter pattern from TypeScript to Python
    and from extension-coupled to CLI-coupled. The per-provider
    complexity that gets dropped (argv mapping, env handling) is
    only dropped because the AI CLI handles it - but that was
    always true; it didn't require a wrapper to be the case. So
    the wrapper has all the operational fragility of a launch
    adapter (must be invoked; bypassed when operators open a
    terminal manually; needs cross-provider passthrough discipline)
    with none of the named drawbacks of the heavyweight version.

(B) The 'narration as fallback' framing trivializes the real
    adoption story. Pass A's wrapper-primary recommendation assumes
    most observability-relevant sessions go through Dabbler-launched
    terminals. But operators routinely open new terminals, use
    integrated terminals in VS Code, run from PowerShell windows,
    invoke AI CLIs from scripts, etc. - all of which BYPASS the
    wrapper. If 30%-80% of real-world sessions are bypassed, the
    wrapper is delivering observability only on the EASY case
    (Dabbler already knows what's happening at launch time) while
    narration carries the load on the HARD case (sessions that
    sprung up outside Dabbler's purview). Trivializing narration
    as 'fallback' under-invests in the path that actually matters
    for adoption.

(C) S6 should defer ALL implementation to Set 045, where the
    wrapper can be designed alongside (not before) the conflict-
    detection joiner that will actually exercise it. Shipping the
    wrapper in S6 without the joiner produces an artifact whose
    correctness can't be validated: the wrapper writes records that
    only the (Set 045) joiner consumes. A wrapper that's correct
    in isolation but joins wrong against the conflict-detection
    semantics is worse than no wrapper. S6 in-set shipping forces
    premature commitment to a wrapper record schema that should be
    a joint design product."

== YOUR TASK ==

Respond in this structure:

PART 1 - STEELMAN STRENGTH ASSESSMENT (one paragraph each on A, B, C)

   For each sub-claim (A, B, C), make the strongest argument you can
   that it's correct. Not 'this is an interesting concern' - actually
   defend the claim. Cite specific evidence from S1-S5 deliverables or
   from your Pass A reasoning that supports the contrarian view.

PART 2 - WHAT WOULD MAKE EACH CLAIM OBVIOUSLY TRUE? (bulleted, per claim)

   For each of A, B, C: what concrete evidence, if present, would
   force you to flip from your Pass A position to the contrarian
   position? Be specific - 'usage data showing X% of sessions
   bypass the wrapper' beats 'evidence the wrapper isn't useful.'

PART 3 - POSITION RECONCILIATION

   After steelmanning A, B, and C: does your Pass A position HOLD
   UP, FLIP, or PARTIALLY-REVISE? State explicitly. If hold-up:
   why does the contrarian case fail despite being steelmanned? If
   flip or partial-revise: what's the new recommendation and why
   does the contrarian win that specific point?

   In particular, did the framing of proposal.md Section 8.7 (positive
   framing of the wrapper, less-foregrounded drawbacks) bias your
   Pass A response? Be honest. If yes, what's your revised
   position once the framing is corrected?

PART 4 - S6 GO/NO-GO UNDER PASS B FRAMING

   Re-answer the S6 GO/NO-GO question, taking the steelmanned
   contrarian into account. If your Pass A position holds: defend
   against the contrarian's claim (C) specifically. If you flip:
   explain what specifically about (A) or (B) or (C) was load-bearing.

== FORMAT ==

Plain prose under the PART labels above. Under ~2500 words total.
""".strip()


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)

    bundle_parts = [
        read_file(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/proposal.md"
        ),
        read_pass_a_response("pass-a-gpt-5-4.json"),
        read_pass_a_response("pass-a-gemini-pro.json"),
        read_pass_a_response("pass-a-opus-4-6.json"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle):,} chars across {len(bundle_parts)} parts")

    context = (
        f"{SYSTEM_SUMMARY}\n\n"
        f"--- BUNDLE START ---\n{bundle}\n--- BUNDLE END ---"
    )

    results: list[tuple[str, dict]] = []
    for model_alias, out_filename in PROVIDERS:
        out_path = OUT_DIR / out_filename
        print(f"\n{'='*64}")
        print(f"[Pass B] {model_alias} -> {out_path.name}")
        print(f"{'='*64}")

        if out_path.exists():
            try:
                prior = json.loads(out_path.read_text(encoding="utf-8"))
                if "_error" not in prior and (prior.get("response") or prior.get("text") or prior.get("content")):
                    print(f"  SKIP: prior successful result on disk (input_tokens="
                          f"{prior.get('input_tokens', '?')}, "
                          f"cost=${prior.get('cost_usd', prior.get('cost', '?'))})")
                    results.append((model_alias, prior))
                    continue
            except json.JSONDecodeError:
                pass

        t0 = time.time()
        try:
            result = ai_router.query(
                model=model_alias,
                content=FOCUS_PROMPT,
                task_type="analysis",
                context=context,
                session_set="044-ai-chat-log-discovery-and-experiments",
                session_number=5,
            )
            result_dict = dump_route_result_to_json(result)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  EXCEPTION after {elapsed:.1f}s: {type(e).__name__}: {e}")
            result_dict = {"_error": f"{type(e).__name__}: {e}", "_elapsed_s": elapsed}
        else:
            elapsed = time.time() - t0
            print(f"  Elapsed: {elapsed:.1f}s")
            print(
                "  Tokens: "
                f"in={result_dict.get('input_tokens', '?')}, "
                f"out={result_dict.get('output_tokens', '?')}"
            )
            print(
                "  Cost:   "
                f"${result_dict.get('cost_usd', result_dict.get('cost', '?'))}"
            )

        out_path.write_text(
            json.dumps(result_dict, default=str, indent=2),
            encoding="utf-8",
        )
        print(f"  Wrote {out_path.relative_to(REPO_ROOT).as_posix()}")
        results.append((model_alias, result_dict))

    print(f"\n{'='*64}")
    print("Pass B summary")
    print(f"{'='*64}")
    total_cost = 0.0
    for alias, rd in results:
        cost = rd.get("cost_usd") or rd.get("cost") or 0
        try:
            cost = float(cost)
        except (TypeError, ValueError):
            cost = 0
        total_cost += cost
        status = "OK" if "_error" not in rd else f"FAIL ({rd['_error'][:60]})"
        print(f"  {alias:20s}  status={status}  cost=${cost}")
    print(f"  ---")
    print(f"  Pass B total: ${total_cost:.4f}")
    print(f"  Cumulative Set 044 routed spend: ${1.0967 + total_cost:.4f} of $15.00 NTE")

    return 0


if __name__ == "__main__":
    sys.exit(main())

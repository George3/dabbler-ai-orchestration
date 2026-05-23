"""Set 044 Session 5 — Pass A consensus driver.

Routes the proposal.md v0 draft + the load-bearing S4 + S5 sidebar
evidence to three providers at max effort:

  - gpt-5.4 (OpenAI, tier 3)
  - gemini-pro (Google, tier 2 — the heaviest Gemini we expose)
  - claude-opus-4-6 (Anthropic, tier 3) — explicitly the 4.6 model
    so the consensus has a within-Anthropic check that's distinct
    from the 4.7 orchestrator authoring the proposal

Each provider gets the same bundle and the same focus prompt
(bias-cautions preamble + the 8 open questions). Calls are
sequential, not parallel, so a 429 on one provider doesn't
cascade.

Outputs:
  verification-output/pass-a-gpt-5-4.json
  verification-output/pass-a-gemini-pro.json
  verification-output/pass-a-opus-4-6.json

Per memory feedback_ai_router_route_result_handling: dump
RouteResult to JSON before any attribute access.
Per memory feedback_split_large_verification_bundles: the bundle
includes the full proposal + the new sidebar + the S4 cross-
backend synthesis but excludes the per-backend narration result
docs (which the proposal §3 compresses). Bundle is ~1300 lines.

Per docs/ai-led-session-workflow.md §Prompt-framing discipline:
the bias-cautions preamble is always-on. Devil's-advocate Pass B
is deferred pending Pass A convergence inspection.
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
    ("gpt-5-4",     "pass-a-gpt-5-4.json"),
    ("gemini-pro",  "pass-a-gemini-pro.json"),
    ("opus",        "pass-a-opus-4-6.json"),
]


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def read_section(path: Path, start_marker: str, end_marker: str | None = None) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        return f"=== FILE: {rel} (SECTION MISSING: {start_marker!r}) ==="
    if end_marker is None:
        section = text[start:]
    else:
        end = text.find(end_marker, start + len(start_marker))
        section = text[start:end] if end > 0 else text[start:]
    return f"=== FILE: {rel} (from {start_marker!r}) ===\n{section}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 044 (AI chat-log discovery + experiments) is the spike that
decides between two strategic approaches for Session Set Explorer
observability:

  (1) Log-harvest observability layer — read the logs the AI CLIs
      already write; this set tests whether that's sufficient.

  (2) Per-provider launch adapters — Sets 037-041, ~4 session-sets
      of TypeScript extension work, scoped BEFORE any empirical
      investigation.

Sessions 1-4 (CLOSED 2026-05-22):
  S1 — Copilot baseline log harvest (OTel JSONL + session-store.db)
  S2 — Claude Code baseline log harvest (~/.claude/projects/*.jsonl)
  S3 — Narration design v1 LOCKED (CLAUDE.md / AGENTS.md template
       contract carrying a phase=session-start marker to close
       the missing C3 boundary signal)
  S4 — Live narration experiments. Copilot complied cleanly under
       v1 contract. Claude REFUSED v1 phrasing (classified as
       prompt-injection). Claude v2 reframed phrasing: emitted
       phase=session-start marker but 0 of 3 phase=turn markers.

S5 — THIS session. Concrete proposal + cross-provider consensus.

S5 deliverables (this driver authors the consensus call):
  - proposal.md (v0 draft, attached)
  - proposal-consensus-journal.md (written post-consensus)
  - Explicit go/no-go decision for S6 in-set vs Set 045 deferral

Cumulative Set 044 routed spend going into Pass A: $0.292 of
$15.00 NTE. Estimated Pass A spend across the 3 providers below:
$1-5. Cumulative projected: $1.3-5.3 of $15.

Recent additions to context (the consensus reviewer should know):
  - 2026-05-23 S5 sidebar: Copilot --effort low + --effort high
    matched-pair runs. gen_ai.request.reasoning_effort attribute
    OMITTED at every effort level. Branch A (native A3) is dead
    on Copilot. Both backends now symmetric in lacking native A3.
  - 2026-05-23 operator-floated idea (§8.7 of the proposal): a
    Python launch wrapper as a logging interceptor — the wrapper
    records Dabbler context outside the AI's output, sidestepping
    Claude's phrasing-sensitivity entirely. Added as an explicit
    open question; NOT in the proposal's headline recommendation.

Workflow doc §Prompt-framing discipline mandates the always-on
bias-cautions preamble and recommends devil's-advocate two-pass
for "decisions that bind long-lived contracts" + "roadmap or
session-set sequence reviews." Both apply here. Pass A runs
with preamble first; Pass B is conditional on convergence
inspection.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt was authored by an AI agent
(claude-opus-4-7, currently orchestrating Set 044 S5) that may
have an opinion on the answer. Its framing may inadvertently
constrain you to in-scope refinements when the right answer is
to question the scope. The work being reviewed may be presented
as further along than it should be. Before answering as posed,
briefly check whether this is the right question. If a different
question would be more useful, answer that one too.

You are being asked for cross-provider consensus review on a
proposal that will reshape ~4 session-sets of planned roadmap
work (Sets 037-041) and commit to an architectural direction for
Session Set Explorer observability. The proposal's headline
recommendation is "build log-harvesting, retire launch adapters."

The verification target is NOT "does the proposal text contain
factual errors" — it's "is the proposal's headline recommendation
defensible given the empirical evidence S1-S5 produced, and how
should the 8 open questions in §8 be resolved?"

== YOUR TASK ==

Please respond in the following structure:

PART 1 — TOP-LEVEL ASSESSMENT (1-3 paragraphs)
   Do you ENDORSE, ENDORSE-WITH-REVISIONS, REJECT, or REFRAME the
   proposal's headline recommendation in §0? If REFRAME: what
   question should the proposal be answering instead?

PART 2 — PER-QUESTION ENGAGEMENT (one paragraph per question)
   For each of §8.1 through §8.7, give your position. Be specific:
   "I recommend X because Y" rather than "this is a difficult
   trade-off." You may decline to engage on items where your
   training doesn't give you a defensible position; say so
   explicitly rather than hedging.

PART 3 — RISKS YOU'D ADD OR REMOVE (bulleted)
   §7 lists risks. What's missing or overweighted?

PART 4 — S6 GO/NO-GO
   Defend a position on §9 (in-set S6 implementation vs deferral
   to Set 045). Cite the §9 flip conditions and whether any of
   them are met by your read of the evidence.

PART 5 — RIGHT QUESTION CHECK (1-2 paragraphs)
   Per the bias-cautions preamble: is the harvest-vs-adapter
   framing of §1 the right framing? Specifically — is the
   operator-floated wrapper idea in §8.7 a genuinely third
   option, or is it a variant of one of the two that should
   collapse into existing framing? If you think the §1 framing
   misses a genuinely-different fourth option, raise it here.

== FORMAT ==

Plain prose, headed by the PART labels above. No need for
bulleted summaries before the PART blocks. Length: as long as
needed to be specific, but stay under ~3000 words total.
""".strip()


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)

    bundle_parts = [
        read_section(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/spec.md",
            "## Project Overview",
            "## Sessions",
        ),
        read_section(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/spec.md",
            "### Session 5 of 6:",
            "### Session 6 of 6:",
        ),
        read_section(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/spec.md",
            "### Session 6 of 6:",
            None,
        ),
        read_file(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/proposal.md"
        ),
        read_file(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/cross-backend-synthesis.md"
        ),
        read_file(
            REPO_ROOT
            / "docs/session-sets/044-ai-chat-log-discovery-and-experiments/copilot-effort-sidebar-results.md"
        ),
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
        print(f"[Pass A] {model_alias} -> {out_path.name}")
        print(f"{'='*64}")

        # Skip if a successful prior result is on disk.
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

    # Summary table
    print(f"\n{'='*64}")
    print("Pass A summary")
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
    print(f"  Pass A total: ${total_cost:.4f}")
    print(f"  Cumulative Set 044 routed spend: ${0.2920 + total_cost:.4f} of $15.00 NTE")

    return 0


if __name__ == "__main__":
    sys.exit(main())

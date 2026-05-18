"""Route the custom-tree pivot design proposal through Gemini Pro.

Per memory `feedback_prefer_ai_consensus_over_human_prompt`: design
judgment calls route through GPT-5.4 + Gemini Pro before any
substantive implementation work. Operator pre-authorized this call
2026-05-18 via the BATON handoff for Set 029 Session 3.

GPT-5.4 is going through the manual-paste workaround
(`gpt-5-4-prompt-for-manual-paste.md`) because the API is
429-rate-limited per memory `feedback_split_large_verification_bundles`.

Per memory `feedback_ai_router_route_result_handling`: RouteResult
is dumped to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# proposal dir -> proposals -> docs -> repo
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dump_result(result, out_path: Path) -> dict:
    if dataclasses.is_dataclass(result):
        result_dict = dataclasses.asdict(result)
    else:
        result_dict = {
            "content": getattr(result, "content", None),
            "model_name": getattr(result, "model_name", None),
            "model_id": getattr(result, "model_id", None),
            "tier": getattr(result, "tier", None),
            "input_tokens": getattr(result, "input_tokens", None),
            "output_tokens": getattr(result, "output_tokens", None),
            "cost_usd": getattr(result, "cost_usd", None),
            "total_cost_usd": getattr(result, "total_cost_usd", None),
            "elapsed_seconds": getattr(result, "elapsed_seconds", None),
        }
    out_path.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return result_dict


def main() -> int:
    proposal_text = _read(HERE / "proposal.md")

    gemini_content = (
        "# Cross-provider review request: custom-tree pivot for Session Sets view\n\n"
        "You are one of two reviewers (the other is GPT-5.4, reviewing "
        "independently via manual paste in GitHub Copilot — they have NOT "
        "seen your verdict and you have NOT seen theirs). Review the design "
        "proposal below and give your independent verdict on each of the "
        "ten open questions (Q1-Q10) plus an overall recommendation. "
        "Structured response per question — verdict + reasoning + any "
        "must-fix items. Be explicit about must-fix vs. recommendations "
        "vs. nice-to-haves. Where you think the proposal is fundamentally "
        "wrong (not just a question I asked), say so directly.\n\n"
        "IMPORTANT CONTEXT: an earlier proposal in this same codebase "
        "(per-workspace orchestrator markers, at "
        "`docs/proposals/2026-05-18-per-workspace-orchestrator-markers/proposal.md`) "
        "was reviewed by both you and GPT-5.4 earlier today. The proposal "
        "below SUPERSEDES that one. Please review THIS proposal on its own "
        "merits; do not assume the per-workspace decisions carry over.\n\n"
        "The operator wants three-way agreement (operator + you + GPT-5.4) "
        "before this is formalized in spec.md for Session 3 of Set 029.\n\n"
        "---\n\n"
        + proposal_text
    )

    spec_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )

    print(f"Gemini Pro prompt size: {len(gemini_content):,} chars")
    gemini_result = ai_router.query(
        model="gemini-pro",
        content=gemini_content,
        task_type="cross-provider-audit",
        session_set=str(spec_path.parent),
        session_number=3,
    )
    gemini_dict = _dump_result(gemini_result, HERE / "consensus-gemini-pro.json")
    gemini_cost = (
        gemini_dict.get("total_cost_usd") or gemini_dict.get("cost_usd")
    )
    print(
        f"Gemini Pro: cost ${gemini_cost} / "
        f"{gemini_dict.get('input_tokens')} in / "
        f"{gemini_dict.get('output_tokens')} out"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Route the S4 custom-tree implementation audit through Gemini Pro.

Per memory `feedback_audit_then_spec_for_substantial_features`:
non-trivial implementation work routes through GPT-5.4 + Gemini Pro
before spec is locked. Operator pre-authorized this call 2026-05-18
at the start of Set 029 Session 4.

GPT-5.4 goes through manual-paste in GitHub Copilot
(`gpt-5-4-prompt-for-manual-paste.md`) per memory
`feedback_split_large_verification_bundles`.

Per memory `feedback_ai_router_route_result_handling`: RouteResult
is dumped to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
        "# Cross-provider review request: custom-tree IMPLEMENTATION audit (Set 029 S4)\n\n"
        "You are one of two independent reviewers (the other is GPT-5.4 via "
        "manual paste in GitHub Copilot — they have NOT seen your verdict and "
        "you will NOT see theirs until both responses are synthesized). The "
        "operator wants three-way agreement (operator + you + GPT-5.4) before "
        "spec.md is updated and implementation begins.\n\n"
        "IMPORTANT CONTEXT: this is the SECOND audit in a two-step process. "
        "The macro pivot itself (TreeView -> WebviewView for `dabblerSessionSets`) "
        "was decided in an earlier audit at "
        "`docs/proposals/2026-05-18-custom-tree-pivot/` (which you reviewed). "
        "S3 has SHIPPED — per-set markers, the walk-up resolver, and "
        "`SessionSetsModel.ts` extraction are all in production code "
        "(commit f1cc44d). This audit is about the IMPLEMENTATION SHAPE for "
        "S4 — message protocol, ARIA semantics, auto-expand persistence, "
        "context-menu mechanism, scope packaging. The pivot itself is "
        "locked; do not re-debate it.\n\n"
        "Please review the proposal below and give your independent verdict "
        "on each of the eleven open questions (Q1-Q11) plus the eight cross-"
        "cutting checks listed under 'What to verify in the consensus call'. "
        "Structured response per question — verdict + reasoning + any must-"
        "fix items. Be explicit about must-fix vs. recommendations vs. nice-"
        "to-haves. Where you think the proposal is fundamentally wrong (not "
        "just a question I asked), say so directly.\n\n"
        "Per memory `feedback_prefer_ai_consensus_over_human_prompt`, where "
        "you would push back on the operator's framing, push back — that is "
        "the value of routing this.\n\n"
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
        session_number=4,
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

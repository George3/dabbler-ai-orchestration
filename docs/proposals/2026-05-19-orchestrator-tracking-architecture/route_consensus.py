"""Route the orchestrator-tracking architecture proposal through
GPT-5.4 + Gemini Pro for cross-provider consensus.

Per memory `feedback_prefer_ai_consensus_over_human_prompt`: design
judgment calls route through GPT-5.4 + Gemini Pro before substantive
implementation work. Operator explicitly authorized this call
2026-05-19 mid-Session-6 (Set 029) — an override on the standing
`feedback_ai_router_usage` end-of-session-only restriction.

Per memory `feedback_ai_router_route_result_handling`: RouteResult is
dumped to JSON before any attribute access.

Per memory `lessons-learned` "Persist Routed Output To Disk Before
Display Or Logging": result.content is written to a .txt sibling file
before anything else.
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


def _dump_result(result, label: str) -> dict:
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

    # Persist content to a .txt sibling file FIRST per lessons-learned
    # ("Persist Routed Output To Disk Before Display Or Logging") — never
    # print(result.content) on Windows cp1252 terminals.
    content_path = HERE / f"consensus-{label}.txt"
    content_path.write_text(
        result_dict.get("content") or "",
        encoding="utf-8",
    )

    json_path = HERE / f"consensus-{label}.json"
    json_path.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return result_dict


def main() -> int:
    proposal_text = _read(HERE / "proposal.md")

    full_content_template = (
        "# Cross-provider consensus request: orchestrator-tracking "
        "architecture for Set 029 Session 6 (dabbler-ai-orchestration)\n\n"
        "You are one of two reviewers (the other is __OTHER__). Read the "
        "proposal below and answer the six numbered questions with the "
        "specified verdict structure. The operator wants three-way "
        "agreement (you, the other reviewer, the operator) on whether to "
        "ship v0.17.x as-is with renamed buttons OR migrate to a "
        "check-out / check-in architecture in a follow-on session set.\n\n"
        "Be honest. If both architectures earn their keep in different "
        "use cases, say so (verdict: hybrid). If the proposal is missing "
        "a failure mode you think is load-bearing, flag it. If you think "
        "the operator's UI minimalism push is over-correcting and the "
        "buttons should stay, say that.\n\n"
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

    # GPT-5.4
    gpt_content = full_content_template.replace("__OTHER__", "Gemini Pro")
    print(f"GPT-5.4 prompt size: {len(gpt_content):,} chars")
    gpt_result = ai_router.query(
        model="gpt-5-4",
        content=gpt_content,
        task_type="cross-provider-audit",
        session_set=str(spec_path.parent),
        session_number=6,
    )
    gpt_dict = _dump_result(gpt_result, "gpt-5-4")
    gpt_cost = gpt_dict.get("total_cost_usd") or gpt_dict.get("cost_usd")
    print(
        f"GPT-5.4: cost ${gpt_cost} / "
        f"{gpt_dict.get('input_tokens')} in / {gpt_dict.get('output_tokens')} out"
    )

    # Gemini Pro
    gemini_content = full_content_template.replace("__OTHER__", "GPT-5.4")
    print(f"Gemini Pro prompt size: {len(gemini_content):,} chars")
    gemini_result = ai_router.query(
        model="gemini-pro",
        content=gemini_content,
        task_type="cross-provider-audit",
        session_set=str(spec_path.parent),
        session_number=6,
    )
    gemini_dict = _dump_result(gemini_result, "gemini-pro")
    gemini_cost = gemini_dict.get("total_cost_usd") or gemini_dict.get("cost_usd")
    print(
        f"Gemini Pro: cost ${gemini_cost} / "
        f"{gemini_dict.get('input_tokens')} in / {gemini_dict.get('output_tokens')} out"
    )

    total = (gpt_cost or 0) + (gemini_cost or 0)
    print(f"Total consensus call cost: ${total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

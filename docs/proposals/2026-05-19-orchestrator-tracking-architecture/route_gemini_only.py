"""Route the consensus packet through Gemini Pro only.

GPT-5.4 hit a 429 on the first attempt at the combined call; running
Gemini Pro independently so the consensus loop isn't blocked. The
GPT-5.4 half is either re-routed later via this script's GPT helper
or pasted manually into Codex IDE / Copilot per memory
`feedback_split_large_verification_bundles`.
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


def _dump(result, label: str) -> dict:
    if dataclasses.is_dataclass(result):
        d = dataclasses.asdict(result)
    else:
        d = {
            "content": getattr(result, "content", None),
            "model_name": getattr(result, "model_name", None),
            "model_id": getattr(result, "model_id", None),
            "input_tokens": getattr(result, "input_tokens", None),
            "output_tokens": getattr(result, "output_tokens", None),
            "cost_usd": getattr(result, "cost_usd", None),
            "total_cost_usd": getattr(result, "total_cost_usd", None),
        }
    (HERE / f"consensus-{label}.txt").write_text(d.get("content") or "", encoding="utf-8")
    (HERE / f"consensus-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    proposal_text = (HERE / "proposal.md").read_text(encoding="utf-8")
    content = (
        "# Cross-provider consensus request: orchestrator-tracking "
        "architecture for Set 029 Session 6 (dabbler-ai-orchestration)\n\n"
        "You are one of two reviewers (the other is GPT-5.4, pending). "
        "Answer the six numbered questions with the verdict structure "
        "specified at the bottom of the proposal. Be honest. If both "
        "architectures earn their keep in different use cases, say so "
        "(verdict: hybrid). If the proposal is missing a load-bearing "
        "failure mode, flag it. If you think the operator's UI-minimalism "
        "push is over-correcting, say that.\n\n"
        "---\n\n"
        + proposal_text
    )
    spec_dir = REPO_ROOT / "docs" / "session-sets" / "029-orchestrator-model-effort-gauges"
    print(f"Gemini Pro prompt size: {len(content):,} chars")
    result = ai_router.query(
        model="gemini-pro",
        content=content,
        task_type="cross-provider-audit",
        session_set=str(spec_dir),
        session_number=6,
    )
    d = _dump(result, "gemini-pro")
    cost = d.get("total_cost_usd") or d.get("cost_usd")
    print(
        f"Gemini Pro: cost ${cost} / "
        f"{d.get('input_tokens')} in / {d.get('output_tokens')} out"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

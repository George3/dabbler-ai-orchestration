"""Route the audit-resolution packet through GPT-5.4 + Gemini Pro.

Set 032 Session 1 deliverable. The packet
(audit-resolution-request.md) asks each engine to confirm / refine /
refute the pre-audit recommended verdicts on H1, H2, H3, OQ1, OQ2.

Per memory `feedback_ai_router_route_result_handling`: dump the
RouteResult to JSON before any attribute access.
Per lessons-learned "Persist Routed Output To Disk Before Display
Or Logging": write content to .txt before printing.
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


def _dump(result, label: str) -> dict:
    if dataclasses.is_dataclass(result):
        d = dataclasses.asdict(result)
    else:
        d = {
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
    (HERE / f"audit-resolution-{label}.txt").write_text(
        d.get("content") or "", encoding="utf-8"
    )
    (HERE / f"audit-resolution-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    packet = (HERE / "audit-resolution-request.md").read_text(encoding="utf-8")

    session_set_dir = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "032-orchestrator-checkout-checkin-audit"
    )

    # GPT-5.4
    gpt_content = packet.replace("__OTHER__", "Gemini Pro")
    print(f"GPT-5.4 prompt size: {len(gpt_content):,} chars")
    try:
        gpt_result = ai_router.query(
            model="gpt-5-4",
            content=gpt_content,
            task_type="cross-provider-audit",
            session_set=str(session_set_dir),
            session_number=1,
        )
        gpt_dict = _dump(gpt_result, "gpt-5-4")
        gpt_cost = gpt_dict.get("total_cost_usd") or gpt_dict.get("cost_usd")
        print(
            f"GPT-5.4: cost ${gpt_cost} / "
            f"{gpt_dict.get('input_tokens')} in / {gpt_dict.get('output_tokens')} out"
        )
    except Exception as exc:
        print(f"GPT-5.4 FAILED: {type(exc).__name__}: {exc}")
        gpt_cost = 0

    # Gemini Pro
    gemini_content = packet.replace("__OTHER__", "GPT-5.4")
    print(f"Gemini Pro prompt size: {len(gemini_content):,} chars")
    try:
        gemini_result = ai_router.query(
            model="gemini-pro",
            content=gemini_content,
            task_type="cross-provider-audit",
            session_set=str(session_set_dir),
            session_number=1,
        )
        gemini_dict = _dump(gemini_result, "gemini-pro")
        gemini_cost = gemini_dict.get("total_cost_usd") or gemini_dict.get("cost_usd")
        print(
            f"Gemini Pro: cost ${gemini_cost} / "
            f"{gemini_dict.get('input_tokens')} in / {gemini_dict.get('output_tokens')} out"
        )
    except Exception as exc:
        print(f"Gemini Pro FAILED: {type(exc).__name__}: {exc}")
        gemini_cost = 0

    total = (gpt_cost or 0) + (gemini_cost or 0)
    print(f"Total audit-resolution call cost: ${total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

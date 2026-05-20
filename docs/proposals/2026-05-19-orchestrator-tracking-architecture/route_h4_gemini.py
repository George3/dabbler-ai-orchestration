"""Route the H4 follow-up packet through Gemini Pro.

Set 032 Session 1 — GPT-5.4 raised H4 (holder identity key) after
confirming H1/H2/H3/OQ1/OQ2. Gemini Pro confirmed the original
five but hasn't seen H4. This packet gets Gemini's H4 verdict so
we have cross-engine consensus on all six items before locking.
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
            "tier": getattr(result, "tier", None),
            "input_tokens": getattr(result, "input_tokens", None),
            "output_tokens": getattr(result, "output_tokens", None),
            "cost_usd": getattr(result, "cost_usd", None),
            "total_cost_usd": getattr(result, "total_cost_usd", None),
            "elapsed_seconds": getattr(result, "elapsed_seconds", None),
        }
    (HERE / f"audit-resolution-h4-{label}.txt").write_text(
        d.get("content") or "", encoding="utf-8"
    )
    (HERE / f"audit-resolution-h4-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    packet = (HERE / "audit-resolution-h4-request.md").read_text(encoding="utf-8")
    session_set_dir = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "032-orchestrator-checkout-checkin-audit"
    )

    print(f"Gemini Pro prompt size: {len(packet):,} chars")
    try:
        result = ai_router.query(
            model="gemini-pro",
            content=packet,
            task_type="cross-provider-audit",
            session_set=str(session_set_dir),
            session_number=1,
        )
        d = _dump(result, "gemini-pro")
        cost = d.get("total_cost_usd") or d.get("cost_usd")
        print(
            f"Gemini Pro: cost ${cost} / "
            f"{d.get('input_tokens')} in / {d.get('output_tokens')} out"
        )
    except Exception as exc:
        print(f"Gemini Pro FAILED: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

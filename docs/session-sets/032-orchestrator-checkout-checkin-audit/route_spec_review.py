"""Route the Set 033 spec review packet through Gemini Pro.

Set 032 Session 2 — cross-provider sanity check on the drafted
implementation spec.md. Per spec Step 3, Gemini Pro is the primary
reviewer; GPT-5.4 manual paste is reserved for must-fix items that
warrant a second opinion.

Cost cap: $0.15 (the spec is bounded; verification doesn't need to
be exhaustive). Forces Gemini Pro via ai_router.query rather than
ai_router.route (per Session 1's pattern — route() picked gpt-5-4
from a similar bundle and we want a deterministic Gemini call here).
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
    (HERE / f"spec-review-{label}.txt").write_text(
        d.get("content") or "", encoding="utf-8"
    )
    (HERE / f"spec-review-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    template = (HERE / "spec-review-request.md").read_text(encoding="utf-8")
    spec_body = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "033-orchestrator-checkout-checkin-implementation"
        / "spec.md"
    ).read_text(encoding="utf-8")
    packet = template.replace("__SPEC_BODY__", spec_body)

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
            session_number=2,
        )
        d = _dump(result, "gemini-pro")
        cost = d.get("total_cost_usd") or d.get("cost_usd")
        print(
            f"Gemini Pro: cost ${cost} / "
            f"{d.get('input_tokens')} in / {d.get('output_tokens')} out"
        )
    except Exception as exc:
        print(f"Gemini Pro FAILED: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

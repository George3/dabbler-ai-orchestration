"""Route the chatSessionId + watcher-scope audit packet through Gemini Pro.

Between-sets review: Set 033 closed; this proposal is the input to a
prospective Set-036-candidate audit cycle. The operator handles
GPT-5.4 manually per the audit-resolution-request paste flow used
in Set 032 (GPT-5.4 route attempts hit 429s historically; manual
paste is the established workaround).

Per memory `feedback_ai_router_route_result_handling`: dump the
RouteResult to JSON before any attribute access.
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
    (HERE / f"audit-resolution-{label}.txt").write_text(
        d.get("content") or "", encoding="utf-8"
    )
    (HERE / f"audit-resolution-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    proposal = (HERE / "proposal.md").read_text(encoding="utf-8")
    request = (HERE / "audit-resolution-request.md").read_text(encoding="utf-8")

    # Gemini gets the proposal as context (so it can refer back to
    # specific paragraphs by name) plus the structured request as
    # the prompt. The request itself names proposal.md, so we
    # prepend the proposal text under a clear delimiter.
    content = (
        "# CONTEXT — proposal.md (the document being reviewed)\n\n"
        f"{proposal}\n\n"
        "---\n\n"
        "# REQUEST — audit-resolution-request.md (structured review prompt)\n\n"
        f"{request}\n"
    )

    print(f"Gemini Pro prompt size: {len(content):,} chars")

    try:
        result = ai_router.query(
            model="gemini-pro",
            content=content,
            task_type="cross-provider-audit",
            session_set=str(HERE),
        )
        dumped = _dump(result, "gemini-pro")
        cost = dumped.get("total_cost_usd") or dumped.get("cost_usd")
        print(
            f"Gemini Pro: cost ${cost} / "
            f"{dumped.get('input_tokens')} in / "
            f"{dumped.get('output_tokens')} out"
        )
        text = dumped.get("content") or ""
        if text:
            print(f"\n--- GEMINI PRO VERDICT (first 4000 chars) ---")
            print(text[:4000])
            if len(text) > 4000:
                print(f"... [{len(text) - 4000} more chars in audit-resolution-gemini-pro.txt]")
            print(f"--- end ---\n")
        return 0
    except Exception as exc:
        print(f"Gemini Pro FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

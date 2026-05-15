"""Cross-provider design-alignment audit for the router-config editor proposal.

Routes the same prompt to gpt-5-4 (OpenAI) and gemini-pro (Google) and
dumps each RouteResult to its own JSON file. Idempotent — if a result
file already exists, that provider is skipped, so a partial-failure
retry doesn't double-spend.

Per the memory rule "ai_router.route() result handling — dump fields
before any attribute access," the full RouteResult is dumped to JSON
*before* reading any field. The dump is the canonical record; any
human-authored synthesis follows the dumps.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 2026-05-15-... -> proposals -> docs -> repo
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402

PROVIDERS = [
    ("gpt-5-4", "gpt-5-4-result.json"),
    ("gemini-pro", "gemini-pro-result.json"),
]


def main() -> int:
    prompt_path = HERE / "prompt.md"
    if not prompt_path.is_file():
        print(f"prompt.md not found at {prompt_path}", file=sys.stderr)
        return 2
    prompt_text = prompt_path.read_text(encoding="utf-8")
    print(f"prompt size: {len(prompt_text):,} chars")

    total_cost = 0.0
    for model_name, out_filename in PROVIDERS:
        out_path = HERE / out_filename
        if out_path.exists():
            print(f"[{model_name}] result already exists at {out_path}; skipping")
            try:
                existing = json.loads(out_path.read_text(encoding="utf-8"))
                cost = existing.get("total_cost_usd") or existing.get("cost_usd") or 0.0
                if isinstance(cost, (int, float)):
                    total_cost += float(cost)
            except Exception:
                pass
            continue

        print(f"[{model_name}] routing...")
        result = ai_router.query(
            model=model_name,
            content=prompt_text,
            task_type="analysis",
            session_set=str(HERE),
            session_number=0,
        )

        # Dump BEFORE any attribute access.
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

        cost = result_dict.get("total_cost_usd") or result_dict.get("cost_usd") or 0.0
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
        print(f"[{model_name}] returned: model_name={result_dict.get('model_name')}")
        print(f"[{model_name}] cost=${cost} input={result_dict.get('input_tokens')} output={result_dict.get('output_tokens')}")
        print(f"[{model_name}] dumped to {out_path}")

    print()
    print(f"Total cost across providers: ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

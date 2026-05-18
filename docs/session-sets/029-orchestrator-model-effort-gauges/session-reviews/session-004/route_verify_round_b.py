"""Route Set 029 Session 4 verification — Round B (integration: view + client).

Round B scope: CustomSessionSetsView.ts + client.js + tree.css +
Q1-Q8 prompt covering M1/M3/M6/M8 + R10/R11/R12. Round A (separate
script) covered the provider-layer extracts.

Per memory `feedback_split_large_verification_bundles`. Per memory
`feedback_ai_router_route_result_handling`.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    prompt_text = _read(HERE / "prompt-round-b.md")

    ext_root = REPO_ROOT / "tools" / "dabbler-ai-orchestration"
    files = [
        ("src/providers/CustomSessionSetsView.ts", "typescript"),
        ("media/session-sets-tree/client.js", "javascript"),
        ("media/session-sets-tree/tree.css", "css"),
    ]

    sections = [prompt_text]
    for i, (rel, lang) in enumerate(files, start=1):
        body = _read(ext_root / rel)
        sections.append(f"\n\n---\n\n## File {i}: {rel}\n\n```{lang}\n{body}\n```\n")

    full_content = "".join(sections)

    rendered_path = HERE / "prompt-round-b.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"Round B prompt size: {len(full_content):,} chars / "
          f"~{full_content.count(chr(10)):,} lines")

    spec_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )
    result = ai_router.query(
        model="gemini-pro",
        content=full_content,
        task_type="session-verification",
        session_set=str(spec_path.parent),
        session_number=4,
    )

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

    out_path = HERE / "verify-result-round-b.json"
    out_path.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    cost = result_dict.get("total_cost_usd") or result_dict.get("cost_usd")
    print(f"verifier model: {result_dict.get('model_name')}")
    print(f"cost: ${cost}")
    print(f"input tokens:  {result_dict.get('input_tokens')}")
    print(f"output tokens: {result_dict.get('output_tokens')}")
    print(f"dumped to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

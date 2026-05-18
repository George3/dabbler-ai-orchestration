"""Route Set 029 Session 2 Round C verification — confirmation pass.

Round A surfaced 3 must-fix items (TOCTOU, UserPromptSubmit clobber,
stale stripes overlay). Round B surfaced 2 must-fix items (effort
suffix wrong signal source, gauge angle math). All 5 fixes applied;
this round confirms.

Per memory `feedback_ai_router_route_result_handling`, RouteResult is
dumped to JSON before any field is read.
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
    prompt_text = _read(HERE / "prompt-round-c.md")

    ext_root = REPO_ROOT / "tools" / "dabbler-ai-orchestration"
    marker_writer = _read(ext_root / "scripts" / "write-orchestrator-marker.js")
    provider = _read(ext_root / "src" / "providers" / "orchestratorIndicatorProvider.ts")
    indicator_css = _read(ext_root / "media" / "orchestrator-indicator" / "indicator.css")

    full_content = (
        prompt_text
        + "\n\n---\n\n## File 1 (post-fix): scripts/write-orchestrator-marker.js\n\n"
        + "```javascript\n"
        + marker_writer
        + "\n```\n\n---\n\n## File 2 (post-fix): src/providers/orchestratorIndicatorProvider.ts\n\n"
        + "```typescript\n"
        + provider
        + "\n```\n\n---\n\n## File 3 (post-fix): media/orchestrator-indicator/indicator.css\n\n"
        + "```css\n"
        + indicator_css
        + "\n```\n"
    )

    rendered_path = HERE / "prompt-round-c.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"rendered Round C prompt size: {len(full_content):,} chars")

    spec_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )
    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(spec_path.parent),
        session_number=2,
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

    out_path = HERE / "verify-result-round-c.json"
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

"""Route the Session 4 verification prompt to a cross-provider verifier.

Per the memory rule "ai_router.route() result handling — dump fields
before any attribute access," we dump the full RouteResult to JSON
*before* reading any field. That dump is the canonical record of what
the verifier returned; the audit-summary verdict that follows is the
spec author's read of that dump.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# session-004 → session-reviews → 023-… → session-sets → docs → repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def main() -> int:
    prompt_path = HERE / "prompt.md"
    if not prompt_path.is_file():
        print(f"prompt.md not found at {prompt_path}", file=sys.stderr)
        return 2

    prompt_text = prompt_path.read_text(encoding="utf-8")

    fs_source = (
        REPO_ROOT / "tools" / "dabbler-ai-orchestration"
        / "src" / "utils" / "fileSystem.ts"
    ).read_text(encoding="utf-8")
    # Slice to just the new guard + helper to keep the prompt small.
    start_marker = "// Detect a stale `status: \"complete\"`"
    end_marker = "export function countDistinctCloseoutSessions"
    fs_start = fs_source.index(start_marker)
    fs_end = fs_source.index(end_marker)
    fs_excerpt = fs_source[fs_start:fs_end]

    test_source = (
        REPO_ROOT / "tools" / "dabbler-ai-orchestration"
        / "src" / "test" / "suite" / "fileSystem.test.ts"
    ).read_text(encoding="utf-8")
    # Slice to just the new suite + a few lines of imports for context.
    test_start_marker = "// Set 023 Session 4:"
    test_end_marker = "suite(\"fileSystem \\u2014 countDistinctCloseoutSessions\""
    try:
        test_start = test_source.index(test_start_marker)
    except ValueError:
        test_start = 0
    try:
        test_end = test_source.index(test_end_marker)
    except ValueError:
        test_end = len(test_source)
    test_excerpt = test_source[test_start:test_end]

    full_content = (
        prompt_text
        + "\n\n---\n\n## Inlined: isMidSetComplete (new) + hasCloseoutEventForSession\n\n"
        + "```typescript\n"
        + fs_excerpt
        + "\n```\n"
        + "\n---\n\n## Inlined: new test suite (F1–F7 plus migration bonus)\n\n"
        + "```typescript\n"
        + test_excerpt
        + "\n```\n"
    )

    rendered_path = HERE / "prompt.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")

    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(
            REPO_ROOT
            / "docs"
            / "session-sets"
            / "023-trust-completed-sessions-array"
        ),
        session_number=4,
    )

    # Dump the result to disk BEFORE any attribute access.
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

    out_path = HERE / "verify-result.json"
    out_path.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    cost = result_dict.get("total_cost_usd") or result_dict.get("cost_usd")
    print(f"verifier model: {result_dict.get('model_name')}")
    print(f"cost: ${cost}")
    print(f"input tokens: {result_dict.get('input_tokens')}")
    print(f"output tokens: {result_dict.get('output_tokens')}")
    print(f"dumped to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

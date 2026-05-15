"""Route the Session 3 audit-verification prompt to a cross-provider verifier.

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

# Find the repo root by walking up from this file. The session-set
# directory is three levels under the repo root.
HERE = Path(__file__).resolve().parent
# session-003 → session-reviews → 023-… → session-sets → docs → repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def main() -> int:
    prompt_path = HERE / "prompt.md"
    if not prompt_path.is_file():
        print(f"prompt.md not found at {prompt_path}", file=sys.stderr)
        return 2

    prompt_text = prompt_path.read_text(encoding="utf-8")

    # Read the audit-findings and the modified source so the verifier
    # has them inline (without needing local filesystem access). Same
    # pattern Session 1 and Session 2 used.
    audit_findings = (
        HERE.parent / "session-003-audit-findings.md"
    ).read_text(encoding="utf-8")
    fix_source = (
        REPO_ROOT / "ai_router" / "__init__.py"
    ).read_text(encoding="utf-8")
    # Slice to the function only — the file is huge, and the verifier
    # only needs the function body to confirm the fix.
    start_marker = "def print_session_set_status("
    end_marker = "def _calculate_cost("
    fn_start = fix_source.index(start_marker)
    fn_end = fix_source.index(end_marker)
    fix_excerpt = fix_source[fn_start:fn_end]

    test_source = (
        REPO_ROOT / "ai_router" / "tests"
        / "test_print_session_set_status_completed_count.py"
    ).read_text(encoding="utf-8")

    full_content = (
        prompt_text
        + "\n\n---\n\n## Inlined: session-003-audit-findings.md\n\n"
        + audit_findings
        + "\n\n---\n\n## Inlined: the modified print_session_set_status function\n\n"
        + "```python\n"
        + fix_excerpt
        + "\n```\n"
        + "\n---\n\n## Inlined: the three new regression tests\n\n"
        + "```python\n"
        + test_source
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
        session_number=3,
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

"""Route the Set 024 Session 1 verification prompt to a cross-provider verifier.

Per the memory rule "ai_router.route() result handling — dump fields
before any attribute access," the full RouteResult is dumped to JSON
*before* reading any field. That dump is the canonical record of what
the verifier returned; any human-authored summary that follows is the
spec author's read of that dump.

This session is deletion-only, so the verifier's job is to confirm:
- no stranded imports / dead references remain in the source tree
- package.json removals are internally consistent
- the simplified `resolvePythonPath()` fallback is the right shape
- the CHANGELOG accurately captures every operator-visible impact
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# session-001 -> session-reviews -> 024-... -> session-sets -> docs -> repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def get_diff() -> str:
    """Return the unified diff of the deletion vs. the prior commit."""
    # The prior commit (HEAD) is `Add Set 024 spec...` — the spec itself was
    # the last change. So `git diff HEAD` captures the entire session-1
    # implementation diff.
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "diff",
            "HEAD",
            "--",
            # Limit to the extension subtree + CLAUDE.md + the session
            # state file; exclude dist/ and out/ build artifacts to keep
            # the prompt tractable.
            "tools/dabbler-ai-orchestration/src",
            "tools/dabbler-ai-orchestration/package.json",
            "tools/dabbler-ai-orchestration/package-lock.json",
            "tools/dabbler-ai-orchestration/CHANGELOG.md",
            "CLAUDE.md",
            "docs/session-sets/024-remove-provider-queues-and-heartbeats-views/session-state.json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git diff failed ({proc.returncode}): {proc.stderr}"
        )
    return proc.stdout


def main() -> int:
    prompt_path = HERE / "prompt.md"
    if not prompt_path.is_file():
        print(f"prompt.md not found at {prompt_path}", file=sys.stderr)
        return 2
    prompt_text = prompt_path.read_text(encoding="utf-8")

    diff_text = get_diff()

    full_content = (
        prompt_text
        + "\n\n---\n\n## Unified diff (session 1 work vs. HEAD)\n\n"
        + "```diff\n"
        + diff_text
        + "\n```\n"
    )

    rendered_path = HERE / "prompt.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"rendered prompt size: {len(full_content):,} chars")
    print(f"rendered to: {rendered_path}")

    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(
            REPO_ROOT
            / "docs"
            / "session-sets"
            / "024-remove-provider-queues-and-heartbeats-views"
        ),
        session_number=1,
    )

    # Dump the result BEFORE any attribute access.
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

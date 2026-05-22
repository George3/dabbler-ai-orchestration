"""Route the launch-adapter design packet to gemini-pro for review.

Writes the fully composed prompt to disk, then calls ai_router.query()
with model='gemini-pro'. Dumps the full RouteResult to JSON before any
attribute access and writes the response body to a markdown file for
human reading.
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


FILES = [
    ("Original adapter design document", REPO_ROOT / "coding-assistant-adapter-spec.md", None),
    (
        "Existing related implementation plan (Set 036)",
        REPO_ROOT / "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/spec.md",
        220,
    ),
    (
        "New shared launch foundation plan (Set 037)",
        REPO_ROOT / "docs/session-sets/037-launch-adapter-foundations/spec.md",
        None,
    ),
    (
        "New Claude adapter plan (Set 038)",
        REPO_ROOT / "docs/session-sets/038-claude-launch-adapter/spec.md",
        None,
    ),
    (
        "New Copilot adapter plan (Set 039)",
        REPO_ROOT / "docs/session-sets/039-copilot-launch-adapter/spec.md",
        None,
    ),
    (
        "New Codex adapter plan (Set 040)",
        REPO_ROOT / "docs/session-sets/040-codex-launch-adapter/spec.md",
        None,
    ),
    (
        "New Gemini adapter plan (Set 041)",
        REPO_ROOT / "docs/session-sets/041-gemini-launch-adapter/spec.md",
        None,
    ),
    (
        "New chat foundation plan (Set 042)",
        REPO_ROOT / "docs/session-sets/042-rudimentary-chat-interface-foundations/spec.md",
        None,
    ),
    (
        "New multi-provider chat follow-up plan (Set 043)",
        REPO_ROOT / "docs/session-sets/043-multi-provider-chat-interface-followup/spec.md",
        None,
    ),
]


def _read_text(path: Path, max_lines: int | None) -> str:
    text = path.read_text(encoding="utf-8")
    if max_lines is None:
        return text
    return "\n".join(text.splitlines()[:max_lines])


def build_prompt() -> str:
    prompt_path = HERE / "prompt.md"
    prompt_text = prompt_path.read_text(encoding="utf-8").rstrip()
    parts = [prompt_text, "", "## Design packet", ""]

    for label, path, max_lines in FILES:
        rendered = _read_text(path, max_lines)
        excerpt_note = ""
        if max_lines is not None:
            excerpt_note = f" (first {max_lines} lines only)"
        parts.extend(
            [
                f"### {label}{excerpt_note}",
                f"Source: {path.relative_to(REPO_ROOT).as_posix()}",
                "```markdown",
                rendered,
                "```",
                "",
            ]
        )

    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    prompt_text = build_prompt()
    composed_prompt_path = HERE / "prompt.composed.md"
    result_json_path = HERE / "gemini-pro-result.json"
    result_md_path = HERE / "gemini-pro-response.md"

    composed_prompt_path.write_text(prompt_text, encoding="utf-8")
    print(f"Wrote composed prompt: {composed_prompt_path}")
    print(f"Prompt size: {len(prompt_text):,} chars")

    result = ai_router.query(
        model="gemini-pro",
        content=prompt_text,
        task_type="analysis",
        session_set=str(HERE),
        session_number=0,
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
            "truncated": getattr(result, "truncated", None),
            "verification": getattr(result, "verification", None),
        }

    result_json_path.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Wrote route result: {result_json_path}")

    content = result_dict.get("content") or ""
    result_md_path.write_text(str(content), encoding="utf-8")
    print(f"Wrote response body: {result_md_path}")

    print(
        f"model={result_dict.get('model_name')} "
        f"cost=${result_dict.get('total_cost_usd') or result_dict.get('cost_usd')} "
        f"input={result_dict.get('input_tokens')} output={result_dict.get('output_tokens')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
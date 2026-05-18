"""Route Set 029 Session 1 verification prompt to gpt-5-4.

Cross-provider verification of the audit synthesis (audit-summary.md
+ spec.md updates) by gpt-5-4. The synthesis being verified was
itself produced from a manual paste-and-collect against GPT-5.4 +
Gemini Pro, so this verification call closes the loop: we're asking
gpt-5-4 whether the Claude-side synthesis accurately captured what
gpt-5-4 (and Gemini) actually said.

Per the memory rule "ai_router.route() result handling -- dump
fields before any attribute access," the RouteResult is dumped to
JSON before any field is read.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# session-001 -> session-reviews -> 029-... -> session-sets -> docs -> repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice(path: Path, ranges: list[tuple[int, int]]) -> str:
    """Return a labelled excerpt of `path` consisting of the given
    1-indexed inclusive line ranges, with line numbers preserved."""
    lines = path.read_text(encoding="utf-8").splitlines()
    rel = path.relative_to(REPO_ROOT).as_posix()
    chunks = []
    total = 0
    for start, end in ranges:
        end = min(end, len(lines))
        section = "\n".join(
            f"{i+1:>5}  {lines[i]}" for i in range(start - 1, end)
        )
        chunks.append(f"--- {rel} lines {start}-{end} ---\n{section}")
        total += end - start + 1
    return (
        f"=== FILE: {rel} ({total} LOC across {len(ranges)} slice(s)) ===\n"
        + "\n\n".join(chunks)
    )


def main() -> int:
    prompt_text = _read(HERE / "prompt.md")

    proposals_dir = (
        REPO_ROOT
        / "docs"
        / "proposals"
        / "2026-05-17-model-effort-gauges-design-audit"
    )
    audit_summary = _read(proposals_dir / "audit-summary.md")
    gpt_result = _read(proposals_dir / "gpt-5-4-result.json")
    gemini_result = _read(proposals_dir / "gemini-pro-result.json")

    spec_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )
    # Slices that materially changed as a result of the audit:
    #   - decisions table D6/D7/D8 area
    #   - effort normalization table + thinking LED table
    #   - resolved Q1-Q6 stubs + showstoppers
    #   - Sessions 2 and 3 step rewrites
    #   - risks R5 and R6
    spec_excerpts = _slice(
        spec_path,
        [
            (96, 145),   # D1-D10 decisions + effort table header
            (146, 200),  # Q1-Q6 resolved + showstoppers + marker schema bump
            (255, 360),  # Session 2 rewritten steps
            (360, 440),  # Session 3 rewritten steps
            (490, 535),  # Risks R5/R6 + routing notes + total cost
        ],
    )

    full_content = (
        prompt_text
        + "\n\n---\n\n## Doc 1: audit-summary.md\n\n"
        + audit_summary
        + "\n\n---\n\n## Doc 2: gpt-5-4-result.json (raw audit input)\n\n```json\n"
        + gpt_result
        + "\n```\n\n---\n\n## Doc 3: gemini-pro-result.json (raw audit input)\n\n```json\n"
        + gemini_result
        + "\n```\n\n---\n\n## Doc 4: spec.md excerpts (audit-driven changes)\n\n"
        + spec_excerpts
    )

    rendered_path = HERE / "prompt.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"rendered prompt size: {len(full_content):,} chars")

    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(spec_path.parent),
        session_number=1,
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

    out_path = HERE / "verify-result.json"
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

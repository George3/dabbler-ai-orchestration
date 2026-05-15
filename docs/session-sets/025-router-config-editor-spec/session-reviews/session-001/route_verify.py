"""Route Set 025 Session 1 verification prompt to gpt-5-4.

Cross-provider verification of the three doc-only deliverables
(spec.md, schema-examples.md, wireframes.md) by a model from a
different provider than the orchestrator (Claude Opus 4.7 ->
gpt-5-4). Includes the audit-summary as Appendix A so the verifier
can spot-check that the locked decisions are captured faithfully.

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
# session-001 -> session-reviews -> 025-... -> session-sets -> docs -> repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


def main() -> int:
    prompt_path = HERE / "prompt.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    set_dir = REPO_ROOT / "docs" / "session-sets" / "025-router-config-editor-spec"
    spec_text = (set_dir / "spec.md").read_text(encoding="utf-8")
    schema_text = (set_dir / "schema-examples.md").read_text(encoding="utf-8")
    wireframes_text = (set_dir / "wireframes.md").read_text(encoding="utf-8")

    audit_summary = (
        REPO_ROOT
        / "docs"
        / "proposals"
        / "2026-05-15-router-config-editor-design-audit"
        / "audit-summary.md"
    ).read_text(encoding="utf-8")

    full_content = (
        prompt_text
        + "\n\n---\n\n## Doc 1: spec.md\n\n"
        + spec_text
        + "\n\n---\n\n## Doc 2: schema-examples.md\n\n"
        + schema_text
        + "\n\n---\n\n## Doc 3: wireframes.md\n\n"
        + wireframes_text
        + "\n\n---\n\n## Appendix A: audit-summary.md (decisions reference)\n\n"
        + audit_summary
    )

    rendered_path = HERE / "prompt.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"rendered prompt size: {len(full_content):,} chars")

    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(set_dir),
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
    print(f"input tokens: {result_dict.get('input_tokens')}")
    print(f"output tokens: {result_dict.get('output_tokens')}")
    print(f"dumped to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Route Set 029 Session 5 verification — Round A.

Scope: detection + Codex watcher + shim commands + small integration
diffs (OrchestratorAccordion empty-state, CustomSessionSetsView wiring,
client.js data-command-args). Round B covers setOrchestratorManual.ts
(533 LOC) as its own bundle.

Per memory `feedback_split_large_verification_bundles`: bundle sized
to stay under the 700 LOC ceiling. Pinned to gemini-pro per the
S3/S4 escape-hatch pattern.

Per memory `feedback_ai_router_route_result_handling`, the
RouteResult is dumped to JSON before any field is read.
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
    prompt_text = _read(HERE / "prompt-round-a.md")

    ext_root = REPO_ROOT / "tools" / "dabbler-ai-orchestration"
    files = [
        ("src/codex/configWatcher.ts", "typescript"),
        ("src/commands/installOrchestratorHookGemini.ts", "typescript"),
        ("src/commands/installOrchestratorHookCopilot.ts", "typescript"),
        ("src/providers/detectOrchestrators.ts", "typescript"),
        # Diff-style snippets for the touched-but-not-rewritten files.
        # Including the full files would blow the LOC budget; the diff
        # snippets carry the load-bearing changes.
    ]

    sections = [prompt_text]
    for i, (rel, lang) in enumerate(files, start=1):
        body = _read(ext_root / rel)
        sections.append(
            f"\n\n---\n\n## File {i}: {rel}\n\n```{lang}\n{body}\n```\n"
        )

    # Diff snippets for files where only small targeted changes landed.
    snippets = [
        (
            "src/providers/OrchestratorAccordion.ts — empty-state changes",
            "typescript",
            _read(ext_root / "src/providers/OrchestratorAccordion.ts"),
            # Keep the empty-state region only — find a marker
            "// Empty state for the accordion",
            "// Loaded state: marker present",
        ),
        (
            "src/providers/CustomSessionSetsView.ts — wiring changes",
            "typescript",
            _read(ext_root / "src/providers/CustomSessionSetsView.ts"),
            "// Allowlist for executeCommand dispatch from the webview",
            "interface RowResolutionInputs",
        ),
        (
            "media/session-sets-tree/client.js — data-command-args dispatch",
            "javascript",
            _read(ext_root / "media/session-sets-tree/client.js"),
            "// Buttons inside accordion / banner with data-command",
            "}\n\n  // Root-level keydown",
        ),
    ]
    for i, (label, lang, full, start, end) in enumerate(
        snippets, start=len(files) + 1
    ):
        si = full.find(start)
        if si < 0:
            body = full[:4000]
        else:
            ei = full.find(end, si)
            if ei < 0:
                body = full[si : si + 4000]
            else:
                body = full[si:ei]
        sections.append(
            f"\n\n---\n\n## Snippet {i}: {label}\n\n```{lang}\n{body}\n```\n"
        )

    full_content = "".join(sections)

    rendered_path = HERE / "prompt-round-a.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(
        f"Round A prompt size: {len(full_content):,} chars / "
        f"~{full_content.count(chr(10)):,} lines"
    )

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
        session_number=5,
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

    out_path = HERE / "verify-result-round-a.json"
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

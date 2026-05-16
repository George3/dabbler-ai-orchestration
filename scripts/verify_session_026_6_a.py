"""Session 6 verification — Part A: data layer.

Bundles the Python queue reader, the TS annotation parser, the
existing-section markup tweak, and the workflow-doc paragraph that
documents the new public surface. The "data layer" half of Session 6.

Part B (companion script) covers the TS commands (decisionReviewQueue,
annotationScanner, flagDecisionForReview, scanAnnotationsForActiveSet)
and the extension.ts wiring.

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access — per
the memory `feedback_ai_router_route_result_handling`.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_ai_router():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import ai_router
    return ai_router


PART_A_FILES = [
    "ai_router/decision_review_queue.py",
    "ai_router/tests/test_decision_review_queue_reader.py",
    "tools/dabbler-ai-orchestration/src/configEditor/annotationParser.ts",
    "tools/dabbler-ai-orchestration/src/test/suite/annotationParser.test.ts",
    "tools/dabbler-ai-orchestration/src/configEditor/sections/significanceFlaggingSection.ts",
    "tools/dabbler-ai-orchestration/src/test/suite/significanceFlaggingSection.test.ts",
]


def main() -> int:
    parts = []
    for rel in PART_A_FILES:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "".join(parts)

    # Also include the workflow-doc significance-flagging insert and
    # the __init__.py decision_review_queue export chunk — small but
    # part of the public-surface promise this slice has to defend.
    init_py = (REPO_ROOT / "ai_router/__init__.py").read_text(encoding="utf-8")
    # Pull just the decision_review_queue import block + a few neighbors
    init_excerpt_start = init_py.find("from .decision_review_queue")
    init_excerpt_end = init_py.find("from .utils", init_excerpt_start)
    if init_excerpt_start > 0 and init_excerpt_end > 0:
        init_excerpt = init_py[max(0, init_excerpt_start - 40):init_excerpt_end + 20]
        bundle += f"\n=== ai_router/__init__.py (excerpt) ===\n{init_excerpt}\n"

    workflow_doc = (REPO_ROOT / "docs/ai-led-session-workflow.md").read_text(
        encoding="utf-8"
    )
    sf_start = workflow_doc.find("### Significance flagging")
    sf_end = workflow_doc.find("### Session-Set Lifecycle and State File", sf_start)
    if sf_start > 0 and sf_end > 0:
        bundle += (
            f"\n=== docs/ai-led-session-workflow.md (Significance flagging section) ===\n"
            f"{workflow_doc[sf_start:sf_end]}\n"
        )

    context = (
        "Set 026 Session 6 of 7 — Significance flagging (Part A of 2: data layer).\n"
        "The single normative reference is `docs/session-sets/026-router-config-editor-implementation/spec.md`\n"
        "Session 6 section, and Set 025 Appendix B for the underlying schema decisions.\n\n"
        "This slice covers the pure data-layer pieces:\n"
        "  - `ai_router/decision_review_queue.py`: read/clear of\n"
        "    `<session-set>/decision-review-queue.jsonl`. The orchestrator\n"
        "    consumes the queue at session start; the two extension commands\n"
        "    (Part B) produce the entries.\n"
        "  - `annotationParser.ts`: regex match + dedup pure functions.\n"
        "    Supports `# @dabbler:outsource-review(\"...\")` (Python/YAML/shell)\n"
        "    and `// @dabbler:...` (JS/TS/Java/C#/C/C++/Go).\n"
        "  - `significanceFlaggingSection.ts`: minor comment-only update\n"
        "    reflecting that the commands now ship (the Session-5 graceful-\n"
        "    fallback narrative is no longer accurate).\n"
        "  - `__init__.py`: re-exports the queue surface as\n"
        "    `read_decision_review_queue` / `clear_decision_review_queue` /\n"
        "    `decision_review_queue_path` to match the existing convention\n"
        "    for session_events and disposition.\n"
        "  - `workflow doc significance-flagging section`: documents the\n"
        "    two surfaces, the queue file path, the JSON line shape, and\n"
        "    the `honor_annotations` toggle.\n\n"
        "Tests passing as of this commit: 18 annotationParser, 13\n"
        "test_decision_review_queue_reader, 6 significanceFlaggingSection,\n"
        "plus the rest of the unit suite — 107 pure-unit TS tests + 427\n"
        "Python tests total, no regressions.\n\n"
        "Verification asks:\n"
        "1. Annotation regex: does it correctly match both `#` and `//`\n"
        "   comment styles? Reject bare (non-comment) `@dabbler:outsource-\n"
        "   review` to avoid false positives in docstrings? Reject empty\n"
        "   reasons? Tolerate escaped quotes / backslashes / nested\n"
        "   parens inside the reason string? Look at the unit tests in\n"
        "   annotationParser.test.ts for the contract.\n"
        "2. Line-number computation: a binary search over precomputed\n"
        "   newline positions returns the correct 1-based line for each\n"
        "   match? CRLF endings handled?\n"
        "3. Path normalization: file paths in the output are POSIX-style\n"
        "   (forward slashes) regardless of the OS-native separator the\n"
        "   scanner passed in?\n"
        "4. Deduplication: key is exactly `file+line+reason`? `ts` and\n"
        "   `source` deliberately ignored so a re-scan doesn't re-emit\n"
        "   the same entry with a fresh timestamp?\n"
        "5. Python queue reader: handles missing file (return []), empty\n"
        "   file, blank lines, malformed JSON (skip+warn), non-object\n"
        "   JSON values (skip+warn)? `clear_queue` is idempotent\n"
        "   (multiple calls return 0 after the first)? Concurrent-clear\n"
        "   case (FileNotFoundError on unlink) does not raise?\n"
        "6. Schema is intentionally open — callers look up fields\n"
        "   defensively. Have we left any place that assumes a fixed\n"
        "   shape?\n"
        "7. `read_decision_review_queue` re-export from `__init__.py`\n"
        "   uses a `read_queue as read_decision_review_queue` alias so\n"
        "   the public name is distinguishable from `read_events`,\n"
        "   `read_disposition`, etc. Sensible choice?\n"
        "8. Workflow-doc significance-flagging section: accurate to the\n"
        "   actual code? Clear about WHY there are two surfaces? Cites\n"
        "   the queue path and the JSON line shape correctly?\n"
        "9. Any TS / Python correctness bugs the unit tests don't cover?\n"
        "10. Any portability concerns (Windows path separators, default\n"
        "    encodings, line-ending handling)?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise list\n"
        "each finding with severity (Blocker / Major / Minor) and\n"
        "file:line references."
    )
    content = (
        "Review the Session 6 Part A data-layer bundle below against\n"
        "the criteria above. Be specific about file paths and line\n"
        "numbers.\n\n"
        f"{bundle}"
    )

    ar = load_ai_router()
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="026-router-config-editor-implementation",
        session_number=6,
    )

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_6_a_result.json"
    try:
        as_dict = dataclasses.asdict(result)
    except TypeError:
        as_dict = {k: v for k, v in vars(result).items()}
    cleaned = {}
    for k, v in as_dict.items():
        try:
            json.dumps(v)
            cleaned[k] = v
        except TypeError:
            cleaned[k] = repr(v)
    dump_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"Dumped result to {dump_path.as_posix()}")

    data = json.loads(dump_path.read_text(encoding="utf-8"))
    print("=== VERIFIER RESPONSE ===")
    print(data.get("content", "<no content>"))
    print()
    print("=== COST ===")
    print(
        f"model={data.get('model_name')} "
        f"input_tokens={data.get('input_tokens')} "
        f"output_tokens={data.get('output_tokens')} "
        f"cost_usd={data.get('total_cost_usd')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

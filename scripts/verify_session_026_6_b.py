"""Session 6 verification — Part B: command + wiring layer.

Bundles the TS command files (decisionReviewQueue pure helpers,
annotationScanner pure helpers, flagDecisionForReview vscode-wiring,
scanAnnotationsForActiveSet vscode-wiring), the test files that exercise
those, plus the package.json / extension.ts / ConfigEditorPanel.ts
wiring diff. The "operator-facing layer" half of Session 6.

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access.
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


PART_B_FILES = [
    "tools/dabbler-ai-orchestration/src/commands/decisionReviewQueue.ts",
    "tools/dabbler-ai-orchestration/src/commands/flagDecisionForReview.ts",
    "tools/dabbler-ai-orchestration/src/commands/annotationScanner.ts",
    "tools/dabbler-ai-orchestration/src/commands/scanAnnotationsForActiveSet.ts",
    "tools/dabbler-ai-orchestration/src/test/suite/flagDecisionForReview.test.ts",
    "tools/dabbler-ai-orchestration/src/test/suite/scanAnnotationsForActiveSet.test.ts",
]


def main() -> int:
    parts = []
    for rel in PART_B_FILES:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "".join(parts)

    # Append the wiring excerpts (small) so the verifier can confirm the
    # commands are actually registered and the ConfigEditorPanel button
    # invocation is now unconditional.
    pkg = (REPO_ROOT / "tools/dabbler-ai-orchestration/package.json").read_text(
        encoding="utf-8"
    )
    flag_start = pkg.find("dabbler.flagDecisionForReview")
    if flag_start > 0:
        # widen to include both new command entries
        scan_end = pkg.find("]", pkg.find("dabbler.scanAnnotationsForActiveSet", flag_start))
        bundle += (
            f"\n=== tools/dabbler-ai-orchestration/package.json (new commands) ===\n"
            f"{pkg[max(0, flag_start - 200):scan_end + 4]}\n"
        )

    ext = (REPO_ROOT / "tools/dabbler-ai-orchestration/src/extension.ts").read_text(
        encoding="utf-8"
    )
    ext_imp = ext.find("registerFlagDecisionForReview")
    ext_reg_start = ext.find('safeRegister("registerFlagDecisionForReview"')
    ext_reg_end = ext.find(")", ext.find('safeRegister("registerScanAnnotationsForActiveSet"', ext_reg_start) + 100)
    if ext_imp > 0 and ext_reg_start > 0:
        bundle += (
            f"\n=== tools/dabbler-ai-orchestration/src/extension.ts (new imports + safeRegister calls) ===\n"
            f"// imports:\n{ext[ext_imp - 60:ext_imp + 250]}\n"
            f"// safeRegister:\n{ext[ext_reg_start:ext_reg_end + 3]}\n"
        )

    panel = (REPO_ROOT / "tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts").read_text(
        encoding="utf-8"
    )
    panel_start = panel.find("_runFlagDecisionCommand")
    if panel_start > 0:
        bundle += (
            f"\n=== tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts (_runFlagDecisionCommand) ===\n"
            f"{panel[panel_start - 4:panel_start + 500]}\n"
        )

    context = (
        "Set 026 Session 6 of 7 — Significance flagging (Part B of 2:\n"
        "operator-facing command + wiring layer).\n\n"
        "The single normative reference is `docs/session-sets/026-router-config-editor-implementation/spec.md`\n"
        "Session 6 section. Set 025 Appendix B covers the underlying schema.\n\n"
        "This slice covers the operator-facing layer:\n"
        "  - `decisionReviewQueue.ts`: pure helpers — `appendQueueEntry` and\n"
        "    `findActiveSessionSetDir`. Shared by both commands. No vscode\n"
        "    import so the helpers can be unit-tested via plain mocha.\n"
        "  - `flagDecisionForReview.ts`: vscode wiring for\n"
        "    `dabbler.flagDecisionForReview`. Input box -> append queue\n"
        "    line `{source: \"command\", file: null, line: null, ts, reason}`.\n"
        "    Cancel / empty-reason are silent no-ops; missing active set\n"
        "    surfaces an info notification.\n"
        "  - `annotationScanner.ts`: pure helpers —\n"
        "    `scanFilesForAnnotations`, `loadHonorAnnotationsToggle`,\n"
        "    `loadExistingQueueEntries`, plus the `SCAN_GLOB` / `SCAN_EXCLUDE_GLOB`\n"
        "    constants.\n"
        "  - `scanAnnotationsForActiveSet.ts`: vscode wiring for\n"
        "    `dabbler.scanAnnotationsForActiveSet`. workspace.findFiles ->\n"
        "    pure scan -> dedup against existing queue -> append fresh\n"
        "    entries. Honors `decision_review.honor_annotations` toggle\n"
        "    (default true; set false to make scanning a no-op).\n"
        "  - `package.json`: two new command registrations under\n"
        "    contributes.commands.\n"
        "  - `extension.ts`: safeRegister calls for both commands.\n"
        "  - `ConfigEditorPanel.ts._runFlagDecisionCommand`: now calls\n"
        "    executeCommand unconditionally (the Session-5 graceful-\n"
        "    fallback branch is gone — the command is registered\n"
        "    alongside the panel from now on).\n\n"
        "Tests passing: 9 flagDecisionForReview, 20 scanAnnotationsForActiveSet,\n"
        "53 total Session-6 TS, 107 pure-unit TS aggregate, no regressions.\n\n"
        "Verification asks:\n"
        "1. `appendQueueEntry`: single appendFileSync, writes one line\n"
        "   ending in \\n. Correct for partial-write tolerance (the Python\n"
        "   reader is the canonical reader and treats a partial trailing\n"
        "   line as a skip-with-warning)?\n"
        "2. `findActiveSessionSetDir`: filters on state === 'in-progress',\n"
        "   tie-breaks on lastTouched descending. Null lastTouched\n"
        "   doesn't crash the sort? Returns null when no in-progress set\n"
        "   exists?\n"
        "3. `flagDecisionForReview` registration: input box with proper\n"
        "   title/placeholder; cancel (undefined) and empty/whitespace\n"
        "   reason are silent no-ops; thrown error on append surfaces as\n"
        "   an error notification rather than propagating?\n"
        "4. `scanFilesForAnnotations`: aggregates per-file results,\n"
        "   skips files that throw on read, normalizes file paths to\n"
        "   POSIX relative-to-workspace-root?\n"
        "5. `loadHonorAnnotationsToggle`: defaults to true on missing\n"
        "   file, missing `decision_review` section, missing\n"
        "   `honor_annotations`, or non-boolean value? Only returns false\n"
        "   when the field is explicitly `false`?\n"
        "6. `loadExistingQueueEntries`: returns only annotation-shaped\n"
        "   entries (file+line+reason all present), skips command-shaped\n"
        "   entries (file: null) since they have nothing to dedup against?\n"
        "   Skips malformed lines without aborting?\n"
        "7. `scanAnnotationsForActiveSet` registration: correctly uses\n"
        "   `vscode.RelativePattern(workspaceRoot, SCAN_GLOB)` so the\n"
        "   search is scoped? `findFiles` exclude pattern is also\n"
        "   workspace-root-relative? The active set's `root` (from\n"
        "   `SessionSet`) is the right value to use for the workspace\n"
        "   root, not the session-set dir?\n"
        "8. `_runFlagDecisionCommand`: now calls executeCommand\n"
        "   unconditionally — is that the right call? (The command is\n"
        "   registered in activate(); if it's somehow not, executeCommand\n"
        "   surfaces an error notification, which is acceptable for a\n"
        "   shipping bug.)\n"
        "9. package.json command entries: titles match the convention\n"
        "   (\"Flag Decision for Cross-Provider Review\", \"Scan Workspace\n"
        "   for @dabbler:outsource-review Annotations\"); category =\n"
        "   \"Dabbler\". Anything missing (icons, when-clauses)?\n"
        "10. Any TS / runtime correctness bugs the unit tests don't\n"
        "    cover? Race conditions on the append path (two simultaneous\n"
        "    command invocations could interleave lines)?\n"
        "11. Any portability concerns (Windows path separators in\n"
        "    workspace walk)?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise list\n"
        "each finding with severity (Blocker / Major / Minor) and\n"
        "file:line references."
    )
    content = (
        "Review the Session 6 Part B operator-facing-layer bundle\n"
        "below against the criteria above. Be specific about file paths\n"
        "and line numbers.\n\n"
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

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_6_b_result.json"
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

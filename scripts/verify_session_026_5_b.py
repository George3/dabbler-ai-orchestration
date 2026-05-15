"""Session 5 verification — Part B: patch.ts + ConfigEditorPanel rewrite.

Companion to verify_session_026_5_a.py. Part B reviews how the
SavePayload flows through applyPatch into the yaml AST, how the
panel coordinates load/save/recovery, and the inline webview script.

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access
(feedback_ai_router_route_result_handling).
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


def main() -> int:
    config_editor_dir = (
        REPO_ROOT
        / "tools"
        / "dabbler-ai-orchestration"
        / "src"
        / "configEditor"
    )
    files = [
        config_editor_dir / "patch.ts",
        config_editor_dir / "ConfigEditorPanel.ts",
    ]
    bundle_parts = []
    for f in files:
        rel = f.relative_to(REPO_ROOT).as_posix()
        body = f.read_text(encoding="utf-8")
        bundle_parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "\n".join(bundle_parts)

    context = (
        "Set 026 Session 5 of 7 — Webview SECTIONS (Part B of 2). "
        "Part B reviews patch.ts (SavePayload -> yaml-AST mutation) "
        "and the ConfigEditorPanel rewrite that wires sections "
        "together. (Part A reviewed the six section render functions.) "
        "The single normative reference is Set 025 Appendix B in "
        "docs/session-sets/025-router-config-editor-spec/spec.md. "
        "Section 5 spec is in docs/session-sets/"
        "026-router-config-editor-implementation/spec.md under "
        "'Session 5 of 7: Webview sections'.\n\n"
        "Architecture: each section renders to an HTML string with "
        "predictable data-attributes. A single client-side <script> "
        "block (inside ConfigEditorPanel._getHtml) gathers all form "
        "values into a SavePayload on Save and posts it back. The "
        "host's _handleSave applies the payload through applyPatch, "
        "validates the resulting batch via validateBatch, and writes "
        "each Document via writeYamlFile (tmp+rename, atomic per-"
        "file). Per-file write failures are tracked for half-batch "
        "recovery. Content-hash drift detection (stringContentHash) "
        "compares last-saved snapshot to current disk content on "
        "next load.\n\n"
        "Verification asks (Part B scope):\n"
        "1. Does applyPatch route each Appendix-B field to its "
        "canonical YAML file? Confirm by walking the matrix: "
        "outsourcingMode (shared OR local), verificationMethod "
        "(budget.yaml shared-only), thresholdUsd (budget shared + "
        "optionally local; emits warning), scope (budget shared-"
        "only), warnAtPercent (budget shared + optionally local), "
        "providers (router-config + 3 local-overridable sub-fields; "
        "display_label shared-only), honorAnnotations (local-only), "
        "pushover (local-only).\n"
        "2. Does applyOverridableField correctly clean up the "
        "OTHER side when an overridable value is promoted/demoted?\n"
        "3. Does pruneEmptyProvidersBlock correctly clean an empty "
        "providers entry in local-overrides after key removal?\n"
        "4. Half-batch recovery: when 2 of 3 writes succeed and 1 "
        "fails, does the editor surface the recovery banner with "
        "actionable retry/accept-baseline buttons? Does retry only "
        "re-attempt the failed file?\n"
        "5. Content-hash drift detection on next load: does it "
        "correctly compare current on-disk content to the last "
        "save snapshot and surface a banner when external "
        "modification is detected?\n"
        "6. The inline webview <script>: is the JS valid? CSP-"
        "compatible (uses nonce, no inline eval, no external src)? "
        "The (shared)/(local) toggle handler — does it correctly "
        "skip default/not-overridable indicators?\n"
        "7. Save-payload gathering: does it correctly read each "
        "field's data-source attribute back through the indicator "
        "DOM lookup? Is there any selector-collision risk where "
        "parentElement.querySelector('.src-indicator') could pick "
        "the wrong indicator in a section with multiple fields per "
        "row (none of the sections do this in practice, but "
        "validating the assumption)?\n"
        "8. Validation timing: does load-time and save-time "
        "validation honor the Set 025 spec? Does save abort cleanly "
        "on validation failure without leaving partial state?\n"
        "9. Any TS/runtime bugs in the rewritten panel that "
        "weren't covered by the 104 unit tests?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise "
        "list each finding with severity (Blocker / Major / Minor) "
        "and file:line references."
    )
    content = (
        "Review patch.ts + ConfigEditorPanel.ts for Session 5 Part B "
        "against Set 025 Appendix B + the Session 5 spec criteria "
        "above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )

    ar = load_ai_router()
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="026-router-config-editor-implementation",
        session_number=5,
    )

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_5_b_result.json"
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

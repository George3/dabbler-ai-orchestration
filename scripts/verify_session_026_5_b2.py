"""Session 5 verification — Part B2: ConfigEditorPanel.ts only.

Splits Part B because the combined patch.ts + ConfigEditorPanel.ts
bundle exceeded the read timeout. B2 reviews the panel rewrite in
isolation, focusing on save coordination, half-batch recovery,
content-hash drift detection, and the inline webview <script> block.

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


def main() -> int:
    target = (
        REPO_ROOT / "tools" / "dabbler-ai-orchestration"
        / "src" / "configEditor" / "ConfigEditorPanel.ts"
    )
    rel = target.relative_to(REPO_ROOT).as_posix()
    body = target.read_text(encoding="utf-8")
    bundle = f"=== {rel} ===\n{body}\n"

    context = (
        "Set 026 Session 5 of 7 — Webview SECTIONS (Part B2 of 3, "
        "isolated review of ConfigEditorPanel.ts). The single "
        "normative reference is Set 025 Appendix B in "
        "docs/session-sets/025-router-config-editor-spec/spec.md.\n\n"
        "ConfigEditorPanel.ts is the singleton webview-panel host. "
        "It loads the three YAML files, derives a SectionState, "
        "renders six section panels via the section modules' "
        "render(state) functions, coordinates the inline webview "
        "<script> block (which collects form values and posts a "
        "SavePayload on Save), and handles save / half-batch-recovery "
        "/ drift-detection / open-local-overrides / run-flag-command "
        "messages. patch.ts owns the SavePayload -> yaml-AST mutation; "
        "this panel owns the file IO + recovery state machine.\n\n"
        "Verification asks:\n"
        "1. Save flow: _handleSave correctly aborts on parse errors / "
        "validation failures BEFORE writing any file? Per-file write "
        "failures correctly recorded into _recovery for the half-"
        "batch banner?\n"
        "2. Half-batch recovery: when 2 of 3 writes succeed and 1 "
        "fails, does _renderRecoveryBanner produce a banner with "
        "actionable Retry / Accept-as-baseline buttons? Does "
        "_retryFailedWrite only re-attempt the failed file?\n"
        "3. Drift detection: _detectDrift correctly compares current "
        "on-disk content hashes to _lastSaveSnapshot? Does it correctly "
        "handle the absent-local-overrides edge case (null hash both "
        "before and after = no drift)?\n"
        "4. Cross-load recovery: _acceptHalfBatchAsBaseline and "
        "_reapplyLastSave — do they leave the panel in a coherent "
        "state? (e.g., _reapplyLastSave writes the in-memory docs to "
        "disk, clearing recovery state.)\n"
        "5. local-overrides write decision: shouldWriteLocal correctly "
        "balances 'no content to write' vs 'file already exists' (we "
        "want to preserve an existing empty file but not create a new "
        "one for no reason)?\n"
        "6. Inline webview <script>: valid JS? CSP-compatible (uses "
        "nonce, no inline eval, no external script src, all DOM "
        "queries are static)?\n"
        "7. The (shared)/(local) indicator toggle: correctly skips "
        "default / not-overridable indicators? Updates the visual + "
        "data-source attribute atomically?\n"
        "8. Save-payload gathering: parentElement.querySelector("
        "'.src-indicator') reliably picks the right indicator? Are "
        "there cells with multiple indicators where this could "
        "collide? (Each provider row's td cells, the §1/§2/§4/§5 "
        "field-row divs.)\n"
        "9. _runFlagDecisionCommand correctly falls back to an info "
        "notification when dabbler.flagDecisionForReview isn't "
        "registered yet (Session 6 deliverable)?\n"
        "10. _openLocalOverridesFile correctly handles the file-"
        "missing case?\n"
        "11. HTML escaping: every state value reaching the rendered "
        "HTML goes through escapeHtml? The drift / parse / recovery "
        "banners?\n"
        "12. Any TS / runtime bugs in the rewritten panel that "
        "weren't covered by the 104 unit tests?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise "
        "list each finding with severity (Blocker / Major / Minor) "
        "and file:line references."
    )
    content = (
        "Review ConfigEditorPanel.ts for Session 5 Part B2 against "
        "Set 025 Appendix B + the Session 5 spec criteria above. Be "
        "specific about file paths and line numbers.\n\n"
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

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_5_b2_result.json"
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

"""One-shot cross-provider verification for Set 026 / Session 5.

Routes Session 5 deliverables (six webview sections + patch module +
ConfigEditorPanel rewrite) to a non-Anthropic verifier via
task_type='session-verification'.

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access,
per feedback_ai_router_route_result_handling — previous one-off
scripts crashed during attribute access and burned the routed
call's cost.
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
    sections_dir = config_editor_dir / "sections"
    test_dir = (
        REPO_ROOT
        / "tools"
        / "dabbler-ai-orchestration"
        / "src"
        / "test"
        / "suite"
    )
    files = [
        sections_dir / "types.ts",
        sections_dir / "helpers.ts",
        sections_dir / "routingAndVerificationSection.ts",
        sections_dir / "budgetSection.ts",
        sections_dir / "providersTableSection.ts",
        sections_dir / "significanceFlaggingSection.ts",
        sections_dir / "notificationsSection.ts",
        sections_dir / "localOverridesSummarySection.ts",
        config_editor_dir / "patch.ts",
        config_editor_dir / "ConfigEditorPanel.ts",
        test_dir / "patch.test.ts",
        test_dir / "configEditor-e2e.test.ts",
    ]
    bundle_parts = []
    for f in files:
        rel = f.relative_to(REPO_ROOT).as_posix()
        body = f.read_text(encoding="utf-8")
        bundle_parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "\n".join(bundle_parts)

    context = (
        "Set 026 Session 5 of 7 — Webview SECTIONS for the new "
        "router-config editor (Session 4 shipped the foundation: "
        "ConfigEditorPanel + yamlReadWrite + schemaValidator). "
        "Goal: build the six wireframed sections, wire them into "
        "the panel shell, implement half-batch recovery + "
        "(shared)/(local override) indicator system, and ship "
        "section + patch + e2e tests. The single normative "
        "reference is Set 025 Appendix B in "
        "docs/session-sets/025-router-config-editor-spec/spec.md, "
        "with the section layouts in "
        "docs/session-sets/025-router-config-editor-spec/wireframes.md. "
        "Session 5 spec is in "
        "docs/session-sets/026-router-config-editor-implementation/"
        "spec.md under 'Session 5 of 7: Webview sections'.\n\n"
        "Test count after Session 5: 38 -> 104 unit tests passing; "
        "tsc clean. New files: 6 sections + types.ts + helpers.ts + "
        "patch.ts. ConfigEditorPanel.ts was rewritten to splice "
        "sections into the shell, route a SavePayload through "
        "applyPatch, persist via tmp+rename, and surface a "
        "half-batch-recovery banner when writes succeed for some "
        "files and fail for others.\n\n"
        "Verification asks:\n"
        "1. Do the six sections match Set 025 wireframes.md "
        "section-by-section (controls, labels, layout)?\n"
        "2. Does applyPatch route each Appendix-B field to its "
        "canonical YAML file? In particular: routing.outsourcing_mode "
        "(shared OR local), verification_method (budget.yaml shared-"
        "only), threshold_usd (budget shared, optionally local), "
        "scope (budget shared-only), warn_at_percent (budget shared, "
        "optionally local), providers.* (router-config shared + "
        "enabled/api_key_env/base_url overridable to local; "
        "display_label shared-only), decision_review.honor_annotations "
        "(local-only), notifications.pushover.* (local-only).\n"
        "3. Does the (shared)/(local override) indicator system "
        "correctly compute the source from the loaded state, AND "
        "correctly persist the source change on Save?\n"
        "4. Does half-batch recovery cleanly surface failed writes "
        "without losing the successfully-written changes? Are the "
        "recovery actions (retry / accept-as-baseline / re-apply) "
        "wired correctly?\n"
        "5. Cost-messaging copy in §2 Budget — does it carry the "
        "explicit dollar ranges + multi-week scale + open-source "
        "caveat + dashboard pointer (feedback_user_facing_cost_messaging)?\n"
        "6. The webview's inline <script> block: is the JS valid? "
        "Is it CSP-compatible (uses nonce, no inline eval, no "
        "external script src)?\n"
        "7. Are there any provider-table edge cases that aren't "
        "handled (no providers, provider with all-empty fields, "
        "provider that exists only in local-overrides — schema "
        "rejects but render should gracefully degrade)?\n"
        "8. Does the section/patch test coverage hit the high-"
        "value invariants for each section, or are there obvious "
        "gaps (e.g., constraint enforcement, default-value paths, "
        "indicator source derivation)?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise "
        "list each finding with severity (Blocker / Major / Minor) "
        "and file:line references."
    )
    content = (
        "Review the Session 5 webview-sections deliverables against "
        "Set 025 Appendix B + wireframes + the spec criteria above. "
        "Be specific about file paths and line numbers.\n\n"
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

    # DUMP TO JSON FIRST — do not access result.* fields before this.
    dump_path = REPO_ROOT / "scripts" / "verify_session_026_5_result.json"
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

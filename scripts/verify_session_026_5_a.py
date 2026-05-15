"""Session 5 verification — Part A: section files + helpers (UI surface).

Splits Session 5's verification into two parts to stay under the
GPT-5-4 read-timeout (300s/attempt). Part A reviews the six section
render functions + types/helpers. Part B reviews patch.ts + the
ConfigEditorPanel rewrite.

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
    sections_dir = (
        REPO_ROOT
        / "tools"
        / "dabbler-ai-orchestration"
        / "src"
        / "configEditor"
        / "sections"
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
    ]
    bundle_parts = []
    for f in files:
        rel = f.relative_to(REPO_ROOT).as_posix()
        body = f.read_text(encoding="utf-8")
        bundle_parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "\n".join(bundle_parts)

    context = (
        "Set 026 Session 5 of 7 — Webview SECTIONS (Part A of 2). "
        "Part A reviews the six section render functions + shared "
        "types/helpers. (Part B reviews patch.ts + the "
        "ConfigEditorPanel rewrite that wires sections in.) The "
        "single normative reference is Set 025 Appendix B in "
        "docs/session-sets/025-router-config-editor-spec/spec.md "
        "with section layouts in the same folder's wireframes.md. "
        "Session 5 spec is in docs/session-sets/"
        "026-router-config-editor-implementation/spec.md under "
        "'Session 5 of 7: Webview sections'. 38->104 unit tests "
        "passing post-Session-5; tsc clean.\n\n"
        "Each section file exports render(state) -> { html: string }. "
        "Sections never touch the yaml AST directly; they emit HTML "
        "and the panel coordinator collects form values via the "
        "client-side <script> block and posts a SavePayload back to "
        "the host. The (shared)/(local override)/(default) indicator "
        "system is implemented via fieldSource() in helpers.ts and "
        "indicatorHtml() in helpers.ts.\n\n"
        "Verification asks (Part A scope):\n"
        "1. Do the six sections match Set 025 wireframes.md "
        "section-by-section (controls present, labels accurate, "
        "interaction model correct)?\n"
        "2. Does each section correctly compute the EFFECTIVE value "
        "of every overridable field (local > shared > default)?\n"
        "3. Does the (shared)/(local override)/(default) indicator "
        "system correctly suppress itself on not-overridable fields "
        "(verification_method, scope, display_label)?\n"
        "4. §2 Budget cost-messaging copy — does it carry the four "
        "required elements per feedback_user_facing_cost_messaging? "
        "(explicit dollar ranges, multi-week scale, open-source "
        "caveat, dashboard pointer)?\n"
        "5. §3 Providers — does the table tolerate edge cases "
        "(empty providers map, provider with all-empty fields, "
        "missing display_label)?\n"
        "6. §6 Local overrides — does the walk() function correctly "
        "produce one row per leaf path, including notifications and "
        "decision_review sub-trees? Does it handle the absent-file "
        "vs. empty-file vs. populated cases distinctly?\n"
        "7. Any HTML-injection vectors via unescaped state values "
        "in any section? (helpers.escapeHtml escapes & < > \" '.)\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise "
        "list each finding with severity (Blocker / Major / Minor) "
        "and file:line references."
    )
    content = (
        "Review the Session 5 webview-section deliverables (Part A) "
        "against Set 025 Appendix B + wireframes + the Session 5 "
        "spec criteria above. Be specific about file paths and line "
        "numbers.\n\n"
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

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_5_a_result.json"
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

"""Session 5 verification — Part B1: patch.ts only.

Splits Part B because the combined patch.ts + ConfigEditorPanel.ts
bundle exceeded the read timeout. B1 reviews patch.ts in isolation.

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
        / "src" / "configEditor" / "patch.ts"
    )
    rel = target.relative_to(REPO_ROOT).as_posix()
    body = target.read_text(encoding="utf-8")
    bundle = f"=== {rel} ===\n{body}\n"

    context = (
        "Set 026 Session 5 of 7 — Webview SECTIONS (Part B1 of 3, "
        "isolated review of patch.ts). The single normative reference "
        "is Set 025 Appendix B in docs/session-sets/"
        "025-router-config-editor-spec/spec.md.\n\n"
        "patch.ts is the host-side module that converts a SavePayload "
        "(structured form values from the webview) into yaml-AST "
        "mutations on the three loaded Documents (router-config, "
        "budget, local-overrides). applyPatch returns a "
        "PatchApplyResult tracking which Documents changed, plus any "
        "warnings the operator should see.\n\n"
        "Verification asks:\n"
        "1. Does applyPatch route each Appendix-B field to its "
        "canonical YAML file? Walk the matrix:\n"
        "   - outsourcingMode (shared OR local; applyOverridableField "
        "promotes/demotes by deleting from the other side)\n"
        "   - verificationMethod (budget.yaml shared-only)\n"
        "   - thresholdUsd (budget shared OR local-with-warning)\n"
        "   - scope (budget shared-only)\n"
        "   - warnAtPercent (budget shared OR local-with-warning)\n"
        "   - providers.<id>.enabled / api_key_env / base_url "
        "(router-config OR local)\n"
        "   - providers.<id>.display_label (router-config only)\n"
        "   - removed providers (delete from both files)\n"
        "   - honorAnnotations (local-only at decision_review.honor_annotations)\n"
        "   - pushoverEnabled / api_key_env / user_key_env (local-only "
        "at notifications.pushover.*)\n"
        "2. Does applyOverridableField correctly clean up the OTHER "
        "side when an overridable value is promoted to local or "
        "demoted to shared? Does it correctly toggle "
        "routerConfigChanged / localOverridesChanged on each branch?\n"
        "3. Does pruneEmptyProvidersBlock correctly handle: (a) a "
        "provider with only one key that just got removed; (b) the "
        "providers: block becoming empty after the last entry "
        "is pruned; (c) iterating in reverse to avoid index shifts?\n"
        "4. Are there bugs in pruneEmptyContainer's empty-check? "
        "(YAMLMap items array is the right structure to inspect?)\n"
        "5. Does emptyLocalOverridesDoc produce a parseable Document "
        "with the initial comment preserved?\n"
        "6. Any TypeScript / runtime concerns with `doc.setIn`, "
        "`doc.getIn`, `doc.hasIn`, `doc.deleteIn` calls — do they "
        "correctly accept the (string|number)[] path type used here?\n"
        "7. docContentHash / stringContentHash — correct for drift "
        "detection? Should they normalize line endings or trim "
        "trailing whitespace?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise "
        "list each finding with severity (Blocker / Major / Minor) "
        "and file:line references."
    )
    content = (
        "Review patch.ts for Session 5 Part B1 against Set 025 "
        "Appendix B + the Session 5 spec criteria above. Be specific "
        "about file paths and line numbers.\n\n"
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

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_5_b1_result.json"
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

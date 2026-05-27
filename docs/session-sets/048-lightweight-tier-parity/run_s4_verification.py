"""Set 048 Session 4 end-of-session cross-provider verification.

Bundles the Lightweight-tier migrator CLI (Commit A), the external-
verification command (B), the review-criteria template files (C),
the wizard tier-branch (D), and the doc revisions (E). Mirrors the
post-Set-045 working verifier pattern: route=sonnet tier=2,
verify=gemini-pro tier=verifier.

Output files alongside this script:
  s4-verification-prompt.md, s4-verification-route.md,
  s4-verification-verify.md, s4-verification-result.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ai_router"))

import ai_router  # noqa: E402

SESSION_SET = "048-lightweight-tier-parity"
SESSION_NUMBER = 4


def _read(p: str) -> str:
    return (REPO_ROOT / p).read_text(encoding="utf-8")


def _build_prompt() -> str:
    migrator_py = _read("ai_router/migrate_lightweight_to_canonical_v4.py")
    external_verification_ts = _read(
        "tools/dabbler-ai-orchestration/src/commands/externalVerification.ts"
    )
    review_criteria_spec = _read("docs/review-criteria/spec.md")
    review_criteria_session = _read("docs/review-criteria/session.md")

    wizard_summary = (
        "## Wizard tier-branch (Commit D)\n\n"
        "`tools/dabbler-ai-orchestration/webview/wizard.html` gained:\n\n"
        "1. A new `<h2>Choose adoption tier</h2>` section above\n"
        "   `<h2>Prerequisites</h2>` containing two radio buttons\n"
        "   `name=\"tier\" value=\"full\"|\"lightweight\"`, with `value=\"full\"`\n"
        "   checked by default. The labels describe each tier's\n"
        "   prerequisites + spend implications in 1-2 sentences.\n"
        "2. Existing prerequisites + the cost-reality callout gained\n"
        "   `data-tier=\"full\"` attributes. A new Lightweight\n"
        "   prerequisite (path-aware review agent) and a new no-API-\n"
        "   spend callout gained `data-tier=\"lightweight\"`.\n"
        "3. The `Configure AI Router` and `Show cost dashboard` buttons\n"
        "   gained `data-tier=\"full\"`. `Troubleshoot` was left untagged\n"
        "   (applies to both tiers).\n"
        "4. JS handler `applyTierVisibility(tier)` toggles `.hidden`\n"
        "   class on every `[data-tier]` element based on the active\n"
        "   radio. Runs once on script-load + on every radio change.\n"
        "5. CSS: `.hidden { display: none !important; }` plus tier-\n"
        "   toggle styling (border + accent-color on the active radio).\n"
        "6. The existing `pricingLink` click handler is now guarded by\n"
        "   `if (pricing)` because the link lives inside the cost-\n"
        "   reality callout which can be hidden.\n"
    )

    docs_summary = (
        "## Doc revisions (Commit E)\n\n"
        "Five doc changes shipped:\n\n"
        "1. `docs/session-state-schema.md` § Tier expectations: the\n"
        "   Lightweight bullet was rewritten from \"router writers don't\n"
        "   operate, hand-edit only\" to the actual Set 048 model — \n"
        "   router writers DO operate under `--no-router` mode; lazy LLM-\n"
        "   SDK imports keep credentials out of the Lightweight path;\n"
        "   verification short-circuits to manual attestation; the\n"
        "   external-verification.md soft gate fires when missing;\n"
        "   hand-maintained Lightweight files are still supported and\n"
        "   the new `migrate_lightweight_to_canonical_v4` CLI handles\n"
        "   non-canonical drift.\n"
        "2. `docs/ai-led-session-workflow.md` Step 6 gained a\n"
        "   `#### Lightweight tier — copyable review prompts replace\n"
        "   routed verification` subsection: 5-step flow covering when\n"
        "   the orchestrator triggers the copy-prompt commands, the\n"
        "   path-aware-agent requirement, the external-verification.md\n"
        "   paste-back convention, the close_session soft gate, and the\n"
        "   review-criteria file convention.\n"
        "3. `docs/planning/session-set-authoring-guide.md`:\n"
        "   - Session Set Configuration block example gains `tier: full`\n"
        "     and updates the requiresUAT/E2E comments to show the\n"
        "     `true | false | \"suggested\"` tri-state.\n"
        "   - Field semantics bullets added for `tier: \"full\"`,\n"
        "     `tier: \"lightweight\"`, `requiresUAT: \"suggested\"`,\n"
        "     `requiresE2E: \"suggested\"` — the suggested values\n"
        "     explicitly document the upfront-positive-confirmation\n"
        "     prompt mechanism that replaces the audit's originally-\n"
        "     proposed triple-redundancy reminder.\n"
        "   - Defaults section updated: `tier: full` joins the implicit\n"
        "     defaults when the configuration block is omitted.\n"
        "4. `docs/adoption-bootstrap.md` closing pointers for Lightweight\n"
        "   tier rewritten to describe Set 048's actual deliverables:\n"
        "   copyable prompts via the four `dabbler.copy*Prompt` commands;\n"
        "   external-verification.md paste-back via the new command;\n"
        "   optional `docs/review-criteria/*.md` files; hand-maintained\n"
        "   state files via the new Lightweight migrator; upgrade-to-Full\n"
        "   path stays.\n"
        "5. `docs/cross-repo-lightweight-notice.md` is a NEW file\n"
        "   following the established `cross-repo-checkout-notice.md` /\n"
        "   `cross-repo-harvest-notice.md` pattern. It's a one-time copy\n"
        "   source for consumer-repo CLAUDE.md authors. Documents the\n"
        "   --no-router activation knobs, the copyable-prompt + paste-\n"
        "   back flow, the agent-capability requirement, the optional\n"
        "   review-criteria files, the per-consumer migrator one-time\n"
        "   recipe, and the Get Started panel tier-branch.\n"
    )

    package_json_delta = (
        "## package.json delta\n\n"
        "`tools/dabbler-ai-orchestration/package.json` gains one new\n"
        "command entry under `contributes.commands`:\n\n"
        "```json\n"
        "{\n"
        "  \"command\": \"dabbler.openExternalVerificationDoc\",\n"
        "  \"title\": \"Open External Verification Document\",\n"
        "  \"category\": \"Dabbler\"\n"
        "}\n"
        "```\n\n"
        "No other contribute-section changes. The command is Command-\n"
        "Palette-only (not added to the right-click QuickPick).\n"
    )

    extension_ts_delta = (
        "## extension.ts delta\n\n"
        "One new import + one new `safeRegister` invocation:\n\n"
        "```typescript\n"
        "import { registerExternalVerificationCommand } from \"./commands/externalVerification\";\n"
        "// ...later in activate():\n"
        "  safeRegister(\"registerExternalVerificationCommand\", () =>\n"
        "    registerExternalVerificationCommand(context),\n"
        "  );\n"
        "```\n\n"
        "The new import shifted the watcher pattern's\n"
        "`createFileSystemWatcher(pattern)` line from 149 to 150;\n"
        "the watcher-inventory pinned line was bumped accordingly.\n"
    )

    test_summary = (
        "## Test counts at close\n\n"
        "- Python: 1009 passed + 1 pre-existing skip (no Python\n"
        "  failures introduced; 16 new tests for the Lightweight\n"
        "  migrator under `ai_router/tests/test_migrate_lightweight_to_canonical_v4.py`).\n"
        "- TypeScript (unit): 665 passed + 2 pre-existing failures\n"
        "  unchanged from S2/S3 (configEditor-foundation +\n"
        "  notificationsSection). No new TS tests in S4 — the\n"
        "  external-verification command is a thin wrapper over\n"
        "  `vscode.commands.executeCommand`, `vscode.window.showQuickPick`,\n"
        "  and `fs.writeFileSync` with no testable pure-function seam.\n"
    )

    return (
        "# Set 048 Session 4 cross-provider verification request\n\n"
        "## Context\n\n"
        "Set 048 Session 4 ships the four \"closing\" deliverables of the\n"
        "Lightweight-tier parity arc: per-consumer migrator CLI, the\n"
        "external-verification command, three review-criteria template\n"
        "files, the Get Started wizard tier-branch, and the four doc\n"
        "revisions plus the cross-repo notice. The audit-locked spec is\n"
        "at `docs/session-sets/048-lightweight-tier-parity/spec.md`\n"
        "§3.7 (migrator), §3.8 (external-verification command), §3.9\n"
        "(review-criteria storage), and §4 row for Session 4 (doc\n"
        "revisions + wizard tier-branch).\n\n"
        "Operator-locked premises in scope:\n"
        "- **P1.** Lightweight orchestrators MUST follow the SAME process\n"
        "  as Full for model/effort/session-set/session identification\n"
        "  and state-file updates.\n"
        "- **P3.** Lightweight differs from Full ONLY in: no router\n"
        "  runtime calls; no auto-verification; copyable review prompts;\n"
        "  suggested-not-required UAT/E2E.\n"
        "- **P4.** Lightweight users must not be required to hand-edit\n"
        "  state files (migrator addresses this).\n"
        "- **L1.** Copyable prompts MUST reference file paths, NOT embed\n"
        "  contents. The §3.9 review-criteria carve-out is the documented\n"
        "  exception (operator-authored meta-instructions).\n\n"
        "## What I'm asking you to verify\n\n"
        "1. **Correctness** — Does the migrator's `_normalize_to_v3_intermediate`\n"
        "   handle the four documented divergences (sessionLog[] alias, missing\n"
        "   schemaVersion, top-level status alias, per-session status alias)\n"
        "   in the right order, without mutating the input dict?\n"
        "2. **Refusal correctness** — Does the migrator correctly refuse\n"
        "   pre-v3 and future-schema inputs, and gracefully handle missing /\n"
        "   malformed state files without raising?\n"
        "3. **Backup atomicity** — `.lwbak.json` is written BEFORE the\n"
        "   new state file (mirroring `.v3.bak.json` in `migrate_v3_to_v4`).\n"
        "   On state-file-write failure with backup landed, the result\n"
        "   includes `backup_path` so the operator knows where to recover.\n"
        "4. **External-verification UX** — When the file is missing, the\n"
        "   command creates an empty file (no templated header per §3.8)\n"
        "   and opens it. EEXIST races fall through gracefully.\n"
        "5. **Review-criteria templates** — Each file's comment header\n"
        "   tells the operator how to edit and what happens if they\n"
        "   delete the file. Sample bullets are repo-relevant.\n"
        "6. **Wizard tier-branch** — The radio-group + data-tier toggle\n"
        "   logic correctly hides full-only content under Lightweight and\n"
        "   vice versa. Default is Full to preserve existing behavior.\n"
        "7. **Doc consistency** — The five doc revisions and the new\n"
        "   cross-repo notice describe the SAME mental model (P1 + P3\n"
        "   + L1 + tri-state + migrator + agent-capability requirement)\n"
        "   without contradicting each other. Pay particular attention\n"
        "   to whether the workflow doc Step 6 Lightweight subsection\n"
        "   and the schema doc Tier-expectations bullet agree on the\n"
        "   `--no-router` short-circuit semantics.\n"
        "8. **Spec compliance** — Are the four §3.x specs (§3.7 migrator,\n"
        "   §3.8 external-verification command, §3.9 review-criteria,\n"
        "   §4 wizard) implemented as specified? Flag any silent gaps\n"
        "   or scope drift.\n\n"
        "Please return findings as a JSON object matching\n"
        "`ai_router/prompt-templates/verification.md` schema.\n\n"
        "---\n\n"
        "## File: ai_router/migrate_lightweight_to_canonical_v4.py\n\n"
        "```python\n"
        + migrator_py
        + "\n```\n\n"
        "---\n\n"
        "## File: tools/dabbler-ai-orchestration/src/commands/externalVerification.ts\n\n"
        "```typescript\n"
        + external_verification_ts
        + "\n```\n\n"
        "---\n\n"
        "## File: docs/review-criteria/spec.md\n\n"
        "```markdown\n"
        + review_criteria_spec
        + "\n```\n\n"
        "---\n\n"
        "## File: docs/review-criteria/session.md\n\n"
        "```markdown\n"
        + review_criteria_session
        + "\n```\n\n"
        "## File: docs/review-criteria/set.md\n\n"
        "(Similar shape to session.md — review-criteria header + 6-bullet\n"
        "checklist focused on whole-set-level review concerns: scope-vs-delivery,\n"
        "memory carry-forward, version-bump correctness, set-level Round-A\n"
        "discipline, cross-repo notice, cumulative budget. Reviewable at\n"
        "docs/review-criteria/set.md in the worktree.)\n\n"
        "---\n\n"
        + wizard_summary
        + "\n---\n\n"
        + package_json_delta
        + "\n---\n\n"
        + extension_ts_delta
        + "\n---\n\n"
        + docs_summary
        + "\n---\n\n"
        + test_summary
    )


def main() -> int:
    prompt = _build_prompt()
    (HERE / "s4-verification-prompt.md").write_text(prompt, encoding="utf-8")
    print(f"Prompt size: {len(prompt):,} chars / {len(prompt.splitlines()):,} lines")

    print("Routing verification via ai_router.route()...")
    route_result = ai_router.route(
        content=prompt,
        task_type="session-verification",
        complexity_hint=70,
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    print(f"Route phase: model={route_result.model_name} tier={route_result.tier} cost=${route_result.cost_usd:.4f}")
    (HERE / "s4-verification-route.md").write_text(route_result.content, encoding="utf-8")

    print("Routing verify-of-verify via ai_router.verify()...")
    try:
        verify_result = ai_router.verify(
            route_result=route_result,
            original_task=prompt,
            task_type="session-verification",
            session_set=SESSION_SET,
            session_number=SESSION_NUMBER,
        )
    except RuntimeError as exc:
        # No cross-provider verifier configured for the routed model
        # (e.g., gpt-5-4 -> no remaining provider with cross-provider
        # discipline). Surface as a single-pass Round A — the route()
        # call itself already routed `task_type="session-verification"`
        # across providers, so the route response IS the Round-A
        # verdict. Record an empty verify-of-verify and proceed.
        print(f"Verify step skipped: {exc}")
        verify_result = None
    if verify_result is not None:
        verify_cost = getattr(verify_result, "verifier_cost_usd", 0.0) or 0.0
        verify_model = getattr(verify_result, "verifier_model", "unknown")
        print(
            f"Verify phase: model={verify_model} cost=${verify_cost:.4f}"
        )
        verify_text = getattr(verify_result, "verifier_response", "") or json.dumps(
            getattr(verify_result, "__dict__", {}), indent=2, default=str
        )
    else:
        verify_cost = 0.0
        verify_model = "skipped"
        verify_text = "Verify-of-verify skipped — no cross-provider verifier available for the route model."
    (HERE / "s4-verification-verify.md").write_text(verify_text, encoding="utf-8")

    total_cost = route_result.cost_usd + verify_cost
    print(f"\nTotal S4 verification cost: ${total_cost:.4f}")
    result = {
        "session_set": SESSION_SET,
        "session_number": SESSION_NUMBER,
        "route": {
            "model": route_result.model_name,
            "tier": route_result.tier,
            "cost_usd": route_result.cost_usd,
            "tokens_in": getattr(route_result, "input_tokens", None),
            "tokens_out": getattr(route_result, "output_tokens", None),
        },
        "verify": {
            "model": verify_model,
            "tier": "verifier",
            "cost_usd": verify_cost,
            "verdict": getattr(verify_result, "verdict", None) if verify_result is not None else None,
        },
        "total_cost_usd": total_cost,
    }
    (HERE / "s4-verification-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

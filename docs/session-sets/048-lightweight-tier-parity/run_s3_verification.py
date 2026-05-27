"""Set 048 Session 3 end-of-session cross-provider verification.

Bundles the TypeScript code shipped in S3 (the copy-prompt commands,
the ActionRegistry reshape, the rowMenuHelpers extraction, and the
CustomSessionSetsView two-step QuickPick rewrite) for review by a
cross-provider verifier. Per feedback_split_large_verification_bundles
the bundle is held to <700 LOC of source code (excluding tests, which
are reviewed via passing-status only).

Output files alongside this script: s3-verification-prompt.md,
s3-verification-route.md, s3-verification-verify.md, s3-verification-result.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
# Mirror the conftest convention: `ai_router/__init__.py` does
# `from runtime_mode import is_no_router_mode` (bare filename) which
# only resolves when ai_router/ is on sys.path.
sys.path.insert(0, str(REPO_ROOT / "ai_router"))

import ai_router  # noqa: E402

SESSION_SET = "048-lightweight-tier-parity"
SESSION_NUMBER = 3


def _read(p: str) -> str:
    return (REPO_ROOT / p).read_text(encoding="utf-8")


def _build_prompt() -> str:
    copy_prompt_ts = _read("tools/dabbler-ai-orchestration/src/commands/copyPromptCommands.ts")
    action_registry_ts = _read("tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts")
    row_menu_helpers_ts = _read("tools/dabbler-ai-orchestration/src/providers/rowMenuHelpers.ts")

    view_changes = (
        "Three structural changes to "
        "`tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`:\n\n"
        "1. COMMAND_ALLOWLIST collapsed from 14 entries to 1 entry.\n"
        "   Old: 14 row-context commands the cursor-anchored popup could\n"
        "        dispatch via the webview->host `executeRowCommand` message.\n"
        "   New: just `dabblerSessionSets.openSpec` for the L5 left-click\n"
        "        activation path. The right-click menu now invokes commands\n"
        "        directly via `vscode.commands.executeCommand` from the host\n"
        "        (no webview round-trip needed for QuickPick selections).\n\n"
        "2. `showContextMenu` rewritten as a two-step QuickPick flow:\n"
        "       const categorized = categorizedActions(set, supports);\n"
        "       const topLevelChoice = await pickTopLevel(...);\n"
        "       if (!topLevelChoice) return;\n"
        "       if (topLevelChoice.kind === 'action') {\n"
        "         this.executeRowAction(topLevelChoice.action, set);\n"
        "         return;\n"
        "       }\n"
        "       const submenu = topLevelChoice.kind === 'openFile'\n"
        "         ? categorized.openFile : categorized.copyEval;\n"
        "       const submenuChoice = await pickSubmenu(submenu, ...);\n"
        "       if (!submenuChoice) return;\n"
        "       this.executeRowAction(submenuChoice, set);\n\n"
        "   The pure decision logic for building QuickPick items + planning\n"
        "   left-click activation lives in rowMenuHelpers.ts (below).\n\n"
        "3. `handleActivateRow` implements L5 dual-action:\n"
        "       private async handleActivateRow(slug: string): Promise<void> {\n"
        "         const set = this.findSetBySlug(slug);\n"
        "         if (!set) return;\n"
        "         const plan = planLeftClickActivation(set.name, set.state);\n"
        "         this.dispatchCommand(plan.openCommand.commandId, [{ set }]);\n"
        "         if (!plan.clipboardWrite) return;\n"
        "         try {\n"
        "           await vscode.env.clipboard.writeText(plan.clipboardWrite.text);\n"
        "           vscode.window.showInformationMessage(plan.clipboardWrite.toast);\n"
        "         } catch (err) {\n"
        "           console.warn(`[CustomSessionSetsView] left-click clipboard write failed for \"${slug}\"`, err);\n"
        "         }\n"
        "       }\n"
    )

    other_changes = (
        "Other Set 048 S3 edits, by file:\n\n"
        "- `src/commands/openFile.ts` — removed the `openAiAssignment` "
        "command registration per L3.\n"
        "- `src/extension.ts` — added `registerCopyPromptCommands` to the "
        "`safeRegister` chain.\n"
        "- `package.json` — removed the `openAiAssignment` command "
        "declaration; added 4 new copy-prompt declarations "
        "(`dabbler.copySpecReviewPrompt`, "
        "`dabbler.copySessionAccomplishmentsPrompt`, "
        "`dabbler.copySetAccomplishmentsPrompt`, "
        "`dabbler.copyStartNextSessionPrompt`).\n"
        "- `src/types/sessionSetsWebviewProtocol.ts` — removed "
        "`RenderContextMenuMsg`, `ContextMenuItem`, and "
        "`ExecuteRowCommandMsg` (the cursor-anchored popup protocol).\n"
        "- `media/session-sets-tree/client.js` — deleted ~100 lines: "
        "the `showCursorContextMenu` / `ensureContextMenuEl` / "
        "`hideContextMenu` / `bandForCommandId` functions; the click + "
        "keydown + resize + scroll listeners that managed the popup; "
        "the `lastContextMenuPos` state and `contextMenuEl` reference; "
        "the `renderContextMenu` host-to-webview case. The contextmenu "
        "event listener on `treeitem` rows survives — it now just posts "
        "`showRowContextMenu` to the host, which opens the native "
        "QuickPick.\n"
        "- `media/session-sets-tree/tree.css` — removed `.context-menu`, "
        "`.context-menu.is-open`, `.context-menu-item`, "
        "`.context-menu-item:hover`, `.context-menu-item.is-active`, "
        "`.context-menu-separator` rules.\n"
        "- `src/test/suite/actionRegistry.test.ts` — rewrote to assert "
        "the 14-entry registry (was 15), the L2-locked 4-item Open File "
        "submenu, the four copyEval entries with their gating "
        "predicates, and the openAiAssignment absence invariant.\n"
        "- `src/test/suite/copyPromptCommands.test.ts` — NEW, "
        "12 prompt-builder tests covering path-reference format, "
        "review-criteria embedding, change-log conditional inclusion, "
        "and L1 (no embedded content).\n"
        "- `src/test/suite/rowMenuHelpers.test.ts` — NEW, "
        "13 tests covering buildTopLevelItems / buildSubmenuItems / "
        "planLeftClickActivation pure functions.\n"
        "- `src/test/playwright/context-menu-quickpick.spec.ts` — NEW, "
        "2 Layer-3 scenarios pinning the negative invariant (no "
        "`.context-menu*` DOM) and L3 absence (no `openAiAssignment` "
        "data-command attribute).\n"
        "- `src/test/suite/watcherInventory.test.ts` — bumped one "
        "pinned line number from 148 to 149 (the new import added an "
        "earlier line to extension.ts).\n"
    )

    return (
        "# Set 048 Session 3 cross-provider verification request\n\n"
        "## Context\n\n"
        "Set 048 Session 3 ships the Lightweight-tier copyable-prompt "
        "commands and the context-menu IA refresh, combined into one "
        "session per the operator's audit Bias 7 disposition. The audit-"
        "locked spec is at `docs/session-sets/048-lightweight-tier-"
        "parity/spec.md` §3.2 (copyable-review-prompt commands), §3.3 "
        "(context-menu IA refresh — Bias 3 FLIP locks QuickPick), and "
        "§3.9 (review-criteria storage convention).\n\n"
        "Operator-locked additions in scope:\n"
        "- **L1.** Prompts MUST reference paths, never embed contents.\n"
        "- **L2.** Open File submenu locked to exactly 4 entries: "
        "Spec / Activity Log / Change Log / Session State.\n"
        "- **L3.** `Open AI Assignment` is fully removed from the menu, "
        "command registration, and dispatch allowlist.\n"
        "- **L4.** Close-on-blur / Escape / explicit dismiss — free "
        "byproduct of `vscode.window.showQuickPick`.\n"
        "- **L5.** Left-click ALWAYS opens spec.md; non-terminal rows "
        "ALSO copy `Start the next session of `<slug>`.` + info toast.\n\n"
        "Test counts at close:\n"
        "- TypeScript: 662 passed + 2 pre-existing failures unrelated to S3\n"
        "  (configEditor-foundation + notificationsSection — both predate Set 048).\n"
        "- Python: 994 collected (no Python changes in S3).\n\n"
        "## What I'm asking you to verify\n\n"
        "1. **Correctness** — Does the code do what the spec says? In "
        "particular: are the four copy-prompt builders correct under the "
        "L1 path-reference format? Does the two-step QuickPick correctly "
        "model the spec §3.3 menu structure?\n"
        "2. **L1 compliance** — Could any of the prompt builders "
        "accidentally embed file content (read-and-splice) instead of "
        "referencing paths?\n"
        "3. **L3 completeness** — Are there any lingering references to "
        "`openAiAssignment` (command id, menu entry, allowlist) that "
        "would resurrect the surface?\n"
        "4. **L5 invariants** — Does `planLeftClickActivation` ALWAYS "
        "open spec.md (preserved S4 default)? Does it correctly skip the "
        "clipboard write on `complete` and `cancelled` rows?\n"
        "5. **Edge cases** — Race conditions, missing-set lookups, "
        "QuickPick cancellation paths (Escape on top-level or submenu), "
        "non-existent review-criteria files, empty changelog files, "
        "slug values containing characters that would break the "
        "back-tick-quoted clipboard payload.\n"
        "6. **Backwards compatibility** — D5 firm CLI backcompat is "
        "not at risk (no Python changes), but: are there any retired "
        "VS Code command ids that consumers might be calling via the "
        "command palette? The pre-existing `copyStartCommand.default` "
        "and `copyStartCommand.parallel` remain registered (palette-"
        "accessible) so this should be a no-op.\n"
        "7. **Scope discipline** — Anything obvious that S3 should "
        "have shipped per the spec but didn't?\n\n"
        "## Code under review\n\n"
        "### tools/dabbler-ai-orchestration/src/commands/copyPromptCommands.ts (new)\n\n"
        "```typescript\n"
        f"{copy_prompt_ts}\n"
        "```\n\n"
        "### tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts (reshape)\n\n"
        "```typescript\n"
        f"{action_registry_ts}\n"
        "```\n\n"
        "### tools/dabbler-ai-orchestration/src/providers/rowMenuHelpers.ts (new)\n\n"
        "```typescript\n"
        f"{row_menu_helpers_ts}\n"
        "```\n\n"
        "### tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts (changes summary)\n\n"
        f"{view_changes}\n\n"
        "### Other file edits (summary)\n\n"
        f"{other_changes}\n\n"
        "## Verdict format\n\n"
        "Return a verdict (VERIFIED / ISSUES_FOUND) at the top of your "
        "response, then itemize concerns by Category (Correctness / "
        "Safety / Completeness / Backcompat / Edge-case / Other), "
        "Severity (Critical / Important / Nice-to-have), Location "
        "(file:line or section reference), Details, and Fix suggestion. "
        "If VERIFIED with no items, say so explicitly.\n"
    )


def _write_response(out_path: Path, label: str, result, verifier=False) -> None:
    text = (
        getattr(result, "raw_response", None)
        or getattr(result, "content", None)
        or ""
    )
    header = [
        f"# {label}",
        "",
        f"- **Provider:** {getattr(result, 'verifier_provider', getattr(result, 'model_id', 'unknown'))}",
        f"- **Model:** {getattr(result, 'verifier_model', getattr(result, 'model_name', 'unknown'))}",
        f"- **Cost:** {getattr(result, 'verifier_cost_usd', getattr(result, 'total_cost_usd', None))}",
    ]
    if verifier:
        header.append(f"- **Verdict:** {getattr(result, 'verdict', 'unknown')}")
    header.extend(["", "---", "", str(text)])
    out_path.write_text("\n".join(header), encoding="utf-8")
    print(f"  -> wrote {out_path.name} ({len(str(text))} chars)")


def main() -> int:
    prompt = _build_prompt()
    (HERE / "s3-verification-prompt.md").write_text(prompt, encoding="utf-8")
    print(f"Prompt: {len(prompt)} chars, {len(prompt.splitlines())} lines")

    print("\n========== ROUTE ==========")
    route_result = ai_router.route(
        content=prompt,
        task_type="code-review",
        context=(
            "Cross-provider verification of Set 048 Session 3's copy-"
            "prompt commands + context-menu IA refresh. The change is "
            "TypeScript-only; no Python touched. Spec §3.2 + §3.3 + §3.9 "
            "are the load-bearing references; L1-L5 operator locks "
            "constrain the implementation."
        ),
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _write_response(HERE / "s3-verification-route.md", "Route response", route_result)

    print("\n========== VERIFY ==========")
    verify_result = ai_router.verify(
        route_result=route_result,
        original_task=prompt,
        task_type="code-review",
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _write_response(
        HERE / "s3-verification-verify.md",
        "Cross-provider verifier response",
        verify_result,
        verifier=True,
    )

    summary = {
        "session_set": SESSION_SET,
        "session_number": SESSION_NUMBER,
        "route_model": getattr(route_result, "model_name", "unknown"),
        "route_cost": getattr(route_result, "total_cost_usd", None),
        "verify_model": getattr(verify_result, "verifier_model", "unknown"),
        "verify_cost": getattr(verify_result, "verifier_cost_usd", None),
        "verify_verdict": getattr(verify_result, "verdict", None),
    }
    (HERE / "s3-verification-result.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print("\n========== SUMMARY ==========")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

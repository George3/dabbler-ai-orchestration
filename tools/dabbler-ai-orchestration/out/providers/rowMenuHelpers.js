"use strict";
// Pure helpers for the Session Sets Explorer right-click QuickPick
// (Set 048 S3 spec §3.3, audit Bias 3 flip) and the L5 left-click
// dual-action. Extracted from `CustomSessionSetsView` so the
// decision logic is unit-testable without instantiating the webview
// provider — the view supplies its own vscode dependencies, this
// module is pure.
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildTopLevelItems = buildTopLevelItems;
exports.buildSubmenuItems = buildSubmenuItems;
exports.planLeftClickActivation = planLeftClickActivation;
// Build the top-level QuickPick item list:
//   - "Open File ▸" when the openFile category is non-empty
//   - "Copy Prompt ▸" when the copyEval category is non-empty (label
//     was "Copy Eval ▸" in Set 048 S3; renamed Set 049 S1 because the
//     submenu contains non-evaluation entries like "Start Next Session"
//     and "Start New Parallel Session". The internal `dabblerKind` /
//     ActionCategory identifier stays `copyEval` so this rename is
//     user-visible only.)
//   - one item per flat action (already sorted by `applicableActions`)
function buildTopLevelItems(categorized) {
    const items = [];
    if (categorized.openFile.length > 0) {
        items.push({ label: "Open File ▸", dabblerKind: "openFile" });
    }
    if (categorized.copyEval.length > 0) {
        items.push({ label: "Copy Prompt ▸", dabblerKind: "copyEval" });
    }
    for (const action of categorized.flat) {
        items.push({ label: action.label, dabblerKind: "action", action });
    }
    return items;
}
function buildSubmenuItems(submenu) {
    return submenu.map((action) => ({ label: action.label, action }));
}
// `state` is typed as the closed `SessionState` union in `types.ts`,
// but we use a positive `in-progress | not-started` check rather
// than a negative `complete | cancelled` check so that any future
// state value (a schema migration introducing e.g. "archived") FAILS
// CLOSED — the unknown state would skip the clipboard shortcut
// rather than fire on a bucket the operator never approved for L5.
function planLeftClickActivation(setName, state) {
    const openCommand = { commandId: "dabblerSessionSets.openSpec", setName };
    if (state !== "in-progress" && state !== "not-started") {
        return { openCommand, clipboardWrite: null };
    }
    const sanitized = setName.replace(/`/g, "'");
    return {
        openCommand,
        clipboardWrite: {
            text: `Start the next session of \`${sanitized}\`.`,
            toast: `Copied: Start the next session of ${setName}`,
        },
    };
}
//# sourceMappingURL=rowMenuHelpers.js.map
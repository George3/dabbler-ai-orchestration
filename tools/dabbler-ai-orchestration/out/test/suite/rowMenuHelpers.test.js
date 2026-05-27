"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("assert"));
const rowMenuHelpers_1 = require("../../providers/rowMenuHelpers");
// Set 048 S3 — rowMenuHelpers tests. The two-step QuickPick item
// construction and the L5 left-click planner are pure functions
// extracted from CustomSessionSetsView; this suite exercises them
// without standing up a webview provider.
function action(over) {
    return {
        id: over.id ?? "dabbler.test",
        label: over.label ?? "Test",
        group: over.group ?? 100,
        category: over.category ?? "flat",
        when: over.when ?? (() => true),
    };
}
function cat(over) {
    return {
        openFile: over.openFile ?? [],
        copyEval: over.copyEval ?? [],
        flat: over.flat ?? [],
    };
}
suite("rowMenuHelpers — buildTopLevelItems", () => {
    test("returns empty list when all three categories are empty", () => {
        assert.deepStrictEqual((0, rowMenuHelpers_1.buildTopLevelItems)(cat({})), []);
    });
    test("includes 'Open File ▸' only when openFile category has entries", () => {
        const withOpen = (0, rowMenuHelpers_1.buildTopLevelItems)(cat({ openFile: [action({ id: "openSpec", label: "Spec", category: "openFile" })] }));
        assert.strictEqual(withOpen.length, 1);
        assert.strictEqual(withOpen[0].label, "Open File ▸");
        assert.strictEqual(withOpen[0].dabblerKind, "openFile");
        const withoutOpen = (0, rowMenuHelpers_1.buildTopLevelItems)(cat({}));
        assert.ok(!withoutOpen.some((i) => i.dabblerKind === "openFile"));
    });
    test("includes 'Copy Prompt ▸' only when copyEval category has entries", () => {
        const withCopy = (0, rowMenuHelpers_1.buildTopLevelItems)(cat({ copyEval: [action({ id: "x", label: "Eval", category: "copyEval" })] }));
        assert.ok(withCopy.some((i) => i.label === "Copy Prompt ▸" && i.dabblerKind === "copyEval"));
    });
    test("appends flat actions verbatim after the submenu chips", () => {
        const items = (0, rowMenuHelpers_1.buildTopLevelItems)(cat({
            openFile: [action({ id: "a", category: "openFile" })],
            copyEval: [action({ id: "b", category: "copyEval" })],
            flat: [
                action({ id: "dabbler.checkOutOrchestrator", label: "Set Orchestrator…", category: "flat" }),
                action({ id: "dabblerSessionSets.cancel", label: "Cancel Session Set", category: "flat" }),
            ],
        }));
        assert.deepStrictEqual(items.map((i) => i.label), ["Open File ▸", "Copy Prompt ▸", "Set Orchestrator…", "Cancel Session Set"]);
        assert.strictEqual(items[2].dabblerKind, "action");
        assert.strictEqual(items[2].action?.id, "dabbler.checkOutOrchestrator");
    });
    test("submenu chips come BEFORE flat actions regardless of category order", () => {
        const items = (0, rowMenuHelpers_1.buildTopLevelItems)(cat({
            flat: [action({ id: "cancel", label: "Cancel", category: "flat" })],
            openFile: [action({ id: "spec", label: "Spec", category: "openFile" })],
            copyEval: [action({ id: "eval", label: "Evaluate Spec", category: "copyEval" })],
        }));
        assert.deepStrictEqual(items.map((i) => i.label), ["Open File ▸", "Copy Prompt ▸", "Cancel"]);
    });
});
suite("rowMenuHelpers — buildSubmenuItems", () => {
    test("maps actions to QuickPick items preserving label and action reference", () => {
        const actions = [
            action({ id: "x", label: "Spec", category: "openFile" }),
            action({ id: "y", label: "Activity Log", category: "openFile" }),
        ];
        const items = (0, rowMenuHelpers_1.buildSubmenuItems)(actions);
        assert.strictEqual(items.length, 2);
        assert.strictEqual(items[0].label, "Spec");
        assert.strictEqual(items[0].action.id, "x");
        assert.strictEqual(items[1].label, "Activity Log");
        assert.strictEqual(items[1].action.id, "y");
    });
    test("returns empty array for empty input", () => {
        assert.deepStrictEqual((0, rowMenuHelpers_1.buildSubmenuItems)([]), []);
    });
});
suite("rowMenuHelpers — planLeftClickActivation (L5)", () => {
    test("ALWAYS opens spec.md (preserved S4 default)", () => {
        for (const st of ["in-progress", "not-started", "complete", "cancelled"]) {
            const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("xy", st);
            assert.strictEqual(plan.openCommand.commandId, "dabblerSessionSets.openSpec");
            assert.strictEqual(plan.openCommand.setName, "xy");
        }
    });
    test("non-terminal rows ALSO copy 'Start the next session of `<slug>`.' + toast", () => {
        for (const st of ["in-progress", "not-started"]) {
            const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("xy", st);
            assert.ok(plan.clipboardWrite !== null, `expected clipboard write for state=${st}`);
            assert.strictEqual(plan.clipboardWrite.text, "Start the next session of `xy`.");
            assert.strictEqual(plan.clipboardWrite.toast, "Copied: Start the next session of xy");
        }
    });
    test("terminal rows skip the clipboard write and toast", () => {
        for (const st of ["complete", "cancelled"]) {
            const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("xy", st);
            assert.strictEqual(plan.clipboardWrite, null);
        }
    });
    test("clipboard text uses the set's slug verbatim (no escaping ambiguity)", () => {
        const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("048-lightweight-tier-parity", "in-progress");
        assert.strictEqual(plan.clipboardWrite.text, "Start the next session of `048-lightweight-tier-parity`.");
    });
    test("sanitizes backticks in slug so the markdown payload stays well-formed (S3 verifier-flagged)", () => {
        const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("set`-with-backtick", "in-progress");
        assert.strictEqual(plan.clipboardWrite.text, "Start the next session of `set'-with-backtick`.");
        // The toast preserves the original name (no markdown rendering on
        // an info notification) — only the clipboard text gets sanitized.
        assert.strictEqual(plan.clipboardWrite.toast, "Copied: Start the next session of set`-with-backtick");
    });
    test("unknown/future state values fail CLOSED — skip clipboard, still open spec.md", () => {
        // Defense-in-depth: if a schema migration introduces a new state
        // value (e.g., "archived"), planLeftClickActivation should NOT
        // fire the L5 clipboard shortcut on a bucket the operator never
        // approved for it. The TS type narrows to the closed 4-value
        // union, but runtime can still see widened strings under cast.
        const plan = (0, rowMenuHelpers_1.planLeftClickActivation)("xy", 
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        "archived");
        assert.strictEqual(plan.openCommand.commandId, "dabblerSessionSets.openSpec");
        assert.strictEqual(plan.clipboardWrite, null);
    });
});
//# sourceMappingURL=rowMenuHelpers.test.js.map
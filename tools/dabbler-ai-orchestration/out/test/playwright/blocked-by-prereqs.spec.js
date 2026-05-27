"use strict";
// Layer-3 rendering smoke for the Set 047 Session 5 blockedByPrereqs
// surface. The Explorer derives `blockedByPrereqs` on each set's
// in-memory record by cross-referencing the spec's `prerequisites:`
// field against the target set's `status`. The renderer surfaces a
// `[BLOCKED BY PREREQS]` badge on non-terminal rows whose
// `blockedByPrereqs` is true.
//
// Scenarios covered:
//   1. Two-set fixture with prereq IN-PROGRESS → dependant renders
//      the [BLOCKED BY PREREQS] badge.
//   2. Same fixture flipped: prereq COMPLETE → dependant renders no
//      badge (i.e., unblocked).
//   3. Spec without prerequisites: → no badge, regardless of any
//      other set's status.
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
const test_1 = require("@playwright/test");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const electronLaunch_1 = require("./electronLaunch");
async function teardown(per) {
    const errs = [];
    if (per.launch) {
        try {
            await (0, electronLaunch_1.closeVSCode)(per.launch);
        }
        catch (e) {
            errs.push(e);
        }
    }
    if (per.tmpPath) {
        try {
            (0, electronLaunch_1.cleanupTmpDir)(per.tmpPath);
        }
        catch (e) {
            errs.push(e);
        }
    }
    if (errs.length > 0) {
        // eslint-disable-next-line no-console
        console.warn("teardown encountered cleanup errors:", errs);
    }
}
async function treeitemTexts(tree) {
    const items = tree.locator('[role="treeitem"]');
    const count = await items.count();
    const out = [];
    for (let i = 0; i < count; i++) {
        const item = items.nth(i);
        const t = (await item.textContent()) || "";
        out.push(t.trim().replace(/\s+/g, " "));
    }
    return out;
}
function appendPrerequisitesToSpec(setDir, prereqSlugs) {
    // The harness emits a spec.md with a fenced ``yaml`` Session Set
    // Configuration block. Append `prerequisites:` lines INSIDE that
    // block so the parser picks them up.
    const specPath = path.join(setDir, "spec.md");
    const original = fs.readFileSync(specPath, "utf8");
    const prereqsBlock = [
        "prerequisites:",
        ...prereqSlugs.map((slug) => `  - slug: ${slug}\n    condition: complete`),
    ].join("\n");
    // Insert the prereqs block right before the closing ``` fence of
    // the Session Set Configuration yaml block. Regex anchored to the
    // first ``` after `## Session Set Configuration`.
    const updated = original.replace(/(##\s*Session Set Configuration[\s\S]*?```ya?ml[\s\S]*?)(\n```)/i, (_full, before, fenceClose) => `${before}\n${prereqsBlock}${fenceClose}`);
    fs.writeFileSync(specPath, updated, "utf8");
}
function setStatusToComplete(setDir) {
    // Forge a v4-shape complete state on disk so the cross-reference
    // resolves the prereq's condition.
    const statePath = path.join(setDir, "session-state.json");
    const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
    state.status = "complete";
    if (Array.isArray(state.sessions)) {
        for (const entry of state.sessions) {
            entry.status = "complete";
        }
    }
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2) + "\n", "utf8");
}
// ---------------------------------------------------------------------
// Scenario 1: dependant renders [BLOCKED BY PREREQS] when prereq is
// not-yet-complete.
// ---------------------------------------------------------------------
(0, test_1.test)("renders [BLOCKED BY PREREQS] when prereq target is in-progress", async () => {
    const per = {};
    try {
        per.tmpPath = (0, electronLaunch_1.makeTmpDir)("dabbler-pw-prereq-blocked");
        // Prereq set — stays at the harness's default "not-started" /
        // sessions[].status = "not-started"; that's "not complete" from
        // the cross-reference's point of view.
        (0, electronLaunch_1.makeSet)(per.tmpPath, "044-prereq", 1);
        // Dependant set — declares the prereq above.
        const depHandle = (0, electronLaunch_1.makeSet)(per.tmpPath, "047-dependant", 2);
        appendPrerequisitesToSpec(depHandle.set_dir, ["044-prereq"]);
        per.launch = await (0, electronLaunch_1.launchVSCode)(depHandle.repo_root);
        const tree = await (0, electronLaunch_1.openSessionSetsView)(per.launch.page);
        await (0, electronLaunch_1.triggerRefresh)(per.launch.page);
        const texts = await treeitemTexts(tree);
        const joined = texts.join("\n");
        (0, test_1.expect)(joined).toContain("047-dependant");
        (0, test_1.expect)(joined).toContain("[BLOCKED BY PREREQS]");
        // Sanity: the prereq row itself should NOT carry the badge
        // (it has no prereqs of its own).
        const prereqRow = texts.find((t) => t.includes("044-prereq"));
        (0, test_1.expect)(prereqRow).toBeDefined();
        (0, test_1.expect)(prereqRow).not.toContain("[BLOCKED BY PREREQS]");
    }
    finally {
        await teardown(per);
    }
});
// ---------------------------------------------------------------------
// Scenario 2: same dependant, with the prereq flipped to complete →
// no badge.
// ---------------------------------------------------------------------
(0, test_1.test)("no [BLOCKED BY PREREQS] badge when prereq target is complete", async () => {
    const per = {};
    try {
        per.tmpPath = (0, electronLaunch_1.makeTmpDir)("dabbler-pw-prereq-unblocked");
        const prereqHandle = (0, electronLaunch_1.makeSet)(per.tmpPath, "044-prereq-done", 1);
        setStatusToComplete(prereqHandle.set_dir);
        const depHandle = (0, electronLaunch_1.makeSet)(per.tmpPath, "047-unblocked", 2);
        appendPrerequisitesToSpec(depHandle.set_dir, ["044-prereq-done"]);
        per.launch = await (0, electronLaunch_1.launchVSCode)(depHandle.repo_root);
        const tree = await (0, electronLaunch_1.openSessionSetsView)(per.launch.page);
        await (0, electronLaunch_1.triggerRefresh)(per.launch.page);
        const texts = await treeitemTexts(tree);
        const depRow = texts.find((t) => t.includes("047-unblocked"));
        (0, test_1.expect)(depRow).toBeDefined();
        (0, test_1.expect)(depRow).not.toContain("[BLOCKED BY PREREQS]");
    }
    finally {
        await teardown(per);
    }
});
// ---------------------------------------------------------------------
// Scenario 3 (S5 verifier Nice-to-have-2): badge suppressed when the
// dependant itself is in a terminal state (complete / cancelled).
// The cross-reference still sets blockedByPrereqs=true, but the
// renderer (and contextValueFor) suppress the badge — once a set is
// closed, its dependency status is no longer actionable.
// ---------------------------------------------------------------------
(0, test_1.test)("no [BLOCKED BY PREREQS] badge on terminal-state row even when blockedByPrereqs=true", async () => {
    const per = {};
    try {
        per.tmpPath = (0, electronLaunch_1.makeTmpDir)("dabbler-pw-prereq-terminal");
        // Prereq target stays not-started (so blockedByPrereqs would be
        // true for any depending set under the cross-reference rule).
        (0, electronLaunch_1.makeSet)(per.tmpPath, "044-still-not-started", 1);
        // Dependant is COMPLETE on disk; badge must be suppressed on the
        // terminal row even though the cross-reference would otherwise
        // mark it blocked.
        const depHandle = (0, electronLaunch_1.makeSet)(per.tmpPath, "047-completed-dep", 1);
        appendPrerequisitesToSpec(depHandle.set_dir, ["044-still-not-started"]);
        setStatusToComplete(depHandle.set_dir);
        per.launch = await (0, electronLaunch_1.launchVSCode)(depHandle.repo_root);
        const tree = await (0, electronLaunch_1.openSessionSetsView)(per.launch.page);
        await (0, electronLaunch_1.triggerRefresh)(per.launch.page);
        const texts = await treeitemTexts(tree);
        const depRow = texts.find((t) => t.includes("047-completed-dep"));
        (0, test_1.expect)(depRow).toBeDefined();
        (0, test_1.expect)(depRow).not.toContain("[BLOCKED BY PREREQS]");
    }
    finally {
        await teardown(per);
    }
});
// ---------------------------------------------------------------------
// Scenario 4: a set without prerequisites declared never carries the
// badge.
// ---------------------------------------------------------------------
(0, test_1.test)("no [BLOCKED BY PREREQS] badge when prerequisites field is absent", async () => {
    const per = {};
    try {
        per.tmpPath = (0, electronLaunch_1.makeTmpDir)("dabbler-pw-prereq-absent");
        const handle = (0, electronLaunch_1.makeSet)(per.tmpPath, "047-standalone", 1);
        // No appendPrerequisitesToSpec call — spec ships without the field.
        per.launch = await (0, electronLaunch_1.launchVSCode)(handle.repo_root);
        const tree = await (0, electronLaunch_1.openSessionSetsView)(per.launch.page);
        await (0, electronLaunch_1.triggerRefresh)(per.launch.page);
        const texts = await treeitemTexts(tree);
        const row = texts.find((t) => t.includes("047-standalone"));
        (0, test_1.expect)(row).toBeDefined();
        (0, test_1.expect)(row).not.toContain("[BLOCKED BY PREREQS]");
    }
    finally {
        await teardown(per);
    }
});
//# sourceMappingURL=blocked-by-prereqs.spec.js.map
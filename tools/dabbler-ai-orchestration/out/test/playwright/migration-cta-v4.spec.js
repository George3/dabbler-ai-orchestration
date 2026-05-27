"use strict";
// Layer 3 rendering smoke for the v3 → v4 migration CTA, Set 047
// Session 3. Each test creates a canonical v3 set via the harness
// (which emits schemaVersion=3 with a populated sessions[] today),
// launches a real Electron VS Code, and asserts the tree surfaces
// the "(needs migration)" badge — the same chip that fired on v2
// files now also fires on canonical v3 files because v3 → v4 is the
// next migration target.
//
// The migration command itself is operator-triggered (modal confirm),
// not auto-fire. End-to-end exercise of the command lives in the TS
// unit tests for `migrateOneSetV4` rather than here, since driving a
// modal confirmation from Playwright reliably across VS Code versions
// is fragile and adds little signal over the direct call. This spec
// covers the badge half of the loop, which is the visible UX surface
// that operators rely on for "is something asking me to migrate?"
Object.defineProperty(exports, "__esModule", { value: true });
const test_1 = require("@playwright/test");
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
// ---------------------------------------------------------------------
// Scenario 1: canonical v3 state file on disk → "(needs migration)"
// badge on row. This is the new Set 047 Session 3 behavior — under
// Set 030 Session 5 the badge only fired on v2 / broken-v3 files.
// ---------------------------------------------------------------------
(0, test_1.test)("renders (needs migration) badge on a canonical v3 set (v3 → v4 target)", async () => {
    const per = {};
    try {
        per.tmpPath = (0, electronLaunch_1.makeTmpDir)("dabbler-pw-v3-needs-v4");
        // `makeSet` emits canonical v3 today (schemaVersion=3 with
        // sessions[] populated by the harness). No on-disk surgery needed
        // — the new detector flips needsMigration to true on this shape.
        const h = (0, electronLaunch_1.makeSet)(per.tmpPath, "scenario-v3-needs-v4", 3);
        per.launch = await (0, electronLaunch_1.launchVSCode)(h.repo_root);
        const tree = await (0, electronLaunch_1.openSessionSetsView)(per.launch.page);
        await (0, electronLaunch_1.triggerRefresh)(per.launch.page);
        const joined = (await treeitemTexts(tree)).join("\n");
        (0, test_1.expect)(joined).toContain("scenario-v3-needs-v4");
        (0, test_1.expect)(joined).toContain("(needs migration)");
        // Negative control: only one set in this fixture; no other badge
        // should appear.
        (0, test_1.expect)(joined).not.toContain("[FORCED]");
    }
    finally {
        await teardown(per);
    }
});
//# sourceMappingURL=migration-cta-v4.spec.js.map
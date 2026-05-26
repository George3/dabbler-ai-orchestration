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

import { expect, test } from "@playwright/test";
import {
  cleanupTmpDir,
  closeVSCode,
  launchVSCode,
  LaunchedVSCode,
  makeSet,
  makeTmpDir,
  openSessionSetsView,
  triggerRefresh,
} from "./electronLaunch";

interface PerTest {
  tmpPath?: string;
  launch?: LaunchedVSCode;
}

async function teardown(per: PerTest): Promise<void> {
  const errs: unknown[] = [];
  if (per.launch) {
    try {
      await closeVSCode(per.launch);
    } catch (e) {
      errs.push(e);
    }
  }
  if (per.tmpPath) {
    try {
      cleanupTmpDir(per.tmpPath);
    } catch (e) {
      errs.push(e);
    }
  }
  if (errs.length > 0) {
    // eslint-disable-next-line no-console
    console.warn("teardown encountered cleanup errors:", errs);
  }
}

async function treeitemTexts(
  tree: import("@playwright/test").FrameLocator,
): Promise<string[]> {
  const items = tree.locator('[role="treeitem"]');
  const count = await items.count();
  const out: string[] = [];
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
test("renders (needs migration) badge on a canonical v3 set (v3 → v4 target)", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-v3-needs-v4");
    // `makeSet` emits canonical v3 today (schemaVersion=3 with
    // sessions[] populated by the harness). No on-disk surgery needed
    // — the new detector flips needsMigration to true on this shape.
    const h = makeSet(per.tmpPath, "scenario-v3-needs-v4", 3);

    per.launch = await launchVSCode(h.repo_root);
    const tree = await openSessionSetsView(per.launch.page);
    await triggerRefresh(per.launch.page);

    const joined = (await treeitemTexts(tree)).join("\n");
    expect(joined).toContain("scenario-v3-needs-v4");
    expect(joined).toContain("(needs migration)");
    // Negative control: only one set in this fixture; no other badge
    // should appear.
    expect(joined).not.toContain("[FORCED]");
  } finally {
    await teardown(per);
  }
});

// Layer 3 rendering smoke for the v3 → v4 migration CTA, Set 047
// Session 3. Each test creates a set via the harness and downgrades
// its state file to canonical v3 (the harness writers emit v4 since
// Set 049 — the original "makeSet emits v3 today" premise rotted and
// left this fixture already-current, so the marker never rendered),
// launches a real Electron VS Code, and asserts the tree surfaces
// the migration asterisk — the same marker that fires on v2 files
// also fires on canonical v3 files because v3 → v4 is the next
// migration target.
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
  downgradeStateFileToV3,
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
test("renders schema-drift asterisk + tooltip on a canonical v3 set (v3 → v4 target)", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-v3-needs-v4");
    // The harness emits canonical v4 since Set 049; downgrade the
    // state file to canonical v3 so the v3 → v4 detector actually has
    // something to flag.
    const h = makeSet(per.tmpPath, "scenario-v3-needs-v4", 3);
    downgradeStateFileToV3(h);

    per.launch = await launchVSCode(h.repo_root);
    const tree = await openSessionSetsView(per.launch.page);
    await triggerRefresh(per.launch.page);

    const joined = (await treeitemTexts(tree)).join("\n");
    expect(joined).toContain("scenario-v3-needs-v4");
    // Set 050 S4: the old "(needs migration)" label is replaced by an
    // unobtrusive asterisk carrying a "Ran under schema v3" tooltip.
    expect(joined).not.toContain("(needs migration)");

    const marker = tree.locator(".row-migration-marker");
    await expect(marker).toHaveCount(1);
    await expect(marker).toHaveText("*");
    expect(await marker.getAttribute("title")).toBe("Ran under schema v3");

    // Negative control: only one set in this fixture; no other badge
    // should appear.
    expect(joined).not.toContain("[FORCED]");
  } finally {
    await teardown(per);
  }
});

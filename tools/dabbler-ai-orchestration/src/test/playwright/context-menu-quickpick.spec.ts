// Layer-3 Playwright Electron smoke for the Set 048 Session 3 menu
// rebuild (spec §3.3, audit Bias 3 flip). The cursor-anchored HTML
// popup that Set 034 introduced is retired in favor of
// `vscode.window.showQuickPick`. This spec pins the negative
// invariant — the retired DOM never appears — so any future re-
// introduction of the popup fails CI immediately. The positive
// QuickPick flow itself is covered by Layer-2 unit tests in
// `rowMenuHelpers.test.ts`; driving the outer VS Code QuickPick from
// inside a Playwright frame is brittle (the QuickPick lives in the
// workbench root, not in the webview's iframe), and the existing
// session-sets-tree.spec.ts file documents that convention at its
// own header.

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
    try { await closeVSCode(per.launch); } catch (e) { errs.push(e); }
  }
  if (per.tmpPath) {
    try { cleanupTmpDir(per.tmpPath); } catch (e) { errs.push(e); }
  }
  if (errs.length > 0) {
    // eslint-disable-next-line no-console
    console.warn("teardown errors:", errs);
  }
}

test("cursor-anchored .context-menu DOM is absent before and after a right-click (Set 048 S3 retirement)", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-quickpick");
    const h = makeSet(per.tmpPath, "048-quickpick-fixture", 3);
    per.launch = await launchVSCode(h.repo_root);
    const inner = await openSessionSetsView(per.launch.page);
    await triggerRefresh(per.launch.page);

    const row = inner.locator(
      '[role="treeitem"][data-slug="048-quickpick-fixture"]',
    );
    await expect(row).toBeVisible({ timeout: 30_000 });

    // Pre-condition: the cursor-anchored popup container that Set 034
    // attached to the webview body is gone. No `.context-menu` element
    // is appended on startup.
    await expect(inner.locator(".context-menu")).toHaveCount(0);
    await expect(inner.locator(".context-menu-item")).toHaveCount(0);

    // Trigger the contextmenu event. The webview posts
    // `showRowContextMenu` to the host, which opens a native
    // QuickPick in the workbench root (outside this iframe). The
    // critical invariant is that NO `.context-menu` element appears
    // inside the webview.
    await row.click({ button: "right" });

    // Give any (incorrectly re-introduced) popup-rendering code a
    // chance to mount. The Set 034 implementation appended the DOM
    // synchronously via `showCursorContextMenu`; a regression would
    // be visible within a few hundred ms.
    await per.launch!.page.waitForTimeout(750);

    await expect(inner.locator(".context-menu")).toHaveCount(0);
    await expect(inner.locator(".context-menu-item")).toHaveCount(0);
    await expect(inner.locator(".context-menu-separator")).toHaveCount(0);
  } finally {
    await teardown(per);
  }
});

test("Open AI Assignment is fully absent from the row tree (Set 048 S3 L3 removal)", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-l3-ai-assignment");
    const h = makeSet(per.tmpPath, "048-l3-removed", 3);
    per.launch = await launchVSCode(h.repo_root);
    const inner = await openSessionSetsView(per.launch.page);
    await triggerRefresh(per.launch.page);

    // The row exists.
    await expect(
      inner.locator('[role="treeitem"][data-slug="048-l3-removed"]'),
    ).toBeVisible({ timeout: 30_000 });

    // The retired popup's data-command attribute (which the cursor-
    // anchored popup used to carry the command id) is gone. Any
    // accidental re-introduction of the data-command for
    // openAiAssignment would surface here.
    await expect(
      inner.locator('[data-command="dabblerSessionSets.openAiAssignment"]'),
    ).toHaveCount(0);
  } finally {
    await teardown(per);
  }
});

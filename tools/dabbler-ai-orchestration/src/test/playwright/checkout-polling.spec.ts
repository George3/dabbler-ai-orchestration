// Set 033 Session 5 — Layer-3 Playwright coverage for the
// CheckoutPollService sentinel-consumption path.
//
// The full poll-and-auto-attach happy path requires the operator to
// click "Poll for release" on a VS Code information-message toast, then
// wait for the service to detect the state-file change and retry
// start_session. Driving VS Code's notification toasts from Playwright
// runs into the same cross-iframe focus brittleness session-sets-
// tree.spec.ts already called out (and S4 hit again with the palette
// path for `Dabbler: Release Check-Out`). Per the existing pattern, we
// cover the load-bearing observable end-to-end (the service consuming
// a sentinel file dropped into the conflicts directory on launch),
// while the click-driven happy path lives in Layer-2 with a documented
// `test.skip` here.

import { expect, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import {
  cleanupTmpDir,
  closeVSCode,
  launchVSCode,
  LaunchedVSCode,
  makeSet,
  makeTmpDir,
  openSessionSetsView,
  seedOrchestratorBlock,
  startSession,
} from "./electronLaunch";

interface PerTest {
  tmpPath?: string;
  launch?: LaunchedVSCode;
  prevHome?: string | undefined;
  prevUserProfile?: string | undefined;
}

function withHomeOverride(per: PerTest, homeOverride: string): void {
  per.prevHome = process.env.HOME;
  per.prevUserProfile = process.env.USERPROFILE;
  process.env.HOME = homeOverride;
  process.env.USERPROFILE = homeOverride;
}

function restoreHome(per: PerTest): void {
  if (per.prevHome === undefined) delete process.env.HOME;
  else process.env.HOME = per.prevHome;
  if (per.prevUserProfile === undefined) delete process.env.USERPROFILE;
  else process.env.USERPROFILE = per.prevUserProfile;
}

async function teardown(per: PerTest): Promise<void> {
  const errs: unknown[] = [];
  if (per.launch) {
    try { await closeVSCode(per.launch); } catch (e) { errs.push(e); }
  }
  restoreHome(per);
  if (per.tmpPath) {
    try { cleanupTmpDir(per.tmpPath); } catch (e) { errs.push(e); }
  }
  if (errs.length > 0) {
    // eslint-disable-next-line no-console
    console.warn("teardown errors:", errs);
  }
}

test("CheckoutPollService consumes a pre-existing conflict sentinel on activation", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-poll-sentinel");
    const homeOverride = path.join(per.tmpPath!, "fake-home");
    fs.mkdirSync(homeOverride, { recursive: true });
    withHomeOverride(per, homeOverride);

    // Scaffold a session set in the workspace, with claude+anthropic
    // currently holding the slot — the conflict record asserts that
    // gpt-5-4+openai got refused while trying to claim it.
    const h = makeSet(per.tmpPath, "033-poll-sentinel", 2);
    startSession(h, 1);
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
    });

    // Drop a sentinel file in the home-override's conflicts dir,
    // simulating what the Claude SessionStart invoker or the Codex
    // configWatcher would have written. The CheckoutPollService's
    // start() method scans this directory at activation, so we can
    // assert end-to-end on consumption without driving the toast.
    const conflictsDir = path.join(homeOverride, ".dabbler", "checkout-conflicts");
    fs.mkdirSync(conflictsDir, { recursive: true });
    const sentinelPath = path.join(conflictsDir, "test-sentinel.json");
    fs.writeFileSync(
      sentinelPath,
      JSON.stringify({
        schemaVersion: 1,
        detectedAt: new Date().toISOString(),
        source: "claude-invoker",
        sessionSetPath: h.set_dir,
        sessionSetSlug: h.slug,
        sessionNumber: 1,
        heldByEngine: "claude",
        heldByProvider: "anthropic",
        heldByModel: "claude-opus-4-7",
        checkedOutAt: "2026-05-20T08:00:00-04:00",
        wouldBeHolderEngine: "gpt-5-4",
        wouldBeHolderProvider: "openai",
        wouldBeHolderModel: "gpt-5",
        wouldBeHolderEffort: "medium",
      }),
      "utf8",
    );

    per.launch = await launchVSCode(h.repo_root);
    // Open the Session Sets view to activate the extension; that
    // triggers the safeRegister chain that includes
    // `CheckoutPollService.start()`.
    await openSessionSetsView(per.launch.page);

    // The service consumes (reads + deletes) sentinel files during
    // start(); we expect the file to be gone within a generous
    // window. The "100ms re-read delay" inside start() is doubled
    // here as a safety margin against slow CI hosts.
    const deadline = Date.now() + 15_000;
    let consumed = false;
    while (Date.now() < deadline) {
      if (!fs.existsSync(sentinelPath)) {
        consumed = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    expect(consumed).toBe(true);

    // Sanity: the session-state.json should still name claude +
    // anthropic — consuming the sentinel surfaces the prompt but
    // does NOT silently force-override.
    const state = JSON.parse(
      fs.readFileSync(path.join(h.set_dir, "session-state.json"), "utf8"),
    ) as { orchestrator?: { engine?: string; provider?: string } };
    expect(state.orchestrator?.engine).toBe("claude");
    expect(state.orchestrator?.provider).toBe("anthropic");
  } finally {
    await teardown(per);
  }
});

// FIXME (Set 033 S5, 2026-05-20): the full "second orchestrator polls,
// holder closes, second orchestrator auto-attaches" happy path requires
// clicking "Poll for release" on a VS Code information-message toast.
// Driving VS Code notification buttons from Playwright runs into the
// same cross-iframe focus brittleness that session-sets-tree.spec.ts
// and S4's release-checkout palette scenario hit. The polling state
// machine itself is exhaustively covered at Layer 2
// (checkoutPollService.test.ts: 25 tests covering parse, identity
// gate, prompt dispatch, retry, dispose, sentinel ingest). Skipping
// until a more reliable notification-button driver is identified;
// manual smoke remains the operator path.
test.skip("second orchestrator polls, holder closes, second orchestrator auto-attaches", async () => {
  // The scenario, for reference:
  //   1. Scaffold a set with claude+anthropic holding.
  //   2. Drop a sentinel naming gpt-5-4+openai as the would-be holder.
  //   3. Launch VS Code; service surfaces the prompt.
  //   4. Click "Poll for release" on the toast.
  //   5. Externally clear the orchestrator block (or flip status →
  //      complete).
  //   6. Within 5s + retry-spawn, the session-state.json's orchestrator
  //      block updates to gpt-5-4+openai (the would-be holder auto-
  //      attached).
  //   7. Verify the success toast text contains the slug.
  //
  // Step 4 is the blocker: Playwright's `getByRole('button', { name:
  // "Poll for release" })` against VS Code's notification iframe is
  // unreliable across VS Code minor versions.
});

// Set 060 Session 3 — unit tests for the pure Getting Started HTML
// builders (media/session-sets-tree/gettingStartedHtml.js, the UMD-lite
// module the webview loads before client.js). Covers:
//
//   - the D6 Full-tier provider-key warning under the Build button
//     (visible only when tier=full AND providerKeyPresent=false), and
//   - the D7 parallel-worktree note under the checkbox — the
//     checked-vs-unchecked rendering test verifier issue
//     S060-S2-V1-001 asked for, shipping with the note itself.
//
// The module is plain JS by design (the webview loads it raw, outside
// the esbuild bundle), so the test requires it straight off disk.

import * as assert from "assert";
import * as path from "path";
import { createRequire } from "module";

// mocha 10 is import-first; under Node >=22 native type-stripping a
// test file with no relative TS imports loads as native ESM, where the
// CJS `require` / `__dirname` globals don't exist. `createRequire`
// anchored at the package root (the npm script's cwd) works in BOTH
// load modes. Do not switch this to a bare `require` or `__dirname`.
const requireFromPackageRoot = createRequire(
  path.join(process.cwd(), "package.json"),
);
const gsHtml = requireFromPackageRoot(
  "./media/session-sets-tree/gettingStartedHtml.js",
) as {
  renderNoFolder(): string;
  renderGettingStarted(
    gs: {
      mode: string;
      structureBuilt: boolean;
      planPresent: boolean;
      sessionSetsPresent: boolean;
      providerKeyPresent: boolean;
    },
    controls: { tier: "full" | "lightweight"; parallel: boolean },
  ): string;
  envWarningHtml(visible: boolean): string;
  worktreeNoteHtml(visible: boolean): string;
  ENV_WARNING_TEXT: string;
  WORKTREE_NOTE_TEXT: string;
};

function gs(overrides: Partial<{
  structureBuilt: boolean;
  planPresent: boolean;
  sessionSetsPresent: boolean;
  providerKeyPresent: boolean;
}> = {}) {
  return {
    mode: "getting-started",
    structureBuilt: false,
    planPresent: false,
    sessionSetsPresent: false,
    providerKeyPresent: true,
    ...overrides,
  };
}

const FULL = { tier: "full" as const, parallel: false };
const LIGHT = { tier: "lightweight" as const, parallel: false };

// The warning/note are always rendered and toggled via the `hidden`
// attribute (so client.js can flip visibility without re-rendering).
// "Visible" = the element exists WITHOUT `hidden`.
function isVisible(html: string, dataAttr: string): boolean {
  const idx = html.indexOf(dataAttr);
  assert.notStrictEqual(idx, -1, `element ${dataAttr} not rendered at all`);
  const tagStart = html.lastIndexOf("<div", idx);
  const tagEnd = html.indexOf(">", idx);
  const openTag = html.slice(tagStart, tagEnd + 1);
  return !/\shidden[\s>]/.test(openTag);
}

suite("gettingStartedHtml — form structure (Set 060 S1/S2 parity)", () => {
  test("renders the three steps with their action buttons", () => {
    const html = gsHtml.renderGettingStarted(gs(), FULL);
    for (const action of [
      "build-structure",
      "import-plan",
      "copy-plan-prompt",
      "build-session-sets",
    ]) {
      assert.ok(
        html.includes(`data-gs-action="${action}"`),
        `missing action button ${action}`,
      );
    }
    assert.ok(html.includes('name="gs-tier"'));
    assert.ok(html.includes('name="gs-parallel"'));
  });

  test("completion flags grey/check the steps (D2/D3)", () => {
    const html = gsHtml.renderGettingStarted(
      gs({ structureBuilt: true }),
      FULL,
    );
    assert.ok(html.includes("gs-step gs-step-complete"));
    assert.ok(html.includes("✓"));
  });

  test("control state survives re-render (radio + checkbox checked attrs)", () => {
    const html = gsHtml.renderGettingStarted(gs(), {
      tier: "lightweight",
      parallel: true,
    });
    assert.ok(/value="lightweight" checked/.test(html));
    assert.ok(/name="gs-parallel" checked/.test(html));
  });

  test("no-folder surface renders the open-folder CTA", () => {
    const html = gsHtml.renderNoFolder();
    assert.ok(html.includes('data-gs-action="open-folder"'));
  });
});

suite("gettingStartedHtml — D6 provider-key warning (Set 060 S3)", () => {
  test("Full tier + no key → warning VISIBLE under the Build button", () => {
    const html = gsHtml.renderGettingStarted(
      gs({ providerKeyPresent: false }),
      FULL,
    );
    assert.strictEqual(isVisible(html, 'data-gs-warning="env"'), true);
    // Placement: inside step 1's body, after the Build button.
    const buildIdx = html.indexOf('data-gs-action="build-structure"');
    const warnIdx = html.indexOf('data-gs-warning="env"');
    const step2Idx = html.indexOf("2. Create or import a project plan");
    assert.ok(buildIdx < warnIdx && warnIdx < step2Idx, "warning not under the Build button");
    // The copy carries the two load-bearing instructions.
    assert.ok(html.includes("ANTHROPIC_API_KEY"));
    assert.ok(html.includes("reload the VS Code window"));
  });

  test("Full tier + key present → warning hidden", () => {
    const html = gsHtml.renderGettingStarted(
      gs({ providerKeyPresent: true }),
      FULL,
    );
    assert.strictEqual(isVisible(html, 'data-gs-warning="env"'), false);
  });

  test("Lightweight tier shows NO warning regardless of keys (D6)", () => {
    const noKey = gsHtml.renderGettingStarted(
      gs({ providerKeyPresent: false }),
      LIGHT,
    );
    assert.strictEqual(isVisible(noKey, 'data-gs-warning="env"'), false);
    const withKey = gsHtml.renderGettingStarted(
      gs({ providerKeyPresent: true }),
      LIGHT,
    );
    assert.strictEqual(isVisible(withKey, 'data-gs-warning="env"'), false);
  });

  test("envWarningHtml escapes its copy and carries role=alert", () => {
    const visible = gsHtml.envWarningHtml(true);
    assert.ok(visible.includes('role="alert"'));
    assert.ok(!/\shidden[\s>]/.test(visible));
    const hidden = gsHtml.envWarningHtml(false);
    assert.ok(/\shidden>/.test(hidden));
  });
});

suite("gettingStartedHtml — D7 worktree note (S060-S2-V1-001)", () => {
  test("checkbox CHECKED → worktree note visible with the git-worktrees copy", () => {
    const html = gsHtml.renderGettingStarted(gs(), {
      tier: "full",
      parallel: true,
    });
    assert.strictEqual(isVisible(html, 'data-gs-note="worktree"'), true);
    assert.ok(html.includes("git worktrees"));
    assert.ok(html.includes("merged back to the main branch"));
  });

  test("checkbox UNCHECKED → worktree note rendered but hidden", () => {
    const html = gsHtml.renderGettingStarted(gs(), {
      tier: "full",
      parallel: false,
    });
    assert.strictEqual(isVisible(html, 'data-gs-note="worktree"'), false);
  });

  test("note sits inside step 3, after the parallel checkbox", () => {
    const html = gsHtml.renderGettingStarted(gs(), {
      tier: "full",
      parallel: true,
    });
    const checkboxIdx = html.indexOf('name="gs-parallel"');
    const noteIdx = html.indexOf('data-gs-note="worktree"');
    assert.ok(checkboxIdx < noteIdx, "note not after the checkbox");
  });
});

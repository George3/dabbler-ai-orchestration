// Set 058 S2 — the session-set generation prompt must steer the AI to the
// canonical spec shape (schemaVersion 4, NNN- slug, tier +
// verificationMode) and never the retired schemaVersion: 2 / bare-slug
// form. Also covers the wizard's "start the next session" cold-start
// closure copy.

import * as assert from "assert";
import * as fs from "fs";
import * as path from "path";
import { buildSessionGenPrompt } from "../../wizard/sessionGenPrompt";
import {
  TemplateBundle,
  loadTemplateBundle,
  resolveBundledTemplateDir,
} from "../../utils/consumerBootstrap";

function canonicalBundleDir(): string {
  const extRoot = path.resolve(__dirname, "../../..");
  const candidates = [
    path.resolve(extRoot, "../../docs/templates/consumer-bootstrap"),
    resolveBundledTemplateDir(extRoot),
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, "spec.md.template"))) return c;
  }
  throw new Error("Could not locate the consumer-bootstrap bundle for tests.");
}
const bundle: TemplateBundle = loadTemplateBundle(canonicalBundleDir());

suite("buildSessionGenPrompt (Set 058 S2)", () => {
  const prompt = buildSessionGenPrompt("PLAN_CONTENT_MARKER", bundle);

  test("embeds the plan text", () => {
    assert.ok(prompt.includes("PLAN_CONTENT_MARKER"));
  });

  test("demands the canonical schemaVersion 4 / NNN- / tier shape", () => {
    assert.ok(/schemaVersion.*4/.test(prompt));
    assert.ok(prompt.includes("NNN-"));
    assert.ok(prompt.includes("tier"));
    assert.ok(prompt.includes("verificationMode"));
  });

  test("never instructs the retired schemaVersion: 2 form", () => {
    assert.ok(!/schemaVersion["']?\s*:\s*2\b/.test(prompt));
  });

  test("shows WRITER-RENDERED, session-expanded exemplars (not raw templates)", () => {
    // The 3-session sample must appear fully expanded — three numbered
    // blocks and three sessions[] objects — not the bundle's illustrative
    // two-block sample.
    const headers = (prompt.match(/### Session \d+ of 3:/g) || []).map((h) =>
      Number(/Session (\d+) of/.exec(h)![1]),
    );
    assert.deepStrictEqual(headers, [1, 2, 3]);
    assert.ok(prompt.includes("session-003/"));
    assert.ok(prompt.includes('"number": 3'));
    assert.ok(prompt.includes('"schemaVersion": 4'));
    assert.ok(/tier:\s*full/.test(prompt));
  });

  test("leaves NO unsubstituted {{TOKEN}} placeholders (rendered, not raw)", () => {
    assert.ok(!prompt.includes("{{"), "prompt should not show raw template tokens");
  });

  test("uses ~~~~ outer fences so the spec's inner ```yaml does not collide", () => {
    assert.ok(prompt.includes("~~~~markdown"));
    assert.ok(prompt.includes("~~~~json"));
  });

  test("worked examples use NNN- slugs everywhere, never a bare slug", () => {
    // The example set is 001-example-feature; every session-set folder /
    // sessionSetName reference must carry the NNN- prefix.
    assert.ok(prompt.includes("001-example-feature"));
    const folderRefs = prompt.match(/docs\/session-sets\/[^/\s"`]+/g) || [];
    assert.ok(folderRefs.length > 0, "expected session-set folder references");
    for (const ref of folderRefs) {
      const leaf = ref.split("/").pop()!;
      // Skip the literal placeholder used in the instructions (<NNN-slug>).
      if (leaf.startsWith("<")) continue;
      assert.ok(
        /^\d{3,}-/.test(leaf),
        `worked-example folder reference is bare-slug: ${ref}`,
      );
    }
    assert.ok(!/"sessionSetName":\s*"[a-z]/.test(prompt), "state example uses NNN- sessionSetName");
  });
});

suite("Get Started wizard — cold-start closure (Set 058 S2)", () => {
  function wizardHtml(): string {
    const candidates = [
      path.resolve(__dirname, "../../../webview/wizard.html"),
      path.resolve(__dirname, "webview/wizard.html"),
    ];
    for (const c of candidates) if (fs.existsSync(c)) return fs.readFileSync(c, "utf8");
    throw new Error("Could not locate wizard.html for tests.");
  }
  const html = wizardHtml();

  test("has an explicit 'start the next session' closure", () => {
    assert.ok(/start the next session/i.test(html));
    assert.ok(html.includes("docs/dabbler/start-here.md"));
  });

  test("states Python is required for both tiers", () => {
    assert.ok(/both tiers/i.test(html));
  });

  test("keeps the tier toggle wiring", () => {
    assert.ok(html.includes('name="tier"'));
    assert.ok(html.includes("applyTierVisibility"));
  });
});

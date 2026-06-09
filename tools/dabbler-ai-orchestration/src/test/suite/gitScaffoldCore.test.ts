// Set 058 S2 — unit tests for the pure scaffolding core
// (scaffoldConsumerRepo). The VS Code wiring (folder picker, tier prompt,
// progress notification) is exercised manually; this asserts the durable
// contract: which files are written, the skip-existing guard, and the ONE
// tier divergence the design lock allows (router config: Full keeps, the
// Lightweight path removes the seeded copy).

import * as assert from "assert";
import * as path from "path";
import { scaffoldConsumerRepo } from "../../commands/gitScaffold";
import { FileOps } from "../../utils/aiRouterInstall";
import {
  BootstrapContext,
  TemplateBundle,
  loadTemplateBundle,
  resolveBundledTemplateDir,
} from "../../utils/consumerBootstrap";
import * as fs from "fs";

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

/** Minimal in-memory FileOps over a normalized-path map. */
function memFileOps(seed: Record<string, string> = {}): {
  ops: FileOps;
  store: Map<string, string>;
} {
  const store = new Map<string, string>();
  const norm = (p: string) => p.replace(/\\/g, "/");
  for (const [k, v] of Object.entries(seed)) store.set(norm(k), v);
  const ops: FileOps = {
    exists: (p) => store.has(norm(p)),
    readFile: (p) => store.get(norm(p)) ?? "",
    writeFile: (p, c) => void store.set(norm(p), c),
    mkdirp: () => {},
    copyDir: () => {},
    removeRecursive: (p) => void store.delete(norm(p)),
    mkdtemp: (prefix) => `/tmp/${prefix}0`,
  };
  return { ops, store };
}

function ctx(over: Partial<BootstrapContext> = {}): BootstrapContext {
  return {
    repoName: "demo",
    setTitle: "First feature",
    purpose: "Do a thing.",
    slug: "001-first-feature",
    created: "2026-06-09",
    tier: "full",
    verificationMode: "out-of-band-or-none",
    totalSessions: 2,
    ...over,
  };
}

const PROJECT = "/repo";
const cfgPath = path.join(PROJECT, "ai_router", "router-config.yaml").replace(/\\/g, "/");

suite("scaffoldConsumerRepo — file writes", () => {
  test("writes the six artifacts under the project dir", async () => {
    const { ops, store } = memFileOps();
    const result = await scaffoldConsumerRepo({
      projectDir: PROJECT,
      ctx: ctx(),
      bundle,
      fileOps: ops,
      installRouter: async () => ({ ok: true, message: "installed" }),
    });
    assert.strictEqual(result.written.length, 6);
    assert.strictEqual(result.skipped.length, 0);
    assert.ok(store.has("/repo/CLAUDE.md"));
    assert.ok(store.has("/repo/AGENTS.md"));
    assert.ok(store.has("/repo/GEMINI.md"));
    assert.ok(store.has("/repo/docs/dabbler/start-here.md"));
    assert.ok(store.has("/repo/docs/session-sets/001-first-feature/spec.md"));
    assert.ok(store.has("/repo/docs/session-sets/001-first-feature/session-state.json"));
  });

  test("never clobbers an existing file (records it as skipped)", async () => {
    const { ops, store } = memFileOps({ "/repo/CLAUDE.md": "PRE-EXISTING" });
    const result = await scaffoldConsumerRepo({
      projectDir: PROJECT,
      ctx: ctx(),
      bundle,
      fileOps: ops,
      installRouter: async () => ({ ok: true, message: "installed" }),
    });
    assert.deepStrictEqual(result.skipped, ["CLAUDE.md"]);
    assert.strictEqual(store.get("/repo/CLAUDE.md"), "PRE-EXISTING");
    assert.strictEqual(result.written.length, 5);
  });
});

suite("scaffoldConsumerRepo — tier divergence (router config)", () => {
  test("Full keeps the seeded router-config.yaml", async () => {
    const { ops, store } = memFileOps();
    // Model the install seeding router-config.yaml (it ships as package data).
    const result = await scaffoldConsumerRepo({
      projectDir: PROJECT,
      ctx: ctx({ tier: "full" }),
      bundle,
      fileOps: ops,
      installRouter: async () => {
        store.set(cfgPath, "models: {}\n");
        return { ok: true, message: "installed" };
      },
    });
    assert.strictEqual(result.routerConfigRemoved, false);
    assert.ok(store.has(cfgPath), "Full tier must keep router-config.yaml");
  });

  test("Lightweight removes the seeded router-config.yaml", async () => {
    const { ops, store } = memFileOps();
    const result = await scaffoldConsumerRepo({
      projectDir: PROJECT,
      ctx: ctx({ tier: "lightweight" }),
      bundle,
      fileOps: ops,
      installRouter: async () => {
        store.set(cfgPath, "models: {}\n");
        return { ok: true, message: "installed" };
      },
    });
    assert.strictEqual(result.routerConfigRemoved, true);
    assert.ok(!store.has(cfgPath), "Lightweight tier must not carry router config");
    // The spec still carries tier: lightweight — the actual switch.
    const spec = store.get("/repo/docs/session-sets/001-first-feature/spec.md")!;
    assert.ok(/tier:\s*lightweight/.test(spec));
  });

  test("surfaces a failed install without throwing", async () => {
    const { ops } = memFileOps();
    const result = await scaffoldConsumerRepo({
      projectDir: PROJECT,
      ctx: ctx(),
      bundle,
      fileOps: ops,
      installRouter: async () => ({ ok: false, message: "pip failed" }),
    });
    assert.strictEqual(result.installOk, false);
    assert.strictEqual(result.installMessage, "pip failed");
    assert.strictEqual(result.written.length, 6); // artifacts still written
  });
});

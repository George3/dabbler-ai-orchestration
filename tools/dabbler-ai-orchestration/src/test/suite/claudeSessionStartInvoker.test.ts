// Set 049 S4 + Set 050 S3 — Layer-2 coverage of the Claude Code SessionStart
// hook invoker shim.
//
// Exports under test:
//   - `parsePayload(raw)` — JSON.parse the hook payload, return `{}` for
//     empty / malformed input.
//   - `recoverPriorClaudeModelEffort(state)` — when the prior orchestrator
//     block is `engine: "claude", provider: "anthropic"`, recover its
//     `model` / `effort` for forwarding. Per Set 049 T3 omit-null contract,
//     recovered values are `undefined` when the prior block omitted them.
//   - `scanSchemaDrift(workspaceRoot)` — Set 050 S3. Pure-JS scan of
//     docs/session-sets/*/session-state.json vs CURRENT_SCHEMA_VERSION;
//     returns a terse string on drift, null when clean. Fail-open.
//   - `CURRENT_SCHEMA_VERSION` — the bundled constant. The Python CI test
//     (test_invoker_schema_constant.py) asserts it equals ai_router's
//     SESSION_STATE_SCHEMA_VERSION; this suite validates the exported value
//     is a positive integer.
//
// The shim is plain Node (no vscode imports); the test loads it via dynamic
// import so exports are available without firing `main()`.

import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { pathToFileURL } from "url";

interface InvokerExports {
  parsePayload: (raw: string) => unknown;
  recoverPriorClaudeModelEffort: (
    state: unknown,
  ) => { model: string | undefined; effort: string | undefined };
  scanSchemaDrift: (workspaceRoot: string) => string | null;
  CURRENT_SCHEMA_VERSION: number;
}

let invoker: InvokerExports;

async function loadInvoker(): Promise<InvokerExports> {
  // npm run test:unit runs from the extension's package root, so the
  // invoker shim lives at `scripts/claude-session-start-invoker.js`
  // relative to cwd. Convert to a file: URL so dynamic import works
  // on Windows where bare paths confuse the ESM loader. The shim uses
  // `module.exports = { ... }`, which the ESM CommonJS interop
  // surfaces as the module's `default` export.
  const invokerPath = path.resolve(
    process.cwd(),
    "scripts",
    "claude-session-start-invoker.js",
  );
  const mod = await import(pathToFileURL(invokerPath).href);
  return (mod.default ?? mod) as InvokerExports;
}

suite("claude-session-start-invoker — parsePayload", () => {
  suiteSetup(async () => {
    invoker = await loadInvoker();
  });

  test("returns the parsed JSON object for a well-formed payload", () => {
    const raw = JSON.stringify({ cwd: "/tmp", session_id: "abc" });
    const parsed = invoker.parsePayload(raw) as Record<string, unknown>;
    assert.strictEqual(parsed.cwd, "/tmp");
    assert.strictEqual(parsed.session_id, "abc");
  });

  test("returns an empty object for empty / whitespace input", () => {
    assert.deepStrictEqual(invoker.parsePayload(""), {});
    assert.deepStrictEqual(invoker.parsePayload("   "), {});
  });

  test("returns an empty object for malformed JSON", () => {
    assert.deepStrictEqual(invoker.parsePayload("{ not json"), {});
  });
});

suite("claude-session-start-invoker — recoverPriorClaudeModelEffort", () => {
  suiteSetup(async () => {
    invoker = await loadInvoker();
  });

  test("returns undefined/undefined when no orchestrator block exists", () => {
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort({}), {
      model: undefined,
      effort: undefined,
    });
    assert.deepStrictEqual(
      invoker.recoverPriorClaudeModelEffort({ orchestrator: null }),
      { model: undefined, effort: undefined },
    );
  });

  test("returns undefined/undefined when engine is not claude", () => {
    const state = {
      orchestrator: {
        engine: "gpt-5-4",
        provider: "openai",
        model: "gpt-5",
        effort: "high",
      },
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: undefined,
      effort: undefined,
    });
  });

  test("returns undefined/undefined when provider is not anthropic", () => {
    const state = {
      orchestrator: {
        engine: "claude",
        provider: "wrong",
        model: "claude-opus-4-7",
        effort: "high",
      },
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: undefined,
      effort: undefined,
    });
  });

  test("recovers model + effort from a top-level claude+anthropic block", () => {
    const state = {
      orchestrator: {
        engine: "claude",
        provider: "anthropic",
        model: "claude-opus-4-7",
        effort: "high",
      },
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: "claude-opus-4-7",
      effort: "high",
    });
  });

  test("recovers model + effort from the v4 in-progress sessions[] entry", () => {
    const state = {
      sessions: [
        { number: 1, status: "complete" },
        {
          number: 2,
          status: "in-progress",
          orchestrator: {
            engine: "claude",
            provider: "anthropic",
            model: "claude-opus-4-7",
            effort: "high",
          },
        },
      ],
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: "claude-opus-4-7",
      effort: "high",
    });
  });

  test("falls back to the most-recently-completed sessions[] entry when no in-progress carries an orchestrator", () => {
    // Common shape immediately after `close_session` flips status —
    // there's no in-progress session yet, but the most recent
    // completed entry's orchestrator is the correct recovery source
    // for a fresh start_session call.
    const state = {
      sessions: [
        {
          number: 1,
          status: "complete",
          orchestrator: {
            engine: "claude",
            provider: "anthropic",
            model: "claude-opus-4-7",
            effort: "high",
          },
        },
        { number: 2, status: "not-started" },
      ],
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: "claude-opus-4-7",
      effort: "high",
    });
  });

  test("returns undefined for missing model/effort strings (no 'unknown' fallback per T3)", () => {
    // Per Set 049 T3 the writer omits keys it cannot declare
    // authoritatively rather than substituting "unknown". The
    // recovery path mirrors that contract — a prior block with no
    // model/effort yields undefined/undefined, and the caller then
    // omits the corresponding CLI flag.
    const state = {
      orchestrator: {
        engine: "claude",
        provider: "anthropic",
      },
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: undefined,
      effort: undefined,
    });
  });

  test("returns undefined for empty-string model/effort (treated as omitted)", () => {
    const state = {
      orchestrator: {
        engine: "claude",
        provider: "anthropic",
        model: "",
        effort: "",
      },
    };
    assert.deepStrictEqual(invoker.recoverPriorClaudeModelEffort(state), {
      model: undefined,
      effort: undefined,
    });
  });
});

// ---------------------------------------------------------------------------
// Set 050 S3 — scanSchemaDrift + CURRENT_SCHEMA_VERSION
// ---------------------------------------------------------------------------

// Helper: write a minimal session-state.json with the given schemaVersion
// into a temp directory. Returns the workspaceRoot path.
function makeTmpWorkspace(sets: Array<{ slug: string; schemaVersion: number | null | "bad" }>): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-drift-test-"));
  const setsDir = path.join(root, "docs", "session-sets");
  fs.mkdirSync(setsDir, { recursive: true });
  for (const { slug, schemaVersion } of sets) {
    const setDir = path.join(setsDir, slug);
    fs.mkdirSync(setDir, { recursive: true });
    if (schemaVersion === "bad") {
      // corrupt file — not valid JSON
      fs.writeFileSync(path.join(setDir, "session-state.json"), "{ not json", "utf8");
    } else {
      const payload = schemaVersion === null
        ? { status: "complete" }
        : { schemaVersion, status: "complete" };
      fs.writeFileSync(
        path.join(setDir, "session-state.json"),
        JSON.stringify(payload),
        "utf8",
      );
    }
  }
  return root;
}

suite("claude-session-start-invoker — CURRENT_SCHEMA_VERSION", () => {
  suiteSetup(async () => {
    invoker = await loadInvoker();
  });

  test("CURRENT_SCHEMA_VERSION is a positive integer", () => {
    assert.ok(
      typeof invoker.CURRENT_SCHEMA_VERSION === "number" &&
        Number.isInteger(invoker.CURRENT_SCHEMA_VERSION) &&
        invoker.CURRENT_SCHEMA_VERSION > 0,
      `Expected CURRENT_SCHEMA_VERSION to be a positive integer, got ${invoker.CURRENT_SCHEMA_VERSION}`,
    );
  });
});

suite("claude-session-start-invoker — scanSchemaDrift", () => {
  suiteSetup(async () => {
    invoker = await loadInvoker();
  });

  test("returns null when all sets are at the current version", () => {
    const root = makeTmpWorkspace([
      { slug: "001-first", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
      { slug: "002-second", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
    ]);
    assert.strictEqual(invoker.scanSchemaDrift(root), null);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("returns a terse message when sets are at older versions", () => {
    const root = makeTmpWorkspace([
      { slug: "old-v2", schemaVersion: 2 },
      { slug: "old-v3", schemaVersion: 3 },
      { slug: "current", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
    ]);
    const msg = invoker.scanSchemaDrift(root);
    assert.ok(msg !== null, "Expected a drift message");
    assert.ok(
      msg.includes("[Dabbler]"),
      `Expected '[Dabbler]' prefix in: ${msg}`,
    );
    assert.ok(
      msg.includes("2 session-set(s)"),
      `Expected '2 session-set(s)' in: ${msg}`,
    );
    assert.ok(
      msg.includes("v2") && msg.includes("v3"),
      `Expected both v2 and v3 in: ${msg}`,
    );
    assert.ok(
      msg.includes("check_migrations"),
      `Expected 'check_migrations' in: ${msg}`,
    );
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("returns null when only one set is present at current version", () => {
    const root = makeTmpWorkspace([
      { slug: "only-current", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
    ]);
    assert.strictEqual(invoker.scanSchemaDrift(root), null);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("skips corrupt state files without crashing (fail-open)", () => {
    const root = makeTmpWorkspace([
      { slug: "corrupt", schemaVersion: "bad" },
      { slug: "current", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
    ]);
    // Both clean (corrupt skipped) or a drift message; must NOT throw.
    const msg = invoker.scanSchemaDrift(root);
    // corrupt file is skipped → 0 drift → null
    assert.strictEqual(msg, null);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("returns null when no session-sets directory exists (fail-open)", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-drift-empty-"));
    assert.strictEqual(invoker.scanSchemaDrift(root), null);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("skips files with missing schemaVersion field without counting as drift", () => {
    const root = makeTmpWorkspace([
      { slug: "no-version", schemaVersion: null },
      { slug: "current", schemaVersion: invoker.CURRENT_SCHEMA_VERSION },
    ]);
    // null schemaVersion → skipped, not drift
    assert.strictEqual(invoker.scanSchemaDrift(root), null);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test("drift message lists a single old version correctly (singular count)", () => {
    const root = makeTmpWorkspace([
      { slug: "old", schemaVersion: 3 },
    ]);
    const msg = invoker.scanSchemaDrift(root);
    assert.ok(msg !== null && msg.includes("1 session-set(s)"), `Got: ${msg}`);
    fs.rmSync(root, { recursive: true, force: true });
  });
});

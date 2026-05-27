// Set 049 S4 — Layer-2 coverage of the Claude Code SessionStart hook
// invoker shim's post-rip shape. The Set 033 / 036 chatSessionId +
// coordination assertions were dropped alongside the upstream rip-out;
// this file now covers the surviving exports:
//
//   - `parsePayload(raw)` — JSON.parse the hook payload, return `{}`
//     for empty / malformed input.
//   - `recoverPriorClaudeModelEffort(state)` — when the prior
//     orchestrator block is `engine: "claude", provider: "anthropic"`,
//     recover its `model` / `effort` for forwarding. Per the Set 049
//     T3 omit-null contract, the recovered values are `undefined` when
//     the prior block omitted them — no `"unknown"` fallback.
//
// The shim is plain Node (no vscode imports); the test loads it via
// dynamic import so the helper exports are available without firing
// `main()`. The chatSessionId / `extractSessionId` / fallback-to-
// "unknown" assertions from the pre-rip suite are gone — none of those
// behaviors survived the Set 049 S2 / S3 simplifications.

import * as assert from "assert";
import * as path from "path";
import { pathToFileURL } from "url";

interface InvokerExports {
  parsePayload: (raw: string) => unknown;
  recoverPriorClaudeModelEffort: (
    state: unknown,
  ) => { model: string | undefined; effort: string | undefined };
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

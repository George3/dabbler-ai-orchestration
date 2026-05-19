import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  detectInstalledOrchestrators,
  pickEmptyStateCta,
} from "../../providers/detectOrchestrators";

// Set 029 Session 5 — orchestrator-detection helper for the smart
// empty-state CTA. Drives priority order + MRU bias against synthetic
// HOME directories (~/.claude/, ~/.codex/) and the vscode-stub's
// extension registry.

interface StubVscode {
  extensions: { __installedExtensions: Set<string> };
}

// The stub vscode module is registered in `vscode-stub.js` and
// resolved by `require("vscode")`. Cast to access its mutable
// `__installedExtensions` set.
function getStubExtensions(): Set<string> {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const vscode = require("vscode") as unknown as StubVscode;
  return vscode.extensions.__installedExtensions;
}

function withScenario(
  opts: {
    claude?: boolean;
    codex?: boolean;
    gemini?: boolean;
    copilot?: boolean;
    mru?: unknown[];
  },
  fn: () => void,
): void {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-detect-"));
  const prevHome = process.env.HOME;
  const prevUserprofile = process.env.USERPROFILE;
  process.env.HOME = tmp;
  process.env.USERPROFILE = tmp;
  if (opts.claude) fs.mkdirSync(path.join(tmp, ".claude"), { recursive: true });
  if (opts.codex) fs.mkdirSync(path.join(tmp, ".codex"), { recursive: true });
  if (opts.mru) {
    fs.mkdirSync(path.join(tmp, ".dabbler"), { recursive: true });
    fs.writeFileSync(
      path.join(tmp, ".dabbler", "orchestrator-mru.json"),
      JSON.stringify(opts.mru, null, 2),
      "utf8",
    );
  }
  const installed = getStubExtensions();
  const previouslyInstalled = new Set(installed);
  installed.clear();
  if (opts.gemini) installed.add("Google.geminicodeassist");
  if (opts.copilot) installed.add("GitHub.copilot");
  try {
    fn();
  } finally {
    installed.clear();
    for (const id of previouslyInstalled) installed.add(id);
    if (prevHome === undefined) delete process.env.HOME;
    else process.env.HOME = prevHome;
    if (prevUserprofile === undefined) delete process.env.USERPROFILE;
    else process.env.USERPROFILE = prevUserprofile;
    try {
      fs.rmSync(tmp, { recursive: true, force: true });
    } catch {
      // best effort
    }
  }
}

suite("detectInstalledOrchestrators", () => {
  test("nothing installed → empty list", () => {
    withScenario({}, () => {
      assert.deepStrictEqual(detectInstalledOrchestrators().installed, []);
    });
  });

  test("priority order when no MRU bias: claude, codex, gemini, copilot", () => {
    withScenario({ claude: true, codex: true, gemini: true, copilot: true }, () => {
      assert.deepStrictEqual(detectInstalledOrchestrators().installed, [
        "anthropic",
        "openai",
        "google",
        "github",
      ]);
    });
  });

  test("MRU bias surfaces most-recent installed provider first", () => {
    // Operator's most-recent override was Gemini; Gemini should
    // surface ahead of the priority-order default (claude).
    withScenario(
      {
        claude: true,
        gemini: true,
        mru: [
          {
            provider: "google",
            model: "gemini-2.5-pro",
            effort: "high",
            thinking: false,
          },
          {
            provider: "anthropic",
            model: "claude-opus-4-7",
            effort: "high",
            thinking: true,
          },
        ],
      },
      () => {
        assert.deepStrictEqual(detectInstalledOrchestrators().installed, [
          "google",
          "anthropic",
        ]);
      },
    );
  });

  test("MRU entries for uninstalled providers are ignored", () => {
    // Operator's MRU mentions Copilot, but Copilot isn't installed —
    // detection should fall back to priority order over the actually
    // installed Codex.
    withScenario(
      {
        codex: true,
        mru: [
          {
            provider: "github",
            model: "gpt-4o",
            effort: "medium",
            thinking: false,
          },
        ],
      },
      () => {
        assert.deepStrictEqual(detectInstalledOrchestrators().installed, [
          "openai",
        ]);
      },
    );
  });
});

suite("pickEmptyStateCta", () => {
  test("returns null when no orchestrators installed (caller falls back to default)", () => {
    withScenario({}, () => {
      assert.strictEqual(pickEmptyStateCta(), null);
    });
  });

  test("Claude-installed scenario → Claude Code hook installer CTA", () => {
    withScenario({ claude: true }, () => {
      const cta = pickEmptyStateCta();
      assert.ok(cta);
      assert.strictEqual(cta?.commandId, "dabbler.installOrchestratorHook.claudeCode");
      assert.match(cta?.label ?? "", /Claude/);
    });
  });

  test("Codex-only scenario → Codex preset CTA with prefillProvider arg", () => {
    withScenario({ codex: true }, () => {
      const cta = pickEmptyStateCta();
      assert.ok(cta);
      assert.strictEqual(cta?.commandId, "dabbler.setOrchestrator");
      assert.deepStrictEqual(cta?.args, [{ prefillProvider: "openai" }]);
    });
  });

  test("Gemini-only scenario → Gemini shim CTA", () => {
    withScenario({ gemini: true }, () => {
      const cta = pickEmptyStateCta();
      assert.ok(cta);
      assert.strictEqual(cta?.commandId, "dabbler.installOrchestratorHook.gemini");
    });
  });
});

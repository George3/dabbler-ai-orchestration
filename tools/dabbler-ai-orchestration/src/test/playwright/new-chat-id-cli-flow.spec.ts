// Set 036 Session 5 — Layer-3 Playwright coverage for the
// Q1-fallback CLI: `python -m ai_router.new_chat_id` mints a UUID v4
// for orchestrators with no native per-chat session-id surface
// (Codex CLI, Gemini Code Assist, GitHub Copilot, manual Lightweight
// tier). Operator workflow:
//
//   $ eval "$(python -m ai_router.new_chat_id --export --shell bash)"
//   $ python -m ai_router.start_session ... [--chat-session-id "$CHAT_SESSION_ID"]
//
// The CLI is idempotent against an existing non-empty $CHAT_SESSION_ID
// — repeated invocations from the same shell emit the same identifier
// so the operator never accidentally re-mints mid-workflow.
//
// This spec exercises three legs at the process boundary:
//   - plain mode mints a valid-shape UUID v4
//   - the minted UUID, set as $CHAT_SESSION_ID, flows into the
//     orchestrator block when start_session is invoked WITHOUT
//     --chat-session-id (env-fallback branch in _resolve_chat_session_id)
//   - idempotency: a second invocation of the CLI in the same env
//     returns the same UUID rather than re-minting.
//
// Together these prove the spec's "manual flow via the fallback CLI"
// claim that the per-chat ID survives the round-trip from CLI mint
// to writer-recorded state field.

import { expect, test } from "@playwright/test";
import * as cp from "child_process";
import * as path from "path";
import {
  attemptStartSession,
  cleanupTmpDir,
  makeSet,
  makeTmpDir,
  readStateFile,
} from "./electronLaunch";

const PYTHON = process.env.HARNESS_PYTHON || "python";
// Repo root needed so `python -m ai_router.new_chat_id` can resolve
// the `ai_router` package when the spec runs from the extension
// subdirectory. Mirrors the REPO_ROOT derivation in electronLaunch.ts
// (extension lives at <repo>/tools/dabbler-ai-orchestration; from
// src/test/playwright/ that's five parent hops: playwright → test →
// src → dabbler-ai-orchestration → tools → repo root).
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..");

// Mirror electronLaunch's filtered-env hygiene so a polluted parent
// shell can't redirect imports inside the CLI subprocess. Kept local
// to this spec rather than exported to avoid widening the helper's
// API surface for a single caller.
function _filteredEnv(extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const passthrough = [
    "PATH",
    "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "WINDIR",
    "HOME", "USERPROFILE",
    "TMP", "TEMP", "TMPDIR",
    "LANG", "LC_ALL", "LC_CTYPE",
    "APPDATA", "LOCALAPPDATA",
  ];
  const out: NodeJS.ProcessEnv = {};
  for (const k of passthrough) {
    const v = process.env[k];
    if (v !== undefined) out[k] = v;
  }
  out.PYTHONIOENCODING = "utf-8";
  out.PYTHONUTF8 = "1";
  for (const [k, v] of Object.entries(extra)) out[k] = v;
  return out;
}

const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function mintChatSessionId(env: NodeJS.ProcessEnv = _filteredEnv()): string {
  const proc = cp.spawnSync(PYTHON, ["-m", "ai_router.new_chat_id"], {
    encoding: "utf8",
    timeout: 30_000,
    cwd: REPO_ROOT,
    env,
  });
  if (proc.status !== 0) {
    throw new Error(
      `new_chat_id mint failed (exit ${proc.status}): ` +
        `stdout=${proc.stdout} stderr=${proc.stderr}`,
    );
  }
  return proc.stdout.trim();
}

interface PerTest {
  tmpPath?: string;
}

function teardown(per: PerTest): void {
  if (per.tmpPath) {
    try { cleanupTmpDir(per.tmpPath); } catch { /* opportunistic */ }
  }
}

test("new_chat_id plain mode prints a UUID v4", () => {
  const id = mintChatSessionId();
  expect(id).toMatch(UUID_V4_RE);
});

test("minted UUID flows through $CHAT_SESSION_ID env into the orchestrator block on start_session", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-newchatid-flow");
    const h = makeSet(per.tmpPath, "036-newchatid-flow", 2);

    // Step 1: mint the UUID via the fallback CLI.
    const chatId = mintChatSessionId();
    expect(chatId).toMatch(UUID_V4_RE);

    // Step 2: spawn start_session with $CHAT_SESSION_ID set (no
    // --chat-session-id arg). This exercises the env-fallback branch
    // of _resolve_chat_session_id (Set 036 Session 1) — the path a
    // bash/PowerShell/fish operator hits after running the
    // `eval "$(... --export ...)"` workflow from the wizard toast.
    const r = attemptStartSession(
      h,
      1,
      { engine: "codex", provider: "openai", model: "gpt-5", effort: "medium" },
      { env: { CHAT_SESSION_ID: chatId } },
    );
    expect(r.exit).toBe(0);

    // Step 3: state file records the minted UUID strictly.
    const state = readStateFile(h) as {
      orchestrator?: {
        engine?: string;
        provider?: string;
        chatSessionId?: string;
      };
    };
    expect(state.orchestrator?.engine).toBe("codex");
    expect(state.orchestrator?.provider).toBe("openai");
    expect(state.orchestrator?.chatSessionId).toBe(chatId);
  } finally {
    teardown(per);
  }
});

test("new_chat_id is idempotent against an existing non-empty $CHAT_SESSION_ID", () => {
  // A first mint generates a fresh UUID; a second invocation in the
  // same shell (env carries the first UUID forward) re-emits the same
  // value. This is the workflow protection that lets operators safely
  // re-run the CLI mid-session without re-minting and losing the
  // composite identity their orchestrator-block already records.
  const first = mintChatSessionId();
  expect(first).toMatch(UUID_V4_RE);
  const second = mintChatSessionId(_filteredEnv({ CHAT_SESSION_ID: first }));
  expect(second).toBe(first);
});

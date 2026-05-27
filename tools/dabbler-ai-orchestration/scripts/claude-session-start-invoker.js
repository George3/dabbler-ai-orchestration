#!/usr/bin/env node
// claude-session-start-invoker.js
//
// Set 033 S3 (H1: hooks become invokers, not writers) +
// Set 049 S3 (post-rip-out simplification).
//
// Successor to the retired `write-orchestrator-marker.js` script for
// the Claude Code SessionStart hook path. Per the Set 033 H1 verdict,
// hooks must NOT write the orchestrator block directly — they invoke
// the canonical writer (`python -m ai_router.start_session`) which
// writes `session-state.json`.
//
// Behavior (Set 049):
//   1. Read Claude Code's SessionStart hook payload from stdin (JSON)
//      for the `cwd` field. Other payload fields are ignored.
//   2. Walk up from `cwd` to locate `docs/session-sets/`. Find the
//      single `status: "in-progress"` subdirectory.
//   3. If zero or multiple in-progress sets: silent no-op, exit 0.
//   4. Read the in-progress set's existing orchestrator block. When
//      the prior block is already `engine: "claude", provider:
//      "anthropic"`, recover its `model` / `effort` for forwarding.
//      Per the T3 omit-null contract, fields the hook cannot declare
//      authoritatively are simply omitted from the CLI call — no
//      `"unknown"` fallback.
//   5. Spawn `python -m ai_router.start_session` with
//      `--engine claude --provider anthropic` plus `--model` /
//      `--effort` only when a value was recovered.
//   6. On non-zero exit or spawn failure, log stderr; always exit 0
//      so the hook chain isn't broken.
//
// Set 049 removed:
//   - `--chat-session-id` forwarding (the H4 composite identity is
//     gone; start_session no longer consumes the flag for coordination,
//     and the writer's accept-with-warning path swallows any legacy
//     consumer-repo invokers that still send it).
//   - `EXIT_CHECKOUT_CONFLICT` handling (H3 hard-coordination retired).
//   - `emitConflictRecord` + `~/.dabbler/checkout-conflicts/` directory
//     writes (CheckoutPollService has no records to consume post-rip).
//   - `DABBLER_ENFORCE_CHECKOUT_COORDINATION` env-var gating (the
//     enforcement layer no longer exists, so the gate has nothing to
//     branch on).
//
// No CLI arguments. The mode is implicit (this script is only attached
// to SessionStart).

const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const CLAUDE_ENGINE = "claude";
const CLAUDE_PROVIDER = "anthropic";

function readStdinSync() {
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function parsePayload(raw) {
  if (!raw || !raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

// Walk up from `startCwd` looking for `docs/session-sets/`. Return the
// resolved in-progress set as { workspaceRoot, slug, setDir }, or
// { reason } on failure. Single in-progress required; fail-closed on
// zero or multiple matches (mirrors the retired marker writer's
// resolver semantics).
function walkUpResolveSet(startCwd) {
  let current = path.resolve(startCwd);
  while (true) {
    const candidate = path.join(current, "docs", "session-sets");
    let exists = false;
    try {
      exists = fs.statSync(candidate).isDirectory();
    } catch {
      // not present at this level; fall through to parent
    }
    if (exists) {
      let entries;
      try {
        entries = fs.readdirSync(candidate, { withFileTypes: true });
      } catch {
        return { reason: "session-sets-unreadable" };
      }
      const inProgress = [];
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const statePath = path.join(candidate, entry.name, "session-state.json");
        try {
          const raw = fs.readFileSync(statePath, "utf8");
          const state = JSON.parse(raw);
          if (state && state.status === "in-progress") {
            inProgress.push({ slug: entry.name, setDir: path.join(candidate, entry.name), state });
          }
        } catch {
          // skip — unreadable / missing / invalid JSON
        }
      }
      if (inProgress.length === 1) {
        return {
          workspaceRoot: current,
          slug: inProgress[0].slug,
          setDir: inProgress[0].setDir,
          state: inProgress[0].state,
        };
      }
      if (inProgress.length === 0) return { reason: "no-in-progress-set" };
      return { reason: "multiple-in-progress-sets" };
    }
    const parent = path.dirname(current);
    if (parent === current) return { reason: "no-docs-session-sets" };
    current = parent;
  }
}

// Read the existing orchestrator block off the in-progress state.
// When the prior block is already claude+anthropic, recover model +
// effort for forwarding to start_session. Per Set 049 T3 (omit-null
// writer contract), the recovered values are returned as undefined
// when the prior block omitted them — the caller then omits the
// corresponding CLI flag rather than substituting "unknown".
//
// Set 049 simplification: holder identity is engine + provider only
// (chatSessionId composite retired). Two distinct Claude chats writing
// to the same session set are no longer distinguished as different
// holders.
function recoverPriorClaudeModelEffort(state) {
  // The orchestrator block has moved location across schema versions.
  // In v4 it lives on the active `sessions[]` entry; pre-v4 it was a
  // top-level field. Read whichever is available — the writer accepts
  // either input and emits canonical v4 on the next write.
  let block = null;
  if (state && Array.isArray(state.sessions)) {
    const active = state.sessions.find((s) => s && s.status === "in-progress");
    if (active && active.orchestrator) {
      block = active.orchestrator;
    } else {
      // Fall back to the most-recently-completed entry's orchestrator
      // — common shape just after `close_session` flips status. Best-
      // effort; a fresh start with no prior holder simply yields null.
      for (let i = state.sessions.length - 1; i >= 0; i -= 1) {
        const s = state.sessions[i];
        if (s && s.orchestrator) {
          block = s.orchestrator;
          break;
        }
      }
    }
  }
  if (!block && state && state.orchestrator) {
    block = state.orchestrator;
  }
  if (!block) return { model: undefined, effort: undefined };
  if (block.engine !== CLAUDE_ENGINE) return { model: undefined, effort: undefined };
  if (block.provider !== CLAUDE_PROVIDER) return { model: undefined, effort: undefined };
  const model = typeof block.model === "string" && block.model.length > 0 ? block.model : undefined;
  const effort = typeof block.effort === "string" && block.effort.length > 0 ? block.effort : undefined;
  return { model, effort };
}

function spawnStartSession(setDir, model, effort) {
  const args = [
    "-m", "ai_router.start_session",
    "--session-set-dir", setDir,
    "--engine", CLAUDE_ENGINE,
    "--provider", CLAUDE_PROVIDER,
  ];
  if (typeof model === "string" && model.length > 0) {
    args.push("--model", model);
  }
  if (typeof effort === "string" && effort.length > 0) {
    args.push("--effort", effort);
  }
  // Inherit env (PATH must reach a python interpreter with
  // dabbler-ai-router importable). No working-directory override:
  // start_session takes the session-set dir as an absolute arg.
  return cp.spawnSync("python", args, {
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
  });
}

function main() {
  const payload = parsePayload(readStdinSync());
  const startCwd = (typeof payload.cwd === "string" && payload.cwd)
    ? payload.cwd
    : process.cwd();

  const resolution = walkUpResolveSet(startCwd);
  if (!resolution.slug) {
    // Fail-closed (no in-progress set, or ambiguous, or no
    // docs/session-sets/ on the walk-up). Silent exit 0 — the hook
    // chain continues; nothing for us to claim.
    process.exit(0);
  }

  const { model, effort } = recoverPriorClaudeModelEffort(resolution.state);

  const result = spawnStartSession(resolution.setDir, model, effort);

  if (result.error) {
    process.stderr.write(
      `claude-session-start-invoker: spawn failed: ${result.error.message}\n`,
    );
    process.exit(0);
  }

  if (result.status !== 0) {
    if (result.stderr) {
      process.stderr.write(
        `claude-session-start-invoker: start_session exit ${result.status}:\n${result.stderr}`,
      );
    } else {
      process.stderr.write(
        `claude-session-start-invoker: start_session exit ${result.status}\n`,
      );
    }
    process.exit(0);
  }

  process.exit(0);
}

// Module exports for unit tests. When the file is invoked as a script
// (the SessionStart hook path), `require.main === module` is true and
// main() runs. When the file is require()-ed from a test, only the
// helpers are exposed and main()'s side effects are skipped.
if (require.main === module) {
  main();
} else {
  module.exports = { parsePayload, recoverPriorClaudeModelEffort };
}

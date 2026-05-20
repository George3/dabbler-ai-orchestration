#!/usr/bin/env node
// claude-session-start-invoker.js
//
// Set 033 Session 3 (H1: hooks become invokers, not writers).
//
// Successor to the retired `write-orchestrator-marker.js` script for the
// Claude Code SessionStart hook path. The previous script wrote the
// per-session-set `.dabbler/orchestrator.json` marker directly; per the
// audit-locked H1 verdict (proposal-addendum §9), hooks must NOT write
// the orchestrator block — they invoke the canonical writer
// (`python -m ai_router.start_session`) which writes
// `session-state.json` under the H3 hard-coordination rules.
//
// Behavior:
//   1. Read Claude Code's SessionStart hook payload from stdin (JSON).
//      The payload supplies `cwd` (the workspace path Claude is running
//      in); other fields are ignored.
//   2. Walk up from `cwd` to locate `docs/session-sets/`. Find the
//      single `status: "in-progress"` subdirectory.
//   3. If zero or multiple in-progress sets: silent no-op, exit 0.
//      (Same fail-closed posture as the retired writer.)
//   4. Read the in-progress set's existing `orchestrator` block. When
//      the existing holder is already `claude + anthropic` (per H4
//      identity), preserve its `model` + `effort` so the
//      same-holder re-attach (S1 writer behavior) bumps only
//      `lastActivityAt` without degrading the model/effort fields.
//   5. Spawn `python -m ai_router.start_session` with the resolved
//      args. The writer enforces H3 hard coordination: if a different
//      engine+provider holds the check-out, it exits 4 (conflict);
//      the shim writes a short note to stderr (visible in Claude Code's
//      hook log) and exits 0 so the hook chain isn't broken.
//
// Exit code is always 0 unless an unrecoverable internal error occurs
// (e.g., spawn fails entirely). This matches the retired writer's
// "best-effort, never block the hook chain" contract.
//
// No CLI arguments. The mode is implicit (this script is only attached
// to SessionStart). Future hook variants (e.g., UserPromptSubmit) can
// either ship their own thin shim or pass a `--mode` flag — the
// previous combined-helper pattern was retired with H1.

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
// { reason } on failure. Matches the resolver semantic that the
// retired marker writer used (single in-progress required; fail-closed).
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

// Per H4 + R3: existing holder is "same" iff engine + provider match.
// Model and effort are mutable fields; preserving them when claude is
// already the holder avoids the SessionStart hook (which has no model
// signal) overwriting a more-accurate model recorded by the manual
// quickpick or another writer.
function preserveExistingClaude(state) {
  const o = state && state.orchestrator;
  if (!o) return null;
  if (o.engine !== CLAUDE_ENGINE) return null;
  if (o.provider !== CLAUDE_PROVIDER) return null;
  return {
    model: typeof o.model === "string" && o.model.length > 0 ? o.model : "unknown",
    effort: typeof o.effort === "string" && o.effort.length > 0 ? o.effort : "unknown",
  };
}

function spawnStartSession(setDir, model, effort) {
  // No `--force`: the SessionStart hook never overrides an existing
  // different-holder check-out (that's the operator's explicit decision
  // via "Release Check-Out" or `start_session --force` on the CLI).
  // If a conflict arises, start_session exits 4; we surface the stderr
  // to Claude Code's hook log and continue.
  const args = [
    "-m", "ai_router.start_session",
    "--session-set-dir", setDir,
    "--engine", CLAUDE_ENGINE,
    "--provider", CLAUDE_PROVIDER,
    "--model", model,
    "--effort", effort,
  ];
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

  const preserved = preserveExistingClaude(resolution.state);
  // SessionStart has no model signal in its payload; default to the
  // last-recorded model when claude already holds the slot, else
  // "unknown" (S1 writer accepts it; H4 identity is what matters).
  const model = preserved ? preserved.model : "unknown";
  const effort = preserved ? preserved.effort : "unknown";

  const result = spawnStartSession(resolution.setDir, model, effort);

  if (result.error) {
    // spawnSync failure (python not on PATH, etc.). Surface to stderr
    // for the hook log, exit 0 so we don't break Claude's hook chain.
    process.stderr.write(
      `claude-session-start-invoker: spawn failed: ${result.error.message}\n`,
    );
    process.exit(0);
  }

  if (result.status !== 0) {
    // EXIT_CHECKOUT_CONFLICT (4) is the H3 refusal — log the holder
    // message and exit 0. Any other non-zero (boundary violations,
    // usage errors) also surfaces to stderr and exits 0; the writer
    // is the source of truth for state, the hook is best-effort
    // notification.
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

main();

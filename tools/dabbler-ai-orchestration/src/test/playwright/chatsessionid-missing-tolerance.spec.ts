// Set 036 Session 5 — Layer-3 Playwright coverage for the Q5
// "tolerant-on-read, strict-on-write" semantics of the chatSessionId
// field. Two cases the start_session writer must handle:
//
//   (a) Legacy state file — pre-Set-036 writer left no chatSessionId
//       field in the orchestrator block. A Set-036+ chat with any
//       chatSessionId can re-attach (same engine + provider) without
//       refusal; the field gets populated on the first new write.
//
//   (b) Set-036 null state — a Set-036 writer that didn't have a
//       chatSessionId at the time of write left the field present
//       and null. Same tolerance: re-attach succeeds; the first
//       write that supplies a non-null chatSessionId populates the
//       field strictly.
//
// After population, subsequent attempts from a DIFFERENT chatSessionId
// are refused per the strict-on-write contract — this is the
// "strict-on-subsequent" leg the spec calls out.

import { expect, test } from "@playwright/test";
import {
  attemptStartSession,
  cleanupTmpDir,
  makeSet,
  makeTmpDir,
  readStateFile,
  seedOrchestratorBlock,
  startSession,
} from "./electronLaunch";

interface PerTest {
  tmpPath?: string;
}

function teardown(per: PerTest): void {
  if (per.tmpPath) {
    try { cleanupTmpDir(per.tmpPath); } catch { /* opportunistic */ }
  }
}

test("legacy state (no chatSessionId field) tolerates a new chat and populates the field on first write", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-legacy");
    const h = makeSet(per.tmpPath, "036-csid-legacy", 2);
    startSession(h, 1);
    // Seed the orchestrator block WITHOUT a chatSessionId key — the
    // shape a pre-Set-036 writer left on disk. seedOrchestratorBlock's
    // "in" check on the overrides preserves the omitted-key shape;
    // re-reading proves no chatSessionId key exists.
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
      // chatSessionId intentionally omitted — legacy shape.
    });
    const seeded = readStateFile(h) as {
      orchestrator?: Record<string, unknown>;
    };
    // Sanity-check the legacy shape held by the writer that left it.
    expect(seeded.orchestrator).toBeTruthy();
    expect("chatSessionId" in (seeded.orchestrator ?? {})).toBe(false);

    // Chat C re-attaches with a chatSessionId. Same engine + provider,
    // legacy state's chatSessionId-key-absent branch → tolerated.
    const chatIdC = "CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC";
    const r = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatIdC },
    );
    expect(r.exit).toBe(0);

    // First new write populates the field strictly.
    const after = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string };
    };
    expect(after.orchestrator?.chatSessionId).toBe(chatIdC);
  } finally {
    teardown(per);
  }
});

test("Set-036 null state tolerates a new chat and populates the field on first write", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-null");
    const h = makeSet(per.tmpPath, "036-csid-null", 2);
    startSession(h, 1);
    // Seed with chatSessionId present and null — the Set-036 writer
    // shape when no ID was available at write time (e.g., Claude
    // chat without a hook-payload session_id, or Codex/Gemini/Copilot
    // operator who skipped the new_chat_id CLI workflow).
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
      chatSessionId: null,
    });
    const seeded = readStateFile(h) as {
      orchestrator?: { chatSessionId?: unknown };
    };
    expect(seeded.orchestrator).toBeTruthy();
    expect(seeded.orchestrator?.chatSessionId).toBeNull();

    const chatIdD = "DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD";
    const r = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatIdD },
    );
    expect(r.exit).toBe(0);
    const after = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string };
    };
    expect(after.orchestrator?.chatSessionId).toBe(chatIdD);
  } finally {
    teardown(per);
  }
});

test("post-population: a different chatSessionId is refused strictly", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-strict");
    const h = makeSet(per.tmpPath, "036-csid-strict", 2);
    startSession(h, 1);
    // Seed legacy shape, populate via chat C, then attempt from chat
    // E. The H3 + H4 strict branch refuses the second chat because
    // the prior block now has a non-null string chatSessionId.
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
      // chatSessionId omitted (legacy).
    });
    const chatIdC = "CCCCCCCC-CCCC-CCCC-CCCC-FFFFFFFFFFFF";
    const populate = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatIdC },
    );
    expect(populate.exit).toBe(0);
    const populated = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string };
    };
    expect(populated.orchestrator?.chatSessionId).toBe(chatIdC);

    const chatIdE = "EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE";
    const r = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatIdE },
    );
    expect(r.exit).toBe(4);
    expect(r.stderr).toContain(chatIdC);
    expect(r.stderr).toContain(chatIdE);
    expect(r.stderr).toContain("--force");

    // State unchanged: still holds chat C.
    const final = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string };
    };
    expect(final.orchestrator?.chatSessionId).toBe(chatIdC);
  } finally {
    teardown(per);
  }
});

// Set 036 Session 5 — Layer-3 Playwright coverage for the
// chatSessionId-mismatch takeover end-to-end at the process boundary.
//
// Two-chat-instance scenario (per spec):
//   - chat A checks out a session with chatSessionId A1
//   - chat B (different chatSessionId B1, same engine + provider)
//     attempts to claim the same session → start_session refuses with
//     EXIT_CHECKOUT_CONFLICT (4) and stderr names both chatSessionIds
//     via the H4-composite "chatSessionId mismatch" preamble
//   - chat B re-runs with --force → exit 0; state file's chatSessionId
//     is now B1; ~/.dabbler/orchestrator-writer.log has a single
//     force-override line carrying both chatSessionIds + both engines
//     + provider + session number.
//
// The takeover MODAL itself (the VS Code surface the operator clicks
// Take Over on) is covered at Layer 2 by chatSessionMismatchModal.test.ts
// + checkOutOrchestratorChatSessionMismatch.test.ts + the
// CheckoutPollService chatSessionId-mismatch-routes-to-modal suite
// (all shipped in Session 4). This Layer 3 spec exercises the writer-
// side process boundary that the modal's Take Over button ultimately
// invokes, mirroring the established pattern in checkout-conflict.spec.ts
// where the deeper palette/modal interaction is acknowledged-brittle
// and deferred to Layer 2.

import { expect, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
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

test("chatSessionId mismatch (same engine + provider) refuses with chatSessionId preamble naming both IDs", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-refusal");
    const h = makeSet(per.tmpPath, "036-csid-refusal", 2);
    startSession(h, 1);
    // Seed in-progress as Claude Code chat A. Engine + provider match
    // the would-be holder below; only the chatSessionId differs — the
    // discriminator the Q3-locked modal/CLI prompt fires on.
    const chatIdA = "00000000-0000-0000-0000-AAAAAAAAAAAA";
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
      chatSessionId: chatIdA,
    });

    const chatIdB = "00000000-0000-0000-0000-BBBBBBBBBBBB";
    const r = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatIdB },
    );

    // EXIT_CHECKOUT_CONFLICT == 4. The chatSessionId branch routes
    // through the same exit; the difference is the preamble line that
    // the extension's modal-router predicate keys on (and that
    // start_session emits unconditionally when both stdin AND stderr
    // are TTYs — but here we're non-interactive, so the operator just
    // sees the plain refusal text).
    expect(r.exit).toBe(4);

    // Holder identity in the refusal text (both chatSessionIds named).
    expect(r.stderr).toContain("claude");
    expect(r.stderr).toContain("anthropic");
    expect(r.stderr).toContain(chatIdA);
    expect(r.stderr).toContain(chatIdB);
    // H4 composite label format: "chatSessionId=<value>"
    expect(r.stderr).toContain(`chatSessionId=${chatIdA}`);
    expect(r.stderr).toContain(`chatSessionId=${chatIdB}`);
    // H3's two named release paths.
    expect(r.stderr).toContain("--force");
    expect(r.stderr).toContain("Release Check-Out");

    // No mutation: the seeded chatSessionId still holds.
    const state = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string; engine?: string };
    };
    expect(state.orchestrator?.engine).toBe("claude");
    expect(state.orchestrator?.chatSessionId).toBe(chatIdA);
  } finally {
    teardown(per);
  }
});

test("--force overrides the chatSessionId mismatch and rewrites the state to the new chat", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-force");
    const h = makeSet(per.tmpPath, "036-csid-force", 2);
    startSession(h, 1);
    const chatIdA = "11111111-1111-1111-1111-AAAAAAAAAAAA";
    seedOrchestratorBlock(h, {
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
      chatSessionId: chatIdA,
      checkedOutAt: "2026-05-20T08:00:00-04:00",
      lastActivityAt: "2026-05-20T08:00:00-04:00",
    });

    // Redirect ~/.dabbler/orchestrator-writer.log to a tmpdir HOME so
    // the audit-trail assertion stays hermetic.
    const homeOverride = path.join(per.tmpPath!, "fake-home");
    fs.mkdirSync(homeOverride, { recursive: true });
    const logPath = path.join(homeOverride, ".dabbler", "orchestrator-writer.log");

    const chatIdB = "11111111-1111-1111-1111-BBBBBBBBBBBB";
    const r = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { force: true, homeOverride, chatSessionId: chatIdB },
    );

    expect(r.exit).toBe(0);

    // State now records chat B — same engine + provider, new
    // chatSessionId; checkedOutAt rewritten to "now" because H4
    // identity changed (chat A's timestamp is gone).
    const state = readStateFile(h) as {
      orchestrator?: {
        engine?: string;
        provider?: string;
        chatSessionId?: string;
        checkedOutAt?: string;
        lastActivityAt?: string;
      };
    };
    expect(state.orchestrator?.engine).toBe("claude");
    expect(state.orchestrator?.provider).toBe("anthropic");
    expect(state.orchestrator?.chatSessionId).toBe(chatIdB);
    expect(state.orchestrator?.checkedOutAt).not.toBe("2026-05-20T08:00:00-04:00");
    expect(state.orchestrator?.lastActivityAt).toBe(state.orchestrator?.checkedOutAt);

    // Writer log: single force-override line naming both holders.
    expect(fs.existsSync(logPath)).toBe(true);
    const log = fs.readFileSync(logPath, "utf-8");
    expect(log).toContain("force-override");
    expect(log).toContain("session=1");
    expect(log).toContain("claude");
    expect(log).toContain("anthropic");
    // Both chatSessionIds present in the audit line so a future
    // observability surface can correlate the handoff to the chats.
    expect(log).toContain(chatIdA);
    expect(log).toContain(chatIdB);
    expect(log).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  } finally {
    teardown(per);
  }
});

test("same chatSessionId re-attach (same engine + provider) preserves checkedOutAt", async () => {
  const per: PerTest = {};
  try {
    per.tmpPath = makeTmpDir("dabbler-pw-csid-reattach");
    const h = makeSet(per.tmpPath, "036-csid-reattach", 2);

    const chatId = "22222222-2222-2222-2222-RRRRRRRRRRRR";
    // First start: fresh claim from chat with chatSessionId.
    const first = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatId },
    );
    expect(first.exit).toBe(0);
    const after1 = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string; checkedOutAt?: string; lastActivityAt?: string };
    };
    expect(after1.orchestrator?.chatSessionId).toBe(chatId);
    const seededCheckedOutAt = after1.orchestrator?.checkedOutAt;
    expect(typeof seededCheckedOutAt).toBe("string");

    // Same chatSessionId calls again. checkedOutAt MUST be unchanged;
    // lastActivityAt MUST move forward. Wall-clock tick gap covers
    // coarse-resolution clocks (mirror of checkout-conflict.spec.ts).
    await new Promise((r) => setTimeout(r, 1100));

    const second = attemptStartSession(
      h,
      1,
      { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
      { chatSessionId: chatId },
    );
    expect(second.exit).toBe(0);
    const after2 = readStateFile(h) as {
      orchestrator?: { chatSessionId?: string; checkedOutAt?: string; lastActivityAt?: string };
    };
    expect(after2.orchestrator?.chatSessionId).toBe(chatId);
    expect(after2.orchestrator?.checkedOutAt).toBe(seededCheckedOutAt);
    expect(
      String(after2.orchestrator?.lastActivityAt) >
        String(after1.orchestrator?.lastActivityAt),
    ).toBe(true);
  } finally {
    teardown(per);
  }
});

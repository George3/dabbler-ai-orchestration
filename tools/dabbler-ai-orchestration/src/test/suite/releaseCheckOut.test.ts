import * as assert from "assert";
import { describeHolder } from "../../commands/releaseCheckOut";
import type { InProgressSet } from "../../commands/checkOutOrchestrator";

// Set 033 Session 3 — `dabbler.releaseCheckOut` is the H3-named
// release path (alongside `start_session --force` on the CLI). The
// VS Code-mediated flow is mostly a confirmation prompt + delegation
// to the renamed `dabbler.checkOutOrchestrator` quickpick, so the
// pure-logic surface worth unit-testing is the holder-rendering
// helper that feeds the confirmation modal.

function fakeSet(
  orchestrator: InProgressSet["state"]["orchestrator"],
  slug: string = "033-orchestrator-checkout-checkin-implementation",
): InProgressSet {
  return {
    slug,
    setDir: `/x/docs/session-sets/${slug}`,
    state: {
      currentSession: 3,
      orchestrator,
    },
  };
}

suite("describeHolder", () => {
  test("renders engine + provider + model when all three present", () => {
    const set = fakeSet({
      engine: "claude",
      provider: "anthropic",
      model: "claude-opus-4-7",
      effort: "high",
    });
    assert.strictEqual(describeHolder(set), "claude + anthropic (claude-opus-4-7)");
  });

  test("omits the model parenthetical when model is absent", () => {
    const set = fakeSet({
      engine: "codex",
      provider: "openai",
    });
    assert.strictEqual(describeHolder(set), "codex + openai");
  });

  test("renders '?' placeholders when engine or provider is missing", () => {
    const set = fakeSet({
      model: "gpt-5-4",
    });
    assert.strictEqual(describeHolder(set), "? + ? (gpt-5-4)");
  });

  test("returns 'no current holder' when orchestrator is null", () => {
    const set = fakeSet(null);
    assert.strictEqual(describeHolder(set), "no current holder");
  });
});

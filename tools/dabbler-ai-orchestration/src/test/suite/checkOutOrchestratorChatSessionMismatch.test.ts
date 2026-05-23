import * as assert from "assert";
import {
  ManualChatMismatchResult,
  maybeShowChatSessionMismatchOnManualCheckout,
  type InProgressSet,
  type OrchestratorTuple,
} from "../../commands/checkOutOrchestrator";
import {
  MODAL_CANCEL,
  MODAL_READ_ONLY,
  MODAL_TAKE_OVER,
} from "../../providers/chatSessionMismatchModal";

// Set 036 Session 4 — Round B Major fix regression test.
//
// `dabbler.checkOutOrchestrator` (the manual Check Out As… command)
// needs the same Q3 takeover modal as CheckoutPollService when the
// would-be holder's tuple has the same engine+provider as the held
// orchestrator but the held block recorded a chatSessionId (manual
// checkout writes chatSessionId=null, so the mismatch is "prior
// string vs new null" under start_session's strict H3 branch).
// Without this routing, the dispatch falls through to a generic
// "Check-out failed (exit 4)" error toast and the operator never
// sees the three-action affordance the audit-locked Q3 verdict
// requires.

function makeTuple(): OrchestratorTuple {
  return {
    provider: "anthropic",
    model: "claude-opus-4-7",
    effort: "high",
    thinking: true,
  };
}

function makeSet(
  orchestrator: InProgressSet["state"]["orchestrator"],
): InProgressSet {
  return {
    slug: "099-fixture",
    setDir: "/repo/docs/session-sets/099-fixture",
    state: {
      currentSession: 1,
      orchestrator,
    },
  };
}

function fakeIntents() {
  const flagged = new Set<string>();
  return {
    setReadOnly: (p: string) => {
      flagged.add(p);
    },
    flagged,
  };
}

suite("maybeShowChatSessionMismatchOnManualCheckout (Round B Major regression)", () => {
  test("no orchestrator block => no-mismatch (caller proceeds to engine+provider path)", async () => {
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet(null),
    );
    assert.strictEqual(result.kind, "no-mismatch");
  });

  test("different engine => no-mismatch (caller handles via maybeConfirmForceOverride)", async () => {
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "codex", provider: "openai", chatSessionId: "abc-123" }),
    );
    assert.strictEqual(result.kind, "no-mismatch");
  });

  test("different provider => no-mismatch", async () => {
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "aws-bedrock", chatSessionId: "abc-123" }),
    );
    assert.strictEqual(result.kind, "no-mismatch");
  });

  test("same engine+provider + prior chatSessionId null => no-mismatch (tolerant-on-read collapse)", async () => {
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic", chatSessionId: null }),
    );
    assert.strictEqual(result.kind, "no-mismatch");
  });

  test("same engine+provider + prior chatSessionId key absent => no-mismatch (pre-Set-036 tolerant)", async () => {
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic" }),
    );
    assert.strictEqual(result.kind, "no-mismatch");
  });

  test("same engine+provider + prior chatSessionId string + operator picks Take Over => take-over", async () => {
    let modalShown = 0;
    const result: ManualChatMismatchResult = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic", chatSessionId: "aaaa-1111" }),
      {
        showModal: () => {
          modalShown += 1;
          return Promise.resolve(MODAL_TAKE_OVER);
        },
      },
    );
    assert.strictEqual(result.kind, "take-over");
    assert.strictEqual(modalShown, 1);
  });

  test("operator picks Read-Only => intent is set on the injected service and result is read-only", async () => {
    const intents = fakeIntents();
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic", chatSessionId: "aaaa-1111" }),
      {
        showModal: () => Promise.resolve(MODAL_READ_ONLY),
        intentService: intents,
      },
    );
    assert.strictEqual(result.kind, "read-only");
    assert.strictEqual(intents.flagged.has("/repo/docs/session-sets/099-fixture"), true);
  });

  test("operator picks Cancel => intent is NOT set and result is cancel", async () => {
    const intents = fakeIntents();
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic", chatSessionId: "aaaa-1111" }),
      {
        showModal: () => Promise.resolve(MODAL_CANCEL),
        intentService: intents,
      },
    );
    assert.strictEqual(result.kind, "cancel");
    assert.strictEqual(intents.flagged.size, 0);
  });

  test("modal dismissed (undefined) collapses to cancel — read-only intent NOT set", async () => {
    const intents = fakeIntents();
    const result = await maybeShowChatSessionMismatchOnManualCheckout(
      makeTuple(),
      makeSet({ engine: "claude", provider: "anthropic", chatSessionId: "aaaa-1111" }),
      {
        showModal: () => Promise.resolve(undefined),
        intentService: intents,
      },
    );
    assert.strictEqual(result.kind, "cancel");
    assert.strictEqual(intents.flagged.size, 0);
  });
});

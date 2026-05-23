import * as assert from "assert";
import {
  ChatSessionMismatchChoice,
  MODAL_CANCEL,
  MODAL_READ_ONLY,
  MODAL_TAKE_OVER,
  MismatchCopy,
  ShowModal,
  buildModalMessage,
  chatSessionMismatchModal,
  formatHolderLabel,
  resolveChoice,
  truncateChatSessionId,
} from "../../providers/chatSessionMismatchModal";

// Set 036 Session 4 — chatSessionMismatchModal Layer-2 coverage.
//
// Pure helpers cover the deterministic copy / truncation / choice
// mapping; the showModal seam exercises the round-trip from the
// modal's button labels through resolveChoice() to the typed
// ChatSessionMismatchChoice union.

suite("truncateChatSessionId", () => {
  test("short ID returns as-is", () => {
    assert.strictEqual(truncateChatSessionId("abc"), "abc");
  });

  test("8-char ID returns as-is (boundary)", () => {
    assert.strictEqual(truncateChatSessionId("12345678"), "12345678");
  });

  test("longer ID is truncated to 8 chars + ellipsis", () => {
    assert.strictEqual(
      truncateChatSessionId("550e8400-e29b-41d4-a716-446655440000"),
      "550e8400…",
    );
  });

  test("null renders as <none>", () => {
    assert.strictEqual(truncateChatSessionId(null), "<none>");
  });

  test("undefined renders as <none>", () => {
    assert.strictEqual(truncateChatSessionId(undefined), "<none>");
  });

  test("empty string renders as <none>", () => {
    assert.strictEqual(truncateChatSessionId(""), "<none>");
  });
});

suite("formatHolderLabel", () => {
  test("formats with truncated chatSessionId", () => {
    assert.strictEqual(
      formatHolderLabel("claude", "anthropic", "550e8400-e29b-41d4-a716-446655440000"),
      "claude + anthropic + chat 550e8400…",
    );
  });

  test("null chatSessionId renders the <none> placeholder", () => {
    assert.strictEqual(
      formatHolderLabel("claude", "anthropic", null),
      "claude + anthropic + chat <none>",
    );
  });
});

suite("buildModalMessage", () => {
  const copy: MismatchCopy = {
    sessionSetSlug: "099-fixture",
    heldByLabel: "claude + anthropic + chat aaaaaaaa…",
    wouldBeLabel: "claude + anthropic + chat bbbbbbbb…",
  };

  test("message names the session set", () => {
    const built = buildModalMessage(copy);
    assert.ok(built.message.includes("099-fixture"));
  });

  test("detail names both holders + describes all three actions", () => {
    const built = buildModalMessage(copy);
    assert.ok(built.detail.includes("aaaaaaaa…"));
    assert.ok(built.detail.includes("bbbbbbbb…"));
    assert.ok(/Take Over/i.test(built.detail));
    assert.ok(/Read-Only/i.test(built.detail));
    assert.ok(/Cancel/i.test(built.detail));
  });
});

suite("resolveChoice", () => {
  test("Take Over label maps to take-over", () => {
    assert.strictEqual(resolveChoice(MODAL_TAKE_OVER), "take-over");
  });

  test("Open in Read-Only Mode label maps to read-only", () => {
    assert.strictEqual(resolveChoice(MODAL_READ_ONLY), "read-only");
  });

  test("Cancel label maps to cancel", () => {
    assert.strictEqual(resolveChoice(MODAL_CANCEL), "cancel");
  });

  test("undefined (modal dismissed) collapses to cancel", () => {
    assert.strictEqual(resolveChoice(undefined), "cancel");
  });

  test("unknown label collapses to cancel (safe default)", () => {
    assert.strictEqual(resolveChoice("Other Mystery Action"), "cancel");
  });
});

suite("chatSessionMismatchModal — showModal injection", () => {
  function fixtureCopy(): MismatchCopy {
    return {
      sessionSetSlug: "099-fixture",
      heldByLabel: "claude + anthropic + chat aaaaaaaa…",
      wouldBeLabel: "claude + anthropic + chat bbbbbbbb…",
    };
  }

  test("modal: true is requested (operator must dismiss explicitly)", async () => {
    let modalFlag = false;
    const show: ShowModal = (_m, options) => {
      modalFlag = options.modal;
      return Promise.resolve(MODAL_CANCEL);
    };
    await chatSessionMismatchModal(fixtureCopy(), show);
    assert.strictEqual(modalFlag, true);
  });

  test("Take Over label returns take-over choice", async () => {
    const show: ShowModal = () => Promise.resolve(MODAL_TAKE_OVER);
    const choice: ChatSessionMismatchChoice = await chatSessionMismatchModal(
      fixtureCopy(),
      show,
    );
    assert.strictEqual(choice, "take-over");
  });

  test("Read-Only label returns read-only choice", async () => {
    const show: ShowModal = () => Promise.resolve(MODAL_READ_ONLY);
    const choice = await chatSessionMismatchModal(fixtureCopy(), show);
    assert.strictEqual(choice, "read-only");
  });

  test("dismissed modal (undefined) returns cancel", async () => {
    const show: ShowModal = () => Promise.resolve(undefined);
    const choice = await chatSessionMismatchModal(fixtureCopy(), show);
    assert.strictEqual(choice, "cancel");
  });

  test("three buttons are passed to the surface in the locked order", async () => {
    let capturedItems: string[] = [];
    const show: ShowModal = (_m, _o, ...items) => {
      capturedItems = items;
      return Promise.resolve(MODAL_CANCEL);
    };
    await chatSessionMismatchModal(fixtureCopy(), show);
    assert.deepStrictEqual(capturedItems, [
      MODAL_TAKE_OVER,
      MODAL_READ_ONLY,
      MODAL_CANCEL,
    ]);
  });

});

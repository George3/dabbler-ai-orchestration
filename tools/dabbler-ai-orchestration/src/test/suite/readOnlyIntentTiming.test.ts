import * as assert from "assert";
import * as vscode from "vscode";
import {
  commitClearReadOnlyIntent,
  confirmRevertReadOnlyIntent,
} from "../../commands/checkOutOrchestrator";
import {
  getReadOnlyIntentService,
  resetReadOnlyIntentServiceForTests,
} from "../../providers/ReadOnlyIntentService";

// Set 036 Session 4 — Round A Minor fix regression test.
//
// The intent-clear used to fire inside the confirm prompt itself,
// so an operator who picked "Clear & Check Out" but then cancelled
// the later force-override modal (or saw the write fail) would have
// silently lost their read-only protection. The two helpers are now
// split: confirmRevertReadOnlyIntent() returns the operator decision
// without mutating state; commitClearReadOnlyIntent() is invoked
// only after dispatchCheckOut() succeeds.

const FIXTURE_SET = {
  slug: "099-fixture",
  setDir: "/repo/docs/session-sets/099-fixture",
  state: {
    status: "in-progress",
    currentSession: 1,
    orchestrator: null,
  },
} as const;

suite("Read-only intent timing (Round A Minor regression)", () => {
  let originalShowWarning: typeof vscode.window.showWarningMessage;

  teardown(() => {
    resetReadOnlyIntentServiceForTests();
    if (originalShowWarning) {
      vscode.window.showWarningMessage = originalShowWarning;
    }
  });

  function stubWarning(answer: string | undefined): void {
    originalShowWarning = vscode.window.showWarningMessage;
    (vscode.window as unknown as {
      showWarningMessage: (...args: unknown[]) => Thenable<string | undefined>;
    }).showWarningMessage = (..._args: unknown[]) =>
      Promise.resolve(answer) as Thenable<string | undefined>;
  }

  test("no read-only intent => confirm returns true without prompting", async () => {
    let called = 0;
    originalShowWarning = vscode.window.showWarningMessage;
    (vscode.window as unknown as {
      showWarningMessage: (...args: unknown[]) => Thenable<string | undefined>;
    }).showWarningMessage = (..._args: unknown[]) => {
      called += 1;
      return Promise.resolve("Clear & Check Out") as Thenable<string | undefined>;
    };
    const proceed = await confirmRevertReadOnlyIntent(FIXTURE_SET as unknown as Parameters<typeof confirmRevertReadOnlyIntent>[0]);
    assert.strictEqual(proceed, true);
    assert.strictEqual(called, 0, "no warning should fire when no intent is set");
  });

  test("intent set + operator clicks 'Clear & Check Out' => confirm returns true but intent is NOT yet cleared", async () => {
    getReadOnlyIntentService().setReadOnly(FIXTURE_SET.setDir);
    stubWarning("Clear & Check Out");
    const proceed = await confirmRevertReadOnlyIntent(FIXTURE_SET as unknown as Parameters<typeof confirmRevertReadOnlyIntent>[0]);
    assert.strictEqual(proceed, true);
    // The Round A fix: the intent must still be set after confirm.
    assert.strictEqual(
      getReadOnlyIntentService().isReadOnly(FIXTURE_SET.setDir),
      true,
      "intent must persist until commitClearReadOnlyIntent fires",
    );
  });

  test("intent set + operator dismisses warning => confirm returns false AND intent is preserved", async () => {
    getReadOnlyIntentService().setReadOnly(FIXTURE_SET.setDir);
    stubWarning(undefined);
    const proceed = await confirmRevertReadOnlyIntent(FIXTURE_SET as unknown as Parameters<typeof confirmRevertReadOnlyIntent>[0]);
    assert.strictEqual(proceed, false);
    assert.strictEqual(
      getReadOnlyIntentService().isReadOnly(FIXTURE_SET.setDir),
      true,
      "intent must NOT be cleared on dismissal",
    );
  });

  test("commitClearReadOnlyIntent clears the intent for the named set only", () => {
    getReadOnlyIntentService().setReadOnly(FIXTURE_SET.setDir);
    getReadOnlyIntentService().setReadOnly("/repo/docs/session-sets/other");
    commitClearReadOnlyIntent(FIXTURE_SET as unknown as Parameters<typeof commitClearReadOnlyIntent>[0]);
    assert.strictEqual(getReadOnlyIntentService().isReadOnly(FIXTURE_SET.setDir), false);
    assert.strictEqual(
      getReadOnlyIntentService().isReadOnly("/repo/docs/session-sets/other"),
      true,
      "unrelated intents must be untouched",
    );
  });
});

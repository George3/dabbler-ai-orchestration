import * as assert from "assert";
import {
  ReadOnlyIntentService,
  getReadOnlyIntentService,
  resetReadOnlyIntentServiceForTests,
} from "../../providers/ReadOnlyIntentService";

// Set 036 Session 4 — ReadOnlyIntentService Layer-2 coverage.
//
// The service is a thin Set wrapper with an EventEmitter; the tests
// pin the observable contract (set / clear / membership / change
// events) so future refactors don't drift.

suite("ReadOnlyIntentService", () => {
  let svc: ReadOnlyIntentService;
  setup(() => {
    svc = new ReadOnlyIntentService();
  });
  teardown(() => {
    svc.dispose();
  });

  test("isReadOnly returns false on a fresh service", () => {
    assert.strictEqual(svc.isReadOnly("/repo/docs/session-sets/099"), false);
  });

  test("setReadOnly marks the set and isReadOnly reflects it", () => {
    svc.setReadOnly("/repo/docs/session-sets/099");
    assert.strictEqual(svc.isReadOnly("/repo/docs/session-sets/099"), true);
    assert.strictEqual(svc.isReadOnly("/repo/docs/session-sets/100"), false);
  });

  test("clearReadOnly removes the flag", () => {
    svc.setReadOnly("/repo/docs/session-sets/099");
    svc.clearReadOnly("/repo/docs/session-sets/099");
    assert.strictEqual(svc.isReadOnly("/repo/docs/session-sets/099"), false);
  });

  test("setReadOnly is idempotent — second call does not double-fire onDidChange", () => {
    let fires = 0;
    svc.onDidChange(() => {
      fires += 1;
    });
    svc.setReadOnly("/repo/docs/session-sets/099");
    svc.setReadOnly("/repo/docs/session-sets/099");
    assert.strictEqual(fires, 1);
  });

  test("clearReadOnly on an unflagged set does not fire onDidChange", () => {
    let fires = 0;
    svc.onDidChange(() => {
      fires += 1;
    });
    svc.clearReadOnly("/repo/docs/session-sets/099");
    assert.strictEqual(fires, 0);
  });

  test("empty path is ignored on set + clear", () => {
    svc.setReadOnly("");
    assert.strictEqual(svc.intentCount, 0);
    svc.clearReadOnly("");
    assert.strictEqual(svc.intentCount, 0);
  });

  test("dispose() clears all intents", () => {
    svc.setReadOnly("/a");
    svc.setReadOnly("/b");
    assert.strictEqual(svc.intentCount, 2);
    svc.dispose();
    assert.strictEqual(svc.intentCount, 0);
    // Re-create for teardown's dispose to find a clean instance.
    svc = new ReadOnlyIntentService();
  });
});

suite("getReadOnlyIntentService — singleton", () => {
  teardown(() => {
    resetReadOnlyIntentServiceForTests();
  });

  test("returns the same instance across calls", () => {
    const a = getReadOnlyIntentService();
    const b = getReadOnlyIntentService();
    assert.strictEqual(a, b);
  });

  test("resetReadOnlyIntentServiceForTests gives a fresh instance", () => {
    const a = getReadOnlyIntentService();
    a.setReadOnly("/repo/docs/session-sets/099");
    resetReadOnlyIntentServiceForTests();
    const b = getReadOnlyIntentService();
    assert.notStrictEqual(a, b);
    assert.strictEqual(b.isReadOnly("/repo/docs/session-sets/099"), false);
  });
});

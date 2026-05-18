import * as assert from "assert";
import {
  SuppressionState,
  isSuppressed,
  suppress,
  clearSuppression,
  prune,
} from "../../providers/suppressionState";

// Set 029 Session 4 — Auto-expand suppression keyed by the
// (slug, marker.updatedAt) tuple per audit Q2(a) + GPT-5.4 M7. Pure
// reducer; suite verifies aging behavior + manual-clear semantics +
// stale-key pruning.

suite("suppressionState", () => {
  test("isSuppressed returns false when no entry exists for slug", () => {
    const state: SuppressionState = {};
    assert.strictEqual(isSuppressed(state, "foo", "2026-05-18T00:00:00Z"), false);
  });

  test("isSuppressed returns true only when slug AND updatedAt match", () => {
    const state: SuppressionState = { foo: "2026-05-18T00:00:00Z" };
    assert.strictEqual(isSuppressed(state, "foo", "2026-05-18T00:00:00Z"), true);
    assert.strictEqual(
      isSuppressed(state, "foo", "2026-05-18T01:00:00Z"),
      false,
      "different updatedAt = different occurrence, must NOT be suppressed",
    );
    assert.strictEqual(isSuppressed(state, "bar", "2026-05-18T00:00:00Z"), false);
  });

  test("isSuppressed returns false for null marker.updatedAt", () => {
    const state: SuppressionState = { foo: "2026-05-18T00:00:00Z" };
    assert.strictEqual(isSuppressed(state, "foo", null), false);
  });

  test("suppress sets the tuple-key entry", () => {
    const before: SuppressionState = {};
    const after = suppress(before, "foo", "2026-05-18T00:00:00Z");
    assert.deepStrictEqual(after, { foo: "2026-05-18T00:00:00Z" });
    assert.notStrictEqual(after, before, "must return a new object (immutability)");
  });

  test("suppress overwrites with a fresher updatedAt for the same slug", () => {
    const before: SuppressionState = { foo: "2026-05-18T00:00:00Z" };
    const after = suppress(before, "foo", "2026-05-18T01:00:00Z");
    assert.deepStrictEqual(after, { foo: "2026-05-18T01:00:00Z" });
  });

  test("clearSuppression removes the slug entry entirely", () => {
    const before: SuppressionState = { foo: "2026-05-18T00:00:00Z", bar: "2026-05-18T01:00:00Z" };
    const after = clearSuppression(before, "foo");
    assert.deepStrictEqual(after, { bar: "2026-05-18T01:00:00Z" });
  });

  test("clearSuppression is a no-op + returns the same instance when slug not present", () => {
    const before: SuppressionState = { bar: "2026-05-18T01:00:00Z" };
    const after = clearSuppression(before, "foo");
    assert.strictEqual(after, before, "no-op path should not allocate");
  });

  test("prune drops entries whose slug is no longer visible", () => {
    const before: SuppressionState = {
      foo: "2026-05-18T00:00:00Z",
      bar: "2026-05-18T01:00:00Z",
      baz: "2026-05-18T02:00:00Z",
    };
    const visible = new Set(["foo", "baz"]);
    const after = prune(before, visible);
    assert.deepStrictEqual(after, {
      foo: "2026-05-18T00:00:00Z",
      baz: "2026-05-18T02:00:00Z",
    });
  });

  test("prune returns the same instance when nothing changes", () => {
    const before: SuppressionState = { foo: "2026-05-18T00:00:00Z" };
    const after = prune(before, new Set(["foo"]));
    assert.strictEqual(after, before);
  });

  test("aging: SessionStart writes a fresh marker → suppression naturally lifts", () => {
    // Occurrence 1: marker updatedAt = T0, operator collapses manually.
    let state: SuppressionState = {};
    state = suppress(state, "foo", "T0");
    assert.strictEqual(isSuppressed(state, "foo", "T0"), true);
    // Next SessionStart: marker updatedAt advances to T1. The new
    // occurrence is NOT suppressed because the key tuple no longer
    // matches — the auto-expand fires normally.
    assert.strictEqual(isSuppressed(state, "foo", "T1"), false);
  });
});

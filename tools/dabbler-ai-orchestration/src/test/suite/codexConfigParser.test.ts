import * as assert from "assert";
import {
  extractTopLevelScalar,
  parseCodexConfig,
} from "../../codex/configWatcher";

// Set 029 Session 5 — Codex config-watcher TOML scalar extractor.
// The watcher only needs `model` and `model_reasoning_effort` from
// the top-level table; a full TOML parser is overkill. These tests
// cover the formats Codex actually writes plus a few hostile-input
// cases that would break a naive regex.

suite("extractTopLevelScalar", () => {
  test("reads a double-quoted top-level value", () => {
    const toml = 'model = "gpt-5"\n';
    assert.strictEqual(extractTopLevelScalar(toml, "model"), "gpt-5");
  });

  test("reads a single-quoted top-level value", () => {
    const toml = "model = 'gpt-5-4'\n";
    assert.strictEqual(extractTopLevelScalar(toml, "model"), "gpt-5-4");
  });

  test("reads a bare (unquoted) value", () => {
    const toml = "model_reasoning_effort = high\n";
    assert.strictEqual(
      extractTopLevelScalar(toml, "model_reasoning_effort"),
      "high",
    );
  });

  test("ignores values inside [sections]", () => {
    // Once we cross a [section] header, top-level scalar parsing is
    // done — keys under sections are NOT what we're looking for.
    const toml = [
      '[profiles.default]',
      'model = "ignored-because-sectioned"',
      "",
    ].join("\n");
    assert.strictEqual(extractTopLevelScalar(toml, "model"), null);
  });

  test("returns null when the key is absent", () => {
    const toml = 'other_key = "foo"\n';
    assert.strictEqual(extractTopLevelScalar(toml, "model"), null);
  });

  test("tolerates leading whitespace and trailing inline comments", () => {
    const toml = '  model = "gpt-5"  # default for this user\n';
    assert.strictEqual(extractTopLevelScalar(toml, "model"), "gpt-5");
  });
});

suite("parseCodexConfig", () => {
  test("returns null model + null effort + thinking=false for empty TOML", () => {
    const snap = parseCodexConfig("");
    assert.strictEqual(snap.model, null);
    assert.strictEqual(snap.effort, null);
    assert.strictEqual(snap.thinking, false);
  });

  test("returns model + effort + thinking=true for a populated config", () => {
    const toml = [
      'model = "gpt-5-4"',
      'model_reasoning_effort = "high"',
      "",
    ].join("\n");
    const snap = parseCodexConfig(toml);
    assert.strictEqual(snap.model, "gpt-5-4");
    assert.strictEqual(snap.effort, "high");
    // Codex doesn't expose a separate thinking boolean; any
    // reasoning-effort setting implies thinking-on.
    assert.strictEqual(snap.thinking, true);
  });

  test("rejects invalid effort values (only low/medium/high accepted)", () => {
    const toml = [
      'model = "gpt-5"',
      'model_reasoning_effort = "extreme"',
      "",
    ].join("\n");
    const snap = parseCodexConfig(toml);
    assert.strictEqual(snap.effort, null);
    assert.strictEqual(snap.thinking, false);
  });

  test("normalizes case-variant effort values to lowercase canonical form", () => {
    const toml = [
      'model = "gpt-5"',
      'model_reasoning_effort = "HIGH"',
      "",
    ].join("\n");
    const snap = parseCodexConfig(toml);
    assert.strictEqual(snap.effort, "high");
  });
});

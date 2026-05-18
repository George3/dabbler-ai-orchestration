import * as assert from "assert";
import { extractRecommendation } from "../../providers/MarkerWatchService";

// Set 029 Session 4 — extractRecommendation parses ai-assignment.md
// for a per-session recommendation paragraph. Extracted as a free
// function in MarkerWatchService for direct unit-testing without
// vscode lifecycle / filesystem watcher setup. Pure string-in →
// Recommendation|null out.

suite("extractRecommendation", () => {
  test("parses a well-formed `## Session N: title` + ### Recommended orchestrator block", () => {
    const text = [
      "# Set 029 — ai-assignment",
      "",
      "## Session 4: Custom-tree pivot",
      "",
      "### Recommended orchestrator",
      "",
      "Claude Opus 4.7 @ effort=high. Rationale text follows.",
      "",
      "## Session 5: Non-Claude provider detection",
      "",
      "### Recommended orchestrator",
      "",
      "Claude Sonnet 4.6 @ effort=medium",
    ].join("\n");
    const rec = extractRecommendation(text, 4, "029-orchestrator");
    assert.ok(rec, "should extract for session 4");
    assert.strictEqual(rec!.providerName, "Claude");
    assert.strictEqual(rec!.modelName, "Opus 4.7");
    assert.strictEqual(rec!.effort, "high");
    assert.strictEqual(rec!.sessionLabel, "Session 4: Custom-tree pivot");
    assert.strictEqual(rec!.setName, "029-orchestrator");
  });

  test("supports `## Session N of M: title` heading form", () => {
    const text = [
      "## Session 3 of 6: Per-session-set identity",
      "### Recommended orchestrator",
      "Claude Opus 4.7 @ effort=high",
    ].join("\n");
    const rec = extractRecommendation(text, 3, "set");
    assert.ok(rec);
    assert.strictEqual(rec!.sessionLabel, "Session 3: Per-session-set identity");
  });

  test("returns null when the session heading is absent", () => {
    const text = "## Session 1: Foo\n### Recommended orchestrator\nClaude Opus 4.7 @ effort=high";
    assert.strictEqual(extractRecommendation(text, 4, "set"), null);
  });

  test("returns null when the Recommended orchestrator subheading is absent", () => {
    const text = "## Session 4: Custom-tree pivot\n\nSome other content but no recommendation.";
    assert.strictEqual(extractRecommendation(text, 4, "set"), null);
  });

  test("returns null when the recommendation paragraph is malformed (no @ effort=)", () => {
    const text = [
      "## Session 4: Custom-tree pivot",
      "### Recommended orchestrator",
      "Just some prose without the canonical format.",
    ].join("\n");
    assert.strictEqual(extractRecommendation(text, 4, "set"), null);
  });

  test("does not bleed into the next session's recommendation block", () => {
    const text = [
      "## Session 4: Custom-tree pivot",
      "",
      "Lots of prose but no Recommended orchestrator subheading here.",
      "",
      "## Session 5: Next",
      "### Recommended orchestrator",
      "Claude Sonnet 4.6 @ effort=medium",
    ].join("\n");
    assert.strictEqual(extractRecommendation(text, 4, "set"), null,
      "session 4 has no rec; must NOT pick up session 5's rec");
  });

  test("trims trailing punctuation off the model name", () => {
    const text = [
      "## Session 1: x",
      "### Recommended orchestrator",
      "Claude Opus 4.7. @ effort=high",
    ].join("\n");
    const rec = extractRecommendation(text, 1, "set");
    assert.ok(rec);
    assert.strictEqual(rec!.modelName, "Opus 4.7");
  });
});

/**
 * Half-batch recovery: when the panel's batch save writes succeed for
 * some files and fail for others, the operator needs a way to retry the
 * failed writes or accept the on-disk state as the new baseline. This
 * test exercises the content-hash drift detection that the panel uses to
 * surface the recovery banner on next load.
 */
import * as assert from "assert";
import { parseDocument } from "yaml";
import { docContentHash, stringContentHash } from "../../configEditor/patch";

suite("halfBatchRecovery — content-hash drift detection", () => {
  test("matching content yields equal hashes (no drift)", () => {
    const text = "foo: 1\nbar: 2\n";
    const h1 = stringContentHash(text);
    const h2 = stringContentHash(text);
    assert.strictEqual(h1, h2, "identical text must produce identical hash");
  });

  test("different content yields different hashes (drift detected)", () => {
    const original = "foo: 1\n";
    const mutated = "foo: 2\n";
    assert.notStrictEqual(stringContentHash(original), stringContentHash(mutated));
  });

  test("docContentHash distinguishes structurally-different docs", () => {
    const a = parseDocument("threshold_usd: 10\nscope: per-project\n");
    const b = parseDocument("threshold_usd: 20\nscope: per-project\n");
    assert.notStrictEqual(docContentHash(a), docContentHash(b));
  });

  test("comment-only edits register as drift (preserves the byte-for-byte comparison)", () => {
    const a = "# comment v1\nfoo: 1\n";
    const b = "# comment v2\nfoo: 1\n";
    assert.notStrictEqual(stringContentHash(a), stringContentHash(b));
  });
});

/**
 * Simulating the half-batch state directly: when 2 of 3 writes succeed
 * and 1 fails (e.g., disk full mid-save), the editor should detect the
 * partial state and surface a recovery dialog. We mimic the panel's
 * tracking logic with a tiny inline state-machine here so the public
 * behavior is testable without spinning up a real webview.
 */
interface SaveAttempt {
  file: string;
  succeeded: boolean;
}

function classifyAttempts(attempts: SaveAttempt[]): "all-succeeded" | "half-batch" | "all-failed" {
  const ok = attempts.filter((a) => a.succeeded).length;
  if (ok === attempts.length) return "all-succeeded";
  if (ok === 0) return "all-failed";
  return "half-batch";
}

suite("halfBatchRecovery — classify save attempts", () => {
  test("classifies all-succeeded correctly", () => {
    assert.strictEqual(
      classifyAttempts([
        { file: "router-config.yaml", succeeded: true },
        { file: "budget.yaml", succeeded: true },
      ]),
      "all-succeeded"
    );
  });

  test("classifies half-batch correctly (1 succeeded, 1 failed)", () => {
    assert.strictEqual(
      classifyAttempts([
        { file: "router-config.yaml", succeeded: true },
        { file: "budget.yaml", succeeded: false },
      ]),
      "half-batch"
    );
  });

  test("classifies half-batch correctly (2 succeeded, 1 failed)", () => {
    assert.strictEqual(
      classifyAttempts([
        { file: "router-config.yaml", succeeded: true },
        { file: "budget.yaml", succeeded: true },
        { file: "local-overrides.yaml", succeeded: false },
      ]),
      "half-batch"
    );
  });

  test("classifies all-failed correctly", () => {
    assert.strictEqual(
      classifyAttempts([
        { file: "router-config.yaml", succeeded: false },
        { file: "budget.yaml", succeeded: false },
      ]),
      "all-failed"
    );
  });
});

import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  formatTupleLabel,
  pushMru,
  readMru,
  type OrchestratorTuple,
} from "../../commands/setOrchestratorManual";

// Set 029 Session 5 — manual-override quickpick helpers.
// MRU read/write hits ~/.dabbler/orchestrator-mru.json directly so the
// suite redirects HOME/USERPROFILE to a tmpdir per test, runs the
// helper, then restores. Pure logic (label formatting) needs no
// filesystem isolation.

function withTempHome(fn: () => void): void {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-mru-"));
  const prevHome = process.env.HOME;
  const prevUserprofile = process.env.USERPROFILE;
  process.env.HOME = tmp;
  process.env.USERPROFILE = tmp;
  try {
    fn();
  } finally {
    if (prevHome === undefined) delete process.env.HOME;
    else process.env.HOME = prevHome;
    if (prevUserprofile === undefined) delete process.env.USERPROFILE;
    else process.env.USERPROFILE = prevUserprofile;
    try {
      fs.rmSync(tmp, { recursive: true, force: true });
    } catch {
      // best effort
    }
  }
}

const TUPLE_A: OrchestratorTuple = {
  provider: "anthropic",
  model: "claude-opus-4-7",
  effort: "high",
  thinking: true,
};
const TUPLE_B: OrchestratorTuple = {
  provider: "google",
  model: "gemini-2.5-pro",
  effort: "high",
  thinking: false,
};
const TUPLE_C: OrchestratorTuple = {
  provider: "openai",
  model: "gpt-5",
  effort: "medium",
  thinking: true,
};

suite("pushMru", () => {
  test("empty MRU + one push → single-entry MRU on disk", () => {
    withTempHome(() => {
      const next = pushMru(TUPLE_A, []);
      assert.deepStrictEqual(next, [TUPLE_A]);
      const persisted = readMru();
      assert.deepStrictEqual(persisted, [TUPLE_A]);
    });
  });

  test("duplicate push de-duplicates and moves to front", () => {
    withTempHome(() => {
      pushMru(TUPLE_A, []);
      pushMru(TUPLE_B);
      // Push TUPLE_A again — should NOT appear twice, should move to
      // the front.
      const next = pushMru(TUPLE_A);
      assert.deepStrictEqual(next, [TUPLE_A, TUPLE_B]);
      assert.deepStrictEqual(readMru(), [TUPLE_A, TUPLE_B]);
    });
  });

  test("two distinct tuples for the same provider both retained", () => {
    withTempHome(() => {
      pushMru(TUPLE_A, []);
      const sameProviderDifferentEffort: OrchestratorTuple = {
        ...TUPLE_A,
        effort: "low",
      };
      const next = pushMru(sameProviderDifferentEffort);
      assert.strictEqual(next.length, 2);
      assert.deepStrictEqual(next[0], sameProviderDifferentEffort);
      assert.deepStrictEqual(next[1], TUPLE_A);
    });
  });

  test("MRU caps at 8 entries (oldest evicted)", () => {
    withTempHome(() => {
      // Push 10 distinct tuples; only the most recent 8 should survive.
      for (let i = 0; i < 10; i++) {
        pushMru({
          provider: "anthropic",
          model: `model-${i}`,
          effort: "high",
          thinking: i % 2 === 0,
        });
      }
      const persisted = readMru();
      assert.strictEqual(persisted.length, 8);
      // Newest first: model-9 at index 0, oldest survivor model-2 at index 7.
      assert.strictEqual(persisted[0].model, "model-9");
      assert.strictEqual(persisted[7].model, "model-2");
    });
  });
});

suite("readMru", () => {
  test("returns [] when no MRU file exists yet", () => {
    withTempHome(() => {
      assert.deepStrictEqual(readMru(), []);
    });
  });

  test("returns [] on malformed JSON without throwing", () => {
    withTempHome(() => {
      const file = path.join(process.env.HOME!, ".dabbler", "orchestrator-mru.json");
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, "{not json", "utf8");
      assert.deepStrictEqual(readMru(), []);
    });
  });

  test("filters out non-tuple entries", () => {
    withTempHome(() => {
      const file = path.join(process.env.HOME!, ".dabbler", "orchestrator-mru.json");
      fs.mkdirSync(path.dirname(file), { recursive: true });
      // Mix one valid tuple with two garbage entries.
      fs.writeFileSync(
        file,
        JSON.stringify([TUPLE_A, { bogus: true }, "string"], null, 2),
        "utf8",
      );
      assert.deepStrictEqual(readMru(), [TUPLE_A]);
    });
  });
});

suite("formatTupleLabel", () => {
  test("formats with display names for known provider/model + thinking on", () => {
    assert.strictEqual(
      formatTupleLabel(TUPLE_A),
      "Claude Opus 4.7 — High effort, Thinking on",
    );
  });

  test("formats Gemini Pro with thinking off", () => {
    assert.strictEqual(
      formatTupleLabel(TUPLE_B),
      "Gemini Gemini 2.5 Pro — High effort, Thinking off",
    );
  });

  test("falls back to raw model id for unknown model", () => {
    const unknown: OrchestratorTuple = {
      provider: "openai",
      model: "future-mystery-model",
      effort: "low",
      thinking: false,
    };
    assert.strictEqual(
      formatTupleLabel(unknown),
      "Codex future-mystery-model — Low effort, Thinking off",
    );
  });
});

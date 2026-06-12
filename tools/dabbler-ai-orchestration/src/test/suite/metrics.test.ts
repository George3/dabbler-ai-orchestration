import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  summarizeMetrics,
  buildSparkline,
  exportToCsv,
  readMetricsFromPath,
  sessionSetDisplayName,
} from "../../utils/metrics";
import { MetricsEntry } from "../../types";

const SAMPLE: MetricsEntry[] = [
  {
    session_set: "user-auth",
    session_number: 1,
    model: "claude-sonnet-4-6",
    effort: "normal",
    input_tokens: 10000,
    output_tokens: 2000,
    cost_usd: 0.25,
    timestamp: "2026-04-20T10:00:00Z",
  },
  {
    session_set: "user-auth",
    session_number: 2,
    model: "claude-sonnet-4-6",
    effort: "normal",
    input_tokens: 8000,
    output_tokens: 1500,
    cost_usd: 0.18,
    timestamp: "2026-04-21T11:00:00Z",
  },
  {
    session_set: "product-catalog",
    session_number: 1,
    model: "claude-opus-4-7",
    effort: "high",
    input_tokens: 20000,
    output_tokens: 5000,
    cost_usd: 1.20,
    timestamp: "2026-04-22T09:00:00Z",
  },
];

suite("metrics", () => {
  test("summarizeMetrics totals cost correctly", () => {
    const summary = summarizeMetrics(SAMPLE);
    assert.ok(Math.abs(summary.totalCost - 1.63) < 0.001);
  });

  test("summarizeMetrics groups by session set", () => {
    const summary = summarizeMetrics(SAMPLE);
    assert.strictEqual(summary.bySessionSet["user-auth"].sessions, 2);
    assert.strictEqual(summary.bySessionSet["product-catalog"].sessions, 1);
    assert.ok(Math.abs(summary.bySessionSet["user-auth"].cost - 0.43) < 0.001);
  });

  test("summarizeMetrics groups by model", () => {
    const summary = summarizeMetrics(SAMPLE);
    assert.ok("claude-sonnet-4-6" in summary.byModel);
    assert.ok("claude-opus-4-7" in summary.byModel);
  });

  test("summarizeMetrics produces 30 daily entries", () => {
    const summary = summarizeMetrics(SAMPLE);
    assert.strictEqual(summary.dailyCosts.length, 30);
  });

  test("buildSparkline returns 30-char string of block chars", () => {
    const summary = summarizeMetrics(SAMPLE);
    const sparkline = buildSparkline(summary.dailyCosts);
    assert.strictEqual(sparkline.length, 30);
    assert.match(sparkline, /^[▁▂▃▄▅▆▇█]+$/);
  });

  test("buildSparkline handles all-zero input", () => {
    const zeros = Array.from({ length: 30 }, (_, i) => ({
      date: `2026-04-${String(i + 1).padStart(2, "0")}`,
      cost: 0,
    }));
    const sparkline = buildSparkline(zeros);
    assert.strictEqual(sparkline.length, 30);
    // All zeros → all lowest block
    assert.match(sparkline, /^▁+$/);
  });

  test("exportToCsv includes header and all rows", () => {
    const csv = exportToCsv(SAMPLE);
    const lines = csv.split("\n");
    assert.strictEqual(lines[0], "session_set,session_number,model,effort,input_tokens,output_tokens,cost_usd,timestamp");
    assert.strictEqual(lines.length, 4); // header + 3 rows
    assert.ok(lines[1].startsWith("user-auth,1,"));
  });

  // ---------------------------------------------------------------------
  // Session-set name normalization (operator report, 2026-06-12): the
  // log carries session_set in four historical shapes; the dashboard
  // must show the bare folder name for every one of them.
  // ---------------------------------------------------------------------
  suite("sessionSetDisplayName", () => {
    test("bare slug passes through unchanged", () => {
      assert.strictEqual(
        sessionSetDisplayName("062-lightweight-verification-affordance"),
        "062-lightweight-verification-affordance",
      );
    });

    test("repo-relative POSIX path reduces to the folder name", () => {
      assert.strictEqual(
        sessionSetDisplayName("docs/session-sets/001-queue-contract-and-recovery-foundation"),
        "001-queue-contract-and-recovery-foundation",
      );
    });

    test("absolute Windows path reduces to the folder name (both drive casings)", () => {
      assert.strictEqual(
        sessionSetDisplayName(
          "C:\\Users\\someone\\source\\repos\\x\\docs\\session-sets\\047-state-file-schema-v4-audit",
        ),
        "047-state-file-schema-v4-audit",
      );
      assert.strictEqual(
        sessionSetDisplayName(
          "c:\\Users\\someone\\source\\repos\\x\\docs\\session-sets\\047-state-file-schema-v4-audit",
        ),
        "047-state-file-schema-v4-audit",
      );
    });

    test("trailing separators are ignored", () => {
      assert.strictEqual(
        sessionSetDisplayName("docs/session-sets/008-cancelled-session-set-status/"),
        "008-cancelled-session-set-status",
      );
    });

    test("null / undefined / empty read as '(no session set)'", () => {
      assert.strictEqual(sessionSetDisplayName(null), "(no session set)");
      assert.strictEqual(sessionSetDisplayName(undefined), "(no session set)");
      assert.strictEqual(sessionSetDisplayName(""), "(no session set)");
      assert.strictEqual(sessionSetDisplayName("   "), "(no session set)");
    });

    test("readMetricsFromPath normalizes so mixed shapes MERGE into one summary row", () => {
      const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-metrics-test-"));
      const file = path.join(dir, "router-metrics.jsonl");
      try {
        const mk = (session_set: string | null, cost: number) =>
          JSON.stringify({
            session_set,
            session_number: 1,
            call_type: "route",
            model: "gpt-5.4",
            effort: "high",
            input_tokens: 1,
            output_tokens: 1,
            cost_usd: cost,
            timestamp: "2026-06-12T10:00:00Z",
          });
        fs.writeFileSync(
          file,
          [
            mk("049-orchestrator-coordination-removal", 0.1),
            mk("docs/session-sets/049-orchestrator-coordination-removal", 0.2),
            mk("C:\\repo\\docs\\session-sets\\049-orchestrator-coordination-removal", 0.3),
            mk(null, 0.4),
          ].join("\n") + "\n",
          "utf8",
        );
        const entries = readMetricsFromPath(file);
        assert.strictEqual(entries.length, 4);
        const summary = summarizeMetrics(entries);
        const row = summary.bySessionSet["049-orchestrator-coordination-removal"];
        assert.ok(row, "merged slug row exists");
        assert.strictEqual(row.sessions, 3);
        assert.ok(Math.abs(row.cost - 0.6) < 1e-9);
        assert.ok(summary.bySessionSet["(no session set)"], "null entries get an honest row");
        // No path-shaped keys survive.
        for (const key of Object.keys(summary.bySessionSet)) {
          assert.ok(!/[\\/]/.test(key), `path-shaped key leaked: ${key}`);
        }
        // The CSV export sees normalized names too (no machine paths).
        const csv = exportToCsv(entries);
        assert.ok(!csv.includes("C:\\"), "absolute path leaked into CSV");
      } finally {
        fs.rmSync(dir, { recursive: true, force: true });
      }
    });
  });
});

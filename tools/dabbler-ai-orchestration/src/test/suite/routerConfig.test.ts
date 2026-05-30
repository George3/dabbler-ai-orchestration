import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  findAiRouterDir,
  routesCost,
  readRouterConfig,
  computeStaleness,
  selectCostState,
  DEFAULT_METRICS_FILENAME,
  DEFAULT_REVIEW_FREQUENCY_DAYS,
  RouterConfigInfo,
} from "../../utils/routerConfig";

// Set 052 S2 — router-capability gate, read-path resolution, and
// staleness/state-selection predicates. All pure file/logic; no vscode.

function mkWorkspace(configBody: string | null): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-rc-"));
  if (configBody !== null) {
    const dir = path.join(root, "ai_router");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "router-config.yaml"), configBody, "utf8");
  }
  return root;
}

function cleanup(root: string): void {
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* opportunistic */ }
}

suite("routerConfig — D3 tier gate", () => {
  test("routesCost true only when ai_router/router-config.yaml exists", () => {
    const withConfig = mkWorkspace("metrics:\n  enabled: true\n");
    const noConfig = mkWorkspace(null);
    // Bare ai_router/ dir with no config file → not routing.
    const bareDir = mkWorkspace(null);
    fs.mkdirSync(path.join(bareDir, "ai_router"), { recursive: true });
    try {
      assert.strictEqual(routesCost(withConfig), true);
      assert.strictEqual(routesCost(noConfig), false);
      assert.strictEqual(routesCost(bareDir), false, "bare ai_router/ folder is insufficient");
      assert.ok(findAiRouterDir(withConfig));
      assert.strictEqual(findAiRouterDir(noConfig), null);
    } finally {
      [withConfig, noConfig, bareDir].forEach(cleanup);
    }
  });
});

suite("routerConfig — D1 read-path resolution", () => {
  test("defaults to router-metrics.jsonl when log_filename absent", () => {
    const root = mkWorkspace("metrics:\n  enabled: true\n");
    try {
      const info = readRouterConfig(root)!;
      assert.strictEqual(info.metricsFilename, DEFAULT_METRICS_FILENAME);
      assert.strictEqual(
        info.metricsPath,
        path.join(root, "ai_router", "router-metrics.jsonl"),
      );
      assert.notStrictEqual(path.basename(info.metricsPath), "metrics.jsonl");
    } finally { cleanup(root); }
  });

  test("honors a custom metrics.log_filename", () => {
    const root = mkWorkspace("metrics:\n  enabled: true\n  log_filename: custom-metrics.jsonl\n");
    try {
      const info = readRouterConfig(root)!;
      assert.strictEqual(info.metricsFilename, "custom-metrics.jsonl");
      assert.strictEqual(path.basename(info.metricsPath), "custom-metrics.jsonl");
    } finally { cleanup(root); }
  });

  test("metricsEnabled defaults true; false only when explicitly disabled", () => {
    const on = mkWorkspace("metrics:\n  log_filename: router-metrics.jsonl\n");
    const off = mkWorkspace("metrics:\n  enabled: false\n");
    try {
      assert.strictEqual(readRouterConfig(on)!.metricsEnabled, true);
      assert.strictEqual(readRouterConfig(off)!.metricsEnabled, false);
    } finally { cleanup(on); cleanup(off); }
  });

  test("returns null when workspace does not route", () => {
    const root = mkWorkspace(null);
    try { assert.strictEqual(readRouterConfig(root), null); } finally { cleanup(root); }
  });

  test("unparseable YAML still resolves (router IS capable) with defaults", () => {
    const root = mkWorkspace(":::not: valid: yaml: [unterminated\n");
    try {
      const info = readRouterConfig(root);
      assert.ok(info, "a present-but-broken config must not flip the gate off");
      assert.strictEqual(info!.metricsEnabled, true);
      assert.strictEqual(info!.metricsFilename, DEFAULT_METRICS_FILENAME);
    } finally { cleanup(root); }
  });
});

suite("routerConfig — D4 staleness", () => {
  const base = (over: Partial<RouterConfigInfo>): RouterConfigInfo => ({
    configPath: "/x/ai_router/router-config.yaml",
    aiRouterDir: "/x/ai_router",
    metricsEnabled: true,
    metricsFilename: DEFAULT_METRICS_FILENAME,
    metricsPath: "/x/ai_router/router-metrics.jsonl",
    pricingReviewed: "2026-04-20",
    reviewFrequencyDays: DEFAULT_REVIEW_FREQUENCY_DAYS,
    ...over,
  });

  test("fresh within threshold is not stale", () => {
    const now = new Date("2026-04-30T00:00:00Z"); // 10 days later
    const r = computeStaleness(base({}), now);
    assert.strictEqual(r.stale, false);
    assert.strictEqual(r.ageDays, 10);
  });

  test("older than threshold is stale", () => {
    const now = new Date("2026-06-01T00:00:00Z"); // 42 days later
    const r = computeStaleness(base({}), now);
    assert.strictEqual(r.stale, true);
    assert.strictEqual(r.ageDays, 42);
  });

  test("missing pricing_reviewed is treated as stale", () => {
    const r = computeStaleness(base({ pricingReviewed: null }), new Date("2026-06-01T00:00:00Z"));
    assert.strictEqual(r.stale, true);
    assert.strictEqual(r.ageDays, null);
  });

  test("invalid pricing_reviewed is treated as stale", () => {
    const r = computeStaleness(base({ pricingReviewed: "not-a-date" }), new Date("2026-06-01T00:00:00Z"));
    assert.strictEqual(r.stale, true);
    assert.strictEqual(r.ageDays, null);
  });
});

suite("routerConfig — D5 three-state selection", () => {
  const info = (over: Partial<RouterConfigInfo>): RouterConfigInfo => ({
    configPath: "/x", aiRouterDir: "/x", metricsEnabled: true,
    metricsFilename: DEFAULT_METRICS_FILENAME, metricsPath: "/x/m.jsonl",
    pricingReviewed: "2026-04-20", reviewFrequencyDays: 30, ...over,
  });

  test("null info → no-router", () => {
    assert.strictEqual(selectCostState(null, 0).kind, "no-router");
  });
  test("metrics disabled → disabled (regardless of entries)", () => {
    assert.strictEqual(selectCostState(info({ metricsEnabled: false }), 5).kind, "disabled");
  });
  test("enabled but no entries → empty", () => {
    assert.strictEqual(selectCostState(info({}), 0).kind, "empty");
  });
  test("enabled with entries → data", () => {
    assert.strictEqual(selectCostState(info({}), 3).kind, "data");
  });
});

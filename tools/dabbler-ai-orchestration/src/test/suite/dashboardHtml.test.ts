import * as assert from "assert";
import {
  disabledStateHtml,
  emptyStateHtml,
  noRouterHtml,
  stalenessBannerHtml,
  findConfigAnchorLine,
} from "../../dashboard/dashboardHtml";
import { StalenessResult } from "../../utils/routerConfig";

// Set 052 S2 — D5 honest-copy invariants. The dead-icon era named a
// fictional `config.py METRICS_ENABLED` flag in every non-data state.
// These tests pin the new copy: never the fictional flag, always the
// real `metrics.enabled` knob, and the staleness banner behavior.

const NONCE = "testnonce";
const CSP = "vscode-resource:";

function assertNoFictionalFlag(html: string): void {
  assert.ok(!/METRICS_ENABLED/.test(html), "must not name the fictional METRICS_ENABLED flag");
  assert.ok(!/config\.py/.test(html), "must not point at config.py");
}

suite("dashboardHtml — D5 disabled state", () => {
  const html = disabledStateHtml(NONCE, CSP, "/repo/ai_router/router-config.yaml");
  test("names the real metrics.enabled knob", () => {
    assert.ok(/metrics\.enabled/.test(html));
  });
  test("does not name the fictional flag", () => assertNoFictionalFlag(html));
  test("points at router-config.yaml and offers an open action", () => {
    assert.ok(/router-config\.yaml/.test(html));
    assert.ok(/data-cmd="openConfig"/.test(html));
  });
});

suite("dashboardHtml — D5 empty state", () => {
  const fresh: StalenessResult = { stale: false, ageDays: 3, reviewFrequencyDays: 30 };
  const html = emptyStateHtml(NONCE, CSP, "/repo/ai_router/router-metrics.jsonl", stalenessBannerHtml(fresh));
  test("distinguishes empty from disabled (no fictional flag)", () => assertNoFictionalFlag(html));
  test("names the real metrics path it reads", () => {
    assert.ok(/router-metrics\.jsonl/.test(html));
  });
  test("says metrics are enabled but nothing logged yet", () => {
    assert.ok(/no routed calls have been recorded/i.test(html));
  });
});

suite("dashboardHtml — no-router defensive state", () => {
  const html = noRouterHtml(NONCE, CSP);
  test("explains absence honestly, no fictional flag", () => {
    assert.ok(/does not route/i.test(html));
    assertNoFictionalFlag(html);
  });
});

suite("dashboardHtml — D4 staleness banner", () => {
  test("empty string when fresh", () => {
    assert.strictEqual(stalenessBannerHtml({ stale: false, ageDays: 1, reviewFrequencyDays: 30 }), "");
  });
  test("renders banner + update action when stale", () => {
    const html = stalenessBannerHtml({ stale: true, ageDays: 42, reviewFrequencyDays: 30 });
    assert.ok(/stale/i.test(html));
    assert.ok(/42 days ago/.test(html));
    assert.ok(/data-cmd="updateRates"/.test(html));
  });
  test("handles unknown age (null) without crashing", () => {
    const html = stalenessBannerHtml({ stale: true, ageDays: null, reviewFrequencyDays: 30 });
    assert.ok(/no recorded review date/i.test(html));
    assert.ok(/data-cmd="updateRates"/.test(html));
  });
});

suite("CostDashboard — D6 config anchor resolution", () => {
  const yaml = [
    "metadata:",
    '  pricing_reviewed: "2026-04-20"',
    "  review_frequency_days: 30",
    "providers:",
    "  anthropic:",
    "metrics:",
    "  enabled: true",
    "  log_filename: router-metrics.jsonl",
  ].join("\n");

  test("metadata anchor lands on pricing_reviewed", () => {
    assert.strictEqual(findConfigAnchorLine(yaml, "metadata"), 1);
  });
  test("metrics anchor lands on metrics.enabled", () => {
    assert.strictEqual(findConfigAnchorLine(yaml, "metrics"), 6);
  });
  test("missing block → -1 (open at top)", () => {
    assert.strictEqual(findConfigAnchorLine("nothing: here\n", "metadata"), -1);
  });
});

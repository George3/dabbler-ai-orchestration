// Set 052 S2 — shared router-capability + cost-config resolution.
//
// This module is the single source of truth the cost surface uses to
// answer three questions, all from the workspace's
// `ai_router/router-config.yaml`:
//
//   1. Does this workspace *route* (and therefore produce cost data)?
//      → `routesCost()` / `findAiRouterDir()` — the D3 tier gate. A
//        Lightweight repo has no `ai_router/router-config.yaml`, so the
//        cost icon/command is contributed only when this resolves.
//   2. Where does the router actually *write* its metrics?
//      → `readRouterConfig().metricsPath` — resolved from
//        `metrics.log_filename` (default `router-metrics.jsonl`), NOT the
//        pre-Set-052 hardcoded `metrics.jsonl`. This read/write path
//        mismatch was the root cause of the dead dashboard (S1 verdict
//        D1). The reader (`utils/metrics.ts`) and the CSV export both go
//        through here so there is exactly one resolution path.
//   3. Are the cost *rate estimates* stale?
//      → `computeStaleness()` — reuses the existing
//        `metadata.pricing_reviewed` + `review_frequency_days` knobs that
//        `config.py:_check_pricing_staleness` already keys off, so the
//        extension and the router share one staleness definition (D4).
//
// Deliberately free of any `vscode` import so it is unit-testable under
// the `test:unit` mocha harness without the editor host.

import * as fs from "fs";
import * as path from "path";
import * as YAML from "yaml";

export const DEFAULT_METRICS_FILENAME = "router-metrics.jsonl";
export const DEFAULT_REVIEW_FREQUENCY_DAYS = 30;

export interface RouterConfigInfo {
  /** Absolute path to the resolved `router-config.yaml`. */
  configPath: string;
  /** Absolute path to the workspace `ai_router/` directory. */
  aiRouterDir: string;
  /** `metrics.enabled` — defaults to `true` when the key is absent
   *  (matches `metrics.py:_metrics_enabled`). */
  metricsEnabled: boolean;
  /** `metrics.log_filename` — defaults to `router-metrics.jsonl`. */
  metricsFilename: string;
  /** Absolute path to the metrics log the router actually writes. */
  metricsPath: string;
  /** `metadata.pricing_reviewed` (ISO date) or null when absent/invalid. */
  pricingReviewed: string | null;
  /** `metadata.review_frequency_days` — defaults to 30. */
  reviewFrequencyDays: number;
}

/**
 * Resolve the workspace `ai_router/` directory IFF it carries a
 * `router-config.yaml`. This is the router-capability signal (D3):
 * folder existence alone is insufficient — a workspace that merely has
 * an empty `ai_router/` (or none at all, i.e. Lightweight) is not
 * routing and must not surface the cost icon. Mirrors the walk semantics
 * of `config.py:_find_workspace_config` at the single-root level the
 * dashboard operates on.
 */
export function findAiRouterDir(workspaceRoot: string): string | null {
  const candidate = path.join(workspaceRoot, "ai_router");
  try {
    if (fs.existsSync(path.join(candidate, "router-config.yaml"))) {
      return candidate;
    }
  } catch {
    // Permission error etc. — treat as "no router signal".
  }
  return null;
}

/**
 * True when the workspace can produce cost data — the D3 gate predicate
 * the extension projects into the `dabblerSessionSets.routesCost`
 * context key.
 */
export function routesCost(workspaceRoot: string): boolean {
  return findAiRouterDir(workspaceRoot) !== null;
}

/**
 * Read the cost-relevant knobs out of `router-config.yaml`. Returns null
 * when the workspace does not route (no resolvable config). When the
 * file exists but is unreadable/unparseable, we still return a record
 * (router IS capable) populated with safe defaults — the gate should not
 * flicker off just because the YAML momentarily fails to parse mid-edit.
 */
export function readRouterConfig(workspaceRoot: string): RouterConfigInfo | null {
  const aiRouterDir = findAiRouterDir(workspaceRoot);
  if (!aiRouterDir) return null;
  const configPath = path.join(aiRouterDir, "router-config.yaml");

  let doc: unknown = {};
  try {
    doc = YAML.parse(fs.readFileSync(configPath, "utf8")) ?? {};
  } catch {
    doc = {};
  }
  const root = (doc && typeof doc === "object" ? (doc as Record<string, unknown>) : {});
  const metricsCfg = asRecord(root.metrics);
  const metadataCfg = asRecord(root.metadata);

  const metricsEnabled = metricsCfg.enabled !== false; // default true
  const rawFilename = metricsCfg.log_filename;
  const metricsFilename =
    typeof rawFilename === "string" && rawFilename.trim()
      ? rawFilename.trim()
      : DEFAULT_METRICS_FILENAME;

  const rawReviewed = metadataCfg.pricing_reviewed;
  const pricingReviewed =
    typeof rawReviewed === "string" && rawReviewed.trim() ? rawReviewed.trim() : null;

  const rawFreq = metadataCfg.review_frequency_days;
  const reviewFrequencyDays =
    typeof rawFreq === "number" && rawFreq > 0 ? rawFreq : DEFAULT_REVIEW_FREQUENCY_DAYS;

  return {
    configPath,
    aiRouterDir,
    metricsEnabled,
    metricsFilename,
    metricsPath: path.join(aiRouterDir, metricsFilename),
    pricingReviewed,
    reviewFrequencyDays,
  };
}

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

export interface StalenessResult {
  /** True when the rate estimates are older than the review frequency,
   *  OR when `pricing_reviewed` is missing/invalid (D4: unknown = stale). */
  stale: boolean;
  /** Whole days since `pricing_reviewed`, or null when it is
   *  missing/invalid. */
  ageDays: number | null;
  /** The threshold used (echoes `reviewFrequencyDays`). */
  reviewFrequencyDays: number;
}

/**
 * Compute rate-estimate staleness in-extension from the same metadata
 * `config.py` keys off (D4). Missing or unparseable `pricing_reviewed`
 * is treated as stale so a freshly-bootstrapped config still prompts a
 * review rather than silently claiming the rates are current.
 */
export function computeStaleness(
  info: RouterConfigInfo,
  now: Date = new Date(),
): StalenessResult {
  const reviewFrequencyDays = info.reviewFrequencyDays;
  if (!info.pricingReviewed) {
    return { stale: true, ageDays: null, reviewFrequencyDays };
  }
  const reviewed = new Date(`${info.pricingReviewed}T00:00:00Z`);
  if (Number.isNaN(reviewed.getTime())) {
    return { stale: true, ageDays: null, reviewFrequencyDays };
  }
  const ageDays = Math.floor((now.getTime() - reviewed.getTime()) / 86_400_000);
  return { stale: ageDays > reviewFrequencyDays, ageDays, reviewFrequencyDays };
}

// --- Three honest dashboard states (D5) ---------------------------------
// The dead-icon era rendered a single "go set a fictional flag"
// placeholder for every non-data condition. Cost surfaces now resolve to
// one of four discrete states; the renderer maps each to honest copy.
export type CostStateKind = "no-router" | "disabled" | "empty" | "data";

export interface CostState {
  kind: CostStateKind;
}

/**
 * Pure state selector shared by the renderer and its tests. `info` is
 * null only when the gate failed (defensive — the command is gated off
 * in that case). `entryCount` is the number of metrics records read from
 * the resolved metrics path.
 */
export function selectCostState(
  info: RouterConfigInfo | null,
  entryCount: number,
): CostState {
  if (!info) return { kind: "no-router" };
  if (!info.metricsEnabled) return { kind: "disabled" };
  if (entryCount <= 0) return { kind: "empty" };
  return { kind: "data" };
}

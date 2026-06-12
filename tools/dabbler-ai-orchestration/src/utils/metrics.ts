import * as fs from "fs";
import { MetricsEntry, CostSummary } from "../types";
import { readRouterConfig } from "./routerConfig";

/**
 * Read the metrics log the router actually writes for *workspaceRoot*.
 *
 * Set 052 S2 (root-cause fix, D1): the path is resolved from
 * `router-config.yaml`'s `metrics.log_filename` (default
 * `router-metrics.jsonl`) via the shared `readRouterConfig` helper —
 * NOT the pre-Set-052 hardcoded `ai_router/metrics.jsonl`, which the
 * router never wrote to, leaving the dashboard permanently empty. The
 * CSV export reads through the same path so the two cannot drift.
 *
 * Returns [] when the workspace does not route (no resolvable config).
 */
export function readMetrics(workspaceRoot: string): MetricsEntry[] {
  const info = readRouterConfig(workspaceRoot);
  if (!info) return [];
  return readMetricsFromPath(info.metricsPath);
}

/**
 * Normalize a logged `session_set` value to the bare session-set
 * FOLDER NAME (operator report, 2026-06-12).
 *
 * Historical log lines carry the field in four shapes — the slug, a
 * repo-relative `docs/session-sets/<slug>`, an absolute set-dir path
 * (either drive-letter casing; the extension spawns the CLIs with
 * absolute paths), and null. Rendering the raw values fragmented one
 * set's spend across up to three table rows, and the absolute-path
 * rows displayed as unreadable machine paths — burying every recent
 * set behind path prefixes (the "dashboard stops at Set 036" effect).
 * Normalizing at parse time merges the shapes into one slug-keyed row
 * everywhere downstream, and keeps machine-specific absolute paths
 * out of the CSV export (which lands in the workspace and can be
 * committed). The on-disk log is untouched; ai_router ≥0.18 also
 * normalizes at the write boundary.
 */
export function sessionSetDisplayName(raw: unknown): string {
  if (typeof raw !== "string") return "(no session set)";
  const parts = raw.split(/[\\/]+/).filter((p) => p.trim().length > 0);
  const name = parts.length > 0 ? parts[parts.length - 1].trim() : "";
  return name === "" ? "(no session set)" : name;
}

/** Parse a metrics JSONL file by absolute path. Skips blank/unparseable
 *  lines and `adjudication` records (no model, zero cost — bookkeeping,
 *  not spend). `session_set` is normalized to the bare folder name (see
 *  sessionSetDisplayName). */
export function readMetricsFromPath(metricsPath: string): MetricsEntry[] {
  if (!fs.existsSync(metricsPath)) return [];
  try {
    const lines = fs.readFileSync(metricsPath, "utf8").split(/\r?\n/).filter(Boolean);
    return lines
      .map((line) => {
        try { return JSON.parse(line) as MetricsEntry; }
        catch { return null; }
      })
      .filter((e): e is MetricsEntry => e !== null && e.call_type !== "adjudication" && !!e.model)
      .map((e) => ({ ...e, session_set: sessionSetDisplayName(e.session_set) }));
  } catch {
    return [];
  }
}

export function summarizeMetrics(entries: MetricsEntry[]): CostSummary {
  const bySessionSet: CostSummary["bySessionSet"] = {};
  const byModel: Record<string, number> = {};
  const dailyMap: Record<string, number> = {};

  for (const e of entries) {
    // Per session-set
    if (!bySessionSet[e.session_set]) {
      bySessionSet[e.session_set] = { sessions: 0, cost: 0, lastRun: "" };
    }
    bySessionSet[e.session_set].sessions++;
    bySessionSet[e.session_set].cost += e.cost_usd;
    if (e.timestamp > bySessionSet[e.session_set].lastRun) {
      bySessionSet[e.session_set].lastRun = e.timestamp;
    }

    // Per model
    byModel[e.model] = (byModel[e.model] ?? 0) + e.cost_usd;

    // Daily
    const day = e.timestamp.slice(0, 10);
    dailyMap[day] = (dailyMap[day] ?? 0) + e.cost_usd;
  }

  const today = new Date();
  const dailyCosts = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (29 - i));
    const dateStr = d.toISOString().slice(0, 10);
    return { date: dateStr, cost: dailyMap[dateStr] ?? 0 };
  });

  return {
    totalCost: entries.reduce((s, e) => s + e.cost_usd, 0),
    bySessionSet,
    byModel,
    dailyCosts,
  };
}

export function buildSparkline(dailyCosts: Array<{ date: string; cost: number }>): string {
  const BLOCKS = "▁▂▃▄▅▆▇█";
  const values = dailyCosts.map((d) => d.cost);
  const max = Math.max(...values, 0.0001);
  return values
    .map((v) => BLOCKS[Math.min(7, Math.floor((v / max) * 7.99))])
    .join("");
}

export function exportToCsv(entries: MetricsEntry[]): string {
  const header = "session_set,session_number,model,effort,input_tokens,output_tokens,cost_usd,timestamp";
  const rows = entries.map((e) =>
    [
      e.session_set,
      e.session_number,
      e.model,
      e.effort,
      e.input_tokens,
      e.output_tokens,
      e.cost_usd.toFixed(4),
      e.timestamp,
    ].join(",")
  );
  return [header, ...rows].join("\n");
}

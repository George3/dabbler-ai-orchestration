/**
 * Q4 spike — joiner sketch in TypeScript (inside extension, sibling
 * candidate to `tools/dabbler-ai-orchestration/src/`).
 *
 * Set 045 / Session 1 spike. Throwaway sketch — kept for reference.
 *
 * Same conflict scenario as the Python sibling
 * (`joiner_python_sketch.py`): orchestrator-engine mismatch. The
 * state file says one engine is checked out; the native log shows a
 * different engine active in the same workspace within the conflict
 * window.
 *
 * Run (from the tools/dabbler-ai-orchestration directory so the
 * extension's ts-node + tsconfig pick up):
 *   npx ts-node --transpile-only ../../docs/session-sets/045-log-harvest-implementation/spike-prototypes/joiner_typescript_sketch.ts
 */

import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

// ---------------------------------------------------------------------------
// Path canonicalization (mirror Python).
// ---------------------------------------------------------------------------

function canonicalizeCwd(cwd: string): string {
  if (!cwd) return "";
  return cwd.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}

function parseIso(ts: string): Date {
  // Tolerate trailing Z (Date handles it natively).
  return new Date(ts);
}

// ---------------------------------------------------------------------------
// Native-log scrapers.
// ---------------------------------------------------------------------------

interface NativeSession {
  engine: "claude" | "copilot";
  convId: string;
  firstEventTs: Date;
  cwdCanonical: string;
  sourceFile: string;
  cwdSource: "jsonl-field" | "slug-fallback" | "context";
}

function* scanClaudeLogs(root: string): IterableIterator<NativeSession> {
  if (!fs.existsSync(root)) return;
  for (const workspaceName of fs.readdirSync(root)) {
    const workspaceDir = path.join(root, workspaceName);
    if (!fs.statSync(workspaceDir).isDirectory()) continue;
    for (const fname of fs.readdirSync(workspaceDir)) {
      if (!fname.endsWith(".jsonl")) continue;
      const jsonlPath = path.join(workspaceDir, fname);
      const convId = fname.slice(0, -".jsonl".length);
      let firstTs: Date | null = null;
      let cwdField: string | null = null;
      try {
        const content = fs.readFileSync(jsonlPath, "utf-8");
        for (const line of content.split(/\r?\n/)) {
          if (!line.trim()) continue;
          let rec: any;
          try { rec = JSON.parse(line); } catch { continue; }
          if (!firstTs && rec.timestamp) {
            const d = parseIso(rec.timestamp);
            if (!Number.isNaN(d.getTime())) firstTs = d;
          }
          if (!cwdField && rec.cwd) cwdField = rec.cwd;
          if (firstTs && cwdField) break;
        }
      } catch { continue; }
      if (!firstTs) continue;
      yield {
        engine: "claude",
        convId,
        firstEventTs: firstTs,
        cwdCanonical: cwdField ? canonicalizeCwd(cwdField) : "",
        sourceFile: jsonlPath,
        cwdSource: cwdField ? "jsonl-field" : "slug-fallback",
      };
    }
  }
}

function* scanCopilotLogs(root: string): IterableIterator<NativeSession> {
  if (!fs.existsSync(root)) return;
  for (const sessName of fs.readdirSync(root)) {
    const sessDir = path.join(root, sessName);
    if (!fs.statSync(sessDir).isDirectory()) continue;
    const events = path.join(sessDir, "events.jsonl");
    if (!fs.existsSync(events)) continue;
    let first: any;
    try {
      const content = fs.readFileSync(events, "utf-8");
      const firstLine = content.split(/\r?\n/, 1)[0];
      if (!firstLine) continue;
      first = JSON.parse(firstLine);
    } catch { continue; }
    if (first?.type !== "session.start") continue;
    const data = first.data ?? {};
    const convId = data.sessionId ?? sessName;
    const startTs = data.startTime ?? first.timestamp;
    if (!startTs) continue;
    const d = parseIso(startTs);
    if (Number.isNaN(d.getTime())) continue;
    yield {
      engine: "copilot",
      convId,
      firstEventTs: d,
      cwdCanonical: data.context?.cwd ? canonicalizeCwd(data.context.cwd) : "",
      sourceFile: events,
      cwdSource: "context",
    };
  }
}

// ---------------------------------------------------------------------------
// Engine-mismatch detector.
// ---------------------------------------------------------------------------

interface ConflictReport {
  kind: "engine-mismatch";
  setSlug: string;
  stateFile: string;
  stateOrchestratorEngine: string | null;
  nativeEngine: string;
  nativeConvId: string;
  nativeSource: string;
  notes: string;
}

function detectEngineMismatch(
  stateFile: string,
  natives: NativeSession[],
  workspaceCwdCanonical: string,
  windowMs: number = 60 * 60 * 1000,
): ConflictReport[] {
  let state: any;
  try {
    state = JSON.parse(fs.readFileSync(stateFile, "utf-8"));
  } catch { return []; }
  const orch = state.orchestrator ?? {};
  const stateEngine: string | undefined = orch.engine;
  if (!stateEngine) return [];
  const lastActivityStr: string | undefined = orch.lastActivityAt ?? state.startedAt;
  if (!lastActivityStr) return [];
  const lastActivity = parseIso(lastActivityStr);
  if (Number.isNaN(lastActivity.getTime())) return [];
  const setSlug = state.sessionSetName ?? path.basename(path.dirname(stateFile));

  const stateEngineNorm = stateEngine.toLowerCase().split("-")[0];
  const conflicts: ConflictReport[] = [];
  for (const ns of natives) {
    if (ns.cwdCanonical !== workspaceCwdCanonical) continue;
    const delta = Math.abs(ns.firstEventTs.getTime() - lastActivity.getTime());
    if (delta > windowMs) continue;
    if (ns.engine.toLowerCase() === stateEngine.toLowerCase()) continue;
    if (ns.engine.toLowerCase() === stateEngineNorm) continue;
    conflicts.push({
      kind: "engine-mismatch",
      setSlug,
      stateFile,
      stateOrchestratorEngine: stateEngine,
      nativeEngine: ns.engine,
      nativeConvId: ns.convId,
      nativeSource: ns.sourceFile,
      notes: `native session within ${Math.round(delta / 1000)}s of last checkout activity`,
    });
  }
  return conflicts;
}

// ---------------------------------------------------------------------------
// Demo (mirror Python).
// ---------------------------------------------------------------------------

function demo() {
  const t0 = performance.now();
  const home = os.homedir();
  const claudeRoot = path.join(home, ".claude", "projects");
  const copilotRoot = path.join(home, ".copilot", "session-state");

  const natives: NativeSession[] = [];
  for (const ns of scanClaudeLogs(claudeRoot)) natives.push(ns);
  for (const ns of scanCopilotLogs(copilotRoot)) natives.push(ns);
  const tScan = (performance.now() - t0) / 1000;

  // The repo root is 4 levels up from this script
  // (.../docs/session-sets/045-.../spike-prototypes/joiner_typescript_sketch.ts).
  const repoRoot = path.resolve(__dirname, "..", "..", "..", "..");
  const realStateFile = path.join(
    repoRoot, "docs", "session-sets",
    "045-log-harvest-implementation", "session-state.json",
  );
  const workspaceCwdCanonical = canonicalizeCwd(repoRoot);

  // Synthetic patched state: pretend Copilot is checked out.
  const realState = JSON.parse(fs.readFileSync(realStateFile, "utf-8"));
  const patched = { ...realState, orchestrator: { ...(realState.orchestrator ?? {}), engine: "copilot" } };
  const tmpPath = path.join(__dirname, "synthetic_conflict_state_ts.json");
  fs.writeFileSync(tmpPath, JSON.stringify(patched, null, 2), "utf-8");

  const t1 = performance.now();
  const synthetic = detectEngineMismatch(tmpPath, natives, workspaceCwdCanonical);
  const tDetect = (performance.now() - t1) / 1000;

  const t2 = performance.now();
  const control = detectEngineMismatch(realStateFile, natives, workspaceCwdCanonical);
  const tControl = (performance.now() - t2) / 1000;

  const report = {
    language: "typescript",
    n_native_sessions_scanned: natives.length,
    scan_seconds: Number(tScan.toFixed(4)),
    detect_seconds_synthetic_conflict: Number(tDetect.toFixed(4)),
    detect_seconds_control: Number(tControl.toFixed(4)),
    synthetic_conflicts_found: synthetic,
    control_conflicts_found: control,
  };

  const outPath = path.join(__dirname, "joiner_typescript_report.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Wrote ${outPath}`);
  console.log(`Scanned: ${report.n_native_sessions_scanned} native sessions in ${report.scan_seconds}s`);
  console.log(`Synthetic conflicts: ${report.synthetic_conflicts_found.length}`);
  console.log(`Control conflicts: ${report.control_conflicts_found.length}`);
}

demo();

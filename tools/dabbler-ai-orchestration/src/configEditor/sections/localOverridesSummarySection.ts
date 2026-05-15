import { SectionState, SectionRenderResult } from "./types";
import { escapeHtml, getByPath } from "./helpers";

/**
 * §6 Local overrides summary.
 *
 * Read-only listing of every path in `local-overrides.yaml`, side-by-side
 * with the corresponding shared value (from router-config.yaml /
 * budget.yaml) where one exists. Includes "Open local-overrides.yaml"
 * buttons that post a message to the host.
 *
 * This section never WRITES — to edit, operators use the relevant feature
 * section (Routing / Budget / Providers / etc.) or hand-edit the YAML.
 */
export function render(state: SectionState): SectionRenderResult {
  const { localOverrides, localOverridesFileExists } = state;

  if (!localOverridesFileExists) {
    return {
      html: `
<div class="section-block">
  <h3>No local overrides on this machine</h3>
  <p class="section-info">
    <code>ai_router/local-overrides.yaml</code> does not exist yet. The file is in
    <code>.gitignore</code> by design — when you set a per-operator override in
    Routing / Budget / Providers / Notifications, the webview creates it on Save.
  </p>
</div>
`,
    };
  }

  const rows = collectOverrideRows(localOverrides as Record<string, unknown> | null, state);

  if (rows.length === 0) {
    return {
      html: `
<div class="section-block">
  <h3>Local overrides summary</h3>
  <p class="section-info">
    <code>local-overrides.yaml</code> exists but contains no override entries.
    All effective config comes from the shared YAML files.
  </p>
  <button type="button" id="s6-open-local-overrides" class="secondary">Open local-overrides.yaml</button>
</div>
`,
    };
  }

  const rowsHtml = rows
    .map((r) => `
<li class="override-row">
  <div class="override-path"><code>${escapeHtml(r.path)}</code></div>
  <div class="override-side">
    <strong>Shared:</strong>
    <code>${escapeHtml(r.sharedDisplay)}</code>
  </div>
  <div class="override-side">
    <strong>Local:</strong>
    <code>${escapeHtml(r.localDisplay)}</code>
  </div>
</li>
`)
    .join("\n");

  const html = `
<div class="section-block">
  <h3>These settings differ from the shared (committed) configuration</h3>
  <ul class="override-list">
    ${rowsHtml}
  </ul>
  <p class="section-info">
    &#9432; <code>local-overrides.yaml</code> is in your <code>.gitignore</code> — values here are
    personal to your machine and never get pushed to the repo.
  </p>
  <button type="button" id="s6-open-local-overrides" class="secondary">Open local-overrides.yaml directly</button>
</div>
`;
  return { html };
}

interface OverrideRow {
  path: string;
  sharedDisplay: string;
  localDisplay: string;
}

function collectOverrideRows(
  localOverrides: Record<string, unknown> | null,
  state: SectionState
): OverrideRow[] {
  if (!localOverrides) return [];
  const rows: OverrideRow[] = [];
  walk(localOverrides, [], (path, value) => {
    // Look up the corresponding shared value. routing/providers come from
    // router-config; threshold_usd/warn_at_percent come from budget;
    // notifications & decision_review have no shared analog.
    const dotted = path.join(".");
    const sharedSource = pickSharedSource(path[0]);
    const sharedVal =
      sharedSource === "routerConfig"
        ? getByPath(state.routerConfig, dotted)
        : sharedSource === "budget"
          ? getByPath(state.budget, dotted)
          : undefined;
    rows.push({
      path: dotted,
      sharedDisplay: sharedSource === "none" ? "(local-only section)" : formatValue(sharedVal),
      localDisplay: formatValue(value),
    });
  });
  return rows;
}

function pickSharedSource(topKey: string | undefined): "routerConfig" | "budget" | "none" {
  if (topKey === "routing" || topKey === "providers" || topKey === "models") return "routerConfig";
  if (topKey === "threshold_usd" || topKey === "warn_at_percent" || topKey === "scope") return "budget";
  return "none"; // notifications, decision_review — no shared analog
}

function formatValue(v: unknown): string {
  if (v === undefined) return "(not set, defaults apply)";
  if (v === null) return "null";
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return String(v);
  return JSON.stringify(v);
}

/**
 * Recursively walk an object emitting leaf paths. Stops descent at
 * non-object values; an object value passed in as a wholesale override
 * (e.g. providers.openai = { ... }) is treated as one leaf.
 */
function walk(
  obj: Record<string, unknown>,
  prefix: string[],
  emit: (path: string[], value: unknown) => void
): void {
  for (const [k, v] of Object.entries(obj)) {
    const path = [...prefix, k];
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      walk(v as Record<string, unknown>, path, emit);
    } else {
      emit(path, v);
    }
  }
}

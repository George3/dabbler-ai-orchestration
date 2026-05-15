import { SectionState, SectionRenderResult, FieldSource } from "./types";
import { asString, envVarBadge, escapeHtml, fieldSource, getByPath, indicatorHtml } from "./helpers";

interface ResolvedProviderRow {
  id: string;
  displayLabel: string;
  enabled: boolean;
  enabledSource: FieldSource;
  apiKeyEnv: string;
  apiKeyEnvSource: FieldSource;
  baseUrl: string;
  baseUrlSource: FieldSource;
}

/**
 * §3 Providers.
 *
 * Variable-length table with one row per `providers.<id>` entry.
 * Columns per wireframes §3: enabled checkbox, display label, ID
 * (read-only), api_key_env input + ✓/(unset) badge, base_url, and a
 * `[...]` button that toggles a popover for the less-common fields.
 *
 * Appendix B:
 * - providers.<id>.enabled / api_key_env / base_url are locally overridable
 * - providers.<id>.display_label is NOT locally overridable
 */
export function render(state: SectionState): SectionRenderResult {
  const sharedProviders =
    state.routerConfig && typeof state.routerConfig === "object"
      ? (state.routerConfig["providers"] as Record<string, unknown> | undefined)
      : undefined;

  const rows: ResolvedProviderRow[] = [];
  if (sharedProviders && typeof sharedProviders === "object") {
    for (const id of Object.keys(sharedProviders)) {
      rows.push(resolveRow(state, id));
    }
  }

  const tableRows = rows.map((row) => renderRow(state, row)).join("\n");

  const html = `
<div class="section-block">
  <h3>AI providers configured for this project</h3>
  <p class="section-help">One row per <code>providers</code> entry in <code>router-config.yaml</code>. Local overrides for <em>enabled</em>, <em>api_key_env</em>, and <em>base_url</em> live in <code>local-overrides.yaml</code> per Appendix B.</p>

  <table class="provider-table" id="s3-providers">
    <thead>
      <tr>
        <th>On?</th>
        <th>Display label</th>
        <th>ID</th>
        <th>API key env var</th>
        <th>API URL</th>
        <th>Edit</th>
      </tr>
    </thead>
    <tbody>
      ${tableRows || `<tr><td colspan="6" class="placeholder">No providers configured. Hand-edit ai_router/router-config.yaml to add providers.</td></tr>`}
    </tbody>
  </table>

  <p class="legend">
    <span class="env-badge env-set">&#10003;</span> env var is set in the current environment &nbsp;|&nbsp;
    <span class="env-badge env-unset">(unset)</span> env var name is configured but not present.
    <br/>
    <em>Tip: The webview never shows env-var <strong>values</strong> — only names + presence.</em>
  </p>
</div>
`;
  return { html };
}

function resolveRow(state: SectionState, id: string): ResolvedProviderRow {
  const sharedPath = (k: string) => `providers.${id}.${k}`;

  const sharedEnabled = getByPath(state.routerConfig, sharedPath("enabled"));
  const localEnabled = getByPath(state.localOverrides, sharedPath("enabled"));
  const enabled = typeof localEnabled === "boolean"
    ? localEnabled
    : typeof sharedEnabled === "boolean"
      ? sharedEnabled
      : true;
  const enabledSource = fieldSource(state, "routerConfig", sharedPath("enabled"), sharedPath("enabled"), true);

  const displayLabel = asString(getByPath(state.routerConfig, sharedPath("display_label")) ?? toTitle(id));

  const sharedKey = getByPath(state.routerConfig, sharedPath("api_key_env"));
  const localKey = getByPath(state.localOverrides, sharedPath("api_key_env"));
  const apiKeyEnv = asString(
    typeof localKey === "string" && localKey.length > 0
      ? localKey
      : typeof sharedKey === "string" ? sharedKey : ""
  );
  const apiKeyEnvSource = fieldSource(state, "routerConfig", sharedPath("api_key_env"), sharedPath("api_key_env"), true);

  const sharedUrl = getByPath(state.routerConfig, sharedPath("base_url"));
  const localUrl = getByPath(state.localOverrides, sharedPath("base_url"));
  const baseUrl = asString(typeof localUrl === "string" ? localUrl : typeof sharedUrl === "string" ? sharedUrl : "");
  const baseUrlSource = fieldSource(state, "routerConfig", sharedPath("base_url"), sharedPath("base_url"), true);

  return { id, displayLabel, enabled, enabledSource, apiKeyEnv, apiKeyEnvSource, baseUrl, baseUrlSource };
}

function renderRow(state: SectionState, row: ResolvedProviderRow): string {
  return `
<tr class="provider-row" data-provider-id="${escapeHtml(row.id)}">
  <td>
    <input type="checkbox" data-field="enabled"${row.enabled ? " checked" : ""} aria-label="Enabled" />
    ${indicatorHtml(row.enabledSource, `providers.${row.id}.enabled`)}
  </td>
  <td>
    <input type="text" data-field="displayLabel" value="${escapeHtml(row.displayLabel)}" />
  </td>
  <td>
    <code>${escapeHtml(row.id)}</code>
  </td>
  <td>
    <input type="text" data-field="apiKeyEnv" value="${escapeHtml(row.apiKeyEnv)}" pattern="^[A-Z_][A-Z0-9_]*$" />
    ${envVarBadge(state, row.apiKeyEnv)}
    ${indicatorHtml(row.apiKeyEnvSource, `providers.${row.id}.api_key_env`)}
  </td>
  <td>
    <input type="text" data-field="baseUrl" value="${escapeHtml(row.baseUrl)}" />
    ${indicatorHtml(row.baseUrlSource, `providers.${row.id}.base_url`)}
  </td>
  <td>
    <button type="button" class="secondary popover-toggle" data-target="popover-${escapeHtml(row.id)}">&hellip;</button>
  </td>
</tr>
<tr class="provider-popover" id="popover-${escapeHtml(row.id)}" style="display:none;">
  <td colspan="6">
    <p class="section-info">
      Advanced provider fields (<code>rate_limit</code>, <code>timeout_seconds</code>, <code>retry</code>)
      are not editable from the webview in v1 — they remain hand-edit-only in
      <code>router-config.yaml</code>. The webview's job is the operator-friendly surface; the
      expert surface is the YAML itself.
    </p>
  </td>
</tr>
`;
}

function toTitle(id: string): string {
  return id
    .split(/[-_]/)
    .map((p) => (p.length === 0 ? p : p[0].toUpperCase() + p.slice(1)))
    .join(" ");
}

"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.escapeHtml = escapeHtml;
exports.getByPath = getByPath;
exports.fieldSource = fieldSource;
exports.indicatorHtml = indicatorHtml;
exports.envVarBadge = envVarBadge;
exports.isOn = isOn;
exports.asString = asString;
exports.asNumber = asNumber;
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
/**
 * Walk an object by dotted path. Returns undefined for any missing segment.
 * Path segments are interpreted as object keys; no array index syntax.
 */
function getByPath(obj, path) {
    if (!obj)
        return undefined;
    const parts = path.split(".");
    let cur = obj;
    for (const p of parts) {
        if (cur === null || cur === undefined || typeof cur !== "object")
            return undefined;
        cur = cur[p];
    }
    return cur;
}
/**
 * Determine where the effective value of an Appendix-B-allowed override path
 * comes from. The `sharedPath` lives on `routerConfig` or `budget`;
 * `localPath` is the corresponding path inside `local-overrides.yaml`.
 *
 * Paths marked "Local-override allowed? No" in Appendix B should pass
 * `allowed: false` — the function returns `"not-overridable"` for those.
 */
function fieldSource(state, sharedObject, sharedPath, localPath, allowed) {
    if (!allowed)
        return "not-overridable";
    if (sharedObject === "localOnly") {
        const localVal = getByPath(state.localOverrides, localPath);
        return localVal !== undefined ? "local" : "default";
    }
    const localVal = getByPath(state.localOverrides, localPath);
    if (localVal !== undefined)
        return "local";
    const sharedVal = sharedObject === "routerConfig"
        ? getByPath(state.routerConfig, sharedPath)
        : getByPath(state.budget, sharedPath);
    return sharedVal !== undefined ? "shared" : "default";
}
/**
 * Emit the (shared) / (local override) indicator markup.
 * Includes a data-source attribute so the client-side patch builder can
 * round-trip the source through Save without re-deriving it.
 */
function indicatorHtml(source, fieldKey) {
    switch (source) {
        case "shared":
            return `<span class="src-indicator src-shared" data-source="shared" data-field="${escapeHtml(fieldKey)}" title="Value comes from the shared (committed) config. Click to move to local overrides.">(shared)</span>`;
        case "local":
            return `<span class="src-indicator src-local" data-source="local" data-field="${escapeHtml(fieldKey)}" title="Value comes from local-overrides.yaml. Click to promote to shared.">(local override)</span>`;
        case "default":
            return `<span class="src-indicator src-default" data-source="default" data-field="${escapeHtml(fieldKey)}" title="Field is using the schema default — no value in either file.">(default)</span>`;
        case "not-overridable":
            return ``;
    }
}
/** ✓ / (unset) badge for env-var-name fields. */
function envVarBadge(state, name) {
    if (!name)
        return `<span class="env-badge env-unset">(unset)</span>`;
    return state.envVarPresence[name]
        ? `<span class="env-badge env-set" title="${escapeHtml(name)} is set in your shell.">&#10003;</span>`
        : `<span class="env-badge env-unset" title="${escapeHtml(name)} is not set in your shell.">(unset)</span>`;
}
/** Bool-ish coercion that treats undefined as a definite "off". */
function isOn(v) {
    return v === true;
}
/** Coerce a value to a string for input field rendering. */
function asString(v, fallback = "") {
    if (v === undefined || v === null)
        return fallback;
    return String(v);
}
/** Coerce to a number for input field rendering; returns NaN if unparseable. */
function asNumber(v) {
    if (typeof v === "number")
        return v;
    if (typeof v === "string") {
        const n = Number(v);
        return Number.isFinite(n) ? n : NaN;
    }
    return NaN;
}
//# sourceMappingURL=helpers.js.map
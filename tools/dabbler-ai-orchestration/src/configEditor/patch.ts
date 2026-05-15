import { Document, parseDocument } from "yaml";
import * as crypto from "crypto";

/**
 * The structured payload the webview posts on Save. Each field is
 * optional so a section can omit values that haven't changed; but
 * sections currently always post their full state for simplicity.
 *
 * For overridable fields the payload includes the operator's chosen
 * `source` so the host knows which YAML file to write to. Sources
 * are limited to `"shared"` / `"local"` — `"default"` rendering is
 * UI-only and is treated as `"shared"` on save (the value gets
 * written to the shared file).
 */
export type WriteSource = "shared" | "local";

export interface OverridableValue<T> {
  value: T;
  source: WriteSource;
}

export interface ProviderPatch {
  id: string;
  removed?: boolean;
  enabled?: OverridableValue<boolean>;
  displayLabel?: string; // shared-only
  apiKeyEnv?: OverridableValue<string>;
  baseUrl?: OverridableValue<string>;
}

export interface SavePayload {
  // §1 Routing & Verification
  outsourcingMode?: OverridableValue<string>; // enum: whenever-helpful | verification-only | disabled
  verificationMethod?: string; // budget.yaml; not overridable

  // §2 Budget
  thresholdUsd?: OverridableValue<number>;
  scope?: string; // budget.yaml; not overridable
  warnAtPercent?: OverridableValue<number>;

  // §3 Providers
  providers?: ProviderPatch[];

  // §4 Significance flagging
  honorAnnotations?: boolean; // local-overrides only

  // §5 Notifications
  pushoverEnabled?: boolean;
  pushoverApiKeyEnv?: string;
  pushoverUserKeyEnv?: string;
}

/** Returned by applyPatch so the caller knows what changed. */
export interface PatchApplyResult {
  routerConfigChanged: boolean;
  budgetChanged: boolean;
  localOverridesChanged: boolean;
  /** Warning notices the operator should see but that don't block save. */
  warnings: string[];
}

/**
 * Apply a SavePayload to the three loaded YAML documents in place.
 *
 * Caller owns: validating before this call (`validateBatch`), persisting
 * after (`writeYamlFile`), and creating localOverridesDoc if it's null
 * and a write needs it.
 */
export function applyPatch(
  routerConfigDoc: Document,
  budgetDoc: Document,
  localOverridesDoc: Document,
  payload: SavePayload
): PatchApplyResult {
  const result: PatchApplyResult = {
    routerConfigChanged: false,
    budgetChanged: false,
    localOverridesChanged: false,
    warnings: [],
  };

  // --- §1 Routing & Verification ----------------------------------------
  if (payload.outsourcingMode !== undefined) {
    const { value, source } = payload.outsourcingMode;
    if (source === "local") {
      if (setIfChanged(localOverridesDoc, ["routing", "outsourcing_mode"], value)) {
        result.localOverridesChanged = true;
      }
      deleteIfPresent(routerConfigDoc, ["routing", "outsourcing_mode"], result, "routerConfigChanged");
    } else {
      if (setIfChanged(routerConfigDoc, ["routing", "outsourcing_mode"], value)) {
        result.routerConfigChanged = true;
      }
      deleteIfPresent(localOverridesDoc, ["routing", "outsourcing_mode"], result, "localOverridesChanged");
      // Clean up an empty routing: {} container in local-overrides
      pruneEmptyContainer(localOverridesDoc, ["routing"], result, "localOverridesChanged");
    }
  }
  if (payload.verificationMethod !== undefined) {
    if (setIfChanged(budgetDoc, ["verification_method"], payload.verificationMethod)) {
      result.budgetChanged = true;
    }
  }

  // --- §2 Budget --------------------------------------------------------
  if (payload.thresholdUsd !== undefined) {
    const { value, source } = payload.thresholdUsd;
    if (source === "local") {
      if (setIfChanged(localOverridesDoc, ["threshold_usd"], value)) {
        result.localOverridesChanged = true;
      }
      result.warnings.push("threshold_usd is project-canonical per Appendix B and may be rejected by the local-overrides allowlist.");
    } else {
      if (setIfChanged(budgetDoc, ["threshold_usd"], value)) {
        result.budgetChanged = true;
      }
      // Demote: if a local override existed, remove it so the shared
      // value actually takes effect after the merge.
      deleteIfPresent(localOverridesDoc, ["threshold_usd"], result, "localOverridesChanged");
    }
  }
  if (payload.scope !== undefined) {
    if (setIfChanged(budgetDoc, ["scope"], payload.scope)) {
      result.budgetChanged = true;
    }
  }
  if (payload.warnAtPercent !== undefined) {
    const { value, source } = payload.warnAtPercent;
    if (source === "local") {
      if (setIfChanged(localOverridesDoc, ["warn_at_percent"], value)) {
        result.localOverridesChanged = true;
      }
      result.warnings.push("warn_at_percent is project-canonical per Appendix B and may be rejected by the local-overrides allowlist.");
    } else {
      if (setIfChanged(budgetDoc, ["warn_at_percent"], value)) {
        result.budgetChanged = true;
      }
      // Demote: remove any local override so the shared value wins.
      deleteIfPresent(localOverridesDoc, ["warn_at_percent"], result, "localOverridesChanged");
    }
  }

  // --- §3 Providers -----------------------------------------------------
  if (payload.providers !== undefined) {
    for (const p of payload.providers) {
      if (p.removed) {
        deleteIfPresent(routerConfigDoc, ["providers", p.id], result, "routerConfigChanged");
        deleteIfPresent(localOverridesDoc, ["providers", p.id], result, "localOverridesChanged");
        pruneEmptyContainer(localOverridesDoc, ["providers"], result, "localOverridesChanged");
        continue;
      }
      if (p.displayLabel !== undefined) {
        if (setIfChanged(routerConfigDoc, ["providers", p.id, "display_label"], p.displayLabel)) {
          result.routerConfigChanged = true;
        }
      }
      if (p.enabled !== undefined) {
        applyOverridableField(
          routerConfigDoc,
          localOverridesDoc,
          ["providers", p.id, "enabled"],
          p.enabled.value,
          p.enabled.source,
          result
        );
      }
      if (p.apiKeyEnv !== undefined) {
        applyOverridableField(
          routerConfigDoc,
          localOverridesDoc,
          ["providers", p.id, "api_key_env"],
          p.apiKeyEnv.value,
          p.apiKeyEnv.source,
          result
        );
      }
      if (p.baseUrl !== undefined) {
        applyOverridableField(
          routerConfigDoc,
          localOverridesDoc,
          ["providers", p.id, "base_url"],
          p.baseUrl.value,
          p.baseUrl.source,
          result
        );
      }
    }
    // After provider edits, prune empty containers in local-overrides
    pruneEmptyProvidersBlock(localOverridesDoc, result);
  }

  // --- §4 Significance flagging ----------------------------------------
  if (payload.honorAnnotations !== undefined) {
    if (setIfChanged(localOverridesDoc, ["decision_review", "honor_annotations"], payload.honorAnnotations)) {
      result.localOverridesChanged = true;
    }
  }

  // --- §5 Notifications ------------------------------------------------
  // These three live exclusively in local-overrides per Appendix B.
  if (payload.pushoverEnabled !== undefined) {
    if (setIfChanged(localOverridesDoc, ["notifications", "pushover", "enabled"], payload.pushoverEnabled)) {
      result.localOverridesChanged = true;
    }
  }
  if (payload.pushoverApiKeyEnv !== undefined) {
    if (setIfChanged(localOverridesDoc, ["notifications", "pushover", "api_key_env"], payload.pushoverApiKeyEnv)) {
      result.localOverridesChanged = true;
    }
  }
  if (payload.pushoverUserKeyEnv !== undefined) {
    if (setIfChanged(localOverridesDoc, ["notifications", "pushover", "user_key_env"], payload.pushoverUserKeyEnv)) {
      result.localOverridesChanged = true;
    }
  }

  return result;
}

/**
 * Apply a field that has both shared and local-override homes. Writing to
 * one side cleans up the other so the file-of-record stays unambiguous.
 */
function applyOverridableField(
  routerConfigDoc: Document,
  localOverridesDoc: Document,
  path: (string | number)[],
  value: unknown,
  source: WriteSource,
  result: PatchApplyResult
): void {
  if (source === "local") {
    if (setIfChanged(localOverridesDoc, path, value)) {
      result.localOverridesChanged = true;
    }
    deleteIfPresent(routerConfigDoc, path, result, "routerConfigChanged");
  } else {
    if (setIfChanged(routerConfigDoc, path, value)) {
      result.routerConfigChanged = true;
    }
    deleteIfPresent(localOverridesDoc, path, result, "localOverridesChanged");
  }
}

/**
 * Set a scalar at `path` only if the current value differs. Returns true
 * iff the document was mutated. The flag-driven write-on-change pattern
 * lets the panel skip filesystem writes (and the resulting mtime bump
 * that would otherwise trip drift detection) when a Save lands an
 * effective no-op.
 */
function setIfChanged(doc: Document, path: (string | number)[], value: unknown): boolean {
  const current = doc.getIn(path);
  if (current === value) return false;
  doc.setIn(path, value);
  return true;
}

function deleteIfPresent(
  doc: Document,
  path: (string | number)[],
  result: PatchApplyResult,
  flag: "routerConfigChanged" | "budgetChanged" | "localOverridesChanged"
): void {
  if (doc.hasIn(path)) {
    doc.deleteIn(path);
    result[flag] = true;
  }
}

/** Remove a container path if it's an empty object after a delete. */
function pruneEmptyContainer(
  doc: Document,
  path: (string | number)[],
  result: PatchApplyResult,
  flag: "routerConfigChanged" | "budgetChanged" | "localOverridesChanged"
): void {
  if (!doc.hasIn(path)) return;
  const node = doc.getIn(path) as unknown;
  if (node && typeof node === "object" && "items" in (node as object)) {
    const items = (node as { items: unknown[] }).items;
    if (Array.isArray(items) && items.length === 0) {
      doc.deleteIn(path);
      result[flag] = true;
    }
  }
}

/**
 * After provider edits, walk local-overrides.providers and remove any
 * provider entry whose value is an empty map. Also remove the providers:
 * block itself if no entries remain.
 */
function pruneEmptyProvidersBlock(doc: Document, result: PatchApplyResult): void {
  const providersNode = doc.getIn(["providers"]) as unknown;
  if (!providersNode || typeof providersNode !== "object" || !("items" in (providersNode as object))) return;
  const items = (providersNode as { items: { key: { value: string } }[] }).items ?? [];
  // Iterate in reverse so deletions don't shift earlier indices.
  for (let i = items.length - 1; i >= 0; i--) {
    const key = items[i]?.key?.value;
    if (typeof key !== "string") continue;
    const providerEntry = doc.getIn(["providers", key]) as unknown;
    if (providerEntry && typeof providerEntry === "object" && "items" in (providerEntry as object)) {
      const innerItems = (providerEntry as { items: unknown[] }).items;
      if (Array.isArray(innerItems) && innerItems.length === 0) {
        doc.deleteIn(["providers", key]);
        result.localOverridesChanged = true;
      }
    }
  }
  pruneEmptyContainer(doc, ["providers"], result, "localOverridesChanged");
}

/** Stable content hash of a document's serialized form. */
export function docContentHash(doc: Document | null): string | null {
  if (!doc) return null;
  return crypto.createHash("sha256").update(doc.toString()).digest("hex");
}

/** Compute content hash for a raw string (used for read-then-compare). */
export function stringContentHash(text: string): string {
  return crypto.createHash("sha256").update(text).digest("hex");
}

/** Build an empty local-overrides Document operators can write into. */
export function emptyLocalOverridesDoc(): Document {
  // Minimal header comment so the file is self-documenting when created.
  const text = `# ai_router/local-overrides.yaml
# Machine-local overrides; this file is .gitignored.
# Appendix B (Set 025 spec) defines which paths are locally overridable.
{}
`;
  return parseDocument(text);
}

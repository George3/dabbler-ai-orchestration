import { Document } from "yaml";
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
    displayLabel?: string;
    apiKeyEnv?: OverridableValue<string>;
    baseUrl?: OverridableValue<string>;
}
export interface SavePayload {
    outsourcingMode?: OverridableValue<string>;
    verificationMethod?: string;
    thresholdUsd?: OverridableValue<number>;
    scope?: string;
    warnAtPercent?: OverridableValue<number>;
    providers?: ProviderPatch[];
    honorAnnotations?: boolean;
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
export declare function applyPatch(routerConfigDoc: Document, budgetDoc: Document, localOverridesDoc: Document, payload: SavePayload): PatchApplyResult;
/** Stable content hash of a document's serialized form. */
export declare function docContentHash(doc: Document | null): string | null;
/** Compute content hash for a raw string (used for read-then-compare). */
export declare function stringContentHash(text: string): string;
/** Build an empty local-overrides Document operators can write into. */
export declare function emptyLocalOverridesDoc(): Document;

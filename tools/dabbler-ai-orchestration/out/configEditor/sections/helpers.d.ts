import { SectionState, FieldSource } from "./types";
export declare function escapeHtml(str: string): string;
/**
 * Walk an object by dotted path. Returns undefined for any missing segment.
 * Path segments are interpreted as object keys; no array index syntax.
 */
export declare function getByPath(obj: Record<string, unknown> | null | undefined, path: string): unknown;
/**
 * Determine where the effective value of an Appendix-B-allowed override path
 * comes from. The `sharedPath` lives on `routerConfig` or `budget`;
 * `localPath` is the corresponding path inside `local-overrides.yaml`.
 *
 * Paths marked "Local-override allowed? No" in Appendix B should pass
 * `allowed: false` — the function returns `"not-overridable"` for those.
 */
export declare function fieldSource(state: SectionState, sharedObject: "routerConfig" | "budget" | "localOnly", sharedPath: string, localPath: string, allowed: boolean): FieldSource;
/**
 * Emit the (shared) / (local override) indicator markup.
 * Includes a data-source attribute so the client-side patch builder can
 * round-trip the source through Save without re-deriving it.
 */
export declare function indicatorHtml(source: FieldSource, fieldKey: string): string;
/** ✓ / (unset) badge for env-var-name fields. */
export declare function envVarBadge(state: SectionState, name: string | undefined): string;
/** Bool-ish coercion that treats undefined as a definite "off". */
export declare function isOn(v: unknown): boolean;
/** Coerce a value to a string for input field rendering. */
export declare function asString(v: unknown, fallback?: string): string;
/** Coerce to a number for input field rendering; returns NaN if unparseable. */
export declare function asNumber(v: unknown): number;

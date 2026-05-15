/**
 * Shared types for config-editor sections.
 *
 * Each section is a pure function `render(state) => { html }` that emits the
 * HTML for its panel body. State is derived once by the panel coordinator
 * from the loaded yaml documents + process.env, and passed to every section.
 *
 * Sections never touch the yaml AST directly. Form values flow back to the
 * host via a single `SavePayload` (see `../patch.ts`) which the panel
 * coordinator converts into yaml-doc mutations.
 */

export interface SectionState {
  routerConfig: Record<string, unknown> | null;
  budget: Record<string, unknown> | null;
  localOverrides: Record<string, unknown> | null;
  /** Map of env var name → present-in-process.env */
  envVarPresence: Record<string, boolean>;
  /** True when ai_router/local-overrides.yaml exists on disk. */
  localOverridesFileExists: boolean;
}

export interface SectionRenderResult {
  html: string;
}

/** Where the effective value for an Appendix-B field comes from. */
export type FieldSource = "shared" | "local" | "default" | "not-overridable";

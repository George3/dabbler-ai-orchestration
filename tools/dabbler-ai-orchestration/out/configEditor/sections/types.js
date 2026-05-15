"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
//# sourceMappingURL=types.js.map
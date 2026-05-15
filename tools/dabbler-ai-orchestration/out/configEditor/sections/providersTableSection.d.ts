import { SectionState, SectionRenderResult } from "./types";
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
export declare function render(state: SectionState): SectionRenderResult;

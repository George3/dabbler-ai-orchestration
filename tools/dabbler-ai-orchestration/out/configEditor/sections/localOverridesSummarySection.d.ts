import { SectionState, SectionRenderResult } from "./types";
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
export declare function render(state: SectionState): SectionRenderResult;

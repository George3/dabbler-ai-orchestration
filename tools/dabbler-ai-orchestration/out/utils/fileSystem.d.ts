import { SessionSet, SessionSetConfig, SessionSetPrerequisite, UatSummary } from "../types";
export declare const SESSION_SETS_REL: string;
export declare const PLAYWRIGHT_REL_DEFAULT = "tests";
export declare function discoverRoots(): string[];
export declare function isMidSetComplete(statePath: string): boolean;
export declare function countDistinctCloseoutSessions(eventsPath: string): number;
export declare function parseSessionSetConfig(specPath: string): SessionSetConfig;
/**
 * Set 047 Session 5: parse the optional ``prerequisites:`` field from
 * the spec's ``Session Set Configuration`` YAML block.
 *
 * Expected shape (per spec §3.3):
 *
 * ```yaml
 * prerequisites:
 *   - slug: 046-some-other-set
 *     condition: complete
 *   - slug: 044-another-set
 *     condition: complete
 * ```
 *
 * Returns ``null`` when the field is absent (no dependency declared).
 * Returns ``[]`` when ``prerequisites: []`` is written explicitly.
 * Returns the parsed list otherwise. Tolerant of operator typos:
 * entries missing ``slug`` are dropped; unrecognized ``condition``
 * values are dropped (only ``"complete"`` is in the enum today, per
 * spec §3.3).
 *
 * The parser is intentionally lightweight (regex, not a YAML parser)
 * so this module stays dependency-free and so a stray indentation
 * issue in the spec doesn't fail-closed across the entire Explorer.
 * A full YAML round-trip lives in the config-editor module; readers
 * here only need to recognize the array form.
 */
export declare function parsePrerequisites(specPath: string): SessionSetPrerequisite[] | null;
export declare function parseUatChecklist(checklistPath: string): UatSummary | null;
export declare function readSessionSets(root: string): SessionSet[];
export declare function readAllSessionSets(): SessionSet[];

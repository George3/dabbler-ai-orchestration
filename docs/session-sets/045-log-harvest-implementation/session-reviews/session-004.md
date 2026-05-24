VERIFIED: no must-fix issues.

---
### Recommendations (Nice-to-have)

-   **Issue:** The `regenerateNarrationTemplates.ts` command uses `spawnSync` without a `vscode.Progress` indicator. A slow Python startup could make the UI feel unresponsive.
    -   **Location:** `tools/dabbler-ai-orchestration/src/commands/regenerateNarrationTemplates.ts` â†’ `runRegenerate()`
    -   **Fix:** Wrap the `renderTemplate` calls in a `vscode.window.withProgress` block to provide feedback to the operator.

-   **Issue:** The manual step of copying the generated template is only mentioned in a transient success toast. This is not highly discoverable and could be missed.
    -   **Location:** `tools/dabbler-ai-orchestration/src/commands/regenerateNarrationTemplates.ts` â†’ `runRegenerate()`
    -   **Fix:** Add an action button to the `showInformationMessage` toast, such as "Copy to Workspace...", which would trigger a file dialog to select the destination for the `CLAUDE.md` file.

### Verification Notes

The following points were reviewed and found to be acceptable design choices or correct implementations.

-   **A1 (`session_end` emission):** Non-emission of a synthetic `session_end` by the streaming Claude parser is correct. The `last_event_ts` from the higher-level `scan_claude_logs` function provides the necessary signal for staleness detection without violating the streaming paradigm.
-   **A2 (Sticky context):** The asymmetry between sticky `cwd` and overwriting `conv_id` is acceptable. The filename is the primary source for `conv_id`, and overwriting from a `sessionId` field within the log is a reasonable strategy for handling potential inconsistencies.
-   **A3 (`session_start` trigger):** Triggering `session_start` on the first `user` OR `assistant` record is more robust than requiring a `user` record, correctly handling log fragments that may not start at the absolute beginning of a conversation.
-   **A4 (Token accounting):** Summing Claude's various input token counts into a single `tokens_in` field correctly adheres to the canonical `HarvestRecord` schema and aids cross-engine comparison.
-   **B1 (Eager list materialization):** Materializing the parser's event stream into a `list` in `_native_events_for` is consistent with the precedent set by the Copilot parser and is functionally sound given the `harvest()` implementation.
-   **C3 (Defensive rules test):** The unit test for defensive rules correctly automates checks for lexical patterns (Rules 1 & 2). Rules 3 (framing) & 4 (caps) require qualitative human judgment, and a manual review confirms the templates are compliant. The test coverage is sufficient.
-   **F3 (Multiple markers):** The parser correctly emits a `marker` event for each detected marker. This "observe what happened" behavior is preferable to silent deduplication, as multiple markers may be a useful diagnostic signal for consumers to analyze.
-   **F4 (`read_progress` strictness):** Requiring a consistent session-state file and refusing to render templates from an invalid state is a feature, not a bug. It correctly enforces data integrity, which is especially valuable for Lightweight-tier operators who may hand-edit these files.
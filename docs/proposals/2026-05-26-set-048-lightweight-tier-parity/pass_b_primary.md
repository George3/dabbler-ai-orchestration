# PASS B (devil's-advocate) - Primary read

- **Provider:** unknown
- **Model:** gemini-pro
- **Cost:** 0.0309225
- **Tokens (in/out):** 8810/1991

---

### Devil's-Advocate Pressure Test

#### Bias 1: Explicit-and-multiple activation (§A1)

*   **Inverted Position:** Use a single, declarative activation mechanism: the `tier: "lightweight"` field in `spec.md`.
*   **Argument for Inversion:** A single source of truth in the spec file is simpler and less error-prone. It ensures the set's intended tier is permanently recorded. Multiple overrides (CLI flag > env var > spec) create cognitive load and a complex precedence order that can lead to unexpected behavior, especially in CI environments where environment variables might be inherited invisibly.
*   **Verdict:** Stand By Proposal. The flexibility of overrides is critical for debugging and CI. A Full-tier developer needs to test the Lightweight flow without committing a spec change. The proposed precedence is a standard, well-understood pattern.

#### Bias 2: Path-reference design (§B1)

*   **Inverted Position:** Prompts must embed file content, not reference file paths.
*   **Argument for Inversion:** The primary value of a copyable prompt is its portability. Path-referencing assumes the receiving agent has access to the local filesystem, which is not universally true (e.g., web-based LLMs, certain IDE chat integrations). This makes the feature fragile and context-dependent. Embedding content creates a self-contained, universally usable artifact.
*   **Verdict:** Flip to Inversion (partially). The operator directive L1 is a hard constraint. However, the implementation should offer a fallback. The `Copy Eval ▸` submenu should contain a fourth option, "Evaluate Specification (with content)", which embeds `spec.md`. This addresses the agent capability risk without violating the L1 directive for the primary commands.

#### Bias 3: Cursor-anchor preservation (§C1)

*   **Inverted Position:** Abandon the custom HTML menu and migrate to the native `vscode.window.showQuickPick` API.
*   **Argument for Inversion:** The engineering cost and risk of implementing a bespoke HTML submenu solution are high. It requires non-trivial, brittle code for focus management, keyboard navigation, and accessibility (ARIA roles). Native `QuickPick` provides all of this out-of-the-box, respects user themes, and is guaranteed to be forward-compatible with VS Code updates. The UX benefit of cursor-anchoring does not justify this significant, ongoing maintenance burden.
*   **Verdict:** Flip to Inversion. The long-term stability, accessibility, and lower engineering cost of a native `QuickPick` menu outweigh the aesthetic benefit of the cursor-anchor. This is a classic case of avoiding NIH syndrome.

#### Bias 4: Triple-redundancy for suggested-state reminder (§E4)

*   **Inverted Position:** Use a single, authoritative location for the reminder: the `activity-log.json`.
*   **Argument for Inversion:** Redundancy creates noise. A one-time toast is ephemeral and easily missed. A log line on close-out is too late. The `activity-log.json` is the canonical, persistent record of session events. Placing the reminder there and only there trains the operator to treat the activity log as the source of truth, improving process discipline.
*   **Verdict:** Stand By Proposal. The cost of redundancy is low, while the cost of a missed suggestion is moderate. The toast provides immediate feedback at session start, the activity log provides a persistent record, and the close-out log provides a final checkpoint. This "belt-and-suspenders" approach is appropriate for a critical process reminder.

#### Bias 5: Warnings over gates (§D2)

*   **Inverted Position:** Implement a soft gate for "suggested" verification steps.
*   **Argument for Inversion:** Warnings in logs are systematically ignored and become noise. For a "suggestion" to be meaningful, it requires a conscious acknowledgment from the operator. A soft gate—such as creating the `external-verification.md` file or prompting for a `[Y/n]` confirmation to proceed with close-out—forces this acknowledgment without being overly restrictive. It turns a passive-fail into an active-choice.
*   **Verdict:** Flip to Inversion. A warning-only approach renders the `"suggested"` state functionally identical to `false`. The close-out process should check for the existence of `docs/session-sets/<slug>/external-verification.md`. If it is missing and UAT/E2E is "suggested", it should print a warning and require an interactive confirmation (`Continue closing session without verification artifact? [y/N]`) before proceeding.

#### Bias 6: Repo-level review-criteria storage (§E10)

*   **Inverted Position:** Store customizable review criteria in per-workspace VS Code settings.
*   **Argument for Inversion:** Review criteria are often a matter of team or individual operator preference, not a canonical attribute of the code repository itself. Using workspace settings allows operators to tune prompts for their preferred agents or review style without creating file churn in the main repository. This decouples personal workflow from the project's versioned source.
*   **Verdict:** Stand By Proposal. Storing criteria in the repo (`docs/review-criteria/*.md`) makes them version-controlled, shareable, and consistent for the entire team. It establishes a project-wide standard for what constitutes a good review, which is more valuable than accommodating individual preferences. An operator can still copy/paste and edit the prompt for a one-off run.

#### Bias 7: Separating B2 and B7 into different sessions (§9 sessions 3 and 4)

*   **Inverted Position:** Combine the copyable-prompt command implementation and the context-menu IA refresh into a single session.
*   **Argument for Inversion:** These two work items are tightly coupled. Session 3 creates commands that Session 4 immediately moves. Combining them allows the developer to implement the new menu structure and its command bindings in one pass, enabling holistic testing and avoiding throwaway work. The scope is manageable for a single implementation session.
*   **Verdict:** Flip to Inversion. The proposed separation is inefficient. Combine into a single session titled "Implement Copyable-Prompt Commands and Context-Menu IA". This delivers the entire feature at once and reduces the risk of integration issues between the two parts.

#### Bias 8: Bundling Set 047's HELD publishes with Set 048's release (§9 session 6)

*   **Inverted Position:** Publish the Set 047 deliverables immediately, before Set 048 implementation begins.
*   **Argument for Inversion:** Releasing Set 047 now delivers the canonical v4 schema and tooling to all users faster. It de-risks the Set 048 release by decoupling the two sets of changes, shrinking the blast radius if something goes wrong. Set 048 can then be built and tested against a stable, published v4 baseline, which is a cleaner engineering practice than building on an unreleased foundation.
*   **Verdict:** Flip to Inversion. Ship Set 047's held release. Independent, incremental delivery is superior to large, bundled releases.

---

### Open Question Dispositions

*   **Q1 (CLI vs. Spec override):** The CLI flag (`--no-router`) must win. An explicit, per-invocation flag is the ultimate authority and should always override declarative configuration for debugging or one-off tasks. The tool should emit a `log.info` message noting the override (e.g., `"CLI flag --no-router overrides spec tier 'full' for this invocation."`), but it must not refuse to run.
*   **Q2 (External Verification Template):** The `external-verification.md` file should be entirely free-form. This aligns with the low-ceremony principle of the Lightweight tier. Avoid premature optimization for machine-readability.
*   **Q3 (Tri-state for Full-tier):** The `"suggested"` state for `requiresUAT`/`requiresE2E` should be valid for both Full and Lightweight tiers. A useful feature should not be artificially constrained. It provides valuable flexibility for any set where UAT is beneficial but not a hard requirement.
*   **Q4 (Set 047 Release Bundling):** Ship Set 047's held publishes independently and before Set 048's implementation begins. See verdict for Bias 8.
*   **Q5 (Add "Evaluate Implementation Plan"):** Do not add this menu item. The `plan.md` artifact is not a documented, standard convention. Adding UI for a speculative workflow adds clutter. Defer until the process is formalized.

---

### Bottom-Line Verdict

**ENDORSE WITH SPECIFIC BIAS FLIPS**

The proposal is well-structured but can be improved by adopting the inverted positions for:
1.  **Bias 3:** Switch to native `QuickPick` for the context menu.
2.  **Bias 5:** Implement a soft gate (interactive confirmation) for suggested verification.
3.  **Bias 7:** Combine the prompt-command and menu-IA sessions into one.
4.  **Bias 8:** Release Set 047's deliverables before starting Set 048.
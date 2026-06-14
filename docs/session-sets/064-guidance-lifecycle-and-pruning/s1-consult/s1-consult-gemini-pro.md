# Set 064 S1 design-lock consult — gemini-pro (google/gemini-2.5-pro)

### D1–D8 Verdicts

1.  **D1 — Cost reporter.** AGREE.
2.  **D2 — Per-lesson metadata serialization.** AGREE-WITH-MODIFICATION.
    -   **Modification:** The `key=value` format is too fragile for human editing. Mandate that all values be double-quoted (e.g., `id="L-064-1" status="active"`) to handle future values with spaces or special characters without breaking a simple split-on-space parser.
3.  **D3 — Citation-at-close seam.** AGREE.
4.  **D4 — Active/archive split.** AGREE.
5.  **D5 — Steady-state triggers + backstop ceiling.** AGREE.
6.  **D6 — Backlog-remediation recipe.** AGREE.
7.  **D7 — Ship to consumers.** AGREE.
8.  **D8 — Docs + release.** AGREE.

### Explicit Questions

1.  **D1–D8 verdicts:** See above.

2.  **D2 (HTML-comment trailer):** The HTML-comment trailer is the correct choice. A visible trailer adds prose clutter for no benefit. A YAML block adds parsing complexity and dependencies for what should be a simple, single line of metadata. The proposed approach is the best balance of being machine-readable, human-editable, and invisible in rendered output.

3.  **D3 (Citation seam):** "Agent runs `cite_lessons` as part of the commit" is decisively cleaner. The metadata update is an auditable part of the work that benefited from the lesson. It keeps the git history coherent (`git blame` on a metadata line points to the commit that used it). The alternative (having `close_session` mutate markdown) breaks this link and leaves content files dirty post-commit, which is poor practice.

4.  **D5 (N=20, 10k/6k ceilings):** The proposed defaults are reasonable. N=20 is a generous signal for human review, not an automated axe, making it safe. The 10k/6k token ceilings are aggressive enough to force remediation on the over-budget repos while providing a sustainable target. As they are configurable, these defaults are a fine starting point.

5.  **D6 (Archive-bankruptcy):** Yes, it should absolutely be offered. It is a safe and pragmatic escape hatch for teams buried in guidance debt. Since archive is not deletion, the cost of a mistake is low (a lesson can be reactivated). The cost of inaction (huge context files) is high and ongoing. Offering this option respects operator time.

### Blind Spots & Risks

1.  **Metadata Fragility:** Hand-editing the D2 metadata comment is error-prone. The implementation should include a linter/validator (`python -m ai_router.validate_guidance_meta`) that can be run in CI or a pre-commit hook to prevent malformed metadata from being committed.
2.  **Citation Compliance:** The design relies on the agent to remember to cite lessons. This is a behavioral loop with no enforcement. If citation rates are low, the `last-used-set` data will be sparse, undermining evidence-based archival. Consider a non-blocking check in `close_session` that warns if a session's transcript mentions lesson IDs but `disposition.json` has no citations.
3.  **Archive Discovery:** The plan for finding archived lessons is "grep-on-demand." This is insufficient. A simple CLI search tool (`python -m ai_router.guidance_search --archive "keyword"`) will be needed to prevent the archive from becoming a write-only black hole.
4.  **Cross-File Dependency Risk:** The D5 trigger "not referenced by active guidance" implies that `project-guidance.md` can reference lessons by ID. The pruning sweep tool must correctly parse both files to build a dependency graph. An error here could lead to archiving a lesson that is still actively referenced by core project guidance. This dependency check is a critical implementation detail that must be robust.
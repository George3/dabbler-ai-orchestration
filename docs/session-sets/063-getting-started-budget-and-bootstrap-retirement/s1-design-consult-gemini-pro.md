### Q1: Disposition of docs/adoption-bootstrap.md

Option (a), RETIRE WITH REDIRECTS, best serves the set's goal of "One onboarding path, one set of docs, no dual-path drift." Maintaining a parallel non-VS-Code onboarding path (Option b) directly contradicts this goal and risks future documentation divergence. The audit findings—zero consumer-repo references to the bootstrap path and the operator's quote questioning its unique value—indicate that retiring it is a low-risk, high-reward simplification. The "no 404" constraint for old clients is satisfied by rewriting `adoption-bootstrap.md` into a redirect stub pointing to the primary VS Code Getting Started flow and the new canonical schema location.

The canonical home for the `budget.yaml` schema should be a new, dedicated file: `docs/budget-yaml-schema.md`. This provides a stable, single-purpose reference for all consumers, including those needing to create the file manually, and decouples the schema definition from any specific onboarding workflow. All other documentation (`quick-start.md`, `ai-led-session-workflow.md`) must be updated to reference this new canonical source.

RECOMMENDATION: Retire `docs/adoption-bootstrap.md` to a redirect stub per option (a) and relocate the canonical schema definition to a new `docs/budget-yaml-schema.md` file.

### Q2: Form's Budget Step for $0

Option (ii) is the superior design choice. Onboarding forms should minimize friction and cognitive load. Forcing an immediate, secondary choice about a nuanced configuration detail (`verification_method`) for a zero-dollar budget adds complexity where it is not needed. Defaulting to the safer option (`manual-via-other-engine`) with clear, brief explanatory copy is a standard and effective UX pattern. This provides a sensible default for new users while empowering them to make changes later once they are more familiar with the system.

The copy for the $0 case should state:
"For $0 budgets, cost verification defaults to manual. You can disable this by editing `verification_method: skipped` in the `ai_router/budget.yaml` file after setup."

RECOMMENDATION: Default the $0 budget case to `verification_method: manual-via-other-engine` and use concise copy to explain the default and how to change it.

### Q3: Form Writer Implementation

The proposal is confirmed; it is sound and has no defects. The Getting Started form's writer should be implemented in pure TypeScript, consistent with the extension's existing patterns. It should directly emit a `budget.yaml` file conforming to the modern, post-migration schema. This ensures that newly onboarded projects start with a clean, valid configuration that does not require a migration step, aligning perfectly with the set's goal of consolidation and simplification. The proposed fields and default values (`scope: "per-project"`, `warn_at_percent: 80`, etc.) are correct and consistent with the expectations of the system's other components, like the VS Code schema validator.

RECOMMENDATION: Confirm the proposal to implement a pure-TypeScript writer that emits the modern `budget.yaml` schema directly, as no defects were identified.
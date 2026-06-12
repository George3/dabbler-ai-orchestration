## Q1

- Choose **(a)** as the product disposition, but implement it as a **compatibility-stub hybrid**.
- Keeping `docs/adoption-bootstrap.md` as a supported manual onboarding path preserves the exact dual-path drift this set is trying to remove; non-VS-Code users need documentation, not a second bootstrap artifact.
- Preserve `docs/adoption-bootstrap.md` at the same path for old raw-URL consumers, but rewrite it to a short deprecation stub in plain language with **absolute URLs** to Quick Start and the schema reference, plus one line telling VS Code users to use the extension’s Getting Started form.
- Make a new dedicated `docs/budget-yaml-schema.md` the canonical home of the `budget.yaml` contract, not a section inside `docs/ai-led-session-workflow.md`, and document the **normalized/current** shape (`scope`, `warn_at_percent`) with legacy compatibility notes (`threshold_scope` migrates to `scope`; legacy `monthly` maps to `scope: per-project` + `period: monthly`).
- Update `docs/quick-start.md` and `docs/ai-led-session-workflow.md` to remove the bootstrap-prompt path from mainline docs; if needed, add a brief “Without VS Code” note to Quick Start that points to manual file creation and the new schema doc.

**RECOMMENDATION:** Retire `docs/adoption-bootstrap.md` as a supported onboarding path, keep the URL alive only as a short compatibility stub for old consumers, and make `docs/budget-yaml-schema.md` the canonical home of the `budget.yaml` contract.

## Q2

- Choose **(i)**, with **no silent default**.
- At `$0`, `verification_method` is a real policy choice and cannot be inferred from the amount, so auto-writing `manual-via-other-engine` would encode intent the operator never supplied.
- Reveal two radios only when the parsed value is `0`, require an explicit selection, and label them **“Check in another engine”** (`manual-via-other-engine`) and **“Skip verification”** (`skipped`).
- `$0` copy: **“A $0 budget still needs a verification rule. Choose whether to check each session in another engine or skip verification.”**

**RECOMMENDATION:** Use option (i): when the budget is `0`, reveal a required inline verification-method choice instead of silently defaulting it.

## Q3

- **Confirm.**
- A pure-TypeScript writer matches the extension’s existing architecture and avoids inventing a Python generation path for a file the Python runtime does not consume.
- Emit the normalized shape directly so the migrator is a no-op and `BUDGET_SCHEMA` validates it unchanged: `threshold_usd`, `scope: "per-project"`, derived `mode`, `verification_method` (including the explicit zero-budget choice from Q2), `verification_nte_usd` defaulted to `threshold_usd`, `set_at` via ISO 8601, `set_by: "getting-started-form"`, and `warn_at_percent: 80`.
- Do **not** emit legacy `threshold_scope` or `period`; treat `notes` as optional/omitted unless the form actually collects it.
- Implement the mode tiers as numeric ranges (`0`, `0 < x < 20`, `20 <= x < 100`, `x >= 100`) and reject negative or invalid input.
- The only companion defect to fix is documentation drift: the published schema must adopt this post-migration shape, or the writer will be correct while the public contract stays wrong.

**RECOMMENDATION:** Confirm the pure-TypeScript writer that emits the normalized post-migration shape directly, with the mandatory companion change that the docs publish that same normalized shape as canonical.
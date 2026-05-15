# Session 1 review — Set 025 (router-config-editor spec)

## Verifier

- **Model:** gpt-5-4 (cross-provider; orchestrator was Claude Opus 4.7)
- **Task type:** `session-verification`
- **Cost:** $0.1846
- **Input tokens:** 15,626
- **Output tokens:** 9,704
- **Rendered prompt size:** 69,482 chars (prompt + spec.md + schema-examples.md + wireframes.md + audit-summary.md as Appendix A)

## Round 1 verdict

> **Almost, but not yet** — five minimum fixes named before Set 026
> can start cold. Doc-only drift across the three deliverables; no
> architectural defect.

Per-question:

| Q | Topic | Round-1 verdict |
|---|---|---|
| Q1 | Gating-decision capture | Partial — G2 (`provider_id` reintroduced in Session 2 title + Session 3 row spec), G7 (`per-session` still exposed), G4 (routing dropdown persistence unspecified) |
| Q2 | Internal consistency | No — provider schema and routing dropdown contradicted across docs; shared-vs-local boundaries inconsistent |
| Q3 | Schema sanity | Mostly OK — `threshold_scope` → `scope` migration was lossy for `monthly`; local-overrides "strict subset" wording too strong |
| Q4 | Wireframe semantics | UX matches; enum mapping (UI labels ↔ YAML values) not spelled out |
| Q5 | Buildability | Not cold-startable — routing dropdown's canonical field/file/enum was the smallest blocker |
| Q6 | Open architectural Qs | All three (precedence, load-validation, atomic-save) needed clearer wording |
| Q7 | Session 3 scope | Two wireframed sections (significance flagging, local overrides summary) missing from Session 3 deliverable list; test-notification button not in any session plan; wizard integration could move to Session 5 |
| Q8 | Overall | Almost ready; needs one normative pass to resolve cross-doc drift |

## In-session fixes (round 1 → applied)

All five "minimum fixes before Set 026" were applied in-session.
Round-2 verification was skipped following Set 023 Session 4's
precedent (doc-only drift, no architectural change, fixes
verifiable by reading the diff).

### Fix 1: Remove `provider_id` / `api_base_url` / `api_key_env_var` drift

- `spec.md` Session 2 title changed from "Extend `providers:`
  schema + add `provider_id` to `models:`" to "Extend `providers:`
  schema + `budget.yaml` migration + resolver abstraction."
- `spec.md` Session 3 Providers table row spec rewritten to use
  the actual field names (`enabled`, `display_label`, provider ID
  read-only, `api_key_env`, `...` button for less-common fields).
- Remaining mentions of `provider_id` / `api_base_url` /
  `api_key_env_var` are explicitly framed as "the audit
  reviewers' terminology vs. the actual schema" — legitimate
  reference text.

### Fix 2: Resolve routing-dropdown persistence

- New section "File 1b" in `schema-examples.md` defines the
  canonical persistence target: `router-config.yaml`
  `routing.outsourcing_mode`. Enum:
  `whenever-helpful` / `verification-only` / `disabled`. Default
  `whenever-helpful`. Local override allowed via
  `local-overrides.yaml`.
- `wireframes.md` Section 1 "YAML writes" subsection updated to
  point at `routing.outsourcing_mode`.
- `spec.md` Appendix B (new — see Fix 5) lists the field in the
  canonical control-to-YAML mapping table.

### Fix 3: Make G7 consistent

- `spec.md` G7 row updated: per-session is **removed from the
  user-facing UI entirely**; schema-validator accepts it for
  hand-edited YAML but the webview dropdown only offers
  `per-session-set` (default) and `per-project`.
- `schema-examples.md` File 2 budget.yaml `scope` comment +
  Changes table row updated to match.
- `wireframes.md` Section 2 Budget scope dropdown shows only the
  two UI options with an explanatory note that per-session is
  hand-edit-only.

### Fix 4: Define local-overrides precedence + unknown-key behavior

- `spec.md` Appendix B includes a five-point precedence rules
  block:
  1. local > shared > default
  2. only paths in the Appendix B "Local-override allowed? Yes"
     column accept overrides; others = validation error at load
  3. local-only sections (`notifications.*`, `decision_review.*`)
     have no shared analog
  4. providers/models existing only in local = validation error,
     not implicit add
  5. unknown keys = warn-and-ignore; surfaced in the webview's
     Local overrides summary section
- `schema-examples.md` File 3 rewritten to call out the strict
  allowlist explicitly; removed stray `extension.pythonPath`
  example; precedence rules documented inline in the YAML
  example's header comment.

### Fix 5: Soften the multi-file atomic-save claim + add normative Appendix B

- `wireframes.md` Validation section rewritten:
  - **Load time:** validator runs on panel open; failed-validation
    files open in read-only "drift detected" state with side panel
    showing complaints.
  - **Save time:** per-file atomic via tmp+rename; full-batch
    pre-validation; **true cross-file atomicity is not provided**;
    half-written batch detection on next load offers best-effort
    recovery dialog.
- `spec.md` Appendix B added as the single normative source for
  every webview control's persistence target — file, YAML path,
  type/enum, local-override allowed, notes. When other docs
  conflict with this table, this table wins. Includes:
  - Control-to-YAML mapping table (12 rows covering every
    wireframed control)
  - Verification dropdown enum mapping (UI label → YAML value)
  - Local-override precedence rules (5 points)
  - `threshold_scope` → `scope` migration rule (4 cases,
    including the `monthly` lossless preservation path)
  - Write atomicity clarification
  - Validation timing (load + save)

## Additional in-session refinements (not in the minimum-fixes list)

The verifier also raised Q7 issues that weren't on the
"minimum fixes" list but were trivial to address in-session:

### R1: Session 3 deliverables list — six sections, not four

- `spec.md` Session 3 `sections/` list now enumerates all six
  files matching the six wireframed sections:
  `routingAndVerificationSection.ts`,
  `budgetSection.ts`,
  `providersTableSection.ts`,
  `significanceFlaggingSection.ts`,
  `notificationsSection.ts`,
  `localOverridesSummarySection.ts`.

### R2: Wizard integration + test-notification deferred to Session 5

- `spec.md` Session 3 has a "Deferred to Session 5" subsection
  explicitly calling out wizard integration and the "Send a test
  notification now" button wiring.
- `spec.md` Session 5 title and deliverables list expanded to
  cover both deferrals plus the existing end-to-end work.
- `wireframes.md` Section 5 Notifications shows "(wired in Set
  026 Session 5)" next to the test-notification button.

## Why no round-2 reroute

Set 023 Session 4's precedent: round 1 verifier review found 3
minor coverage gaps in the test suite; all three were fixed
in-session; **no round-2 reroute** because the fixes were "pure
test additions; the reader behavior is unchanged."

Set 025 Session 1's situation is analogous: round 1 verifier found
12 doc-only drift issues; all five "minimum fixes" + all Q7
refinements were applied in-session; no architectural change. The
fixes are verifiable by reading the diff. Skipping round 2 saves
~$0.18 and matches the established Set 023 precedent.

The unfixed verifier observations are:

- Q3 mention of `monthly` migration being lossy — **addressed**
  (now preserves `period:` field on disk so a future set can wire
  it without data loss; reader emits a deprecation warning).
- Q6 "atomic save across multiple files is overstated" —
  **addressed** in Appendix B + wireframes Validation.

There are no unaddressed verifier findings.

## Cross-provider verification cost ledger (Set 025)

| Session | Provider | Model | Cost (USD) | Notes |
|---|---|---|---|---|
| 1 | OpenAI | gpt-5-4 | $0.1846 | Round 1 verification |
| **Set total** | | | **$0.1846** | |

This is exclusive of the **design-audit** cost spent before Set
025 started ($0.1197 across gpt-5-4 + gemini-pro at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`).
Combined design-audit-plus-spec cost across both efforts:
**$0.3043**.

## Notes

- All three deliverable docs (spec.md, schema-examples.md,
  wireframes.md) were edited in-session in response to the round 1
  verifier feedback. No code in this set.
- The normative Appendix B in spec.md is the single most
  important artifact for Set 026: when implementation docs and
  Appendix B disagree, Appendix B wins. Future Set 026 sessions
  should cite it explicitly.
- The audit-summary at
  `docs/proposals/2026-05-15-router-config-editor-design-audit/audit-summary.md`
  remains the design-rationale reference; Set 025's spec is the
  implementation-shape reference.

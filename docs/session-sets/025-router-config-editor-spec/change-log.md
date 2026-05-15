# Set 025: router-config-editor-spec — Change Log

**Sessions:** 1 of 1 completed (2026-05-15)
**Orchestrator:** Anthropic / Claude Opus 4.7 (1M context) — single session
**Cumulative routed cost (this set):** $0.1846 — Session 1
verification (gpt-5-4, `task_type=session-verification`).
**Companion design-audit cost (preceded this set):** $0.1197
across gpt-5-4 + gemini-pro at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`.
Combined audit-plus-spec cost: **$0.3043**.

---

## What Set 025 delivers

Set 025 is a **doc-only** session set. Its sole purpose is to
capture the cross-provider design audit's locked decisions into
three operationalizable documents that Set 026 (the implementation
set) will build to. No code in this set.

The triggering event: Set 024 removed the Provider Queues +
Provider Heartbeats tree views from the extension because they
were scaffolding for an unused workflow (`outsourceMode: last`).
Set 024's removal raised the question — *if the
queue-mediated-daemon path was unused, was the spec-level
`outsourceMode` flag still earning its keep?* That question
broadened into a wholesale rethink of how operators configure the
framework: API key env-var names, mid-session routing modes,
budget-approval scopes, secret storage, and the absence of an
operator-facing config UI today.

The operator and Claude sketched a config-editor design; the
operator then requested a cross-provider design audit before any
implementation. Set 025 captures that audit's verdict in a form
Set 026 can build to.

### Session 1 — Authored spec.md + schema-examples.md + wireframes.md

Three deliverable docs under
`docs/session-sets/025-router-config-editor-spec/`:

#### `spec.md`

Captures all eight gating decisions (G1–G8) locked from the audit
and from operator selection between divergences:

- **G1 (`outsourceMode` cleanup)** — clean-sweep: delete the flag,
  ~10 Python modules, the workflow doc, and the step-6/step-8
  mode-aware branches. Operator confirmed three Marketplace
  downloads (all suspected theirs) — no external users to
  grandfather.
- **G2 (provider schema)** — extend the existing `providers:`
  block at `router-config.yaml:24–57` with `display_label` and
  `enabled`. Existing `api_key_env` and `base_url` already match
  what the audit reviewers asked for under different names; no
  rename needed. `models:` entries unchanged.
- **G3 (significance flagging)** — operator-invoked only: a new
  VS Code command (`Dabbler: Flag Decision for Cross-Provider
  Review`) plus a recognized code-annotation syntax
  (`# @dabbler:outsource-review("reason")`). No silent
  heuristic.
- **G4 (verification UX)** — two decoupled dropdowns. Routing:
  `Whenever helpful` / `Verification only` / `Disabled`.
  Verification: `Automatic via API` / `Manual via portable
  markdown` / `None`. API option greys out when routing =
  Disabled.
- **G5 (shared vs local config)** — `.gitignore`-d
  `ai_router/local-overrides.yaml` for operator-machine-local
  fields. Webview labels every field as `(shared)` or
  `(local override)`.
- **G6 (secret storage)** — resolver abstraction in v1;
  env-var-only backend ships; secretStorage / keyring backends
  added in future sets on demand.
- **G7 (budget scope default)** — per-session-set default; UI
  offers `per-session-set` + `per-project` only;
  per-session is hand-edit-only (validator accepts but webview
  does not surface).
- **G8 (sequencing)** — two session sets: Set 025 (this, doc-only)
  + Set 026 (implementation).

Plus the canonical **Appendix B** — single normative source for
every webview control's persistence target. When other docs
conflict with Appendix B, Appendix B wins. Includes:

- 12-row control-to-YAML mapping table (file, YAML path,
  type/enum, local-override-allowed, notes)
- Verification dropdown enum mapping (UI label → YAML value)
- Five-point local-override precedence rules
- Four-case `threshold_scope` → `scope` migration rule
- Write atomicity clarification (per-file atomic; cross-file
  not provided; best-effort recovery on next load)
- Validation timing (load + save)

Plus a five-session Set 026 plan:

1. `outsourceMode` clean-sweep (deletion-only)
2. Schema migration + resolver abstraction (Python-side)
3. Webview implementation (six section files)
4. Significance-flagging command + annotation handling
5. Wizard integration + test-notification wiring + end-to-end + release

#### `schema-examples.md`

Side-by-side current vs proposed YAML for every file Set 026 will
touch:

- **`router-config.yaml`** `providers:` block: adds
  `display_label` + `enabled` (both optional, default-tolerant);
  shows an example operator-added custom OpenAI-compatible
  endpoint row.
- **New `router-config.yaml`** `routing.outsourcing_mode` field
  (the canonical persistence target for the webview's routing
  dropdown — resolved during round-1 verifier fixes).
- **`router-config.yaml`** `models:` block: **no schema change**
  — existing `provider:` field already references the
  `providers:` block by key.
- **`budget.yaml`**: renames `threshold_scope` → `scope`;
  constrains canonical UI values to `per-session-set` +
  `per-project` (validator accepts `per-session` for hand-edits
  but UI does not surface); adds `warn_at_percent` (default 80);
  lossless preservation of legacy `monthly` value via a `period:`
  field.
- **New `ai_router/local-overrides.yaml`**: `.gitignore`-d
  operator-machine-local overrides; subset of shared-config paths
  marked "Local-override allowed: Yes" in Appendix B, plus
  explicit local-only sections (`notifications`,
  `decision_review`). Precedence rules and unknown-key behavior
  documented inline.
- **`package.json`**: no schema changes; two new commands
  (`dabbler.openConfigEditor`, `dabbler.flagDecisionForReview`).
- **`.gitignore`**: one new line — `ai_router/local-overrides.yaml`.

Plus migration script behavior for
`ai_router/migrate_router_config.py` (idempotent forward
migration; preserves YAML comments via AST round-trip).

#### `wireframes.md`

ASCII layouts for six webview sections plus the cross-cutting
validation surface:

1. Routing & Verification (two decoupled dropdowns with explicit
   YAML write targets)
2. Budget (threshold + scope + warn-at-percent slider + 3-state
   UX preview, with operator-required cost-messaging copy:
   explicit dollar ranges, multi-week scale, open-source caveat,
   dashboard pointer)
3. Providers table (variable-length, add/remove/edit-row, with
   ✓ / (unset) env-var-presence badges; never displays key values)
4. Significance flagging (read-only documentation of the
   command + annotation surfaces)
5. Notifications (Pushover enabled toggle + env-var-name inputs;
   test-notification button noted as Session-5 wiring)
6. Local overrides summary (read-only side-by-side of shared
   vs local values, with click-through to the override file)

Plus the validation surface: load-time + save-time validation;
per-file atomic writes; best-effort cross-file recovery.

### Cross-provider verification

Round 1 (gpt-5-4, $0.1846) found 12 doc-only drift issues across
the three deliverables. Verdict: "Almost, but not yet" with 5
named "minimum fixes before Set 026 can start." All 5 fixes plus
2 Q7 refinements were applied **in-session**:

1. Removed `provider_id` / `api_base_url` / `api_key_env_var`
   drift from `spec.md` (leftover from Claude's earlier mistaken
   edits before reading the existing schema).
2. Resolved routing-dropdown persistence: added schema-examples
   File 1b defining `routing.outsourcing_mode` in
   `router-config.yaml`; updated wireframes Section 1.
3. Made G7 per-session-removed-from-UI consistent across all
   three docs.
4. Defined local-overrides precedence + unknown-key behavior in
   new `spec.md` Appendix B (5-point precedence rules).
5. Softened multi-file atomic-save claim in wireframes
   Validation; added the normative Appendix B as the single
   source of truth for every webview control's persistence
   target.

Round-2 reroute skipped following Set 023 Session 4 precedent
(doc-only drift, no architectural change, fixes verifiable by
reading the diff). Raw verifier output preserved at
`session-reviews/session-001/verify-result.json`; in-session
fix detail at `session-001-review.md`.

---

## What this set does NOT do

- It does not ship any code. All deliverables are docs.
- It does not modify any existing extension or `ai_router`
  source file. Set 026 Session 1 (outsourceMode clean-sweep) will
  be the first commit that touches existing source files in
  service of this redesign.
- It does not commit to a future-set timeline. Set 026's spec
  authoring happens in a new conversation when the operator is
  ready.
- It does not modify the audit artifacts at
  `docs/proposals/2026-05-15-router-config-editor-design-audit/`
  — those remain the design-rationale reference and are
  intentionally separate from this session set's deliverables.

---

## Release

No release. Doc-only set. The next operator-visible release is
gated on Set 026's eventual completion (proposed extension
version: v0.13.15 or similar, depending on Set 026's scope at
authoring time).

## Next steps for the operator

When ready, start Set 026 in a fresh conversation:

> "Start the next session of `026-router-config-editor-implementation`"

(After scaffolding Set 026's `docs/session-sets/026-...` folder
with its own `spec.md` and `session-state.json`. Set 026's spec
should be a thin doc that cites this set's deliverables —
especially `spec.md` Appendix B — as the canonical reference.)

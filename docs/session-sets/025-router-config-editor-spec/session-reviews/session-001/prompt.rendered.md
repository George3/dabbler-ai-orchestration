# Session 1 verification prompt — Set 025 (router-config editor spec)

## Context

Set 025 is a **doc-only** session set. Its sole purpose is to capture
a cross-provider design audit's locked decisions into three
operationalizable documents that Set 026 (the implementation set)
will build to.

The audit ran earlier today: GPT-5.4 + Gemini Pro reviewed the same
design prompt, this orchestrator (Claude Opus 4.7) synthesized their
verdicts, and the operator picked between divergences. Eight gating
decisions (G1–G8) are locked. Set 025 Session 1 produces:

1. `spec.md` — implementation spec for Set 026, including the
   session-by-session plan and the decisions captured.
2. `schema-examples.md` — current-vs-proposed YAML side-by-side
   for `router-config.yaml`, `budget.yaml`, the new
   `local-overrides.yaml`, plus `package.json` and `.gitignore`.
3. `wireframes.md` — ASCII webview layout for six sections
   (routing/verification, budget, providers table, significance
   flagging, notifications, local overrides).

The full audit work + synthesis is preserved at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`
(prompt.md, gpt-5-4-result.json, gemini-pro-result.json,
audit-summary.md).

## What you're being asked to verify

Set 025 produces only docs — no code. Your verification is a
**doc-only review** of the three deliverables. The implementation
itself happens in Set 026; your role here is to catch sharp edges
in the spec before any code is written.

Please review the three documents inlined below and answer:

**Q1. Gating-decision capture.** Does `spec.md` accurately capture
all eight gating decisions (G1–G8) from the audit summary? Any
decision misrepresented, lost in translation, or contradicted between
documents? (The audit summary itself is included as Appendix A
below for reference.)

**Q2. Internal consistency across the three docs.** Do `spec.md`,
`schema-examples.md`, and `wireframes.md` agree on the schema shape,
the dropdown semantics, the file boundaries (shared vs. local),
and the migration path? Any mutual contradictions?

**Q3. Schema sanity (`schema-examples.md`).** Is the proposed YAML
shape implementable as described? Specifically:
- Does the `providers:` block extension (`display_label`,
  `enabled`) collide with any existing field in the current schema?
- Is the `budget.yaml` `threshold_scope` → `scope` rename with
  legacy-name aliasing a safe migration, or does it create a
  permanent ambiguity?
- Is the `local-overrides.yaml` shape a strict subset of the
  shared YAMLs, or does it introduce keys that have no canonical
  shared analog (and is that OK)?

**Q4. Wireframe / dropdown semantics consistency.** The "Routing &
Verification" section (Section 1 of wireframes.md) shows two
decoupled dropdowns with a constraint ("Automatic via API" is
disabled when routing = Disabled). Does the spec's G4 decision text
match the wireframe behavior? Does the wireframe's UX preview match
the actual constraint (does "Manual" still work when routing =
Disabled)?

**Q5. Set 026 buildability.** Reading just `spec.md` + the two
companion docs (and not this prompt or the audit summary), could a
fresh orchestrator pick up Set 026 cold and execute Sessions 1–5
as described? What's the smallest concrete gap that would force
them to circle back to a design decision?

**Q6. Open architectural questions.** Specifically:
- Does the `local-overrides.yaml` merge semantics need a clearer
  precedence rule (e.g., what if a provider exists ONLY in
  `local-overrides.yaml`, never in the shared file — is that an
  add or an error)?
- The webview validation runs at save time; should it also run on
  *load* to catch hand-edited YAML drift?
- The "atomic save across multiple files" behavior in
  `wireframes.md` § Validation — is the proposed `tmp write +
  rename` sequence actually atomic across multiple files, or only
  per-file? If only per-file, the cross-file consistency claim
  needs softening.

**Q7. Anything missing from the Set 026 session breakdown.** The
spec proposes five Set 026 sessions
(`outsourceMode` clean-sweep → schema → webview → significance
flagging → release). Reading the deliverables, would you split,
merge, or reorder any? Any session that needs work the spec
doesn't mention?

**Q8. Overall.** Is the spec ready for Set 026 to start? If not, the
smallest concrete change to get it there.

A short, structured response (per-question verdict + reasoning + any
concrete suggestions) is fine.


---

## Doc 1: spec.md

# Router-config editor spec (for Set 026 implementation)

> **Purpose:** This set is **doc-only**. It produces the
> implementation spec, schema example, and wireframes that
> Set 026 will execute against. No code in this set.
>
> **Session Set:** `docs/session-sets/025-router-config-editor-spec/`
> **Created:** 2026-05-15
> **Workflow:** Full
> **Prerequisite:** Cross-provider design audit at
> `docs/proposals/2026-05-15-router-config-editor-design-audit/`
> with synthesis at that folder's `audit-summary.md`.

---

## Session Set Configuration

```yaml
totalSessions: 1
requiresUAT: false
requiresE2E: false
uatStyle: ad-hoc
uatScope: none
effort: normal
outsourceMode: first
```

> Rationale: single-session doc-authoring set. No new code, no UAT,
> no E2E. The design has already been locked across three frontier
> models; this session's job is to capture the locked decisions in
> a form Set 026 can build to.

---

## Decisions locked from the audit (do not re-litigate)

The cross-provider audit at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`
produced eight gating decisions. All eight are locked. The
audit's raw verdicts (`gpt-5-4-result.json` and
`gemini-pro-result.json`) and synthesis (`audit-summary.md`) are
the canonical record.

| # | Decision | Locked value |
|---|---|---|
| G1 | `outsourceMode` cleanup scope | **Clean-sweep.** Delete the flag, ~10 Python modules, the workflow doc, and the step-6/step-8 mode-aware branches. Operator confirmed three Marketplace downloads (all suspected to be theirs) — no external users to grandfather. |
| G2 | Provider schema | **Extend the existing `providers:` block** at `router-config.yaml:24–57`. Add `display_label` and `enabled`. The existing `api_key_env` and `base_url` fields already match the audit's "api_key_env_var" / "api_base_url" recommendation — no rename needed. Each `models:` entry already references its provider via `provider: <key>`; no `provider_id` migration is required. (The audit reviewers worked from incomplete info; the existing schema is closer to GPT's recommendation than the audit summary captured.) |
| G3 | "Significance" flagging | **Operator-invoked only.** Two surfaces: (a) a VS Code command `Dabbler: Flag Decision for Cross-Provider Review`; (b) a recognized code-annotation pattern `# @dabbler:outsource-review("reason")` that the orchestrator picks up during session work. No silent heuristic. |
| G4 | Verification UX | **Two decoupled dropdowns.** Routing: `Whenever helpful` / `Verification only` / `Disabled`. Verification method: `Automatic via API` / `Manual via portable markdown` / `None`. The API option is greyed out when routing = Disabled. Surfaces `budget.yaml`'s existing `verification_method` field. |
| G5 | Shared-vs-local config | **`.gitignore`-d `ai_router/local-overrides.yaml`** for operator-machine-local fields (notification env-var names, Pushover keys, optional API-key env-var overrides). Webview clearly labels which fields are shared-canonical vs. local-overridden. |
| G6 | secretStorage | **Resolver abstraction in v1, secretStorage backend later.** Every key lookup goes through a `resolve_secret(name, source)` indirection. Env-var is the only backend Set 026 ships; secretStorage / keyring backends added in a future set on demand. |
| G7 | Budget scope default | **Per session-set** (matches the operator's `feedback_budget_question_scope` memory). Per-project is the advanced option in the dropdown. Per-session is demoted to "hide-behind-advanced" or fully removed; Set 026 implements per-session-set + per-project as the user-facing options. |
| G8 | Sequencing | **Two session-sets.** Set 025 (this one) is doc-only. Set 026 is the implementation. |

---

## Set 026 implementation plan

Set 026 — **`router-config-editor-implementation`** — runs against
this spec once the operator starts it. Proposed session breakdown
(Set 026's own spec.md will refine these; this is the scaffolding
shape):

### Session 1: `outsourceMode` clean-sweep

**Goal:** Remove the queue-mediated daemon (`outsourceMode: last`)
infrastructure end-to-end. No new code.

**Deletes:**

- Python: `ai_router/queue_status.py`, `ai_router/heartbeat_status.py`,
  `ai_router/queue_db.py`, `ai_router/queue_verification.py`,
  `ai_router/daemon_pid.py`, `ai_router/orchestrator_role.py`,
  `ai_router/restart_role.py`, `ai_router/role_status.py`,
  `ai_router/capacity.py` (≈9 modules — verify with `grep -l outsource_mode\|queue_db\|daemon` after deletion).
- Docs: `ai_router/docs/two-cli-workflow.md`.
- Workflow doc: every reference to `outsourceMode: last`,
  `subscription CLI`, `verifier daemon`, queue-related step-6/step-8
  branches, the `outsource-last` row in the budget-tier table.
- Close-out doc: every mode-aware branch in `close_session`
  invocation flow and gate descriptions.
- Spec authoring guide: the `outsourceMode:` config-block row.
- Existing session-set spec.md files: scrub the `outsourceMode:`
  line. (Use `git grep outsourceMode docs/session-sets` to find
  them all.)

**Edits:**

- `ai_router/close_session.py`, `start_session.py`: remove
  `outsource_mode` parameter / case branches; collapse to the
  outsource-first path.
- `ai_router/gate_checks.py`: drop queue-related gate predicates.
- `ai_router/router-config.yaml`: drop the `queue_db_path` and any
  daemon-related config rows.
- CHANGELOG: reversal note acknowledging v0.13.14's "the CLIs stay"
  promise; explain operator decision (zero observed external usage
  per Marketplace download metrics).

**Test surface:** strictly shrinks. No new tests.

**Release:** extension `v0.13.15` (or whatever Set 026 lands on)
ships the operator-facing cleanup; ai_router package gets a minor
version bump (e.g., `0.3.0`) since this is a breaking change for
any hypothetical outsource-last user.

---

### Session 2: Extend `providers:` schema + add `provider_id` to `models:`

**Goal:** Bring the YAML schema into the shape the webview needs.
No webview yet; pure Python-side schema + reader changes.

**Schema changes** (see `schema-examples.md` for the full
before/after):

- `router-config.yaml` `providers:` block gains two new optional
  fields: `display_label` (default: title-cased provider key) and
  `enabled` (default: `true`). Existing `api_key_env` and `base_url`
  fields stay as-is; no renames.
- `models:` block is **unchanged at the schema level**. Each entry's
  existing `provider:` field already references the `providers:`
  block by key. Set 026 adds validation that the referenced key
  exists at write time.
- `budget.yaml` gains `warn_at_percent: <NUMBER>` (default 80) and
  renames `threshold_scope` → `scope` with expanded values
  (`per-session-set` / `per-project` / `per-session`). Legacy
  `threshold_scope` still loads with a deprecation warning.
- New file `ai_router/local-overrides.yaml`: `.gitignore`-d.
  Schema is a strict optional subset of `router-config.yaml` +
  `budget.yaml` + a `notifications:` block + a `decision_review:`
  block. See `schema-examples.md` File 3 for the full shape.

**Resolver abstraction** (G6): introduce
`ai_router/secret_resolver.py` exporting `resolve_secret(name:
str, source: str = "env") -> str | None`. Env-var backend is the
only implementation in this session. Future backends
(`secretStorage`, `keyring`) plug in via a registry.

**Reader updates:**

- `ai_router/config.py`: parse new optional fields with
  default-tolerant handling (older files load cleanly; readers
  inject defaults for missing `display_label` / `enabled`).
- `ai_router/providers.py`: existing `api_key_env` read path is
  unchanged.
- Migration script `ai_router/migrate_router_config.py`: idempotent
  forward migration that injects `display_label` + `enabled` into
  existing `providers:` entries, renames `budget.yaml`'s
  `threshold_scope` → `scope` (with value translation), and injects
  `warn_at_percent: 80` if absent. Re-running on a freshly-migrated
  file is a no-op.

**Test surface grows:**
`test_secret_resolver_env_backend.py`,
`test_config_reads_new_providers_fields.py`,
`test_migrate_router_config_idempotent.py`,
`test_budget_yaml_scope_rename.py`,
`test_local_overrides_merge.py`.

---

### Session 3: Webview implementation (extension side)

**Goal:** Ship the custom-webview config editor that reads + writes
the YAML files. This is the bulk of the user-facing work.

**Deliverables:**

- `tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts`
  — webview panel registration + HTML/CSS/JS scaffolding.
- `tools/dabbler-ai-orchestration/src/configEditor/yamlReadWrite.ts`
  — round-trip-safe YAML reader/writer (preserves comments and
  formatting; uses `yaml` npm package's AST mode, not the default
  parse-and-restringify).
- `tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts`
  — JSON-schema validator that runs on every load + every write.
  Surfaces errors in the webview UI; refuses to write invalid YAML.
- `tools/dabbler-ai-orchestration/src/configEditor/sections/` —
  one file per webview section (general, providers table,
  outsourcing-mode dropdown, verification-mode dropdown, budget,
  notifications).
- New command `dabbler.openConfigEditor` registered in
  `package.json` (title: "Open Dabbler Config Editor").
- Wizard integration: the project-setup wizard's "Configure AI
  Router" step opens the config editor instead of (or in addition
  to) writing `router-config.yaml` programmatically.

**Layout** (per `wireframes.md`):

- **Section 1: Routing & Verification.** Two decoupled dropdowns
  (G4). Heads-up text describing the constraint
  ("API verification disabled when routing is Disabled").
- **Section 2: Budget.** Scope dropdown (G7), threshold input,
  `warn_at_percent` slider, three-state preview of the
  optimally-intrusive UX.
- **Section 3: Providers table.** Variable-length table with
  add/remove/edit-row controls. Each row: `display_label`,
  `provider_id`, `api_base_url`, `api_key_env_var`, `enabled`.
  Per row, show "env var is set" / "env var is not set" badge
  (read at panel open + on demand).
- **Section 4: Significance flagging.** Read-only documentation
  of the `Dabbler: Flag Decision for Cross-Provider Review`
  command + `# @dabbler:outsource-review("reason")` annotation
  syntax. Toggle for "honor annotations in the current session
  set" (default on).
- **Section 5: Notifications.** Pushover enabled toggle +
  env-var-name inputs (Pushover API Key env var, Pushover User
  Key env var). All Section-5 fields live in
  `local-overrides.yaml`.
- **Section 6: Local overrides.** Read-only summary of which
  fields are currently overridden in `local-overrides.yaml` vs.
  inherited from `router-config.yaml` / `budget.yaml`. Links to
  open the override file directly.

**Test surface:**
`yamlReadWrite.test.ts` (comment preservation, multi-line strings,
unicode), `schemaValidator.test.ts` (every validation rule),
`configEditor-rendering.test.ts` (webview-host tests via Electron).

---

### Session 4: Significance-flagging command + annotation handling

**Goal:** Ship the explicit operator-invoked significance-flag
surfaces (G3).

**Deliverables:**

- `tools/dabbler-ai-orchestration/src/commands/flagDecisionForReview.ts`
  — registers `dabbler.flagDecisionForReview`. When invoked: prompts
  the operator for a reason (single-line input), appends a structured
  entry to `docs/session-sets/<active-slug>/decision-review-queue.jsonl`
  (one JSON line per flag), surfaces an info notification, returns.
- `ai_router/decision_review_queue.py` — Python reader for the queue
  file. Loaded by the orchestrator at session start; flagged items
  are surfaced in the orchestrator's initial planning checklist.
- Annotation parser: when the orchestrator opens a file during
  session work, comments matching
  `# @dabbler:outsource-review\("(.+?)"\)`
  are detected. Each match is appended to the queue with the
  containing file/line as context.
- Workflow doc updates: a new "Significance flagging" section in
  `docs/ai-led-session-workflow.md` documenting both surfaces.
- Setting in `local-overrides.yaml`: `decision_review.honor_annotations:
  <BOOL>` (default true; operator can disable annotation scanning).

**Test surface:**
`flagDecisionForReview.test.ts` (queue file append + idempotency),
`test_decision_review_queue_reader.py`,
`test_annotation_parser_extracts_correctly.py`.

---

### Session 5: End-to-end testing + docs + release

**Goal:** Wire everything together; release as a single
operator-facing version.

**Deliverables:**

- Update adoption-bootstrap doc to point new operators at the
  config editor (`Dabbler: Open Config Editor`) as the canonical
  setup surface, with the wizard as a backup.
- Update `quick-start.md` with a section on the config editor.
- End-to-end smoke test: open the editor, edit each section,
  verify YAML files round-trip correctly, verify Python reader
  picks up new values without restart.
- CHANGELOG entry covering the whole set (extension version bump +
  ai_router version bump).
- Marketplace + Open VSX release via existing tag-driven workflow.

---

## Risks (and the audit-derived mitigations)

- **Webview is the extension's largest UI surface to date.** Mitigation:
  yaml `read+validate+write` round-trip with schema validation is the
  most-tested piece (both audit reviewers flagged this as
  non-negotiable).
- **YAML migration breaks an existing operator's `router-config.yaml`.**
  Mitigation: forward migration is idempotent (Session 2); old shape
  still loads with deprecation warnings; old hardcoded env-var names
  still resolve at the resolver layer.
- **Multi-orchestrator concurrency on the YAML files.** Mitigation:
  Gemini called this YAGNI ("single-user editor"); GPT recommended
  last-write detection. Set 026 ships **last-write detection**
  (mtime check + content hash on write; warn before overwrite); no
  file locking.
- **`secretStorage` operator demand materializes mid-implementation.**
  Mitigation: resolver abstraction (G6) means adding the backend is
  a small follow-up set, not a refactor of every key-reading site.
- **Reversing v0.13.14's "the CLIs stay" promise.** Mitigation:
  CHANGELOG explains the operator decision and cites the Marketplace
  download count. Operators upgrading from v0.13.14 → v0.13.15 see
  the migration note.

---

## Sessions (this set, 025)

### Session 1 of 1: Author the implementation spec, schema example, and wireframes

**Goal:** Produce the three doc deliverables for Set 026 to build
against. All locked decisions captured; no new design work — this
is synthesis of the audit verdicts into operationalizable form.

**Steps:**

1. Author `docs/session-sets/025-router-config-editor-spec/spec.md`
   (this file).
2. Author `docs/session-sets/025-router-config-editor-spec/schema-examples.md`
   showing current vs. proposed `router-config.yaml` /
   `budget.yaml` / new `local-overrides.yaml` side-by-side.
3. Author `docs/session-sets/025-router-config-editor-spec/wireframes.md`
   with ASCII layouts for every webview section described in
   "Session 3: Webview implementation."
4. Cross-provider verification (single route call,
   `task_type='session-verification'`) of the three docs together
   — looking for: gating-decision capture accuracy, schema sanity,
   wireframe consistency with the dropdown semantics, anything
   missing.
5. Apply any non-blocking refinements the verifier raises.
6. Close out.

**Creates:**

- `docs/session-sets/025-router-config-editor-spec/spec.md` (this file)
- `docs/session-sets/025-router-config-editor-spec/schema-examples.md`
- `docs/session-sets/025-router-config-editor-spec/wireframes.md`
- `docs/session-sets/025-router-config-editor-spec/session-reviews/session-001/`
  (verification artifacts)
- `docs/session-sets/025-router-config-editor-spec/activity-log.json`
- `docs/session-sets/025-router-config-editor-spec/disposition.json`
- `docs/session-sets/025-router-config-editor-spec/ai-assignment.md`
- `docs/session-sets/025-router-config-editor-spec/change-log.md`

**Touches:** none outside the session set folder.

**Ends with:** Set 025 closes complete; Set 026 has a spec to build
against; operator can spin up Set 026's Session 1 (the
outsourceMode clean-sweep) in a fresh conversation when ready.

**Progress keys:** `session-001/spec`, `session-001/schema-examples`,
`session-001/wireframes`, `session-001/verification`,
`session-001/close-out`.

**Release:** None. Doc-only set.

---

## Success criteria

After Set 025 closes:

1. `spec.md`, `schema-examples.md`, `wireframes.md` are in place and
   internally consistent.
2. All eight gating decisions from the audit are explicitly captured.
3. Set 026's session-1-through-5 shape is sketched concretely enough
   that Set 026's own spec authoring is mostly mechanical filling-in.
4. The cross-provider verifier's verdict is captured in
   `session-reviews/session-001/`.
5. Sets 023, 024, 025 form a coherent narrative: 023 (writer/reader
   alignment) → 024 (UI surface cleanup) → 025 (next-feature spec
   informed by what 024 surfaced about underused infrastructure).


---

## Doc 2: schema-examples.md

# Schema examples — current vs. proposed

> **Purpose:** Side-by-side examples of every YAML file Set 026
> will touch. Current shape on the left, proposed shape on the
> right, with the delta highlighted in a "Changes" subsection
> beneath each.
>
> The actual schema lives in code (`ai_router/config.py` reads,
> Set 026's `schemaValidator.ts` validates). This document is the
> human-readable reference Set 026's implementation sessions will
> diff against.

---

## File 1: `ai_router/router-config.yaml`

### Current — `providers:` block (lines 24–57, abbreviated)

```yaml
providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    base_url: https://api.anthropic.com/v1/messages
    api_version: "2023-06-01"
    rate_limit:
      requests_per_minute: 50
      tokens_per_minute: 80000
    timeout_seconds: 600
    retry:
      max_retries: 2
      backoff_base_seconds: 2

  google:
    api_key_env: GEMINI_API_KEY
    base_url: https://generativelanguage.googleapis.com/v1beta
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 100000
    timeout_seconds: 300
    retry:
      max_retries: 2
      backoff_base_seconds: 2

  openai:
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 100000
    timeout_seconds: 300
    retry:
      max_retries: 2
      backoff_base_seconds: 2
```

### Proposed — `providers:` block (Set 026)

```yaml
providers:
  anthropic:
    display_label: "Anthropic (Claude)"   # NEW: webview-visible name
    enabled: true                          # NEW: toggle without deletion
    api_key_env: ANTHROPIC_API_KEY         # unchanged
    base_url: https://api.anthropic.com/v1/messages  # unchanged
    api_version: "2023-06-01"              # unchanged
    rate_limit:
      requests_per_minute: 50
      tokens_per_minute: 80000
    timeout_seconds: 600
    retry:
      max_retries: 2
      backoff_base_seconds: 2

  google:
    display_label: "Google (Gemini)"       # NEW
    enabled: true                          # NEW
    api_key_env: GEMINI_API_KEY            # unchanged
    base_url: https://generativelanguage.googleapis.com/v1beta
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 100000
    timeout_seconds: 300
    retry:
      max_retries: 2
      backoff_base_seconds: 2

  openai:
    display_label: "OpenAI (GPT)"          # NEW
    enabled: true                          # NEW
    api_key_env: OPENAI_API_KEY            # unchanged
    base_url: https://api.openai.com/v1
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 100000
    timeout_seconds: 300
    retry:
      max_retries: 2
      backoff_base_seconds: 2

  # NEW: example of an operator-added custom provider.
  # When the webview's "Add Provider" button is used, a row of this
  # shape is appended. The minimum required fields are display_label,
  # enabled, api_key_env, and base_url; the rest get sensible defaults.
  custom-openai-compatible:
    display_label: "Custom OpenAI-Compatible Endpoint"
    enabled: false                          # disabled until the operator fills it in
    api_key_env: CUSTOM_OPENAI_API_KEY
    base_url: ""                            # operator fills in
    rate_limit:
      requests_per_minute: 30
      tokens_per_minute: 60000
    timeout_seconds: 300
    retry:
      max_retries: 2
      backoff_base_seconds: 2
```

### Changes

| Field | Status | Default | Notes |
|---|---|---|---|
| `display_label` | **NEW** | Title-cased provider key | UI-visible name. Defaults to a friendly conversion of the YAML key if absent. |
| `enabled` | **NEW** | `true` | Webview shows a toggle. When `false`, models referencing this provider are excluded from routing. |
| `api_key_env` | unchanged | per-provider (e.g., `ANTHROPIC_API_KEY`) | Already supported; surfaced in the webview as the env-var-name input. |
| `base_url` | unchanged | per-provider default | Already supported; surfaced in the webview as the API URL input. |
| Everything else | unchanged | per-existing | Webview reads but does not edit `rate_limit`, `timeout_seconds`, `retry`, `api_version`. Operators who need to tune those still edit the YAML by hand. |

**Backwards compatibility:** `router-config.yaml` files without
`display_label` / `enabled` load cleanly. The reader injects
`enabled: true` and a sensible `display_label` default on read. No
forced migration.

---

### Current — `models:` block (sample entry, line 95)

```yaml
models:
  gemini-pro:
    provider: google
    model_id: gemini-2.5-pro
    tier: 2
    is_enabled: true
    is_enabled_as_verifier: true
    input_cost_per_1m: 1.25
    output_cost_per_1m: 10.00
    max_context_tokens: 1048576
    max_output_tokens: 65536
    system_prompt_file: prompt-templates/system-prompts.md
    notes: "Good for medium-complexity analysis, documentation, code review"
    generation_params:
      thinking_budget: -1
```

### Proposed — `models:` block (no changes)

**No changes.** The `provider: google` field already references the
`providers:` block by key — the audit's "add `provider_id`"
recommendation was based on the audit reviewers not seeing the
existing `provider:` reference. The schema is already correct.

The only operational change: when the webview adds a new model row,
its `provider:` field must reference an existing `providers:` key
(or one being added in the same write). Set 026's schema validator
enforces this at write time.

---

## File 2: `ai_router/budget.yaml`

### Current — informal schema (defined inline in `docs/adoption-bootstrap.md`)

```yaml
# Existing fields, per docs/adoption-bootstrap.md inline schema:
mode: limited-budget               # zero-budget | limited-budget | middle-tier | ample-budget
threshold_usd: 15                  # dollar threshold
threshold_scope: project-lifetime  # project-lifetime | monthly (default: project-lifetime)
verification_method: api           # api | manual-via-other-engine | skipped (default: api)
```

### Proposed — `ai_router/budget.yaml` (Set 026)

```yaml
mode: limited-budget               # unchanged
threshold_usd: 15                  # unchanged

# RENAMED FIELD: threshold_scope -> scope
# The legacy name still loads (with deprecation warning) for one
# release cycle. Webview always writes the new name. Migration
# script flips existing files on first edit.
scope: per-session-set             # NEW canonical: per-session-set | per-project | per-session

# NEW FIELD: per-tier warn percentage. The optimally-intrusive UX:
#   below warn_at_percent       → silent (no prompt)
#   warn_at_percent..100        → one heads-up notification per band
#   100+ (would exceed cap)     → explicit confirm-or-abort dialog
warn_at_percent: 80                # NEW (default 80)

verification_method: api           # unchanged (api | manual-via-other-engine | skipped)
```

### Changes

| Field | Status | Default | Notes |
|---|---|---|---|
| `scope` | **renamed from `threshold_scope`**; **values expanded** | `per-session-set` | Legacy `threshold_scope: project-lifetime` reads as `scope: per-project`; `threshold_scope: monthly` reads as `scope: per-project` plus a `period: monthly` field (not yet wired in Set 026 — emits a deprecation note). |
| `warn_at_percent` | **NEW** | `80` | Percent of `threshold_usd` at which to switch from silent to heads-up. Operator-configurable in the webview slider. |
| `period` | **deferred** | n/a | The legacy `threshold_scope: monthly` case maps to `scope: per-project, period: monthly` *in the schema*; Set 026 does not implement period-based reset. A future set adds it. |

**Three-state UX recap:**

```
projected_cumulative := current_spend + estimated_call_cost

if projected_cumulative < threshold_usd * (warn_at_percent / 100):
    silent — proceed with the call, log to cost-dashboard
elif projected_cumulative < threshold_usd:
    heads-up — non-blocking notification, proceed automatically
else:
    block — modal confirm-or-abort, operator chooses
```

The "one warning per band" hysteresis is per-scope: at `per-session-set`,
crossing the warn threshold once during a set produces one warning
for the whole set, not one per call.

---

## File 3: `ai_router/local-overrides.yaml` (new file)

### Current

**Does not exist.** No machine-local override file shipped today.

### Proposed — full schema (Set 026)

```yaml
# ai_router/local-overrides.yaml
# THIS FILE IS GIT-IGNORED. It is operator-machine-local — anything
# that should NOT be shared with collaborators or committed to the
# repo lives here. Add this file to `.gitignore` in Set 026 Session 1.
#
# Schema is a strict subset of router-config.yaml + budget.yaml +
# new local-only sections. Every field is optional. Whatever is
# present overrides the same field in the canonical YAML at read
# time. Whatever is absent inherits from the canonical YAML.
#
# Example use cases:
#   - You set GEMINI_API_KEY in your shell as MY_PERSONAL_GEMINI_KEY
#     and want this project's ai_router to find it without renaming
#     your env var (override providers.google.api_key_env).
#   - You want Pushover notifications enabled on your machine but
#     not for other collaborators (set notifications.pushover.enabled).
#   - You want to use a different Python interpreter than the one
#     committed in dabblerSessionSets.pythonPath (set
#     extension.pythonPath here, then it wins over the committed
#     setting on your machine).

# --- Provider overrides ---
# Fields you can override per provider:
#   - api_key_env  (point at a different env var)
#   - base_url     (point at a personal proxy / mirror)
#   - enabled      (disable a provider on your machine only)
providers:
  google:
    api_key_env: MY_PERSONAL_GEMINI_KEY
  # other providers inherit from router-config.yaml unchanged

# --- Budget overrides ---
# Operators with personal cost-tracking can override scope / threshold
# without affecting the project-committed values. Use sparingly —
# if the committed values are wrong for the project, fix them
# canonically rather than overriding locally.
# budget:
#   warn_at_percent: 50

# --- Notifications (entirely local) ---
# Pushover keys are personal — they should never live in
# router-config.yaml. This is where they go.
notifications:
  pushover:
    enabled: true
    api_key_env: MY_PUSHOVER_API_KEY    # default: PUSHOVER_API_KEY
    user_key_env: MY_PUSHOVER_USER_KEY  # default: PUSHOVER_USER_KEY

# --- Decision-review queue (significance flagging) ---
# Whether the orchestrator scans the active session-set's open files
# for `# @dabbler:outsource-review("...")` annotations. Default: true.
decision_review:
  honor_annotations: true

# --- Secret resolver backend selection (future-proofing) ---
# Set 026 ships env-var as the only backend. Future sets can add
# `secretStorage` (VS Code) or `keyring` (OS-level). When those land,
# operators select per-key here:
#   providers.google.api_key_source: secretStorage
#   providers.google.api_key_name: dabbler-gemini-key
# Empty / absent in Set 026 — implementation begins in a future set.
```

### Notes

- **`.gitignore` entry:** Set 026 Session 1 adds
  `ai_router/local-overrides.yaml` to the repo's `.gitignore`.
- **Webview labeling:** every field in the webview that *can* be
  locally overridden shows an indicator: "(shared)" if the
  effective value comes from `router-config.yaml`, "(local
  override)" if it comes from `local-overrides.yaml`.
  Clicking the indicator opens a small popover offering "promote
  to shared" / "move to local override" toggles.
- **Validation:** the webview refuses to save a Pushover key
  value to `router-config.yaml` (the shared file) — only env-var
  *names* go in shared; key *values* never live in either YAML
  file. The env-var resolution then reads the actual secret from
  the operator's shell env at runtime.

---

## File 4: `package.json` (extension)

### Current — `contributes.configuration.properties`

```json
{
  "dabblerSessionSets.uatSupport.enabled": { ... },
  "dabblerSessionSets.e2eSupport.enabled": { ... },
  "dabblerSessionSets.e2e.testDirectory": { ... },
  "dabblerSessionSets.pythonPath": { ... },
  "dabblerSessionSets.aiRouterRepoUrl": { ... }
}
```

### Proposed — `contributes.configuration.properties` (Set 026)

**No changes.** The five existing settings stay. The new
configuration surface (providers, routing mode, verification mode,
budget, notifications, significance-flag annotations) lives in YAML,
edited via the webview — *not* in `package.json` per the truth-source
decision (G2).

### Proposed — `contributes.commands`

| New command | ID | Title |
|---|---|---|
| Open config editor | `dabbler.openConfigEditor` | "Open Dabbler Config Editor" |
| Flag decision for review | `dabbler.flagDecisionForReview` | "Flag Decision for Cross-Provider Review" |

Both commands also show up under the "Dabbler" category in the
command palette.

---

## File 5: `.gitignore`

### Current

Whatever's there today, plus the lines added in earlier sets.

### Proposed — diff

```diff
 # existing entries
+
+# ai_router operator-machine-local overrides (Set 026)
+ai_router/local-overrides.yaml
```

Add a single line. Set 026 Session 1 does this as part of the
clean-sweep commit (along with the `outsourceMode` deletions),
since both are repo-housekeeping.

---

## Migration script behavior — `ai_router/migrate_router_config.py`

Set 026 Session 2 ships an idempotent migration. Behavior:

```
On run:
  1. Load router-config.yaml.
  2. For each provider missing `display_label`, inject a default
     (title-cased key).
  3. For each provider missing `enabled`, inject `true`.
  4. (Future) For any other schema additions in subsequent sets,
     apply forward migration here.
  5. Load budget.yaml.
  6. If `threshold_scope` is present and `scope` is not, rename
     `threshold_scope` -> `scope` and translate values:
       - `project-lifetime` -> `per-project`
       - `monthly` -> `per-project` (with a deprecation note;
         period-based reset not yet implemented)
  7. If `warn_at_percent` is absent, inject `80`.
  8. Write both files back (YAML comments preserved via the AST
     round-trip path).

Output: a one-line summary per file —
  "router-config.yaml: 3 providers migrated (display_label injected)"
  "budget.yaml: scope renamed from threshold_scope; warn_at_percent
   added (80)"

Exit codes:
  0 = success (or no-op if already migrated)
  1 = parse error (file is unreadable; refuses to overwrite)
  2 = unexpected schema version (future-proofing)
```

The migration is idempotent: re-running on a freshly-migrated file
produces no changes and exits 0 with a "no migrations applied"
message.

---

## What this spec does NOT touch

- The `models:` block (other than enforcing `provider:` references a
  real `providers:` key at write time — no schema change, just
  validation).
- The `routing:` block (tier assignments, task-type overrides). Set
  026 might tune defaults but does not change the schema.
- The `task_type_params:` block.
- The `verification:` block (cross-provider verification map).
- The `delegation:` / `metrics:` / `proposals:` / `cost_guard:`
  blocks.

These are all out of scope for Set 026. A future set ("router-config
editor v2") can extend the webview to cover them once v1 is shipped
and the table-row UX is validated against the simpler providers
schema.


---

## Doc 3: wireframes.md

# Webview wireframes — Dabbler Config Editor

> **Purpose:** ASCII layouts for every section of the config editor
> webview that Set 026 Session 3 will implement. These are intent
> sketches, not pixel-perfect mockups — Set 026 will choose the
> actual styling (probably matching VS Code's `vscode-elements` /
> codicon vocabulary). Focus on **layout** and **labels** here, not
> visual polish.
>
> Each section header in the live webview shows a collapse/expand
> chevron and a "(modified)" indicator if the section has unsaved
> edits.

---

## Top-level shell

```
+===============================================================================+
| Dabbler Config Editor                                          [ Save ] [ X ] |
+===============================================================================+
|                                                                               |
|  Editing: ai_router/router-config.yaml + budget.yaml + local-overrides.yaml   |
|  Status:  All changes saved.  /  *Unsaved changes in 2 sections (Save)*       |
|                                                                               |
|  +--- Sections ---+                                                           |
|  | > Routing & Verification    (1)                                            |
|  | > Budget                    (2)                                            |
|  | > Providers                 (3)                                            |
|  | > Significance flagging     (4)                                            |
|  | > Notifications             (5)                                            |
|  | > Local overrides summary   (6)                                            |
|  +----------------+                                                           |
|                                                                               |
+===============================================================================+
```

**Behavior:**

- Tabs / collapsible sections in a vertical layout.
- A single **Save** button at the top right writes ALL modified
  files in one batch (so a partial save doesn't leave the YAML
  files inconsistent).
- The "(modified)" indicator next to each section header is the
  cheap signal; the title-bar status line is the authoritative one.
- Closing with unsaved changes prompts: "Discard changes? / Save
  and close / Cancel."

---

## Section 1: Routing & Verification

```
+----- Routing & Verification ----------------------------------------------+
|                                                                          |
|  Mid-session outsourcing                                                 |
|  ---------------------------------------------------------------------   |
|  When should the orchestrator route reasoning tasks to external          |
|  AI providers during the session itself (not at session end)?            |
|                                                                          |
|     [ Whenever helpful (let AI decide)         v ]                       |
|       ( ) Verification only                                              |
|       ( ) Disabled                                                       |
|                                                                          |
|  Cross-provider verification                                             |
|  ---------------------------------------------------------------------   |
|  How should end-of-session cross-provider verification run?              |
|  (Rule 2 of the workflow doc: every session ends with verification       |
|   unless this is explicitly set to None.)                                |
|                                                                          |
|     [ Automatic via API (recommended)          v ]                       |
|       ( ) Manual via portable markdown                                   |
|       ( ) None                                                           |
|                                                                          |
|  i  "Automatic via API" requires outsourcing to be enabled.              |
|     When outsourcing is Disabled, only "Manual" and "None" are           |
|     available here.                                                      |
|                                                                          |
|  Manual verification template URL (when verification = Manual):          |
|     https://raw.githubusercontent.com/darndestdabbler/                   |
|         dabbler-ai-orchestration/master/                                 |
|         ai_router/prompt-templates/verification.md                       |
|                                                                          |
|                                       [ Open template in browser ]       |
|                                                                          |
+--------------------------------------------------------------------------+
```

**Behavior:**

- The two dropdowns interact: setting outsourcing to "Disabled"
  greys out "Automatic via API" in the verification dropdown and
  shows a tooltip on hover.
- The info note ("i") is always visible; the manual-template
  block appears conditionally when verification = Manual.
- The "Open template in browser" button uses VS Code's
  `vscode.env.openExternal` API.
- **YAML writes:**
  - Outsourcing dropdown → `local-overrides.yaml` or a new
    `routing.outsourcing_mode:` field in `router-config.yaml` (Set
    026 picks the file based on whether the operator wants the
    setting shared or local; default is shared).
  - Verification dropdown → `budget.yaml`'s existing
    `verification_method` field (already supported end-to-end by
    the Python `ai_router`).

---

## Section 2: Budget

```
+----- Budget -------------------------------------------------------------+
|                                                                         |
|  Budget threshold                                                       |
|  ---------------------------------------------------------------------  |
|  Operating cost is governed by an open-source AI orchestration          |
|  framework — actual provider costs vary $0–~$50/week depending on       |
|  routing mode and session frequency. See the cost dashboard for         |
|  live spend.                                                            |
|                                                                         |
|  Threshold (USD):     [____15.00____]                                   |
|                                                                         |
|  Scope:               [ Per session-set (recommended)     v ]           |
|                         ( ) Per project                                 |
|                         ( ) Per session  (advanced — high friction)     |
|                                                                         |
|  Warn at:             [================|----] 80%   (slider, 0–100%)    |
|                                                                         |
|  Prompt UX preview                                                      |
|  ---------------------------------------------------------------------  |
|  Below 80% of $15.00 ($12.00):                                          |
|     Silent — no prompt, just log to cost dashboard                      |
|                                                                         |
|  Between 80% and 100% ($12.00–$15.00):                                  |
|     Heads-up — non-blocking notification, one per band                  |
|                                                                         |
|  At or above $15.00:                                                    |
|     Confirm-or-abort — modal dialog before the call proceeds            |
|                                                                         |
|  i  See "Cost dashboard" (Dabbler: Show Cost Dashboard) for live        |
|     cumulative spend. The framework is open-source; you are not         |
|     billed by Dabbler — you are billed by Anthropic, Google, and/or     |
|     OpenAI directly per their pricing.                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Behavior:**

- Threshold input accepts dollar amounts; validates `>= 0`.
- Scope dropdown defaults to "Per session-set". "Per session" is
  visible but flagged as "advanced — high friction" so the
  operator self-selects out of it without it being hidden.
- The slider has snap stops at 50%, 60%, 70%, 80%, 90%.
- The "Prompt UX preview" block re-renders live as the operator
  changes threshold or warn percentage — concrete dollar amounts,
  not abstract percentages, so the operator can sanity-check their
  thresholds before saving.
- **Cost-messaging copy** explicitly follows the operator's
  `feedback_user_facing_cost_messaging` memory: explicit dollar
  ranges, multi-week scale, open-source caveat, dashboard pointer.
- **YAML writes:** all three fields to `budget.yaml` (with the
  `scope` rename + `warn_at_percent` field per
  `schema-examples.md` File 2).

---

## Section 3: Providers

```
+----- Providers ----------------------------------------------------------+
|                                                                         |
|  AI providers configured for this project                               |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  +-------+---------------+---------+-----------------------+----------+ |
|  | On?   | Display label | ID      | API key env var       | Edit URL | |
|  +-------+---------------+---------+-----------------------+----------+ |
|  | [x]   | Anthropic     | anthropic | ANTHROPIC_API_KEY ✓ |  [ ... ] | |
|  |       | (Claude)      |         |                       |          | |
|  +-------+---------------+---------+-----------------------+----------+ |
|  | [x]   | Google        | google  | GEMINI_API_KEY    ✓   |  [ ... ] | |
|  |       | (Gemini)      |         |                       |          | |
|  +-------+---------------+---------+-----------------------+----------+ |
|  | [x]   | OpenAI (GPT)  | openai  | OPENAI_API_KEY    ✓   |  [ ... ] | |
|  +-------+---------------+---------+-----------------------+----------+ |
|  | [ ]   | Custom        | custom- | CUSTOM_OPENAI_API_KEY |  [ ... ] | |
|  |       | OpenAI Endpt  | openai- |               (unset) |          | |
|  |       |               | compat  |                       |          | |
|  +-------+---------------+---------+-----------------------+----------+ |
|                                                                         |
|         [ + Add Provider ]                                              |
|                                                                         |
|  Legend:                                                                |
|    ✓ = env var is set in the current environment                        |
|    (unset) = env var name is configured but not present in the env      |
|                                                                         |
|  i  When you click [...] you can edit per-provider fields: API URL,     |
|     rate limits, timeouts. Most operators only edit the env-var name    |
|     and the Enabled toggle.                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Behavior:**

- The On? column is a checkbox per row mapped to the `enabled`
  field.
- The Display label column is a free-text input; defaults to a
  title-cased version of the ID if blank.
- The ID column is read-only after creation (renaming would orphan
  every `models:` entry referencing it). To rename, delete + re-add.
- The API key env var column shows the env var name (editable) with
  a live "is it set?" badge that re-queries `process.env` on focus.
  ✓ if set; (unset) if not. **No value is ever shown** — only the
  name and presence.
- The Edit URL `[...]` button opens a per-row editor popover for
  the less-common fields (`base_url`, `rate_limit`,
  `timeout_seconds`, `retry`).
- The `[ + Add Provider ]` button appends a new row with `enabled:
  false` and a placeholder ID like `new-provider-1`.
- **YAML writes:** each row → one entry in `router-config.yaml`'s
  `providers:` block.

---

## Section 4: Significance flagging

```
+----- Significance flagging ----------------------------------------------+
|                                                                         |
|  Two ways to flag a decision for cross-provider review                  |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  1) Run the command                                                     |
|     +-----------------------------------------------------------+       |
|     | Dabbler: Flag Decision for Cross-Provider Review          |       |
|     +-----------------------------------------------------------+       |
|     You'll be prompted for a one-line reason. The flag is queued        |
|     in the active session-set's decision-review queue.                  |
|                                                                         |
|     [ Run command now... ]                                              |
|                                                                         |
|  2) Add an annotation in source code                                    |
|                                                                         |
|     # @dabbler:outsource-review("reason text here")                     |
|                                                                         |
|     The orchestrator scans open files at session start; any new         |
|     annotations are queued automatically.                               |
|                                                                         |
|  [x] Honor `@dabbler:outsource-review` annotations in this project      |
|      (defaults to ON; this setting lives in local-overrides.yaml)       |
|                                                                         |
|  i  The queue file is at:                                               |
|        docs/session-sets/<active-slug>/decision-review-queue.jsonl      |
|                                                                         |
|     Flagged decisions surface in the orchestrator's initial             |
|     planning checklist at the next session start.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Behavior:**

- The section is mostly informational — the heavy lifting is in
  the command + annotation parser shipped by Set 026 Session 4.
- The "Run command now..." button invokes
  `dabbler.flagDecisionForReview` so the operator can try it
  without leaving the editor.
- The annotation-honoring checkbox writes to
  `local-overrides.yaml`'s
  `decision_review.honor_annotations` field.

---

## Section 5: Notifications

```
+----- Notifications ------------------------------------------------------+
|                                                                         |
|  Pushover notifications at end-of-session                               |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  [x] Enable Pushover                                                    |
|                                                                         |
|  API key env var:    [ PUSHOVER_API_KEY  ] (✓ set)                      |
|  User key env var:   [ PUSHOVER_USER_KEY ] (✓ set)                      |
|                                                                         |
|  i  These values live in local-overrides.yaml — they are                |
|     NOT shared with collaborators when you push the repo.               |
|     The env vars themselves resolve from your operating-system          |
|     shell environment, not from any file in the repo.                   |
|                                                                         |
|  [ Send a test notification now ]                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Behavior:**

- Section appears greyed-out until the operator checks "Enable
  Pushover".
- Both env-var-name inputs validate as non-empty; show the same
  ✓ / (unset) badge as the providers table.
- "Send a test notification now" attempts to fire a single test
  Pushover message using the configured env vars; surfaces the
  Pushover API response (success / failure with reason) inline.
- **YAML writes:** `local-overrides.yaml`'s `notifications:`
  block. Never `router-config.yaml`.

---

## Section 6: Local overrides summary

```
+----- Local overrides summary --------------------------------------------+
|                                                                         |
|  These settings differ from the shared (committed) configuration:       |
|                                                                         |
|    providers.google.api_key_env                                         |
|       Shared:  GEMINI_API_KEY                                           |
|       Local:   MY_PERSONAL_GEMINI_KEY                                   |
|                                       [ Open local-overrides.yaml ]     |
|                                                                         |
|    notifications.pushover.enabled                                       |
|       Shared:  (not set, defaults to false)                             |
|       Local:   true                                                     |
|                                       [ Open local-overrides.yaml ]     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  i  local-overrides.yaml is in your .gitignore — values here are        |
|     personal to your machine and never get pushed to the repo.          |
|                                                                         |
|  [ Edit local-overrides.yaml directly ]                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**Behavior:**

- Section is empty + shows a "no local overrides" message when
  `local-overrides.yaml` is absent or empty.
- Each row shows the shared (committed) value and the local
  override side-by-side, with a click-through to open the file.
- Read-only — to actually edit, operators use the relevant
  feature section (Providers / Notifications / etc.) or open
  the YAML directly.

---

## Validation surface (cross-cutting)

When the operator hits **Save**:

1. The webview converts the current form state into the proposed
   YAML shape for each file.
2. The schema validator runs:
   - All required fields present.
   - All `provider:` references in `models:` resolve.
   - All `api_key_env` names look like valid env-var names
     (uppercase + underscores).
   - `threshold_usd >= 0`; `warn_at_percent` in `[0, 100]`.
3. If any validation fails, the webview surfaces inline errors
   (red border + tooltip on the offending field) and **does not
   write any file**. Partial saves are not allowed.
4. If validation passes, all files are written atomically:
   `tmp` write + `rename` to avoid partial-write corruption.
5. The Python `ai_router` watches the YAML files; on next call it
   picks up the new values automatically. No daemon restart
   needed.

---

## Out-of-scope for the v1 webview (future work)

- The `routing:` block tier assignments + task-type overrides.
- The `task_type_params:` per-task generation params.
- The `verification:` cross-provider map.
- The `delegation:` / `metrics:` / `cost_guard:` blocks.
- `secretStorage` / `keyring` backends (the schema makes room;
  the backend implementations are future sets).

These all stay edit-the-YAML-by-hand for v1. The webview's job is
the **operator-friendly** surface; the **expert** surface is the
YAML itself.


---

## Appendix A: audit-summary.md (decisions reference)

# Router-config editor — design alignment audit (synthesis)

**Date:** 2026-05-15
**Reviewers:** GPT-5.4 (OpenAI), Gemini Pro (Google), Claude Opus 4.7 (this orchestrator)
**Audit cost:** $0.1197 across both reviewers (GPT-5.4 $0.0919 + Gemini Pro $0.0278)
**Raw verdicts preserved at:** `gpt-5-4-result.json` and `gemini-pro-result.json` in this folder.

---

## Headline

**All three reviewers concur the design is ready to spec — with conditions.**

Both AI reviewers return "yes-with-conditions"; this orchestrator
shares that verdict. The disagreements are bounded and focused on
two architectural details (provider schema, significance heuristic)
and one judgement call (CLI deletion scope). Everything else is
either consensus or low-stakes refinement.

---

## Where all three agree (consensus — lock these in)

| Topic | Consensus position |
|---|---|
| **Q2 — Truth source** | YAML files (`router-config.yaml` + `budget.yaml`) stay canonical. Extension grows a custom-webview editor. `package.json` settings stay only for extension-UI-behavior (notifications toggle, view filters, `pythonPath`). |
| **Q3a — Budget scope** | Three-way dropdown is fine, but **default to per session-set**. Per-project is the advanced option. Per-session is friction-heavy and contradicts the operator's "no per-write prompts" preference — keep it available but framed as exception, not equal choice. |
| **Q3b — Optimally intrusive UX** | Combination: hard cap + warn-at-percent (operator-configurable, e.g., 80%). **Three-state UI:** silent if projected cumulative is below warn threshold; heads-up notification if it crosses warn; explicit confirm if it crosses block. Hysteresis: one warning per band, not on every call. |
| **Q5 — Configurable env-var names** | Real win, not YAGNI. Resolution lives in **Python `ai_router`** (canonical — every execution path honors it) AND the extension reads the same field for setup validation + diagnostics ("env var `MY_ORG_GEMINI_KEY` is not set"). |
| **Q7 — Sharp edges (the must-haves)** | (a) **Schema validation** on round-trip read + write — non-negotiable. (b) **Webview scope includes `budget.yaml`** too, not just `router-config.yaml`. (c) **Forward-migration** on schema version mismatch. |
| **Q8 — Sequencing** | **Split into two session-sets.** Audit-and-spec set first (this one); implementation set later. Both reviewers prefer this over the single-set option; this orchestrator's initial preference (single set) is overridden by the consensus. |

---

## Where the reviewers diverge (operator must pick)

### D1. `outsourceMode` cleanup scope (Q1)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | Deprecate the **spec-level flag** now. **Keep** `ai_router.queue_status`, `heartbeat_status`, and `two-cli-workflow.md` until there's explicit evidence no external repo uses them. |
| **Gemini Pro** | Deprecate **everything**: spec flag, both CLIs, and the workflow doc. Architectural dead end; clean-sweep. |
| **Claude (this orch.)** | The Set 024 commit message and CHANGELOG explicitly said the CLIs stay "for operators running outsource-last in other repos." Reversing that within a week of v0.13.14 would be a credibility hit. **Side with GPT** — flag deprecation in this work, CLI deletion as a future "if we're sure" cleanup. |

**Recommendation:** Pick GPT's cautious path. Concrete next step: spec
deprecates `outsourceMode` from `spec.md` but leaves Python CLIs +
two-cli-workflow.md untouched. A future "Set N+M: remove
outsource-last entirely" decision can be made on evidence (or its
absence).

### D2. Provider schema — `providers:` vs alias-for-`models:` (Q6)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | **Dissent** with table-as-`models:`-alias. Credentials, endpoints, and API protocol are provider-level; `models:` is a routing inventory. Multi-model providers (OpenAI has many models behind one API key) would duplicate auth config under the alias approach. Recommends a new top-level `providers:` block; `models:` entries reference `provider_id`. |
| **Gemini Pro** | **Concur** with table-as-`models:`-alias. Simpler implementation; one canonical structure; direct UI-to-data mapping. |
| **Claude (this orch.)** | GPT's reasoning is technically more correct (provider ≠ model is right OO modeling, and the existing `router-config.yaml` already has a separate `providers:` block at lines 25–48 — `anthropic:`, `google:`, `openai:` — that the proposed alias would conflict with). Gemini missed that existing structure. **Side with GPT.** |

**Recommendation:** Adopt GPT's `providers:` shape. The current
`router-config.yaml` already has a `providers:` block; the new schema
**extends** that block to include `api_key_env_var`, `api_base_url`,
`display_label`, `enabled`. `models:` entries gain a `provider_id`
reference field (today the provider is inferred from the model_id
prefix — that ad-hoc coupling becomes explicit).

### D3. "Significance" heuristic (Q4)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | **Mixed.** Feasible only as soft suggestion in planning/checklist flow, never silent gating. Score from high-signal events (schema changes, dependency choices, multi-repo blast radius). One dismiss per session. |
| **Gemini Pro** | **Dissent.** Scrap the heuristic entirely. Replace with explicit operator-invoked mechanism: a `Dabbler: Flag Decision for Cross-Provider Review` command, or a code annotation (`# @dabbler:outsource-review("...")`) the orchestrator recognizes. |
| **Claude (this orch.)** | Both AIs converge on "automatic detection is unreliable." Gemini's explicit-command path is the more defensible UX and matches the operator's "default not started; positive evidence to escalate" memory pattern. **Side with Gemini.** |

**Recommendation:** Replace the "Suggest outsourcing on significant
decisions" checkbox with: (a) a manual VS Code command
(`Dabbler: Flag Decision for Cross-Provider Review`) that the
operator invokes when they want a routed second opinion, and (b) a
recognized code-annotation pattern the orchestrator picks up during
session work. The toggle goes away; the capability becomes a tool
the operator reaches for deliberately.

---

## New sharp edges surfaced (lock these before spec)

### S1. "Never" routing-mode conflicts with mandatory verification (GPT, Q7)

The proposed `AI Outsourcing` dropdown has a "Never" option. The
workflow's Rule 2 is "Never skip verification" — the only legal
bypass today is `budget.yaml`'s `verification_method: skipped` or
`manual-via-other-engine`. **The dropdown must reconcile with the
existing budget.yaml verification policy**. Concrete options:

- (a) "Never" disables **all non-verification routing only**;
  end-of-session verification still fires unless `budget.yaml`
  separately declares `verification_method: skipped`.
- (b) "Never" sets `verification_method: skipped` in `budget.yaml`
  too — single-knob convenience, at the cost of hiding the
  audit-trail implication.
- (c) Rename "Never" to "Verification only" to make the semantics
  explicit (Verification only == "all routing except mandatory
  end-of-session verification is disabled").

**Recommendation:** Pick (c). The current dropdown already has
"Only for Cross-Provider Verification" as a distinct option; "Never"
adds confusion. Either drop "Never" entirely (the
"verification only" option already covers the "minimal routing"
intent) **or** rename "Never" to "Disabled including verification"
to force the operator to acknowledge they're opting out of Rule 2.

### S2. Shared-vs-local config separation (GPT, Q7)

`router-config.yaml` is checked into the repo (shared with
collaborators). But some fields are **operator-machine-local**:
notification env-var names, Pushover keys, possibly `pythonPath`,
maybe even API-key env-var name overrides. Today there's no
local-only YAML; this design needs one.

**Recommendation:** Introduce a `.gitignore`-d
`ai_router/local-overrides.yaml` (or similar) for operator-local
fields. Webview shows which fields are shared-canonical vs.
local-overridden. Round 2 of the spec should decide which fields
default to which file.

### S3. secretStorage as a future-proofing concern (both)

Both reviewers raise VS Code's `secretStorage` API as an alternative
to env-var-only key storage. **Gemini calls it a must-have**; GPT
says "defer with an abstraction." The current env-var-only model
is fine for most operators but creates friction in security-strict
orgs.

**Recommendation:** GPT's middle path — design the resolver
abstraction now (every key lookup goes through
`resolve_secret(name, source)`), implement env-var as the only
backend in v1, add `secretStorage` and `keyring`/etc. backends in
future sets when there's demand. Gemini's "ship it now" is overkill
without a concrete operator request.

---

## Updated gating-decision checklist (operator picks before spec)

| # | Decision | Recommended |
|---|---|---|
| G1 | `outsourceMode` cleanup scope | GPT's path — deprecate spec flag, keep CLIs |
| G2 | Provider schema shape | GPT's path — extend `providers:` block, add `provider_id` to `models:` |
| G3 | "Significance" heuristic | Gemini's path — replace toggle with explicit command + annotation |
| G4 | "Never" dropdown semantics | Rename or drop; reconcile with `verification_method` |
| G5 | Shared-vs-local config | Add `.gitignore`-d local-overrides file |
| G6 | secretStorage | Resolver abstraction now, backends as needed |
| G7 | Budget scope default | Per session-set (per consensus) |
| G8 | Sequencing | Two session-sets (this one finishes as audit + spec doc; next set implements) |

---

## What this audit-and-spec set produces, if the operator concurs

If the operator agrees with the recommendations above, the
remaining deliverables for this set are:

1. **`spec.md`** for the eventual implementation set — locking the
   schema, the UX shapes, the migration path, and the "Never"
   semantics resolution.
2. **A schema example file** showing the proposed shape of
   `router-config.yaml` + `budget.yaml` + `local-overrides.yaml`
   post-change, side by side with the current shape, for diff
   review.
3. **Wireframes** (ASCII or markdown-table mockups) of the
   webview — table layout for providers, dropdown for outsourcing
   mode, three-state budget prompt UX.
4. **No implementation code.** That's the next session-set.

---

## Open questions the audit could **not** answer (these need operator input)

- **Q-A. The `outsourceMode` removal sequencing.** Does the operator
  agree with GPT's "remove flag now, keep CLIs until evidence"
  staging, or prefer Gemini's clean-sweep?

- **Q-B. The "Never" naming.** The operator originally wrote "Never"
  in the sketch. Is that an explicit "disable verification too"
  intent, or an oversight that should be renamed?

- **Q-C. Per-session budget scope.** Both reviewers want it
  de-prioritized. Is the operator OK demoting it to advanced /
  hidden, or do they have a use case in mind where per-session
  approval is the right granularity?

- **Q-D. The local-overrides file.** Does the operator want
  `ai_router/local-overrides.yaml`, `.dabbler-local.yaml`, or a
  different name? Does it live in the repo root or in `ai_router/`?

- **Q-E. The annotation pattern for significance flagging.** Is
  `# @dabbler:outsource-review("...")` the right syntax, or does the
  operator have a preference (`# DABBLER-REVIEW:`, structured
  comment, dedicated file, etc.)?

# Router-config editor — implementation

> **Purpose:** Implement the router-config editor that Set 025
> spec'd. Six sessions: outsourceMode clean-sweep → YAML schema +
> Python reader + resolver → webview foundation → webview sections
> → significance flagging → wizard + test-notification + release.
> Ships extension v0.13.15 + ai_router v0.3.0.
>
> **Session Set:** `docs/session-sets/026-router-config-editor-implementation/`
> **Created:** 2026-05-15
> **Workflow:** Full
> **Prerequisite:** Set 025 closed (audit + spec). The single
> normative reference for every persistence question is
> `docs/session-sets/025-router-config-editor-spec/spec.md`
> **Appendix B** (the control-to-YAML mapping table, enum
> mappings, precedence rules, migration rules, and validation
> timing). When this spec is ambiguous, Appendix B wins; this
> spec deliberately does **not** re-state Appendix B.

---

## Session Set Configuration

```yaml
totalSessions: 6
requiresUAT: false
requiresE2E: false
uatStyle: ad-hoc
uatScope: none
effort: normal
```

> **Note on `outsourceMode`:** This spec deliberately omits the
> `outsourceMode:` field. Session 1 of this set deletes the flag
> from the spec-authoring guide; authoring this spec without the
> field is the first instance of the post-cleanup format. The
> workflow tooling tolerates the omission (defaults to
> outsource-first semantics, which is what this set wants
> regardless).
>
> Rationale: multi-session set spanning Python + TypeScript work
> + Marketplace release. `effort: normal` because each session is
> bounded, but the cumulative surface (~3500 LOC across new files,
> ~500 LOC of edits to existing files) is more than any single
> session in the recent history. Sessions are sized so each fits
> in one conversation; the implementing orchestrator may split
> Session 4 (webview sections) into 4a + 4b if the
> conversation-budget gets tight.

---

## Decisions inherited from Set 025 (do not re-litigate)

All eight gating decisions (G1–G8) and the normative Appendix B
from Set 025's `spec.md` are inherited. Audit rationale lives at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`;
deliverable shapes live at `docs/session-sets/025-router-config-editor-spec/`
(spec.md, schema-examples.md, wireframes.md).

This spec **expands** Set 025's five-session breakdown into six
sessions by splitting the webview work into foundation
(Session 3) and sections (Session 4). The total deliverable set
is unchanged from Set 025's spec; only the per-session
granularity is different.

---

## Sessions

### Session 1 of 6: `outsourceMode` clean-sweep

**Goal:** Remove the queue-mediated daemon (`outsourceMode: last`)
infrastructure end-to-end. Deletion-only — no new code, no schema
changes. Mirrors Set 024's deletion-only profile.

**Steps:**

1. Delete the Python modules (~10 files):
   - `ai_router/queue_status.py`
   - `ai_router/heartbeat_status.py`
   - `ai_router/queue_db.py`
   - `ai_router/queue_verification.py`
   - `ai_router/daemon_pid.py`
   - `ai_router/orchestrator_role.py`
   - `ai_router/restart_role.py`
   - `ai_router/role_status.py`
   - `ai_router/capacity.py`
   - Any other module flagged by `grep -l 'outsource_mode\|queue_db\|daemon\|capacity_signal' ai_router/`
2. Delete the workflow doc: `ai_router/docs/two-cli-workflow.md`.
3. Delete the corresponding Python test files (run `grep -l
   'queue_db\|heartbeat_status\|capacity' ai_router/test_*.py` to
   find them).
4. Edit `ai_router/close_session.py`:
   - Remove `outsource_mode` parameter, case branches, and any
     "queue mode" verification-wait logic.
   - Collapse to a single (formerly outsource-first) verification
     path.
5. Edit `ai_router/start_session.py`:
   - Remove `outsource_mode` parameter handling.
6. Edit `ai_router/gate_checks.py`:
   - Remove queue-related gate predicates (e.g., any
     `check_queue_*` predicates wired into `GATE_CHECKS`).
7. Edit `ai_router/router-config.yaml`:
   - Remove `queue_db_path` and any other daemon-related config
     rows.
8. Edit `docs/ai-led-session-workflow.md`:
   - Remove every reference to `outsourceMode: last`, "subscription
     CLI," "verifier daemon," queue-related step-6 / step-8
     branches.
   - Remove the `outsource-last` row from the budget-tier table.
   - Remove the "What outsource-first vs. outsource-last actually
     means" explainer if present.
9. Edit `docs/planning/session-set-authoring-guide.md`:
   - Remove the `outsourceMode:` row from the Session Set
     Configuration block reference.
10. Edit `ai_router/docs/close-out.md`:
    - Remove every mode-aware branch from the `close_session`
      invocation flow and gate descriptions.
11. Edit `docs/adoption-bootstrap.md`:
    - Replace the outsource-first vs outsource-last explainer
      with a single-mode description.
    - Update the budget-tier dialog so the "less than ~$20"
      and "$20–$99" tiers no longer recommend `outsource-last`.
12. Scrub existing session-set spec files: `git grep -l
    outsourceMode docs/session-sets/` and remove the
    `outsourceMode:` line from every match.
13. Bump version: `ai_router/__init__.py` to `0.3.0`
    (major-minor bump signals breaking change for any hypothetical
    outsource-last consumer); extension `package.json` /
    `package-lock.json` to `0.13.15` (operator-facing release).
14. Add to `.gitignore`: `ai_router/local-overrides.yaml` (one
    line; preemptive for Session 2's file creation).
15. CHANGELOG entries:
    - `ai_router/CHANGELOG.md` (if it exists) — `[0.3.0]` section
      acknowledging the breaking change.
    - `tools/dabbler-ai-orchestration/CHANGELOG.md` — `[0.13.15]`
      section explaining the Provider Queues / Heartbeats Python
      CLIs are no longer shipped. Cite Set 024's `v0.13.14`
      CHANGELOG explicitly and note the reversal.
16. Compile + test: `npx tsc --outDir out` for the extension;
    `python -m pytest` for ai_router. Both must pass clean.
17. Cross-provider verification.

**Creates:** none

**Touches:**

- Deletes ≈10 Python modules + 1 doc + several test files
- `ai_router/close_session.py`, `start_session.py`,
  `gate_checks.py`, `router-config.yaml`, `__init__.py`
- `docs/ai-led-session-workflow.md`,
  `docs/planning/session-set-authoring-guide.md`,
  `ai_router/docs/close-out.md`,
  `docs/adoption-bootstrap.md`
- Every `docs/session-sets/*/spec.md` containing
  `outsourceMode:`
- `tools/dabbler-ai-orchestration/package.json`,
  `package-lock.json`, `CHANGELOG.md`
- `.gitignore`

**Ends with:** No remaining references to `outsourceMode`,
`queue_db`, `daemon_pid`, `verifier daemon`, or
`subscription CLI` anywhere in the repo (confirm via
`git grep -i 'outsourcemode\|queue_db\|verifier daemon\|subscription cli'`).
Both compile + pytest pass.

**Progress keys:** `session-001/delete-python-modules`,
`session-001/delete-workflow-doc`,
`session-001/strip-mode-aware-branches`,
`session-001/scrub-existing-specs`,
`session-001/version-bumps`,
`session-001/changelog`,
`session-001/compile-and-test`,
`session-001/verification`.

**Release:** None at the end of Session 1 alone — the version
bumps land but no Marketplace publish until Session 6.

---

### Session 2 of 6: YAML schema + Python reader updates + resolver abstraction

**Goal:** Bring the YAML files into the Set-025-Appendix-B shape;
add the secret-resolver abstraction with env-var as its only
backend; ship the idempotent migration script. Pure Python —
no extension code yet.

**Steps:**

1. Edit `ai_router/router-config.yaml`:
   - Add new `display_label` + `enabled` fields to each existing
     `providers:` block entry (anthropic, google, openai). Field
     values per Set 025's `schema-examples.md` File 1 proposed
     section.
   - Add new top-level `routing.outsourcing_mode: whenever-helpful`
     field per Set 025's `schema-examples.md` File 1b.
2. Edit `ai_router/config.py`:
   - Parse the new `display_label`, `enabled`, and
     `routing.outsourcing_mode` fields with default-tolerant
     handling (missing fields → schema defaults).
   - Validate `models.<id>.provider` references resolve against
     the `providers:` block; raise a clear error on dangling
     references.
   - Read `local-overrides.yaml` if present; apply per Appendix B
     precedence rules (local > shared > default). Reject
     overrides on paths marked "Local-override allowed? No";
     reject providers/models that exist only in local-overrides.
3. Edit `ai_router/providers.py`:
   - No changes needed — existing `api_key_env` read path is
     unchanged. Spot-check that the resolver indirection (Step 4)
     replaces direct `os.environ[...]` lookups here.
4. Create `ai_router/secret_resolver.py`:
   - Export `resolve_secret(name: str, source: str = "env") -> str | None`.
   - Implement the `env` backend (resolves `name` via
     `os.environ.get`).
   - Register the backend in a module-level registry so future
     sets can add `secretStorage`, `keyring`, etc. without
     touching callers.
   - Tests: `test_secret_resolver_env_backend.py` covering
     present, absent, empty-string, and case-sensitivity cases.
5. Refactor every direct env-var lookup in `ai_router/` to go
   through `resolve_secret`. Grep target:
   `os.environ\[\|os.environ.get` inside `ai_router/`. Each
   match either becomes `resolve_secret(name)` or stays as-is
   (for non-API-key env vars like
   `AI_ROUTER_ALLOW_FORCE_CLOSE_OUT`).
6. Create `ai_router/migrate_router_config.py`:
   - Idempotent forward migration per Appendix B's
     `threshold_scope` → `scope` rules and Set 025
     `schema-examples.md` Migration Behavior section.
   - On run: load `router-config.yaml`, inject defaults for
     missing `display_label` / `enabled`, normalize
     `routing.outsourcing_mode` if absent; load `budget.yaml`,
     rename `threshold_scope` → `scope`, translate values
     (`project-lifetime` → `per-project`; `monthly` →
     `per-project` + `period: monthly`); inject
     `warn_at_percent: 80` if absent.
   - Preserve YAML comments via `ruamel.yaml` AST round-trip
     (add `ruamel.yaml>=0.18` to `ai_router/requirements.txt` if
     not already present).
   - Exit codes per Appendix B: 0 = success or no-op, 1 = parse
     error, 2 = unexpected schema version.
   - Tests: `test_migrate_router_config_idempotent.py`,
     `test_migrate_router_config_threshold_scope_rules.py`,
     `test_migrate_router_config_preserves_comments.py`.
7. Run the migration once against this repo's current
   `router-config.yaml` + `budget.yaml` (if a budget.yaml exists;
   otherwise create one with defaults). Commit the migrated
   files as part of this session.
8. Add `local-overrides.yaml` schema-validation test:
   `test_local_overrides_merge.py` covering precedence (local
   wins), allowlist violations (path not in Appendix B "yes" set
   = validation error), local-only providers (validation error),
   and unknown keys (warn-and-ignore).
9. Update `ai_router/__init__.py`: ensure
   `secret_resolver.resolve_secret` is exported as part of the
   public surface.
10. CHANGELOG: append to `ai_router/CHANGELOG.md` the new
    schema fields + migration script + resolver abstraction.
11. Run `python -m pytest`. All new tests pass; no existing
    tests regress.
12. Cross-provider verification.

**Creates:**

- `ai_router/secret_resolver.py`
- `ai_router/migrate_router_config.py`
- `ai_router/test_secret_resolver_env_backend.py`
- `ai_router/test_migrate_router_config_idempotent.py`
- `ai_router/test_migrate_router_config_threshold_scope_rules.py`
- `ai_router/test_migrate_router_config_preserves_comments.py`
- `ai_router/test_local_overrides_merge.py`
- `ai_router/budget.yaml` (if absent — operator may have one
  already; if so, migrate in place)

**Touches:**

- `ai_router/router-config.yaml` (new fields)
- `ai_router/config.py` (parse + validate + merge)
- `ai_router/providers.py` (resolver indirection)
- `ai_router/__init__.py` (export resolver)
- `ai_router/requirements.txt` (ruamel.yaml if not present)
- `ai_router/CHANGELOG.md`
- Other Python files using `os.environ` for API-key lookups
  (resolver indirection)

**Ends with:** `python -m pytest` clean; migration script
idempotent (running twice produces no second-run changes);
`router-config.yaml` carries the new fields; `local-overrides.yaml`
is gitignored but reading it works end-to-end.

**Progress keys:** `session-002/yaml-schema-fields`,
`session-002/config-py-readers`,
`session-002/resolver-abstraction`,
`session-002/migration-script`,
`session-002/local-overrides-merge`,
`session-002/test-suite`,
`session-002/verification`.

**Release:** None (still in implementation).

---

### Session 3 of 6: Webview foundation

**Goal:** Stand up the config-editor webview's *infrastructure* —
panel registration, YAML round-trip, schema validation. No
section UIs yet (those land in Session 4). The success criterion is
"I can open the editor, see a placeholder for each section,
modify a YAML file by hand, reload, and see the validator's
output."

**Steps:**

1. Add `js-yaml` (or `yaml`) npm package to
   `tools/dabbler-ai-orchestration/package.json` dependencies.
   Prefer `yaml` (Eemeli Aro's library) for AST-mode round-trip
   that preserves comments — match the Python side's
   `ruamel.yaml` semantics.
2. Add `ajv` (or equivalent JSON-schema validator) to
   dependencies.
3. Create `tools/dabbler-ai-orchestration/src/configEditor/`
   directory. Inside it:
   - `ConfigEditorPanel.ts` — webview panel registration. One
     panel per workspace; subsequent opens reveal the existing
     panel. HTML/CSS scaffolded with a section nav (chevrons + 6
     placeholder section divs).
   - `yamlReadWrite.ts` — exports `readYamlFile`,
     `writeYamlFile`, `parseDocument` (AST mode). Round-trip-safe
     — round-tripping `router-config.yaml` through
     parseDocument + serialize must produce byte-identical
     output (no comment / formatting loss).
   - `schemaValidator.ts` — Two schemas: one for
     `router-config.yaml`, one for `budget.yaml`, plus
     local-overrides-specific validation (allowlist enforcement
     per Appendix B). Exports
     `validateBatch(batch: { ... }): ValidationResult` that
     runs all schemas + cross-file invariants (models reference
     real providers, etc.).
4. Register the new command in `package.json`:
   - `dabbler.openConfigEditor` — title: "Open Dabbler Config
     Editor". Category: "Dabbler".
5. Register the command handler in `src/extension.ts`:
   - Wire `dabbler.openConfigEditor` to
     `ConfigEditorPanel.createOrShow(context)`.
6. Per the Set 025 wireframes `## Top-level shell` block: the
   webview's top-level HTML shows the file paths being edited,
   a save state, a section nav, and a single Save button. The
   section content area shows section placeholders saying "Coming
   in Session 4" — Session 3 wires the shell + load + validate +
   save *without* the section UIs.
7. Implement the load flow:
   - Panel open → call `yamlReadWrite.readYamlFile` for each of
     `router-config.yaml`, `budget.yaml`, `local-overrides.yaml`
     (if present).
   - Run `schemaValidator.validateBatch` on the loaded set.
   - On failure: render a "drift detected" banner with the
     validator's complaints listed; sections stay read-only.
   - On success: sections become editable (still placeholders
     until Session 4).
8. Implement the save flow (per Appendix B atomicity rules):
   - In-memory batch validation first; abort on failure with
     inline error highlights.
   - Per-file `tmp write + rename` for atomic per-file writes.
   - Half-batch recovery on next load via mtime + content-hash
     drift detection (the recovery dialog itself ships in
     Session 4; Session 3 only needs to detect drift and surface
     a one-line warning).
9. Tests in `src/test/suite/`:
   - `yamlReadWrite.test.ts` — round-trip preservation (comments,
     multi-line strings, unicode), parse-error handling.
   - `schemaValidator.test.ts` — every validation rule from
     Appendix B (required fields present, provider references
     resolve, env-var name shape, threshold_usd ≥ 0,
     warn_at_percent in [0, 100], local-overrides allowlist).
   - `configEditor-foundation.test.ts` — panel open / reveal /
     dispose; load-time validation; save-time atomicity.
10. Compile + run tests. `npx tsc --outDir out` clean;
    affected mocha tests pass.
11. Cross-provider verification.

**Creates:**

- `tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/yamlReadWrite.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/yamlReadWrite.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/schemaValidator.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/configEditor-foundation.test.ts`

**Touches:**

- `tools/dabbler-ai-orchestration/package.json` (dependency
  adds, command registration)
- `tools/dabbler-ai-orchestration/package-lock.json`
- `tools/dabbler-ai-orchestration/src/extension.ts` (command
  handler wiring)

**Ends with:** `Dabbler: Open Dabbler Config Editor` opens a
working webview shell. Save flow round-trips YAML files
losslessly. Validator surfaces drift on load. No section UIs yet
— that's Session 4.

**Progress keys:** `session-003/dependencies`,
`session-003/panel-shell`,
`session-003/yaml-readwrite`,
`session-003/schema-validator`,
`session-003/load-flow`,
`session-003/save-flow`,
`session-003/test-suite`,
`session-003/verification`.

**Release:** None.

---

### Session 4 of 6: Webview sections

**Goal:** Implement the six webview sections inside the Session-3
shell. Each section reads its bound YAML paths via the
foundation's load API and writes via the save API. UI conforms
to the ASCII layouts in Set 025's `wireframes.md`.

**Steps:**

1. Create one section file per
   `tools/dabbler-ai-orchestration/src/configEditor/sections/`:
   - `routingAndVerificationSection.ts` — two decoupled
     dropdowns; constraint (API verification greys out when
     routing = Disabled) per Set 025 wireframes §1.
   - `budgetSection.ts` — threshold input + scope dropdown
     (two UI options per G7) + warn-at-percent slider +
     3-state preview that re-renders live. Uses the
     operator-required cost-messaging copy verbatim
     (explicit dollar ranges, multi-week scale, open-source
     caveat, dashboard pointer per memory:
     `feedback_user_facing_cost_messaging`).
   - `providersTableSection.ts` — variable-length table with
     add/remove/edit-row controls; per-row enabled checkbox,
     display label, ID (read-only after creation),
     `api_key_env` input with ✓/(unset) badge, and a "..."
     button that opens a popover for `base_url` +
     `rate_limit` + `timeout_seconds` + `retry`. Never
     displays env-var *values*, only names + presence.
   - `significanceFlaggingSection.ts` — read-only documentation
     section per Set 025 wireframes §4, with a "Run command
     now..." button bound to
     `dabbler.flagDecisionForReview` (the command itself
     ships in Session 5; the button surface exists in
     Session 4 with a graceful fallback message if the
     command is not yet registered) and the
     `decision_review.honor_annotations` toggle wired to
     `local-overrides.yaml`.
   - `notificationsSection.ts` — Pushover enabled toggle +
     two env-var-name inputs with ✓/(unset) badges. The
     "Send a test notification now" button shows as
     disabled with "(wired in Session 6)" — implementation
     happens in Session 6.
   - `localOverridesSummarySection.ts` — read-only listing of
     paths present in `local-overrides.yaml`, side-by-side
     with the shared value, with click-through "Open
     local-overrides.yaml" buttons.
2. Each section file exports a `render(state) => HTMLElement`
   function plus an `onSave() => Patch` function the panel
   coordinator calls during save.
3. Wire each section into the Session-3 shell — replace the
   "Coming in Session 4" placeholders.
4. Implement the half-batch recovery dialog from Appendix B's
   atomicity clarification:
   - On panel open, detect mtime/content-hash drift between the
     loaded batch and the last successful save.
   - Surface a modal: "Last save left N of M files unwritten.
     Re-apply from cache, or accept the current on-disk state
     as the new baseline?"
5. Add the "(shared)" / "(local override)" indicator per field
   (Appendix B's effective-value rules):
   - Effective value comes from `router-config.yaml` /
     `budget.yaml` → `(shared)`.
   - Effective value comes from `local-overrides.yaml` →
     `(local override)`.
   - Fields marked "Local-override allowed? No" in Appendix B
     show no indicator.
   - Clicking the indicator opens a popover with "promote to
     shared" / "move to local override" toggles (where the
     allowlist permits).
6. Section-rendering tests in `src/test/suite/`:
   - `routingAndVerificationSection.test.ts` (constraint enforcement)
   - `budgetSection.test.ts` (slider behavior, 3-state preview)
   - `providersTableSection.test.ts` (add/remove/edit-row,
     ✓/(unset) badge logic)
   - `significanceFlaggingSection.test.ts`
   - `notificationsSection.test.ts`
   - `localOverridesSummarySection.test.ts`
7. End-to-end webview smoke test:
   - Open the editor → all six sections render.
   - Edit one field per section → Save → re-open → values
     persist.
   - Hand-edit `router-config.yaml` to introduce an invalid
     field → reload → validator surfaces it in the "drift
     detected" banner.
8. Compile + test. `npx tsc --outDir out` clean; all six
   section tests + the foundation tests pass.
9. Cross-provider verification.

**Creates:**

- `tools/dabbler-ai-orchestration/src/configEditor/sections/routingAndVerificationSection.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/budgetSection.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/providersTableSection.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/significanceFlaggingSection.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/notificationsSection.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/localOverridesSummarySection.ts`
- One `.test.ts` per section under `src/test/suite/`.

**Touches:**

- `tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts`
  (replace placeholders with real section renders)

**Ends with:** All six wireframed sections functional. The
webview is operator-usable end-to-end for every field listed in
Appendix B's control-to-YAML mapping table.

**Progress keys:** `session-004/six-sections`,
`session-004/half-batch-recovery`,
`session-004/shared-vs-local-indicator`,
`session-004/section-tests`,
`session-004/end-to-end-smoke`,
`session-004/verification`.

**Release:** None.

---

### Session 5 of 6: Significance flagging — command + annotation handling

**Goal:** Ship the explicit operator-invoked surfaces for "flag a
decision for cross-provider review" (Set 025 decision G3).

**Steps:**

1. Create `tools/dabbler-ai-orchestration/src/commands/flagDecisionForReview.ts`:
   - Registers `dabbler.flagDecisionForReview`.
   - On invocation: prompts for a single-line reason
     (`vscode.window.showInputBox`).
   - On accept: appends a structured JSON line to
     `docs/session-sets/<active-slug>/decision-review-queue.jsonl`:
     `{ "ts": "<ISO>", "reason": "<text>", "source": "command",
     "file": null, "line": null }`.
   - On the active set being absent (no in-progress session set
     in the workspace): show an info notification "No active
     session set to flag against" and return.
2. Register the command in `package.json` under
   `contributes.commands`:
   - `dabbler.flagDecisionForReview` — title: "Flag Decision for
     Cross-Provider Review". Category: "Dabbler".
3. Wire the command handler into `src/extension.ts`.
4. Create `ai_router/decision_review_queue.py`:
   - Export `read_queue(session_set_dir: Path) -> list[dict]`
     that reads `decision-review-queue.jsonl`, parses each line
     as JSON, returns the list.
   - Export `clear_queue(session_set_dir: Path)` for orchestrator
     use after acknowledging the entries.
   - Tests: `test_decision_review_queue_reader.py` covering
     empty file, malformed line (skip + warn), idempotent clear.
5. Implement the annotation parser:
   - Create `tools/dabbler-ai-orchestration/src/configEditor/annotationParser.ts`
     exporting `findAnnotations(text: string, filePath: string)
     -> Annotation[]`.
   - Regex: `# @dabbler:outsource-review\("([^"]+)"\)` (Python
     comment style; extend to `// @dabbler:outsource-review(...)`
     and similar for JS/TS/Java/C# if scope permits).
   - Each match → `{ ts: now, reason: <captured>, source:
     "annotation", file: <relative>, line: <line> }`.
6. Create `tools/dabbler-ai-orchestration/src/commands/scanAnnotationsForActiveSet.ts`:
   - Registers `dabbler.scanAnnotationsForActiveSet` (also
     surfaced as part of the active set's session-start hook in
     a future set).
   - Walks the workspace files (respecting `.gitignore`),
     accumulates annotations, appends them to the active set's
     `decision-review-queue.jsonl` (deduplicating against
     existing entries by file+line+reason).
   - Honors the `local-overrides.yaml`
     `decision_review.honor_annotations` toggle — if false,
     scanning is a no-op with an info notification.
7. Wire `dabbler.flagDecisionForReview` and
   `dabbler.scanAnnotationsForActiveSet` into the
   `significanceFlaggingSection.ts` section's button. Replace
   Session 4's "graceful fallback message" with the real
   command invocations.
8. Update `docs/ai-led-session-workflow.md` with a new
   "Significance flagging" section documenting both surfaces +
   the annotation syntax + the queue file path.
9. Tests:
   - `flagDecisionForReview.test.ts` (queue file append +
     idempotency).
   - `annotationParser.test.ts` (regex matches; multiline /
     unicode / nested-paren cases).
   - `scanAnnotationsForActiveSet.test.ts` (workspace walk,
     dedup, honor-annotations toggle).
10. Compile + test. Clean tsc, all new tests pass.
11. Cross-provider verification.

**Creates:**

- `tools/dabbler-ai-orchestration/src/commands/flagDecisionForReview.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/annotationParser.ts`
- `tools/dabbler-ai-orchestration/src/commands/scanAnnotationsForActiveSet.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/flagDecisionForReview.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/annotationParser.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/scanAnnotationsForActiveSet.test.ts`
- `ai_router/decision_review_queue.py`
- `ai_router/test_decision_review_queue_reader.py`

**Touches:**

- `tools/dabbler-ai-orchestration/package.json` (commands)
- `tools/dabbler-ai-orchestration/src/extension.ts`
- `tools/dabbler-ai-orchestration/src/configEditor/sections/significanceFlaggingSection.ts`
  (wire up the real commands)
- `docs/ai-led-session-workflow.md`

**Ends with:** Both surfaces work end-to-end. Operator can run
the command, append a queue entry, scan annotations, and see them
in the section's read-only listing.

**Progress keys:** `session-005/flag-command`,
`session-005/queue-reader`,
`session-005/annotation-parser`,
`session-005/workspace-scanner`,
`session-005/workflow-doc-update`,
`session-005/test-suite`,
`session-005/verification`.

**Release:** None.

---

### Session 6 of 6: Wizard integration + test-notification + end-to-end + release

**Goal:** Final integration polish, the deferred test-notification
button, and the Marketplace + Open VSX release. Ships v0.13.15 +
ai_router 0.3.0.

**Steps:**

1. Wizard integration: edit
   `tools/dabbler-ai-orchestration/src/wizard/WizardPanel.ts`
   (and any related step files) so the "Configure AI Router"
   step opens the new config editor instead of (or in addition
   to) writing `router-config.yaml` programmatically. Existing
   wizard tests continue to pass.
2. Test-notification button wiring: implement the "Send a test
   notification now" handler in
   `notificationsSection.ts`. Fire a single Pushover message
   using the configured env vars; surface the Pushover API
   response inline (success / failure with reason). Use
   `ai_router/notifications.py` as the existing canonical
   Pushover sender.
3. Update `docs/adoption-bootstrap.md`:
   - Point new operators at `Dabbler: Open Dabbler Config
     Editor` as the canonical setup surface.
   - Wizard remains as a guided alternative for first-time
     setup.
4. Update `docs/quick-start.md`:
   - Add a "Configuring your project" section pointing at the
     config editor.
5. End-to-end smoke test (manual):
   - Open the editor.
   - Edit one field in each of the six sections.
   - Save.
   - Run `python -m ai_router` (or the orchestrator's start
     hook) and confirm the new values are picked up.
   - Hand-edit `router-config.yaml` to break it.
   - Reopen the editor and confirm the validator surfaces the
     breakage.
   - Send a test Pushover notification; confirm receipt.
   - Run `dabbler.flagDecisionForReview` and confirm queue
     append.
   - Drop a `# @dabbler:outsource-review("test")` annotation in
     a Python file; run `dabbler.scanAnnotationsForActiveSet`;
     confirm queue append.
6. Update `tools/dabbler-ai-orchestration/CHANGELOG.md`
   `[0.13.15]` section to cover the full set: the config
   editor, the flag-decision command, the annotation parser,
   the wizard integration, the test-notification button. Cite
   Set 025 + Set 026 explicitly.
7. Update `CLAUDE.md`:
   - Current version line: `v0.13.15`.
   - Add a "Router-config editor" subsection under "Building &
     testing" pointing operators at the editor.
8. Cross-provider verification.
9. Commit + push.
10. Tag `vsix-v0.13.15` and push tags — triggers the existing
    tag-driven Marketplace deployment job (operator approves in
    GitHub Actions UI per
    `docs/planning/marketplace-release-process.md`).
11. ai_router PyPI release (manual or tag-driven, per existing
    flow): version `0.3.0`.

**Creates:** none (all new files created in prior sessions)

**Touches:**

- `tools/dabbler-ai-orchestration/src/wizard/WizardPanel.ts`
  (+ related)
- `tools/dabbler-ai-orchestration/src/configEditor/sections/notificationsSection.ts`
- `tools/dabbler-ai-orchestration/src/extension.ts` (any
  outstanding wiring)
- `docs/adoption-bootstrap.md`
- `docs/quick-start.md`
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md`

**Ends with:** Extension v0.13.15 + ai_router 0.3.0 shipped via
Marketplace + Open VSX + PyPI. End-to-end smoke test passes. Set
026 closes.

**Progress keys:** `session-006/wizard-integration`,
`session-006/test-notification-wiring`,
`session-006/adoption-doc-update`,
`session-006/quick-start-update`,
`session-006/changelog`,
`session-006/end-to-end-smoke`,
`session-006/verification`,
`session-006/release`.

**Release:** VS Code Marketplace
`DarndestDabbler.dabbler-ai-orchestration` v0.13.15 via
tag-driven workflow (`git tag vsix-v0.13.15 && git push --tags`;
approve `marketplace` deployment in GitHub Actions UI per
`docs/planning/marketplace-release-process.md`). PyPI:
`dabbler-ai-router` 0.3.0 via existing tag-driven flow.

---

## Risks

- **Largest implementation surface in the repo's history.**
  Mitigation: six-session split keeps each session bounded; the
  webview-foundation / webview-sections split (Sessions 3+4) is
  the explicit guard against conversation-budget overrun in the
  middle of UI work.
- **YAML round-trip fidelity.** The `yaml` npm library and
  Python's `ruamel.yaml` must both preserve comments, ordering,
  and formatting. Mitigation: Session 3's `yamlReadWrite.test.ts`
  asserts byte-identical round-trip on the actual
  `router-config.yaml` shipped in this repo. If either library
  fails the test, swap implementations (e.g., add explicit
  comment-preservation helpers) before proceeding to Session 4.
- **Migration script breaks an existing operator's
  `router-config.yaml`.** Mitigation: idempotent + comment-
  preserving; Session 2 runs the migration against this repo's
  actual file and commits the migrated result. Any unhappy edge
  case is caught before any external user encounters it.
- **`secretStorage` operator demand materializes mid-set.**
  Mitigation: the resolver abstraction (Session 2) makes adding
  a new backend a contained change. If demand surfaces during
  Set 026, defer to a follow-up set rather than expanding
  scope.
- **Reversing v0.13.14's "the CLIs stay" promise within ten days.**
  Mitigation: CHANGELOG `[0.13.15]` explicitly acknowledges the
  reversal and cites the operator's `marketplace-download-count`
  memory (3 downloads, all theirs) as the justification.
- **`outsource-last` consumer surfaces post-release.** Mitigation:
  v0.13.14 → v0.13.15 ships a CHANGELOG note flagging the
  removal. If a real external user surfaces and asks for
  outsource-last back, restore is git-revert-able from this set's
  Session 1 commit.

---

## Routing notes

Per-session orchestrator recommendation (also captured in this
set's `ai-assignment.md` once Session 1 starts):

- **Session 1** (deletion-only): Claude Opus 4.7 @ effort=low —
  mechanical; matches Set 024 profile.
- **Session 2** (Python schema + reader + migration + resolver):
  Claude Opus 4.7 @ effort=medium — risk is back-compat in
  reader behavior.
- **Session 3** (webview foundation): Claude Opus 4.7 @ effort=high
  — largest single-session surface in this set;
  YAML-round-trip-fidelity tests must pass before moving on.
- **Session 4** (webview sections): Claude Opus 4.7 @ effort=high
  — six section files + their tests. Implementing orchestrator
  may split 4a + 4b if the conversation budget gets tight.
- **Session 5** (significance flagging): Claude Opus 4.7 @
  effort=medium — bounded surface (one command + one parser).
- **Session 6** (wizard + release): Claude Opus 4.7 @
  effort=medium — coordination + release. No new surfaces;
  pulling together prior sessions' deliverables.

---

## Success criteria

After Set 026 closes:

1. The Dabbler AI Orchestration extension ships v0.13.15 with
   a working **Open Dabbler Config Editor** command that renders
   all six wireframed sections.
2. The `ai_router` package ships v0.3.0 with the new schema +
   resolver abstraction + migration script.
3. `outsourceMode` and all related infrastructure (~10 Python
   modules + `two-cli-workflow.md` + mode-aware branches) are
   gone from the repo. `git grep -i 'outsourcemode\|queue_db\|
   verifier daemon\|subscription cli'` returns zero hits.
4. `router-config.yaml` + `budget.yaml` carry the new schema;
   `ai_router/local-overrides.yaml` is gitignored and reading it
   works end-to-end.
5. Significance-flagging works via both the command and the
   `# @dabbler:outsource-review("...")` annotation.
6. The end-of-session cross-provider verification surface
   (Verification dropdown) writes to `budget.yaml`'s existing
   `verification_method` field; the routing dropdown writes to
   the new `routing.outsourcing_mode` field per Appendix B.
7. Sessions 023, 024, 025, 026 form a coherent narrative: 023
   (writer/reader alignment) → 024 (UI surface cleanup) → 025
   (next-feature spec informed by 024) → 026 (the
   implementation 025 spec'd).

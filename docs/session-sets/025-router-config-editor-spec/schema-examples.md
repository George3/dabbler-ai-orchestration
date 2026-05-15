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

## File 1b: `routing.outsourcing_mode` (new top-level field in router-config.yaml)

Session 2 adds a `routing.outsourcing_mode` field to
`router-config.yaml`. It's the canonical persistence target for
the webview's outsourcing dropdown (§1 of `wireframes.md`).

```yaml
# In router-config.yaml, alongside the existing routing: block:
routing:
  outsourcing_mode: whenever-helpful   # NEW: whenever-helpful | verification-only | disabled
  tier1_max_complexity: 30             # existing
  tier2_max_complexity: 65             # existing
  default_tier: 2                      # existing
  tier_assignments:                    # existing
    1: gemini-flash
    2: gemini-pro
    3: opus
  # ... rest unchanged ...
```

**Default:** `whenever-helpful` (matches today's de-facto behavior
where the router decides per-task).

**Enum values:**

- `whenever-helpful` — orchestrator may route mid-session tasks
  to APIs per the existing tier-assignment logic.
- `verification-only` — only `task_type: session-verification`
  calls hit APIs; all other routing is blocked.
- `disabled` — no API calls at all, including end-of-session
  verification. **Note:** when `disabled`, the webview greys out
  `verification_method: api` in the verification dropdown.
  Operators selecting `disabled` must also set
  `verification_method: manual-via-other-engine` or `skipped`.

**Local override:** allowed. An operator can set
`routing.outsourcing_mode: disabled` in `local-overrides.yaml`
to suppress all API calls on their machine without changing the
shared project default.

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
# Canonical values: "per-session-set" (default) | "per-project".
# The validator also accepts "per-session" for hand-edited files,
# but the webview dropdown does NOT offer it -- it's an
# expert-only option that bypasses the UI.
scope: per-session-set             # NEW canonical field

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
| `scope` | **renamed from `threshold_scope`**; **values constrained** | `per-session-set` | UI dropdown offers only `per-session-set` and `per-project`. Validator accepts `per-session` for hand-edited YAML (an expert-only escape hatch) but the webview does not surface it. |
| `warn_at_percent` | **NEW** | `80` | Percent of `threshold_usd` at which to switch from silent to heads-up. Operator-configurable in the webview slider. |
| `period` | **deferred + lossless** | n/a | Legacy `threshold_scope: monthly` migrates to `scope: per-project, period: monthly`. Period-based reset is not yet implemented in Set 026 — the `period:` field is preserved on disk so a future set can wire it without data loss. Reader emits a one-line deprecation warning per session. |

### Migration rules (binding)

The migration script's behavior on `threshold_scope` is normative
(see `spec.md` Appendix B for the canonical statement):

- `threshold_scope: project-lifetime` → `scope: per-project` (clean
  rename; no `period:` field added).
- `threshold_scope: monthly` → `scope: per-project, period: monthly`
  (preserve `period:` on disk; warn once). Cumulative-tracking
  semantics apply until a future set wires period reset.
- Both `threshold_scope` and `scope` present → `scope` wins; warn
  that `threshold_scope` should be removed.
- Unknown `scope` value → reject with a clear message naming the
  valid set.

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
# Schema = (subset of shared-config paths marked "local-override
# allowed" in spec.md Appendix B) + (explicit local-only sections
# below: notifications, decision_review). Every field is optional.
# Whatever is present overrides the same field in the canonical YAML
# at read time. Whatever is absent inherits from the canonical YAML.
#
# Precedence (canonical, from spec.md Appendix B):
#   local-overrides.yaml > router-config.yaml / budget.yaml > schema default
#
# Constraints:
#   - Only paths marked "Local-override allowed? Yes" in Appendix B
#     accept overrides. Hand-editing an override for a "No" path is
#     a validation error at load time.
#   - Providers and models can only OVERRIDE existing entries here;
#     adding a brand-new provider or model that has no shared
#     counterpart is a validation error.
#   - Unknown keys are warn-and-ignore; the webview's "Local overrides
#     summary" section lists them so the operator can decide.

# --- Provider overrides (allowed paths: enabled, api_key_env, base_url) ---
providers:
  google:
    api_key_env: MY_PERSONAL_GEMINI_KEY
  # other providers inherit from router-config.yaml unchanged

# --- Budget overrides (allowed paths: threshold_usd, warn_at_percent) ---
# Operators with personal cost-tracking can override threshold /
# warn_at_percent without affecting the project-committed values.
# `scope` and `verification_method` are NOT locally overridable
# (project-canonical per Appendix B).
# budget:
#   warn_at_percent: 50

# --- Routing override (allowed: outsourcing_mode) ---
# Disable all outsourcing on this machine without changing the
# shared project default.
# routing:
#   outsourcing_mode: disabled

# --- Notifications (local-only section; no shared analog) ---
notifications:
  pushover:
    enabled: true
    api_key_env: MY_PUSHOVER_API_KEY    # default: PUSHOVER_API_KEY
    user_key_env: MY_PUSHOVER_USER_KEY  # default: PUSHOVER_USER_KEY

# --- Decision-review queue (local-only section; no shared analog) ---
# Whether the orchestrator scans the active session-set's open files
# for `# @dabbler:outsource-review("...")` annotations. Default: true.
decision_review:
  honor_annotations: true

# --- Secret resolver backend selection (future-proofing, not in Set 026) ---
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
  effective value comes from `router-config.yaml` /
  `budget.yaml`, "(local override)" if it comes from
  `local-overrides.yaml`. Clicking the indicator opens a small
  popover offering "promote to shared" / "move to local override"
  toggles. Fields marked "Local-override allowed? No" in Appendix
  B do not show the indicator.
- **Validation:** the webview refuses to save a Pushover key
  *value* anywhere — only env-var *names* are stored, in
  `local-overrides.yaml`. The actual secret resolves from the
  operator's shell env at runtime. The webview also refuses
  loads where `local-overrides.yaml` declares an override for a
  path marked "Local-override allowed? No" in Appendix B; the
  offending entry is surfaced in the validation error banner.

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

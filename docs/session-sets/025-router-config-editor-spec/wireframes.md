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
- **YAML writes** (canonical per spec.md Appendix B):
  - Outsourcing dropdown → `router-config.yaml`
    `routing.outsourcing_mode`. Enum: `whenever-helpful` /
    `verification-only` / `disabled`. Local-overridable via
    `local-overrides.yaml` (a "(shared)" / "(local override)"
    indicator next to the dropdown shows which file is in effect).
  - Verification dropdown → `budget.yaml` `verification_method`.
    Enum mapping (UI label → YAML value):
    `"Automatic via API"` → `api`;
    `"Manual via portable markdown"` → `manual-via-other-engine`;
    `"None"` → `skipped`.
    Not locally overridable (project-canonical).

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
|                                                                         |
|                       (Per-session scope is hand-edit only; it is       |
|                        accepted by the validator but not offered        |
|                        in this dropdown. See schema-examples.md.)       |
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
|  [ Send a test notification now ]   (wired in Set 026 Session 5)        |
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

**On load (panel open):** the webview parses each YAML file, runs
the validator against the schema, and surfaces drift / unknown
keys / parse errors before letting the operator edit. A
failed-validation file opens in a read-only "drift detected" state
with a side panel showing the validator's complaints, so the
operator can fix the YAML by hand or accept the validator's
proposed normalization before switching to edit mode.

**On save (operator hits Save):**

1. The webview converts the current form state into the proposed
   YAML shape for each file.
2. The schema validator runs against the in-memory batch:
   - All required fields present.
   - All `provider:` references in `models:` resolve.
   - All `api_key_env` names look like valid env-var names
     (uppercase + underscores).
   - `threshold_usd >= 0`; `warn_at_percent` in `[0, 100]`.
   - `local-overrides.yaml` only overrides paths marked
     "Local-override allowed? Yes" in spec.md Appendix B.
   - No providers or models exist only in `local-overrides.yaml`.
3. If any validation fails, the webview surfaces inline errors
   (red border + tooltip on the offending field) and **does not
   write any file**. Partial saves are not allowed.
4. If validation passes, each file is written individually via
   `tmp write + rename` for **per-file atomicity**. **True
   cross-file atomicity is not provided** — a filesystem failure
   between the rename of file A and file B leaves a half-written
   batch on disk. The webview detects this on next load (by
   comparing mtime + content hash against the last successful
   save) and offers a best-effort recovery dialog: re-apply the
   un-written file from the cached batch, or accept the
   half-written state as the new baseline.
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

# Audit Inventory — `dabbler-ai-orchestration` complexity review

**Prepared for:** Set 020 Session 1 cross-provider review (2026-05-11)
**Purpose:** Structured input to two independent verifier prompts (GPT-5.4,
Gemini 2.5 Pro). This document describes *what exists* — no judgements about
what should be cut. Verifiers draw their own conclusions.

**Three active consumer repos:**

| Repo | Orchestration surface it uses |
|---|---|
| `dabbler-platform` | Full tier — ai_router, close-out machinery, DSL UAT (`requiresUAT: true`, `uatStyle: "dsl"`), worktree CLI, extension, Cost Dashboard, verifier daemon (`outsourceMode: last`) |
| `dabbler-access-harvester` | Full tier — ai_router, close-out machinery, all gates, no UAT (`requiresUAT: false`), worktree CLI, extension |
| `dabbler-homehealthcare-accessdb` | Lightweight tier (candidate) — Extension + `docs/session-sets/*/spec.md` only. No ai_router, no Python, no close-out script, no gates. Not yet migrated. |

**Repo philosophy (from `CLAUDE.md`):**
> Universal core, gated extensions, addendum specifics.
>
> Anything in the core must work unmodified when `requiresUAT: false` and
> `requiresE2E: false` are permanent defaults. UI/UAT/E2E-specific behavior
> must be gated on spec-level flags.

---

## Bucket A — Workflow document

**File:** `docs/ai-led-session-workflow.md`
**Line count:** 1,752 lines

**What it does:** The single source of truth for orchestrator behavior during a
session. Every AI agent reads its own instruction file (CLAUDE.md / AGENTS.md /
GEMINI.md), which points here for the full procedure and rules.

**Key sections:**
- **Steps 0–10** (10 numbered steps) — the per-session procedure: read guidance,
  register start, read spec, implement, build+test, verify (cross-provider), handle
  verification result, close out, reorganization review (last session only), stop.
- **Step 7: Handle Verification Result** — includes a 4-option human adjudication
  ladder (accept finding / accept dismissal / re-verify with reshaped context /
  second opinion from a different provider) plus an `record_adjudication()` API call
  requirement. Full sub-section on verifier-disagreement handling.
- **Step 8: Close Out** — names `disposition.json` as a deliverable; references
  `docs/disposition-schema.md`, `ai_router/docs/close-out.md` Section 1, and
  `ai_router/docs/two-cli-workflow.md`. Also contains worktree cleanup sub-section.
- **Step 9: Reorganization Proposals** — promotion/demotion logic for Lessons →
  Conventions → Principles. Mandatory review even when no changes are proposed.
- **Reading the Session Set Configuration** — explains how the orchestrator reads
  `requiresUAT`, `requiresE2E`, `uatStyle`, `uatScope` and gates behavior on them.
- **UAT Checklist Rule** — shared preamble + DSL-driven subsection (Playwright, `uat-coverage-review`) + Ad-hoc subsection (`ProgrammaticVerification` / `NoProgrammaticPathReason`). Added Set 019.
- **When UAT Is Required** — authoring-time heuristic mirrored here for orchestrator reference. Includes `### Choosing uatStyle` subsection added Set 019.
- **AI Router Details** — task types table (13 types), delegation discipline, routing code snippets.
- **Rules (1–16)** — the authoritative rules list, with sub-rules 11a/11b added Set 019.
- **Parallel session trigger phrases** — canonical trigger variants for sequential vs. parallel vs. maxout sessions.
- **Verifier fallback escalation ladder** — two-attempt fallback, escalation when both fail.
- **Delegation discipline** — criteria for which tasks must go through `route()` vs. be handled directly.
- **Cost-budgeted verification modes** — outsource-first vs. outsource-last, budget-tier mapping, adoption-tier disambiguation (added Set 018).
- **Appendix: spec template, session set config block, orchestrator instruction files, switching orchestrators between sessions.**

**Flags / modes this doc governs:**
- Session configuration: `requiresUAT`, `requiresE2E`, `uatStyle`, `uatScope`, `effort`, `outsourceMode`, `totalSessions` (7 spec flags)
- Trigger variants: sequential, parallel, maxout, parallel-maxout
- Outsource modes: `first` (synchronous API), `last` (queue-mediated daemon)
- Adjudication options: 4 options + `record_adjudication()` log entry

**Consumer fit:** All three consumer repos. Lightweight consumers read this doc
too (no per-Lightweight-consumer instruction file currently exists) — the Lightweight
path is mentioned at several points but not separated into a distinct track.

---

## Bucket B — Session-set authoring guide

**File:** `docs/planning/session-set-authoring-guide.md`
**Line count:** 489 lines

**What it does:** The spec-authoring reference for humans (and AI) writing new
session-set specs. Governs which flags to set, when UAT/E2E is required, how to
size a session, slug naming, deliverables checklist, anti-patterns, and the
config-block field semantics.

**Key sections:**
- **Session Set Configuration block** — YAML template + field-by-field semantics
  for all 4 UAT/E2E flags (`requiresUAT`, `requiresE2E`, `uatStyle` [added Set 019], `uatScope`).
  Includes defaults, the invalid-combination rule (`uatStyle: "dsl"` + `requiresE2E: false` rejected).
  Migration note for `dabbler-platform` (added Set 019).
- **When UAT is required** — triggers for `requiresUAT: true`. Includes `### Choosing uatStyle`
  subsection added Set 019.
- **When E2E is required** — triggers for `requiresE2E: true`.
- **Deliverables checklist** — what every spec must include; conditional items
  for UAT/E2E.
- **Spec template snippet** — copy-paste starting point.
- **Cross-set dependencies** — how to declare prerequisites; synthesis sets.
- **Anti-patterns** — 7 named anti-patterns (implicit UAT, too-broad sets, UAT
  deferred, re-using prior checklists, bypass-navigation E2E tests, etc.).
- **Repo-specific addendum** pointer — for UI/UAT/E2E repos, a separate `platform-addendum.md` is expected.

**Consumer fit:** Used by spec authors (human + AI). The Lightweight-tier addendum
mentioned in the spec template (`requiresUAT: false` + `requiresE2E: false` is the
default) means Lightweight consumers can ignore almost all of the UAT/E2E content.
The UAT/E2E sections are approximately 200 of the 489 lines.

---

## Bucket C — Adoption bootstrap

**File:** `docs/adoption-bootstrap.md`
**Line count:** 465 lines

**What it does:** The entry-point doc an AI uses when onboarding a new project. It
is the content of the clipboard prompt emitted by the extension's "Copy adoption
bootstrap prompt" command. A human pastes it into any AI chat; the AI follows the
9-step interactive flow to set up the project.

**Key steps:**
- Steps 1–4: detect state from VS Code context, handle missing workspace, state-B
  sub-paths (new project / local project / clone remote).
- **Step 4.5 (added Set 018):** Adoption tier choice — Lightweight (L: Explorer +
  spec files only, no ai_router, no budget, no close-out) vs. Full (F: everything).
  Includes coexistence sub-dialog (replace / parallel / index existing session protocol).
- Step 5 (Full only): Budget-threshold dialog — 4 tiers ($0/limited/middle/ample).
- **Step 6:** Plan alignment — 2–4 candidate session-set organizations using an
  abstract pattern catalog (7 named patterns). Added via Set 018's pattern catalog.
- Step 7: Build the action checklist — operator reviews / edits / batch-approves.
- Step 8: Execute. Exception: State B sub-path (3) clone happens earlier.
- Step 9: Closing pointers — branched for Lightweight (shorter) and Full (full).
- **Appendix:** The `CLAUDE.md` template a new project writes.

**Consumer fit:** New projects only (at onboarding time). Existing Full-tier
consumers have already run this and don't revisit. The Step 4.5 split and
pattern catalog add ~80 lines (added Set 018); the abstract pattern catalog
alone is ~30 lines.

---

## Bucket D — Close-out machinery

**Files:** `ai_router/close_session.py` (1,677 lines), `ai_router/gate_checks.py`
(630 lines), `ai_router/disposition.py` (391 lines), `ai_router/close_lock.py`,
`ai_router/close_out.py`
**Combined line count:** ~2,800 lines (excluding close_lock and close_out)

**What it does:** The sole synchronization barrier between session work and a
session being marked complete. Runs deterministic gate checks, waits on
verification (queue mode only), emits ledger events, flips session state.

**Gates (5 functions in gate_checks.py):**
1. `check_working_tree_clean` — no uncommitted changes in the session-set directory
2. `check_pushed_to_remote` — all commits pushed to remote
3. `check_activity_log_entry` — session has at least one entry in activity-log.json for the current session number
4. `check_next_orchestrator_present` — disposition.json's next_orchestrator field is valid when required (status=completed, not final session)
5. `check_change_log_fresh` — change-log.md was modified recently enough

**Invocation modes (5 distinct CLI modes):**
1. **Normal** — `python -m ai_router.close_session --session-set-dir <path>`
2. **Force** (`--force` + env var `AI_ROUTER_ALLOW_FORCE_CLOSE_OUT=1` + `--reason-file`) — bypasses all gates. Hard-scoped to incident recovery.
3. **Manual-verify** (`--manual-verify` + `--interactive` or `--reason-file`) — skips queue-verification wait; replaces with operator attestation.
4. **Repair** (`--repair`) — diagnostic: reports drift between session-state.json, session-events.jsonl, disposition.json. Four drift cases detected.
5. **Repair + apply** (`--repair --apply`) — corrective: applies fixes for Cases 1 and 2 (synthetic event append, state flip). Cases 3 and 4 are report-only.

**Two `disposition.json`-absent paths:**
- In `run_gate_checks()` (called by `mark_session_complete()`): synthetic `GateResult(check="disposition_present")` failure.
- In `run()` CLI flow: `invalid_invocation` result before the gate even runs.

**Queue-mode polling (outsource-last):** `_wait_for_verifications()` — polls
`provider-queues/<provider>/queue.db` at 5s intervals up to `--timeout` minutes
(default 60). Handles missing messages, per-message terminal state cache, and
partial-deadline synthetic `timed_out` outcomes.

**Lock:** `close_lock.py` implements a file-based concurrency lock around the
gate+event+flip flow.

**Consumer fit:** Full-tier consumers only. All three invocation modes beyond
"normal" (force, manual-verify, repair) are edge-case paths. The queue-mode
polling path (outsource-last) is used only by `dabbler-platform`; harvester uses
outsource-first.

---

## Bucket E — Session-state machinery

**Files:** `ai_router/session_state.py` (1,293 lines), `ai_router/session_events.py`,
`ai_router/backfill_session_state.py`, `ai_router/dump_session_state_schema.py`
**Combined line count:** ~1,600+ lines

**What it does:** Manages the per-session-set lifecycle snapshot
(`session-state.json`) and the append-only events ledger
(`session-events.jsonl`). The snapshot is the consumer-readable cache;
the ledger is the authoritative source.

**Key surfaces:**
- `register_session_start()` — creates/updates `session-state.json`, appends a
  `work_started` event idempotently.
- `mark_session_complete()` — runs gate checks via `close_session.run_gate_checks()`,
  flips the snapshot, has a `force=True` bypass with audit-trail event.
- `_flip_state_to_closed()` — internal gate-bypass helper called by `close_session.run()`
  on the success path and by `--repair --apply` on the case-2 path. Separate
  from `mark_session_complete()` to avoid re-running gates after close-out already
  succeeded.
- `NextOrchestrator` / `NextOrchestratorReason` dataclasses + `validate_next_orchestrator()`.
- `NEXT_ORCHESTRATOR_REASON_CODES` — 4 codes: `continue-current-trajectory`,
  `switch-due-to-blocker`, `switch-due-to-cost`, `other`.
- Schema v2 (v1 exists for backward compat via `backfill_session_state.py`).
- The session-events module defines `SessionLifecycleState` enum (WORK_IN_PROGRESS,
  WORK_VERIFIED, CLOSEOUT_PENDING, CLOSEOUT_BLOCKED, CLOSED) and `current_lifecycle_state()`
  which derives state from the events ledger.
- The `dump_session_state_schema.py` and `backfill_session_state.py` utilities
  were written for migrations during the v1→v2 schema transition.

**Consumer fit:** Full-tier consumers. The `NextOrchestrator` handoff recommendation
machinery runs every session (required when status=completed, not final session).
`backfill_session_state.py` and `dump_session_state_schema.py` are migration/debug
utilities with no ongoing runtime role.

---

## Bucket F — Router + task-type taxonomy

**Files:** `ai_router/__init__.py` (containing `route()`), `ai_router/router-config.yaml`
(587 lines), `ai_router/models.py`, `ai_router/providers.py`, `ai_router/prompting.py`,
`ai_router/cost_report.py`, `ai_router/metrics.py`, `ai_router/capacity.py`
**router-config.yaml line count:** 587 lines

**What it does:** Selects a model, calls the appropriate provider API, records
cost metrics, enforces the cross-provider verification rule, handles escalation
and fallback.

**13 task types** (from router-config.yaml task_type_scores + forced_model overrides):
`formatting`, `summarization`, `documentation`, `test-generation`, `code-review`,
`analysis`, `refactoring`, `uat-plan-generation`, `uat-coverage-review`,
`session-verification`, `security-review`, `architecture`, `planning`.
Plus `session-close-out` (internal) and `verification` (internal verifier path).

**Model stable:** gemini-flash (tier 1), gemini-pro (tier 2), sonnet (tier 2),
opus (tier 3), gpt-5-4 (tier 3), gpt-5-4-mini (tier 2).

**Explicit model forces (from `task_routing.forced_model`):**
- `code-review → sonnet` (rationale documented: Anthropic better at line-by-line)
- `architecture → opus` (rationale: 100% verifier rejection rate in early metrics at tier 2)
- `uat-plan-generation, uat-coverage-review → opus`
- `session-verification → gpt-5-4` (cross-provider pin for Claude orchestrators)
- `session-close-out → sonnet` (rationale: cheapest reliable CLI invocation model)

**Complexity estimation:** 4-weight heuristic (context_length 30%, keyword_signals
35%, task_type 20%, explicit_hint 15%) → 1-100 score → tier selection.

**Escalation:** automatic 1-step escalation if verifier rejects the first-choice
model's output.

**Adjudication support:** `record_adjudication()` writes to `router-metrics.jsonl`.
4 resolution codes. The distribution in metrics is intended to drive routing
parameter tuning.

**DELIBERATE NON-GOAL (comment in router-config.yaml L374):** "Do not invest
further engineering in tightening this [complexity] heuristic." The 2-try
escalation safety net is the intended stopping point.

**Consumer fit:** Full-tier only. Lightweight consumers have no ai_router. Among
Full-tier consumers: all three task types currently used in practice are
`session-verification`, `uat-plan-generation` (platform only), and `architecture`
(for design-review sets). The 13-type taxonomy was built for generality; routine
sessions use 3-4 types.

---

## Bucket G — Adoption × budget tier matrix

**Primary doc:** `docs/adoption-bootstrap.md` Steps 4.5 and 5; cross-referenced in
`docs/ai-led-session-workflow.md` §"Cost-budgeted verification modes"
**Secondary doc:** Per-consumer `budget.yaml` files

**What it does:** Defines two orthogonal dimensions consumers choose at bootstrap:

**Adoption tier (Step 4.5, added Set 018):**
- **Lightweight (L):** Explorer + spec.md files. No ai_router, no Python, no
  budget, no close-out, no cross-provider verification.
- **Full (F):** Everything — ai_router, close-out, verification, cost dashboard.

**Budget tier (Step 5, Full only):**
- **$0:** AI does only local deterministic work; all routing to paid API disabled.
- **Limited:** Small session budget (e.g., $5); verification routes allowed; no
  architecture/planning routes.
- **Middle:** Moderate budget; selective use of expensive task types.
- **Ample:** Uncapped; use best model for every task.

**Interaction rules:**
- Adoption × budget is a 2×4 matrix, but effectively 1×4 + 1 (Lightweight is
  always budget-zero by definition, so the matrix collapses to one Lightweight
  row + four Full rows).
- The workflow doc's "Cost-budgeted verification modes" section disambiguates
  that "adoption tier" and "budget tier" are different dimensions (added Set 018).

**Consumer fit:** Adoption tier is chosen once at bootstrap. Budget tier is
per-session-set and written to `ai_router/budget.yaml`. The disambiguation
paragraph in the workflow doc adds ~12 lines that all orchestrators see on every
Step 0 read, but it only matters on the boundary between the two dimensions.

---

## Bucket H — UAT/E2E gate stack

**Primary doc:** `docs/ai-led-session-workflow.md` §UAT Checklist Rule (preamble + DSL + Ad-hoc),
§When UAT Is Required, §Choosing uatStyle, §Rules 11a/11b
**Secondary doc:** `docs/planning/session-set-authoring-guide.md` §Choosing uatStyle
**Line count (workflow doc UAT sections):** ~200 lines (post-Set-019)

**What it does:** Governs the mechanical-verification floor the orchestrator
enforces before notifying the human that a session's UAT checklist is ready.

**Four spec flags governing this surface:**
- `requiresUAT: false | true` — gate-level opt-in; false means entire surface skipped
- `requiresE2E: false | true` — E2E coverage gate; only meaningful on the DSL path
- `uatStyle: "dsl" | "ad-hoc"` — which mechanical-verification floor applies (added Set 019)
- `uatScope: per-session | per-set | none` — when in the session lifecycle the checklist is compiled

**Two execution paths (added Set 019):**
- **DSL-driven (`uatStyle: "dsl"`):** Playwright coverage gate; requires `requiresE2E: true`; `uat-coverage-review` task route gates handoff. Used only by `dabbler-platform`.
- **Ad-hoc (`uatStyle: "ad-hoc"`, default):** Per-item `ProgrammaticVerification` or `NoProgrammaticPathReason` fields; local orchestrator validation only; no Playwright, no API route. Designed for non-web consumers.

**Invalid combinations explicitly rejected:**
- `uatStyle: "dsl"` + `requiresE2E: false` → rejected at Step 2.

**Mixed-surface rule:** Combined web/non-web sets must use `uatStyle: "ad-hoc"`.

**External dependency:** `uat-checklist-editor` (separate repo at
`darndestdabbler/uat-checklist-editor`) — the human-facing UI for running
checklists. Checklist JSON schema lives there.

**Consumer fit:** `dabbler-platform` uses the DSL path (`requiresUAT: true`,
`uatStyle: "dsl"`, `requiresE2E: true`). Harvester and healthcare-accessdb have
`requiresUAT: false` on all current sets. The ad-hoc path exists for potential
healthcare-accessdb use; no consumer has used it in production yet.

---

## Bucket I — Extension surfaces

**Directory:** `tools/dabbler-ai-orchestration/src/`
**Published version:** v0.13.3 (Marketplace: `darndestdabbler.dabbler-ai-orchestration`)

**What it does:** The VS Code extension that provides the Session Set Explorer
tree view, Cost Dashboard, and various CLI commands.

**Commands (8 files in `src/commands/`):**

| File | What it registers |
|---|---|
| `cancelLifecycleCommands.ts` | Commands to cancel a session set / session |
| `copyAdoptionBootstrapPrompt.ts` | "Copy adoption bootstrap prompt" — emits the clipboard prompt pointing at `docs/adoption-bootstrap.md` |
| `copyCommand.ts` | "Copy session trigger phrase" — copies the canonical trigger phrase for the active session |
| `gitScaffold.ts` | Scaffolds the git worktree + branch for a new session set |
| `installAiRouterCommands.ts` | "Install ai_router" — runs `pip install dabbler-ai-router` |
| `openFile.ts` | Opens a specific session artifact in the editor |
| `queueActions.ts` | Commands to interact with the provider queues (outsource-last) |
| `troubleshoot.ts` | Diagnostic command — collects session-set state for bug reports |

**Providers/tree views (4 files):**

| File | What it renders |
|---|---|
| `SessionSetsProvider.ts` | Main session-set tree view — reads `docs/session-sets/*/session-state.json`, shows status, lifecycle badges |
| `CostDashboard.ts` | Webview for cost report from `router-metrics.jsonl` |
| `ProviderHeartbeatsProvider.ts` | Tree view for outsource-last daemon heartbeats |
| `ProviderQueuesProvider.ts` | Tree view for outsource-last queue states |

**Wizard (`src/wizard/`):**
- `sessionGenPrompt.ts` — "Generate session set prompt" command: reads `docs/planning/project-plan.md`, builds a prompt, copies to clipboard. The PROMPT_SYSTEM template enumerates the config block fields including `uatStyle` (added Set 019).
- `copyAdoptionBootstrapPrompt.ts` is separate (it copies the pointer to `docs/adoption-bootstrap.md`; the wizard generates session specs).

**Consumer fit:** All consumers use the Session Set Explorer and the bootstrap
prompt command. The Cost Dashboard, ProviderHeartbeatsProvider, and
ProviderQueuesProvider are Full-tier-only (no metrics or queues in Lightweight).
The queue-related commands (`queueActions.ts`, `ProviderQueuesProvider.ts`,
`ProviderHeartbeatsProvider.ts`) are relevant only to `dabbler-platform` which
uses `outsourceMode: last`.

---

## Bucket J — Memory system

**Location:** `~/.claude/projects/<repo>/memory/` (operator-side, not in the repo)
**Current entries (this repo's project memory):** 15 files + MEMORY.md index

**What it does:** Persistent file-based memory that the AI reads at conversation
start to recall durable preferences, feedback, project state, and references
without the operator having to repeat them.

**Four memory types:**
- **user** — operator role, preferences, knowledge level (currently: Claude Code
  user, collaborative style preferences)
- **feedback** — corrections and confirmed approaches (currently 8 entries —
  e.g., "don't invoke ai-router mid-session," "dump RouteResult before access,"
  "batch-approve checklists before per-write prompts")
- **project** — ongoing project state (currently 7 entries — consumer repos,
  UAT DSL status, marketplace follow-ups, pluggable pipeline, etc.)
- **reference** — pointers to external resources (currently 0 entries in this repo)

**MEMORY.md index:** 15 entries, loaded into every conversation context. The
system prompt notes lines past 200 are truncated.

**Consumer fit:** This is the orchestrator's operator-side memory; it doesn't
directly affect consumer repos. The 15 entries are specific to this orchestration
repo's project. Consumer repos have their own memory dirs.

---

## Cross-bucket dependencies

Understanding *why* complexity exists in one bucket often traces back to another:

| Child (dependent) | Parent (dependency) | Why |
|---|---|---|
| close_session.py D | disposition.py D | The gate's `disposition_present` check exists because the close-out script needs a structured handoff. Adding fields to `Disposition` adds conditionals to the gate. |
| close_session.py D | session_state.py E | `mark_session_complete()` runs gate checks; `_flip_state_to_closed()` is a bypass-gate internal helper. The two modules are tightly coupled. |
| gate_checks.py D | activity-log.json format | `check_activity_log_entry` enforces a specific entries[] schema shape. Set 020 Session 1 itself was caught by this gate during initial close-out. |
| UAT Checklist Rule H | uat-checklist-editor (external) | The checklist JSON schema is owned by a separate repo. The per-item `ProgrammaticVerification` / `NoProgrammaticPathReason` fields added in Set 019 are forward-compatible additions not yet reflected in the editor. |
| Step 8 (workflow doc A) | disposition-schema.md | Step 8 names the schema doc as a deliverable. The schema doc is the fix (Set 019) for the gate's prior undiscoverability. |
| router-config.yaml F | task type taxonomy | 13 task types exist in the config; only 3-4 are used in routine sessions. The others are there for generality. |
| outsource-last path D/F | ProviderQueuesProvider I | The queue-mode daemon, the lock file, the `_wait_for_verifications()` polling, and the queue tree view are all dedicated to `dabbler-platform`'s `outsourceMode: last` workflow. |
| Adoption tier matrix G | workflow doc A | The "Cost-budgeted verification modes" section in the workflow doc contains the disambiguation paragraph between adoption tier and budget tier that all orchestrators read (even those where the distinction is irrelevant). |
| UAT gate stack H | authoring guide B | Every rule in the UAT Checklist Rule section of the workflow doc is mirrored / cross-referenced in the authoring guide. Two docs with related but non-identical coverage of the same gates. |

---

## Surface not covered by the audit (out of scope)

- **`ai_router/tests/`** — the test suite. Not in scope; its complexity tracks production code complexity.
- **`docs/planning/project-guidance.md` and `lessons-learned.md`** — living governance docs; not in scope for a complexity cut (their growth pattern is the subject of Step 9 reorganization reviews).
- **`docs/upstream-feedback/`** — hand-off artifacts to sibling repos; not in scope.
- **Per-consumer repos** (`dabbler-platform`, etc.) — not in scope; the audit is of this orchestration repo only.
- **GitHub Actions / CI** — this repo has none currently.

# Delegation Consensus Config Spec

> **Purpose:** ship V1 of `delegation.decision_consensus` — a config
> option that lets the orchestrator route in-session design /
> architecture / process decisions through cross-engine consensus
> before falling back to `AskUserQuestion`.
> **Created:** 2026-05-19
> **Session Set:** `docs/session-sets/031-delegation-consensus-config/`
> **Prerequisite:** [`docs/planning/delegation-consensus-config.md`](../../planning/delegation-consensus-config.md)
> design proposal (three-way approved by operator + GPT-5.4 + Gemini
> Pro on 2026-05-17). **Audit phase intentionally skipped** per memory
> `feedback_audit_then_spec_for_substantial_features` (design already
> cross-engine-vetted).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 2
requiresUAT: false
requiresE2E: false
```

> **Rationale:** the change is YAML schema + workflow doc + journal
> format + per-agent instruction-file pointers + PyPI release. Zero
> user-visible UI changes; no browser behavior. UAT and E2E gates do
> not apply.

---

## Project Overview

The Dabbler workflow already routes substantive reasoning through
`route(task_type=…)` and ends each session with mandatory cross-
provider verification. What it does NOT do is delegate in-session
design / architecture / process decisions to routed consensus before
falling back to `AskUserQuestion`. Set 030 ships the config knob that
lets a repo opt into that delegation.

Set 030 is the IMPLEMENTATION set for a design that was already
authored, cross-engine-vetted, and three-way-approved by the operator
on 2026-05-17 (per `docs/planning/delegation-consensus-config.md`).
The audit phase is skipped accordingly — the spec's open questions
are answered below by Claude's best-judgment synthesis per the
operator's standing
[[feedback_prefer_ai_consensus_over_human_prompt]] preference, with
the operator's review at session-set creation as the three-way-
agreement checkpoint.

### Operator-confirmable judgment calls (per design's "Open questions")

These are the three taste / scope calls the design doc flagged as
"won't try to AI-consensus away." Claude's recommended answers,
operator-editable at start_session time:

| # | Design open question | Recommended answer | Reasoning |
|---|---|---|---|
| Q1 | Where does the implementation session set live? | **This repo (`dabbler-ai-orchestration`)** | Schema lives here; PyPI release is from here; consumer repos pull via PyPI. The design proposal recommended this answer. |
| Q2 | Default `categories` list — broader (8 categories) or narrower? | **Start narrower: 4 mechanical categories** (`refactor-placement`, `file-layout`, `scoping`, `spec-clarification`) | These are the highest-convergence categories — placement questions where engines reliably agree. V1.5 expands to `testing-strategy` + `api-surface`; V2 adds `design` + `architecture` after observing convergence on the narrower set. Operator can broaden at any time by editing `router-config.yaml`. |
| Q3 | Journal git-tracked or gitignored? | **Committed**, follow `router-metrics.jsonl` precedent. Full-payload dir `consensus-decisions/` gitignored. | Consistent with existing journal precedent; preserves cross-conversation continuity for the audit summary while keeping disk-heavy per-call payloads local. |

---

## Feature 1: `delegation.decision_consensus` config sub-block

### Scope

Add a `decision_consensus` sub-block to the existing `delegation:`
block in [`ai_router/router-config.yaml`](../../../ai_router/router-config.yaml).
Schema:

```yaml
delegation:
  # Existing keys (unchanged):
  always_route_task_types: [ ... ]
  direct_work_max_lines: 50
  direct_work_max_files: 1

  # NEW sub-block (default: opt-out — backward compatible):
  decision_consensus:
    enabled: false
    engines:
      - openai:gpt-5-4
      - google:gemini-pro
    categories:
      - refactor-placement
      - file-layout
      - scoping
      - spec-clarification
    unresolved_action: ask_user      # ask_user | proceed_with_orchestrator_judgment
    journal_path: ai_router/consensus-decisions.jsonl
    journal_full_payloads_dir: ai_router/consensus-decisions  # null disables
```

### Standards

- Default `enabled: false` preserves backward compatibility (every
  existing repo's behavior is unchanged).
- `engines` is independent of `verification.preferred_pairings` — the
  two roles (verify vs. consult) may want different model pairings.
- Schema validation rejects invalid `engines` entries at load time
  (engines must reference real provider:model pairs from the
  configured `models:` table).
- Per-line journal shape matches `router-metrics.jsonl`'s precedent
  (append-only JSONL, one object per call, timestamp + cost-tracked).
- Full-payload dir uses one file per call: `<ISO timestamp>-<hash>.md`
  with prompt + per-engine responses + synthesized recommendation.

---

## Feature 2: Workflow documentation + per-agent instruction pointers

### Scope

[`docs/ai-led-session-workflow.md`](../../ai-led-session-workflow.md)
gains a new section ("Decision-time consensus") that documents:

- The decision tree (human-only → consensus-eligible → categories →
  consensus flow → synthesis → `unresolved_action`).
- Human-only category examples (business priority, taste calls,
  irreversible / high-blast-radius actions).
- Consensus-eligible category examples for each of the 4 V1
  categories.
- Journal format + opt-in path documentation.

[`CLAUDE.md`](../../../CLAUDE.md), [`AGENTS.md`](../../../AGENTS.md),
and [`GEMINI.md`](../../../GEMINI.md) each get a short identical
pointer to the new workflow section (per the
keep-agent-instruction-files-in-sync convention).

### Standards

- The workflow doc section follows the existing "Rules apply to all
  orchestrators" section's tone — declarative, example-driven.
- The pointer text in all three agent instruction files is
  byte-identical (deliberate convention).
- No changes to the existing AskUserQuestion behavior — the new
  section is purely additive (gated on the config knob being on).

---

## Feature 3: PyPI release + cross-repo notification

### Scope

- Bump `dabbler-ai-router` PyPI version: **0.4.0 → 0.5.0** (minor
  bump for new schema feature).
- Update [`CHANGELOG.md`](../../../CHANGELOG.md) (repo-root, the
  ai_router CHANGELOG) with the new schema + journal format note.
- Drop one-liner pointers in consumer repos' CLAUDE.md files
  pointing at the new workflow section (per S6 deferral —
  delegation-consensus is the first cross-repo workflow change since
  v0.14.2). Consumer repos: `dabbler-access-harvester`,
  `dabbler-platform`, `dabbler-homehealthcare-accessdb`.

### Standards

- PyPI release goes through the existing `python -m build && twine
  upload` flow (or the repo's documented release script).
- Cross-repo pointers are MANUAL writes to each consumer's CLAUDE.md
  — no automation; the orchestrator opens each repo's file and adds
  the line.

---

## Session 1 of 2: Schema acceptance + journal format + workflow doc

**Goal:** ship the schema, validation, journal helpers, and the
workflow doc section. Everything that lives in this repo's source
tree.

**Steps:**

1. **Confirm three open questions** at session start via
   `AskUserQuestion` (showing Claude's recommended answers + the
   "use your best judgment" alternative). Operator either confirms
   the recommendations or supplies alternatives. Result is recorded
   in `ai-assignment.md` so subsequent steps reference the
   authoritative choices.
2. **Schema additions** to `ai_router/router-config.yaml` —
   add the `decision_consensus` sub-block with default values
   matching the operator-confirmed answers from step 1. Keep the
   existing `delegation:` block fields unchanged.
3. **Schema validation in the Python loader.** The `ai_router`
   config loader currently parses `delegation:` — extend it to
   accept the new sub-block. Validate:
   - `engines` references exist in the `models:` table.
   - `categories` are one of the recognized slugs (the V1 list
     from step 1).
   - `unresolved_action` is one of `ask_user` /
     `proceed_with_orchestrator_judgment`.
   - `journal_path` is a writable path (or null).
   - `journal_full_payloads_dir` is a writable directory path (or
     null).
4. **JSON schema mirror.** Update the AJV-based config-editor
   schema in `tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts`
   so the visual config editor accepts the new sub-block too.
5. **Journal writer helper.** Add a small helper to ai_router
   (e.g., `ai_router/consensus_journal.py`) that writes one
   per-line JSON record matching the design's shape. Used by the
   orchestrator after each consensus call. Includes:
   - Atomic append (write to temp, rename).
   - Per-call hash computation (`sha256:` prefix on the
     question + category + timestamp tuple).
   - Optional full-payload sibling file write.
6. **Unit tests.** Cover schema acceptance, validation
   rejections, and journal-writer atomicity. Target ~15 tests; <300 LOC.
7. **Workflow doc section** in `docs/ai-led-session-workflow.md`
   — new "Decision-time consensus" section after the existing
   "Cross-provider verification" section. Include the decision
   tree, human-only examples, consensus-eligible examples, journal
   format snippet, and opt-in path.
8. **End-of-session verification** (gemini-pro per recent
   pattern). Schema + journal helper + workflow doc are the bundle.

**Creates:**
- `ai_router/consensus_journal.py`
- `ai_router/tests/test_consensus_journal.py`
- `ai_router/tests/test_decision_consensus_schema.py`

**Touches:**
- `ai_router/router-config.yaml` (delegation block extended)
- `ai_router/__init__.py` (config loader extension)
- `tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts`
- `docs/ai-led-session-workflow.md` (new section)
- `docs/session-sets/031-delegation-consensus-config/ai-assignment.md`

**Ends with:** Schema accepted; journal helper landed; workflow doc
section published. Existing repos with no `decision_consensus`
block configured continue working unchanged (default opt-out).

**Progress keys:** `session-001/three-open-questions-confirmed`,
`session-001/schema-extended`, `session-001/validation-landed`,
`session-001/journal-helper-landed`, `session-001/workflow-doc-updated`,
`session-001/round-a-verification`

**Estimated cost:** $0.05–$0.15 (single Round-A verification, no
audit-cycle spend).

---

## Session 2 of 2: Per-agent pointers + PyPI release + cross-repo notification + close-out

**Goal:** finalize the cross-cutting wiring + ship the PyPI release.

**Steps:**

1. **Per-agent instruction-file pointers.** Add identical pointer
   line to [`CLAUDE.md`](../../../CLAUDE.md),
   [`AGENTS.md`](../../../AGENTS.md), and
   [`GEMINI.md`](../../../GEMINI.md) referencing the new workflow
   section. Per the keep-in-sync convention.
2. **CHANGELOG.md** (repo-root ai_router changelog) entry for
   0.5.0 noting the new schema feature + journal format + opt-in
   default.
3. **`pyproject.toml` version bump** 0.4.0 → 0.5.0.
4. **PyPI release.** `python -m build && twine upload dist/*` (or
   the repo's documented release script). Operator-gated.
5. **Cross-repo notification one-liners** in consumer repos'
   CLAUDE.md (`dabbler-access-harvester`, `dabbler-platform`,
   `dabbler-homehealthcare-accessdb`) pointing at the new workflow
   section. Operator opens each consumer repo briefly to add the
   line.
6. **`.gitignore` update** — add `ai_router/consensus-decisions/`
   (full-payload dir) per Q3 answer.
7. **End-of-session verification** (gemini-pro).
8. **Generate change-log.md** (final-session pattern) +
   `close_session` invocation.

**Creates:** none (final-session aggregation only).

**Touches:**
- `CLAUDE.md` (one-line pointer)
- `AGENTS.md` (identical one-line pointer)
- `GEMINI.md` (identical one-line pointer)
- `CHANGELOG.md` (ai_router 0.5.0 entry)
- `pyproject.toml` (version bump)
- `.gitignore` (add consensus-decisions/ payload dir)
- Consumer repos' CLAUDE.md (3 files outside this repo)
- `docs/session-sets/031-delegation-consensus-config/change-log.md` (NEW final-session aggregation)
- `docs/session-sets/031-delegation-consensus-config/ai-assignment.md` (S2 entry)

**Ends with:** dabbler-ai-router 0.5.0 on PyPI; all four
instruction files (this repo's three + the consumer repos' one
each) point at the new workflow section; Set 030 is `complete` /
`closed`.

**Progress keys:** `session-002/agent-pointers-added`,
`session-002/changelog-entry-added`, `session-002/version-bumped`,
`session-002/pypi-released`, `session-002/cross-repo-pointers-added`,
`session-002/gitignore-updated`, `session-002/round-a-verification`,
`session-002/change-log-generated`, `session-002/close-session-succeeded`

**Estimated cost:** $0.02–$0.10 (single Round-A verification, no
audit-cycle spend; smaller diff than S1).

---

## Risks

- **R1 — Schema-validation strictness vs. forward compatibility.**
  If we reject `decision_consensus` blocks with unknown fields at
  load time, future V1.5 additions (e.g., `agreement_level`
  heuristic config) break older readers. Mitigation: validation
  rejects only known-bad fields (e.g., invalid engine strings, bad
  enum values for `unresolved_action`). Unknown sub-keys are
  IGNORED with a one-time warning per load, mirroring the existing
  config loader's behavior for forward-compat.
- **R2 — Journal disk growth.** A repo with consensus-decisions
  on for months accumulates thousands of journal lines. Mitigation:
  the journal is JSONL append-only; `router-metrics.jsonl`
  precedent shows this is acceptable (currently in this repo at
  many thousands of lines with no friction). Full-payload dir is
  the disk-heavy one; default-on but explicitly opt-outable.
- **R3 — Cross-repo notification drift.** Three consumer repos
  each get a one-liner. If we drift between them (one points at
  the wrong section, another has the wrong wording), the
  keep-in-sync convention is violated. Mitigation: operator opens
  each consumer repo serially in Session 2 step 5; same line
  copy-pasted to each; verify byte-identical via grep at session
  close.
- **R4 — PyPI release rollback complexity.** PyPI doesn't allow
  re-uploading the same version. If 0.5.0 ships with a bug,
  rollback means 0.5.1. Mitigation: Session 1's tests cover the
  schema + journal helper; Round-A verification covers the
  cross-cutting workflow. Operator-gated publish (Session 2 step
  4) ensures the operator sees the final shape before going live.
- **R5 — Engines list staleness.** If `gpt-5-4` is deprecated /
  retired before this set ships, the default `engines` value
  breaks every fresh enablement. Mitigation: the default is in
  YAML, easy to update. Pre-release sanity-check that the default
  engines are reachable via `query()` from a clean state.

---

## Routing notes

- **No audit phase.** The design was three-way approved
  2026-05-17; the audit-then-spec pattern's audit cycle is
  intentionally skipped here per memory
  `feedback_audit_then_spec_for_substantial_features`'s carve-out
  ("operator wants three-way agreement before non-trivial work
  begins" — three-way agreement is already on disk).
- **Session-end verification (S1, S2):**
  `task_type='session-verification'`, single verifier (gemini-pro
  per recent pattern) via `ai_router.query(...)`. Estimated
  $0.02–$0.10 per round. Two rounds budgeted (Round-A in each
  session); Round-B only if Round-A flags must-fix items.
- **Implementation work (S1, S2):** pure Claude tokens, no router
  invocation. The new consensus behavior the set is shipping is
  itself a future capability — Set 030 cannot dogfood the
  consensus call on its own implementation (the config knob
  doesn't exist yet inside this set).

---

## Total estimated cost (pre-spend forecast)

- Session 1: $0.05–$0.15 (single Round-A verification).
- Session 2: $0.02–$0.10 (single Round-A verification; smaller
  diff).
- **Total Set 030 forecast: $0.07–$0.25.**

For context: Set 029's total spend was ~$1.70 across 6 sessions
with an audit cycle, mid-set audit, and consensus calls. Set 030
is implementation-only and benefits from the pre-shipped design —
forecast is intentionally lean.

---

## What ships at the end

- `dabbler-ai-router` 0.5.0 on PyPI with `decision_consensus`
  schema accepted, validated, and documented.
- `docs/ai-led-session-workflow.md` has the new "Decision-time
  consensus" section.
- Per-agent instruction files (CLAUDE.md / AGENTS.md / GEMINI.md)
  point at the new workflow section.
- Three consumer repos' CLAUDE.md files point at the new workflow
  section.
- `ai_router/consensus_journal.py` ships the per-line JSON writer
  + optional full-payload writer.
- Operators of consumer repos can enable the behavior at any time
  by adding the `decision_consensus` block to their own
  `router-config.yaml` with `enabled: true`. The default opt-out
  preserves every existing repo's behavior unchanged.

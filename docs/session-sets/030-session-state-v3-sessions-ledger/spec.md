# Session-state v3 `sessions` ledger + terminology alignment

> **Purpose:** Replace the fragile `currentSession` / `totalSessions` /
> `completedSessions` triple with a single canonical `sessions[]`
> array (schema v3). Phased migration preserves backward compatibility
> through Phase 3, then drops legacy field writes. Aligns terminology
> across the JSON schema and the Session Set Explorer display
> ("Complete" everywhere, retiring "Done"). Ships a regex-first /
> AI-fallback migration UX for existing session-set state files
> across this repo and three consumer repos.
>
> **Session Set:** `docs/session-sets/030-session-state-v3-sessions-ledger/`
> **Created:** 2026-05-17
> **Workflow:** Full
> **Prerequisite:** Proposal at
> `docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`
> (authored by/with GPT-5.4, reviewed and strong-approved by Gemini Pro).

---

## Session Set Configuration

```yaml
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
totalSessions: 5
```

> **`effort: high`** — schema migration touching Python writers,
> TypeScript readers, all existing state files, documentation, and
> three consumer repos. High coordination risk; high cost if a
> writer-side bug ships and corrupts state.
>
> **`requiresE2E: true`** — Layer 1 (pytest) covers Python writers;
> Layer 3 (Playwright) covers the Explorer's count-derivation and the
> new "Setting up your project…" loading state. Both are essential to
> guard the count-display invariants ctelr-spec drift exposed.

---

## Problem statement

`session-state.json` v2 carries three progress fields that must
remain consistent:

- `currentSession` — ambiguous: sometimes "in flight", sometimes
  "most recently closed"
- `totalSessions` — planned count
- `completedSessions[]` — canonical "X done out of N" ledger

The intended invariant is documented (the schema doc's "State
invariant" section) but the *shape* is fragile because the three
fields drift independently. Real failure modes we've hit:

1. **ctelr-spec N-1/N display drift (2026-05-12).** Hand-written
   state file with `status: "completed"` instead of `"complete"`
   displayed as N-1/N until the count-derivation logic was made
   canonical in extension v0.13.10.
2. **Fresh-set `completedSessions` schema gap (Set 028 S1).**
   `register_session_start` omitted the key on fresh sets,
   creating inconsistency Lightweight-tier orchestrators had to
   work around. Fixed in v0.3.2 by always emitting `[]`.
3. **Mixed-mode drift between hand-edits and writer emits.**
   Operator hand-edits a state file with an old shape; writer
   later re-emits in a slightly different shape; readers diverge.

The root cause across all three is **multiple independent fields
representing the same underlying concept**: "what session is in
flight; what's done; what's planned." Schema v3 collapses these
to a single canonical ledger and derives the summary fields from
it.

---

## Goal state

When this set ships:

1. **`session-state.json` schema v3** is canonical. New sets are
   created with `sessions[]` directly; legacy fields are gone from
   new writes. Tolerant read support for v2 files persists
   indefinitely.
2. **Single normalized progress helper** (`get_progress()`)
   exists in both Python (`ai_router`) and TypeScript (extension)
   and is the *only* path readers use. No direct reads of
   `currentSession` / `totalSessions` / `completedSessions`
   anywhere in either codebase.
3. **Terminology aligned on "Complete"** across JSON schema and
   Explorer display. The Explorer's old "Done" label is migrated.
4. **All existing state files** in this repo (28+ sets) and
   consumer repos (dabbler-platform, dabbler-access-harvester,
   dabbler-homehealthcare-accessdb) are migrated to v3 — either
   bulk-migrated by Session 4's one-shot migrator, or
   lazy-migrated by the extension's activation-time scanner from
   Session 5.
5. **Writer-side rule enforcement** — both `register_session_start`
   and `close_session` fail loud on rule violations (e.g., two
   sessions in-progress simultaneously, "done" session preceding
   a "not-started" session). No silent recovery; explicit repair
   tooling only.
6. **Explorer activation UX** shows "Setting up your project…"
   with the Dabbler icon during async scan (replacing the
   flash-of-welcome-CTA the operator currently sees).

---

## Decisions locked from operator dialogue + GPT-5.4 proposal + Gemini Pro review

| # | Decision | Locked value |
|---|---|---|
| D1 | Schema shape | **Array of structured records.** `sessions[].{number, title, status}`. Numbers are positive ints, unique, sorted ascending. Titles copied from spec.md headings for display; title drift is cosmetic (per Gemini's locked clarification). |
| D2 | Status terminology | **`"complete"` at BOTH session and set level.** Unified mental model. Session-level statuses: `"not-started"`, `"in-progress"`, `"complete"`, `"cancelled"`. Top-level statuses match. The proposal's `"done"` is mapped to `"complete"` everywhere. **Per GPT-5.4 revision (2026-05-17): the proposal doc `docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md` MUST be updated to use `"complete"` instead of `"done"` before Session 1 begins, so the proposal and spec align as a single source of truth.** |
| D3 | Explorer display labels | **Migrate Explorer's "Done" label to "Complete".** Old "Not Started", "In Progress", "Done" become "Not Started", "In Progress", "Complete". Eliminates the JSON-vs-display word split. |
| D4 | Phased migration | **5 phases over 5 sessions** (per GPT-5.4 revision 2026-05-17): docs/helpers (P1), dual-write writers (P2), reader migration (P3), bulk migrator + in-repo migration + consumer dry-run docs / **no publish** (P4), migration UX + loading state + **final publish** (P5). Final publish is gated on the migration UX being in place — operators upgrading the extension must see the v2-detection CTA, not a broken state file. |
| D5 | Backward compat | **Dual-write is the operational steady state for this set** (per GPT-5.4 revision 2026-05-17). Writers emit BOTH v3 `sessions[]` and the legacy fields (derived from `sessions[]`) starting in Session 2; this set does NOT drop legacy emission. A future set may flip "stop writing legacy" once v3 readers are confirmed across all three consumer repos. Tolerant v2 read support is permanent. |
| D6 | Writer rule enforcement | **Fail loud, never silently recover.** Both `register_session_start` and `close_session` raise actionable errors on rule violations. Recovery lives in explicit repair tooling (`close_session --repair`, future `migrate_session_state`). Per Gemini's review. |
| D7 | Title extraction (Session 5) | **Regex-first, AI-fallback.** Default path: regex `### Session K of N: <title>` from spec.md headings — deterministic, zero router cost. Fallback: when headings are malformed/missing, route through `ai_router` with `task_type='spec-title-extraction'`. Operator confirms before any AI cost. |
| D8 | Detection trigger | **On extension activation (tree provider scan).** When the Explorer loads, the tree provider scans for v2 state files and surfaces a one-time "migrate?" CTA per set. Most discoverable for the operator. |
| D9 | Loading-state UX | **Replace the welcome-CTA flash with a "Setting up your project…" loading state** during the activation-time scan. Tree provider returns a loading sentinel TreeItem with the Dabbler icon + progress text. The welcome viewsWelcome content shows only after the scan completes AND the workspace genuinely has no session sets. |
| D10 | Lightweight tier UX | **Hand-editing `sessions[]` must be ergonomic.** Schema doc ships with worked examples for the Lightweight tier showing exactly which field flips on each transition (start a session: change `"not-started"` → `"in-progress"`; close a session: change `"in-progress"` → `"complete"`). One field change per transition. |
| D11 | Per-session metadata | **Defer** (per proposal §"Open questions"). `startedAt`, `completedAt`, `verificationVerdict`, `orchestrator` stay top-level. A future schema bump can add per-session history when a real need emerges. |
| D12 | Skipped sessions | **Not supported in v3** (per proposal §"Open questions"). If a planned session is removed, edit spec.md and reconcile `sessions[]` via repair tooling. Strict sequential invariant. |
| D13 | "No legacy reads" rule scope | **"No application reader may read legacy fields except through approved compatibility helpers"** (per GPT-5.4 revision 2026-05-17). The rule applies to *application* code (close-out gates, the extension tree provider, repair logic, the reconciler). It explicitly does NOT apply to `progress.py` / `progress.ts` (the helpers themselves), the migrator, tests, or any other compat path. Session 3's lint rule encodes this carve-out. |
| D14 | Final publish gate | **Marketplace + PyPI publish moves from Session 4 to Session 5** (per GPT-5.4 revision 2026-05-17). Operators upgrading the extension before the migration UX exists would see broken or confusing state on v2 files; publishing only after S5 ensures the UX is in place to handle them. Session 4 ships a release-candidate build (`v0.14.0-rc.1`) for internal smoke; S5 ships the GA release. |
| D15 | Set 029 ordering | **Both orders supported** (per GPT-5.4 revision 2026-05-17). If Set 029 runs before Set 030 Session 4, its state file is born v2 and gets caught by the bulk migrator. If Set 030 runs first, Set 029's state file is born v3 from scaffolding. No ordering dependency. |
| D16 | Lightweight ergonomics validation | **Dry-run bulk migrator against a representative dabbler-homehealthcare-accessdb state file before Session 5's final publish** (per GPT-5.4 revision 2026-05-17). Per memory `project_consumer_repos`, accessdb is the Lightweight-tier candidate; the hand-editing UX must be validated against a real state file before consumers see v3 in a published release. |

---

## Invariants (from proposal, locked)

Writers and readers enforce these eight rules; violations are
fail-loud errors, never silent recovery:

1. `sessions` is required and non-empty for any set with a known plan.
2. `sessions[].number` values are positive integers, unique, sorted
   ascending.
3. At most one session may have `status: "in-progress"`.
4. A session may not be `"complete"` if an earlier session is
   `"not-started"` or `"in-progress"`. (Maps to proposal rule 4.)
5. Top-level `status: "not-started"` requires every session to be
   `"not-started"`.
6. Top-level `status: "in-progress"` allows either exactly one
   in-progress session or a between-sessions state (≥1 complete,
   ≥1 not-started, no in-progress).
7. Top-level `status: "complete"` requires every session to be
   `"complete"`.
8. `lifecycleState: "closed"` pairs with top-level
   `status: "complete"` or `"cancelled"` only.

---

## Derived values

Single helper, returned from `get_progress()` (Python + TypeScript
parity):

```text
totalSessions = sessions.length
completedSessions = sessions where status == "complete", mapped to number
currentSession = the single session where status == "in-progress", else null
nextSession = first session where status == "not-started", else null
isBetweenSessions = currentSession is null AND completedSessions is non-empty AND nextSession is not null
```

Readers MUST use this helper. Direct field reads of
`currentSession` / `totalSessions` / `completedSessions` are
forbidden in code touched by this set (lint rule in Session 3).

---

## Sessions

### Session 1 of 5: Schema doc + `get_progress()` helper + v2-read synthesizer

**Goal:** Establish the canonical v3 schema in documentation and ship
read-side compatibility. No writer changes yet; no behavior change
visible to the operator. After this session, every reader CAN
consume v3 (and v2, transparently) but no v3 files exist yet.

**Steps:**

1. **Rewrite `docs/session-state-schema.md`** for v3. Sections:
   schema shape, derived values, 8 invariants, status-value glossary
   ("complete" unified — explicitly retire references to "done" and
   "completed"), Lightweight-tier worked example (one-field-flip per
   transition), migration notes, reader contract (must use
   `get_progress()`).
2. **Rewrite `docs/session-state-schema-example.json`** as a v3
   example. Update `docs/session-state-schema-example.md` with
   side-by-side v2 vs v3 narrative.
3. **Python `get_progress()` helper.** New module
   `ai_router/progress.py` with:
   - `get_progress(state: dict) -> ProgressView` dataclass
   - `synthesize_v3_from_v2(state: dict, spec_md_path: Path) -> dict`
     for read-time v2 normalization
   - Validators enforcing the 8 invariants
4. **TypeScript `get_progress()` helper.** New module
   `tools/dabbler-ai-orchestration/src/utils/progress.ts` mirroring
   the Python helper. Single source of truth on shape; mirrors via
   shared interface declaration.
5. **Unit tests (Python + TS).**
   - v3 happy path: fresh, in-flight, between-sessions, complete,
     cancelled
   - v2 read synthesis: each of the v2 shapes from existing repo
     fixtures
   - Invariant violations: each rule produces an actionable error
   - Edge cases: empty `sessions[]`, duplicate numbers, non-sorted
     numbers, "complete" before "in-progress", multiple in-progress
6. **Update the proposal doc** (`docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`)
   so it uses `"complete"` instead of `"done"` at session level. Adds
   a "Revisions" footer noting the 2026-05-17 GPT-5.4 follow-up
   recommendations and the operator's terminology lock. This keeps
   the proposal aligned with the spec as the single source of truth
   (per D2 / GPT-5.4 revision).
7. **Register `spec-title-extraction` task type in router config**
   (per D14 / GPT-5.4 revision). Add the task type to
   `ai_router/router-config.yaml` with sensible defaults
   (provider/model selection that suits short structured-JSON
   extraction tasks), plus a unit test asserting the route resolves.
   Session 5 depends on this being available; landing it early
   removes a dependency risk.

**Creates:**
- `ai_router/progress.py`
- `ai_router/tests/test_progress.py`
- `tools/dabbler-ai-orchestration/src/utils/progress.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/progress.test.ts`

**Touches:**
- `docs/session-state-schema.md` (full rewrite for v3)
- `docs/session-state-schema-example.md`
- `docs/session-state-schema-example.json`
- `docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`
  ("done" → "complete" alignment; Revisions footer)
- `ai_router/router-config.yaml` (register `spec-title-extraction`
  task type)
- `tools/dabbler-ai-orchestration/src/types.ts` (add `ProgressView`,
  `SessionRecord`, `SessionStatus` interfaces)

**Ends with:** Both helpers shipped with full test coverage.
Proposal doc aligned with spec. `spec-title-extraction` task type
registered and tested. No visible behavior change; existing v2 files
still drive the Explorer + close-out as before.

**Progress keys:** `session-001/schema-doc-rewritten`,
`session-001/python-helper-shipped`, `session-001/ts-helper-shipped`,
`session-001/v2-synthesizer-tested`, `session-001/proposal-doc-aligned`,
`session-001/spec-title-extraction-registered`

**Estimated cost:** $0.10 – $0.30 (one verification call).

---

### Session 2 of 5: Phase 2 dual-write writers + scaffolding

**Goal:** Update Full-tier writers to emit BOTH the canonical v3
`sessions[]` array AND the legacy `currentSession` / `totalSessions`
/ `completedSessions` fields. Legacy fields are generated from
`sessions[]`, never independently maintained. Scaffolding writes v3
from the start. Writer-side rule enforcement (fail loud).

**Steps:**

1. **Update `register_session_start(N)`** in `ai_router/session_state.py`:
   - Ensure `sessions[]` exists, backfilling from spec.md if needed
     (use the Session 1 synthesizer)
   - Validate no other session is `"in-progress"` — fail loud if so
   - Set session N to `"in-progress"`
   - Emit BOTH `sessions[]` and the derived legacy fields
   - Top-level `status: "in-progress"`, `lifecycleState: "work_in_progress"`
2. **Update `close_session.py` / `mark_session_complete`:**
   - Validate session N is `"in-progress"` or already `"complete"`
     (idempotent retry case)
   - Set session N to `"complete"`
   - If all sessions are `"complete"` AND `change-log.md` is present:
     top-level `status: "complete"`, `lifecycleState: "closed"`
   - Otherwise: between-sessions state (top-level still
     `"in-progress"` with `"work_in_progress"` lifecycle)
3. **Update scaffolding** (wherever a new set's `session-state.json`
   is first written): write v3 `sessions[]` directly from spec.md.
   Legacy fields still emitted from derivation.
4. **Writer-side invariant enforcement.** Both writers raise
   `SessionStateInvariantError` (new exception class) with
   actionable messages when an invariant is violated. No
   force-close, no silent recovery.
5. **pytest coverage:**
   - Each writer produces a state file passing all v3 invariants
   - Each writer rejects each invariant-violating input
   - Dual-write parity: legacy fields always agree with `sessions[]`
   - Backfill-from-spec.md happens once and is idempotent

**Creates:**
- `ai_router/tests/test_session_state_v3.py` (new test module)

**Touches:**
- `ai_router/session_state.py`
- `ai_router/close_session.py`
- `ai_router/start_session.py`
- `ai_router/exceptions.py` (add `SessionStateInvariantError`)
- Scaffolding entry points (audit codebase for sites that write
  initial state — likely a helper in `session_state.py` already)

**Ends with:** All Full-tier-written state files dual-format
(v3 + legacy). Hand-written and Lightweight-tier files unchanged
(still v2). Readers still rely on legacy fields — that migration
is Session 3.

**Progress keys:** `session-002/register-start-emits-v3`,
`session-002/close-session-emits-v3`, `session-002/scaffold-writes-v3`,
`session-002/invariants-enforced-fail-loud`, `session-002/dual-write-parity-tested`

**Estimated cost:** $0.10 – $0.30.

---

### Session 3 of 5: Phase 3 reader migration + Explorer "Done" → "Complete"

**Goal:** All readers move to `get_progress()`. No direct reads of
legacy fields anywhere in `ai_router` (close-out gates, repair, the
reconciler) or the VS Code extension (tree provider, count
derivation, status badges). Explorer display labels migrated from
"Done" to "Complete" wherever the operator sees them.

**Steps:**

1. **Audit + grep for direct legacy-field reads.** `grep -rn
   'currentSession\|totalSessions\|completedSessions' ai_router/
   tools/dabbler-ai-orchestration/src/`. Every hit is either a
   reader (replace with `get_progress()`) or a writer (already
   handled in Session 2).
2. **Migrate `ai_router` readers:**
   - `close_session` gate predicates (`check_change_log_fresh`,
     `check_baton_present`, etc. — anywhere that reads progress
     state)
   - The reconciler (if it reads progress)
   - `ai_router/start_session.py`'s pre-flight checks
3. **Migrate extension readers:**
   - `tools/dabbler-ai-orchestration/src/utils/sessionState.ts`
   - `tools/dabbler-ai-orchestration/src/providers/sessionSetsProvider.ts`
     (the count-derivation logic that surfaced the ctelr-spec drift)
   - Tree-item badge logic (`[FORCED]`, "in flight", "N/N", etc.)
4. **Explorer label migration "Done" → "Complete":**
   - Tree provider's display string mapping
   - View welcome content (if it mentions the label)
   - README screenshots (defer screenshot regen to Session 4)
   - Layer 3 Playwright assertions that text-match "Done" → update
     to "Complete"
5. **Lint rule (Python).** Add a pytest that enforces D13's rule:
   **"No application reader may read legacy fields except through
   approved compatibility helpers."** Grep-assert NO direct reads of
   `currentSession` / `totalSessions` / `completedSessions` in
   `ai_router/` source — with explicit allowlist carve-outs for
   `progress.py` itself, the migrator, v2
   compat code). Test fails if a regression sneaks in.
6. **Lint rule (TypeScript).** Same as above for
   `tools/dabbler-ai-orchestration/src/`. Implement as an ESLint
   custom rule OR a simple grep test in the Mocha suite.
7. **Test surface expansion:**
   - Layer 1 (pytest): all close-out gates pass against v3 fixture
     state
   - Layer 2 (extension stub harness): tree-provider count derivation
     matches expected output for v3 fixtures
   - Layer 3 (Playwright Electron): rendered "1/4", "in flight",
     `[FORCED]` badges match expected text for v3 state

**Creates:**
- `ai_router/tests/test_no_legacy_field_reads.py`
- `tools/dabbler-ai-orchestration/src/test/suite/no-legacy-field-reads.test.ts`

**Touches:** numerous files — full inventory determined by the
Session 3 grep audit. Probable list:
- `ai_router/close_session.py`, `start_session.py`, gate checks
- `tools/dabbler-ai-orchestration/src/utils/sessionState.ts`
- `tools/dabbler-ai-orchestration/src/providers/sessionSetsProvider.ts`
- Layer 2/3 test files

**Ends with:** Zero direct reads of legacy fields in either
codebase. Explorer displays "Complete" not "Done". All three test
layers green against v3 fixtures.

**Progress keys:** `session-003/legacy-reads-grepped`,
`session-003/python-readers-migrated`, `session-003/ts-readers-migrated`,
`session-003/explorer-label-complete`, `session-003/lint-rules-added`,
`session-003/all-three-layers-green`

**Estimated cost:** $0.10 – $0.30.

---

### Session 4 of 5: Bulk migrator + in-repo migration + consumer dry-run docs (NO publish)

**REVISED per GPT-5.4 (2026-05-17):** This session ships the bulk
migrator and migrates this repo's state files, but **does NOT publish
to PyPI or Marketplace**. Publishing moves to Session 5 (after the
migration UX is in place) so operators upgrading the extension never
see broken state on v2 files. Dual-write of legacy fields stays put
(per D5 revision) — this set never drops legacy emission. Dropping
legacy is a separate future set gated on consumer-repo v3-reader
confirmation.

**Goal:** Ship the one-shot bulk migrator CLI. Migrate the 28+
in-repo state files to v3 (dual-write format). Run a Lightweight-tier
ergonomics dry-run against a representative
`dabbler-homehealthcare-accessdb` state file (per D16). Produce
consumer-repo migration dry-run docs so consumers can preview what
the migrator will do before they upgrade. Build a release-candidate
VSIX (`v0.14.0-rc.1`) for internal smoke; no publish.

**Steps:**

1. **Bulk migrator CLI.** New CLI command
   `python -m ai_router.migrate_session_state` with flags:
   - `--scan <path>` (default: workspace root) — find all
     `session-state.json` files under `docs/session-sets/`
   - `--dry-run` — print what would change, don't write
   - `--in-place` — migrate each file in place
   - `--strategy regex|ai|interactive` (default: `interactive`) —
     title-extraction strategy (regex-first AI-fallback per D7)
   - **Note:** writers continue to dual-write per D5 revision; the
     migrator only touches files already in v2 shape on disk.
2. **Migrate this repo's state files.** Run the bulk migrator
   `--in-place --strategy regex` on the 28+ sets under
   `docs/session-sets/`. Verify each one passes v3 invariants.
   Commit the migration as its own commit ("Set 030 Session 4:
   bulk-migrate v2 state files to v3 (dual-write)").
3. **Lightweight-tier ergonomics dry-run** (per D16). Copy a
   representative `dabbler-homehealthcare-accessdb` state file
   (one of the older sets with hand-edits) into a temp fixture.
   Run the migrator. Hand-edit a state transition (e.g., flip
   session 2 from `"not-started"` to `"in-progress"`). Capture
   the diff. Confirm the one-field-flip property holds; document
   the experience in the consumer dry-run doc (step 4 below). If
   the ergonomics test fails (more than one edit needed per
   transition), pause and reassess D10 before Session 5.
4. **Consumer dry-run docs.** Author
   `docs/migration-v3-dry-run.md` covering:
   - what the migrator does to a v2 file
   - the dual-write shape (so consumers can see legacy fields are
     still there)
   - the rollback path (file is JSON; revert from git)
   - the Lightweight-tier hand-edit transitions (one-field-flip
     worked examples from step 3)
   - how to run `--dry-run` from a consumer repo's checkout
5. **Bump version numbers (RC):**
   - `ai_router` minor version (e.g., 0.3.2 → 0.4.0-rc.1)
   - Extension version (e.g., 0.13.18 → 0.14.0-rc.1)
6. **Build the release candidate VSIX locally.** `npx vsce package`
   produces `dabbler-ai-orchestration-0.14.0-rc.1.vsix`. Install
   the RC into a clean VS Code instance; smoke-test that the
   Explorer still renders correctly, close-out still works, and
   the new migrator CLI runs end-to-end. **No `vsce publish`.**
   No `twine upload`.

**Creates:**
- `ai_router/migrate_session_state.py`
- `ai_router/tests/test_migrate_session_state.py`
- `docs/migration-v3-dry-run.md`
- `tools/dabbler-ai-orchestration/dabbler-ai-orchestration-0.14.0-rc.1.vsix`
  (local artifact only; not committed)

**Touches:**
- `ai_router/__main__.py` or wherever CLI commands are registered
- `ai_router/CHANGELOG.md`, `ai_router/pyproject.toml` (RC version)
- `tools/dabbler-ai-orchestration/package.json` (RC version)
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- 28+ files: `docs/session-sets/*/session-state.json`

**Ends with:** Bulk migrator shipped and tested. This repo's state
files all in v3 (dual-write). Consumer dry-run doc published.
Lightweight ergonomics validated. RC VSIX built locally and
smoke-tested. **Nothing published externally.** Set 030 ready for
Session 5.

**Progress keys:** `session-004/bulk-migrator-shipped`,
`session-004/inrepo-files-migrated`, `session-004/lightweight-dry-run-passed`,
`session-004/consumer-dry-run-doc-published`, `session-004/rc-vsix-built`,
`session-004/rc-smoke-passed`

**Estimated cost:** $0.10 – $0.30.

---

### Session 5 of 5: Alignment migration UX + loading state + FINAL release

**REVISED per GPT-5.4 (2026-05-17):** Session 5 now ships both the
migration UX (its original scope) AND the final PyPI + Marketplace
publish (moved from Session 4 per D14). Publish only happens after
the in-extension v2 detection / loading state / migration CTA are
all in place, so operators upgrading the extension never encounter
broken state on v2 files.

**Goal:** Ship the in-extension lazy migration UX for any v2 state
files the operator (or consumer repos) didn't bulk-migrate. Fix the
Explorer's flash-of-welcome-CTA bug with a proper "Setting up your
project…" loading state. Validate the RC built in Session 4 one
more time, then publish the GA release to PyPI and Marketplace.
Notify consumer repos.

**Steps:**

1. **Tree-provider scan with loading state.** On extension
   activation, the tree provider enters a `scanState: "loading"`
   state. `getChildren()` returns a single sentinel TreeItem with
   label "Setting up your project…", description "scanning session
   sets…", icon = Dabbler logo (resourceUri to the existing
   `media/icon.svg`). Async scan runs in the background.
2. **Welcome view gating.** The viewsWelcome contribution's `when`
   clause checks `dabblerSessionSets.scanState`. Welcome content
   only renders when `scanState == "ready"` AND the workspace
   genuinely has zero session sets. No more flash.
3. **v2 detection during scan.** As the scanner walks
   `docs/session-sets/*/session-state.json`, it flags v2 files (no
   `schemaVersion: 3`). Counted into the scan result.
4. **Migration CTA per set.** Each v2 set renders in the tree with
   a "(needs migration)" badge and a context-menu command
   "Migrate to v3 schema". Invoking it opens a quickpick:
   - "Use spec.md headings" (regex extraction — zero cost)
   - "Use AI to refine titles" (router call,
     `task_type='spec-title-extraction'` — already registered in
     Session 1 step 7 — ~$0.05 per spec, confirm cost before
     running)
   - "Use generic labels (Session 001, Session 002, …)" (fallback
     for malformed/missing specs)
5. **Migration helper shared with the bulk migrator.** Both the
   CLI bulk migrator (Session 4) and the in-extension lazy migrator
   call the same `migrate_one_set(path, strategy)` helper. Helper
   lives in `ai_router/migrate_session_state.py` and is invoked from
   the extension via Python subprocess (same pattern the config
   editor uses).
6. **AI-fallback path:**
   - Reads spec.md
   - Routes via `ai_router.route()` with
     `task_type='spec-title-extraction'`, prompting for a JSON array
     of `{number, title}` records
   - Validates response against spec.md's parsed session count
   - Dumps `RouteResult` to JSON before attribute access (per memory
     `feedback_ai_router_route_result_handling`)
7. **Layer 3 Playwright smoke:**
   - Activate extension with a v2 fixture state file
   - Assert loading state renders with Dabbler icon + "Setting up
     your project…" label
   - After scan completes, assert tree shows the set with "(needs
     migration)" badge
   - Invoke migration command with "Use spec.md headings", assert
     the v3 schema is written and the badge clears
8. **Bump version numbers (GA).**
   - `ai_router`: 0.4.0-rc.1 → 0.4.0
   - Extension: 0.14.0-rc.1 → 0.14.0
9. **Final smoke pass on the GA build.** Build the production VSIX
   (`npx vsce package`). Install in a clean VS Code instance.
   Smoke-test:
   - Explorer renders without the welcome-CTA flash
   - A workspace with a deliberately-unmigrated v2 fixture shows
     the "(needs migration)" badge
   - The migration CTA's regex path writes a v3 file the Explorer
     immediately re-reads correctly
10. **Release** (operator confirms each):
    - `cd ai_router && python -m build && twine upload dist/*` to
      PyPI
    - `cd tools/dabbler-ai-orchestration && npx vsce publish --pat
      $env:AZURE_VSCODE_MARKETPLACE_TOKEN` to Marketplace
11. **Consumer-repo notification.** Drop a one-liner in each
    consumer repo's CLAUDE.md or equivalent pointing at the new
    schema doc + the dry-run doc from Session 4. Each consumer
    runs the bulk migrator on their own state files at their
    convenience. Rollback path documented in `migration-v3-dry-run.md`.

**Creates:**
- `tools/dabbler-ai-orchestration/src/providers/scanState.ts` (or
  similar — the scanState context-key manager)
- `tools/dabbler-ai-orchestration/tests/playwright/loading-state.spec.ts`
- `tools/dabbler-ai-orchestration/tests/playwright/migration-cta.spec.ts`

**Touches:**
- `tools/dabbler-ai-orchestration/src/providers/sessionSetsProvider.ts`
  (loading sentinel; v2 detection; migration badge)
- `tools/dabbler-ai-orchestration/src/extension.ts` (register
  scanState context key + migrate command)
- `tools/dabbler-ai-orchestration/package.json` (new command +
  viewsWelcome `when` clause update; GA version)
- `ai_router/migrate_session_state.py` (factor `migrate_one_set`
  out of the bulk CLI for shared use)
- `ai_router/pyproject.toml` (GA version)
- `ai_router/CHANGELOG.md`, `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md` (this repo) + consumer repos' CLAUDE.md files

**Ends with:** Operator no longer sees the welcome-CTA flash on
activation. Any remaining v2 state files (in this repo or consumer
repos opened in VS Code) get a clear migration CTA per set, with a
zero-cost default path. **PyPI + Marketplace published** with the
v3 schema + migration UX shipped together. Set 030 ready for
close-out.

**Progress keys:** `session-005/loading-state-shipped`,
`session-005/v2-detection-in-scan`, `session-005/migration-cta-per-set`,
`session-005/shared-helper-with-bulk-migrator`, `session-005/ai-fallback-wired`,
`session-005/layer-3-smoke-green`, `session-005/ga-smoke-passed`,
`session-005/pypi-published`, `session-005/marketplace-published`,
`session-005/consumer-repos-notified`

**Estimated cost:** $0.10 – $0.30 (verification call). The
operator-driven AI-fallback path's cost is per-spec, billed only
when the operator chooses it, not part of the set's verification
budget.

---

## Risks

- **R1 — Writer-side bug corrupts state.** A bug in the dual-write
  path (Session 2) could write inconsistent `sessions[]` and legacy
  fields. Mitigation: dual-write parity tests assert legacy fields
  are *always* derived from `sessions[]`, never independently
  maintained. Plus, the Session 3 lint rule prevents direct legacy
  reads, so a bug there can't propagate silently.
- **R2 — Reader migration misses a code path.** Some niche reader
  (a one-off script, a dashboard query) might still read legacy
  fields and silently degrade. Mitigation: Session 3's grep audit
  + lint rule. Acceptance: anything outside `ai_router/` and
  `tools/dabbler-ai-orchestration/src/` is out of scope; consumer
  repos audit their own readers when they upgrade.
- **R3 — Lightweight-tier UX harder than v2.** Editing a `sessions[]`
  array by hand is more friction than flipping a `currentSession`
  integer. Mitigation: D10 — schema doc ships with worked examples
  showing one-field-flip transitions; later sets can ship VS Code
  snippets if the friction proves too high.
- **R4 — Title drift accumulates.** If spec.md titles change after
  scaffolding, the `sessions[]` titles don't update. Mitigation:
  per Gemini-approved clarification, this is cosmetic; a future
  reconciliation command can refresh titles on demand. Not
  blocking for this set.
- **R5 — AI-fallback cost surprises operator** (Session 5).
  Mitigation: the AI fallback path explicitly confirms cost
  before each route call. Default strategy is regex-first, so AI
  cost is opt-in.
- **R6 — Loading state hides a real "no sets" workspace.** If the
  scan errors silently, the operator sees "Setting up your
  project…" forever. Mitigation: hard timeout (5s) on the scan;
  on timeout, fall through to the welcome view with a "(scan
  errored — check Output panel)" annotation.

---

## Routing notes

- Implementation work (Sessions 1-5): pure Claude tokens, no
  router invocation per memory `feedback_ai_router_usage`.
- Session-end verification (Sessions 1-5): `task_type='session-verification'`,
  single verifier (gpt-5-4). $0.10–$0.30 each.
- Session 5 operator-driven AI fallback: `task_type='spec-title-extraction'`,
  ~$0.05 per spec, opt-in per CTA. NOT part of the set's
  forecast cost — billed against the operator's decision to use
  the AI path.

## Total estimated cost

$0.50 – $1.50 across all five sessions (verification calls only).
AI-fallback usage in Session 5 is operator-driven and not in this
forecast.

## Cross-references

- Proposal: `docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`
- Schema (current): `docs/session-state-schema.md` — rewritten in S1
- Related memory: `project_canonical_schemas_shipped`,
  `feedback_default_not_started_evidence_to_escalate`

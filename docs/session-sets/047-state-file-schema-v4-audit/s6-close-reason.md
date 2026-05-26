# Set 047 Session 6 — Close-out reason

## Scope shipped (per spec §4 row for Session 6)

Schema-doc + authoring-guide revision + change-log + close-out.
Dual publish was held by the operator at close-out (option preserved
to bundle with Set 048 or Set 049).

### Canonical schema doc rewrite

[`docs/session-state-schema.md`](../../session-state-schema.md)
rewritten from v3 canonical to v4 canonical. Key sections:

- **"v4 is canonical; v1/v2/v3 read support persists through the
  transition"** replaces the v3-era "v3 is canonical; v2 read
  support is permanent" header. Per spec §3.4, the v3-shim is
  scheduled for removal in a future explicitly-scoped set after v4
  has shipped on a release — not literally permanent.
- **Reader contract** split into Layer 1 (the
  `normalize_to_v4_shape` / `normalizeToV4Shape` shim — returns
  the normalized dict with derived top-level fields), Layer 2
  (`get_progress()` / `getProgress()` — returns a `ProgressView`
  carrying only progress-counting fields), and Layer 3 (the
  cancellation reader carve-out — reads raw `state.status`
  directly).
- **v4 schema shape** section documents the new top-level keys
  (`schemaVersion`, `sessionSetName`, `status`, `sessions`) and
  the per-session record fields (`number`, `title`, `status`,
  `startedAt`, `completedAt`, `orchestrator`, `verificationVerdict`).
- **Per-session orchestrator block** documents the 7-field block
  currently emitted with a forward-pointer to Set 049's
  simplification.
- **Check-out / check-in** preserves the Set 033 / 036 semantics
  with the production "off by default" gate
  (`DABBLER_ENFORCE_CHECKOUT_COORDINATION=1`) called out.
- **Plan-less carve-out** documents the `sessions[]`-absent shape
  with top-level passthroughs.
- **8 v4 invariant rules** — rules 1-7 carry from v3 (rule 1
  relaxed for plan-less); rule 8 documents
  `sessions[N].orchestrator non-null whenever status ==
  "in-progress"` (writer-side enforced by required CLI flags) and
  the historical-attribution preservation on close.
- **Lightweight tier one-field-flip** worked example updated for
  v4 per-session shape.
- **Worked examples** (not-started, mid-set, between-sessions,
  complete) rewritten to v4 shape with populated per-session
  orchestrator blocks on closed sessions.
- **Derived values** section split into Layer 1 (normalized dict
  shape) and Layer 2 (ProgressView shape) with the exact
  derivation rules.
- **Prerequisites** section (new) documents the spec-side YAML
  field, parser semantics, and cross-reference rules.
- **v3 → v4 migration** section documents the migrator CLI + the
  VS Code right-click action + rollback procedure cross-reference.

### Authoring-guide update

[`docs/planning/session-set-authoring-guide.md`](../../planning/session-set-authoring-guide.md):

- Session Set Configuration block documentation gains the
  `prerequisites:` field with `slug` + `condition` (default
  `"complete"`).
- New field-semantics paragraph documents cross-references run
  after merge, unknown-slug staying blocked, badge suppression on
  terminal rows.
- "Cross-set dependencies" section updated: declare prereqs in
  two places (prose preamble + machine-readable
  `prerequisites:` field). The structured field is what drives
  the Explorer's `[BLOCKED BY PREREQS]` badge.
- Spec template snippet gains a commented-out `prerequisites:`
  block as a copyable starting point.

### Set change-log

[`change-log.md`](change-log.md) ships covering S1-S6 with
per-session scope, verifier rounds, cumulative routed cost
($2.314 of $10 NTE; 23.1%), and cross-references back to
predecessor (Set 046), companion (Set 048), and follow-on
(Set 049) sets.

### Version bumps (publish held)

- `pyproject.toml`: `dabbler-ai-router` 0.8.0 → 0.9.0
- `ai_router/__init__.py`: `__version__` 0.5.1 → 0.9.0 (catching
  up a stale string that fell behind in Set 044/045 — pyproject
  was at 0.8.0, init at 0.5.1)
- `tools/dabbler-ai-orchestration/package.json`: extension 0.21.0
  → 0.22.0
- `tools/dabbler-ai-orchestration/CHANGELOG.md`: new 0.22.0 entry
  detailing the v4 schema work
- `CLAUDE.md`: "Extension versioning" section walks updated
  (current → 0.22.0; previous → 0.21.0; v0.22.0 description
  added; v0.21.0 description preserved in the walk).
- `CLAUDE.md`: "Hard-coordination enforcement" section's parking
  pointer updated from "Set 048+" to "Set 049
  (`049-orchestrator-coordination-removal`)".

### Build artifacts

- `dabbler-ai-orchestration-0.22.0.vsix` built locally (852.81 KB,
  23 files). Not pushed to Marketplace per operator hold.
- PyPI release build NOT executed (operator hold).

## Cross-provider verification

Routed verification via
`python docs/session-sets/047-state-file-schema-v4-audit/run_s6_verification.py`
against `task_type='session-verification'` (gpt-5-4, tier 3).
One round, 873s, $0.5053. Verdict: ISSUES_FOUND with 3 Critical +
4 Important + 2 Nice-to-have items. All 9 items addressed
in-flight per memory `feedback_dont_hide_behind_out_of_scope`:

1. **Critical 1** — Per-session orchestrator close-out documented
   backwards. Pre-emptively caught by the closing orchestrator
   before the verifier returned (a re-read of S4 close-reason
   revealed the inconsistency); fix applied to the field-table
   entry, Check-out/check-in section, rule 8, Lightweight tier
   worked example, three worked examples, and Tier expectations.
2. **Critical 2** — Reader contract conflated normalize shim with
   `get_progress()`. Split into Layer 1 / Layer 2 / Layer 3
   carve-out structure; documented exact dict-vs-ProgressView
   field sets; added plan-less handling at the shim layer.
3. **Critical 3** — `verificationVerdict` documented as strict
   2-token enum but writer accepts any string. Widened field
   type to `string | null` with canonical tokens called out and
   the bundled S4 record's `ISSUES_FOUND_RESOLVED_IN_FLIGHT`
   value documented as an extension token.
4. **Important 1** — Derived top-level field semantics misstated.
   Rewrote "Derived values" + lifecycleState section to match
   `progress.py` lines 470-572: `startedAt` from in-progress
   else most-recently-completed scanning in reverse;
   `completedAt` ONLY when set-status == complete; `lifecycleState`
   synthesized for in-progress and complete but NOT cancelled.
5. **Important 2** — "Exactly one reader path" wrong. Carved out
   `readCancellationState` as Layer 3; corrected TS import to
   `../utils/progress`; corrected Python helper name to
   `ensure_session_state_file`.
6. **Important 3** — "Permanent" wording overstated spec §3.4.
   Reworded.
7. **Important 4** — Change-log S6 summary recorded the
   nonexistent rule-8-IFF invariant. Replaced with actual
   behavior summary.
8. **Nice-to-have 1** — `lastActivityAt` bump claim overstated.
   Corrected per session_state.py grep (only emission site is
   `register_session_start`).
9. **Nice-to-have 2** — Top-level vs per-session status vocabulary
   alignment misleading. Reworded.

In-flight CHANGELOG fix: the shim's TS source file was
mis-attributed to `src/utils/sessionState.ts` in the 0.22.0
entry; corrected to `src/utils/progress.ts`.

## Test posture

- **Python:** 896 passed, 1 skipped (pre-existing), 0 failed.
  Confirmed `__version__ = "0.9.0"` doesn't break any test asserts
  (the only mention of the constant in `ai_router/` is the
  definition site).
- **TS:** unchanged from S5 (no TS source touched this session
  beyond CHANGELOG.md and package.json version string). 623
  passed + 2 pre-existing baseline failures unchanged.
- **Build:** `npx vsce package` produced
  `dabbler-ai-orchestration-0.22.0.vsix` (23 files, 852.81 KB).

## Cumulative routed cost

- S1 audit (consensus): $0.10851
- S2 reader-first phase + 2 verification rounds: $0.48351
- S3 migrator phase + 1 verification round: $0.28820
- S4 writer-flip phase 1 + 1 verification round: $0.45704
- S5 writer-flip phase 2 + 1 verification round: $0.47171
- S6 close-out + 1 verification round: **$0.50530**
- **Cumulative S1+S2+S3+S4+S5+S6: $2.31427 of $10 NTE (23.1%).**

Plenty of headroom remained at set close; the verifier round
returned a substantial 9-item dispositionable list which warranted
the spend.

## Manual-verify attestation

I have manually verified:
- The schema doc accurately reflects the v4 writer's actual
  on-disk emission (cross-checked against `session_state.py`,
  `session_lifecycle.py`, `progress.py`, and the
  bundled live state file).
- The 8 invariant rules match what the validators enforce in
  `progress.py` (rules 1-7 from v3 carry; rule 8 added per the
  Set 047 spec § 3.1 contract).
- The Reader contract's three layers match the actual call sites
  in `read_progress`, `get_progress`, `readSessionSets`,
  `readCancellationState`.
- The change-log's per-session summaries match the S1-S5
  close-reason files (verifier flagged Important #4 and that's
  been fixed).
- The CHANGELOG.md 0.22.0 entry references the correct source
  paths (`src/utils/progress.ts` for the shim,
  `src/utils/sessionState.ts` for the writers).
- Python tests all green; extension builds.
- Operator-locked decisions (no orchestrator-block simplification
  in Set 047; no Set 049 work done mid-stream; v3-shim removal
  schedule documented but not actioned).

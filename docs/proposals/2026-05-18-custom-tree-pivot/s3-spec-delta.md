# Set 029 spec delta — pivot to per-session-set identity (DRAFT)

> **Status:** Authored 2026-05-18 from the custom-tree-pivot cross-provider
> audit. Replaces the per-workspace-markers spec delta at
> `../2026-05-18-per-workspace-orchestrator-markers/s3-spec-delta.md`
> (now obsolete — do not apply).
>
> **Audit artifacts:**
> - `proposal.md` (this directory)
> - `consensus-gemini-pro.json` + `consensus-gpt-5-4-manual.md`
> - `synthesis.md` — divergence analysis
>
> **Operator decisions (2026-05-18):**
> - **D1 (packaging):** Split per GPT-5.4. S3 = identity-only;
>   custom-tree work moves to a new S4.
> - **D2 (ambiguity):** Fail closed (skip write, log) per GPT-5.4.
>   No Quick Pick / workspaceState persistence in S3.
> - **D3 (orphan):** Implicit fail-closed for S3 (skip write when
>   no in-progress set is resolvable; current WebviewView
>   indicator shows its existing empty-state CTA). Richer orphan
>   UI defers to S4 alongside the custom tree.
>
> **Operator reviews this delta before I apply it to
> `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`.**

---

## Renumbering summary

Set 029 grows from 4 sessions to 6:

| New | Old | Goal |
|---|---|---|
| S1 | S1 | (no change — done) audit |
| S2 | S2 | (no change — done as v0.14.2) Claude-only orchestrator-indicator |
| **S3** | _(new)_ | **Per-session-set identity** (this delta) |
| **S4** | _(new)_ | **Custom-tree pivot** (spec'd closer to that session via its own audit per `feedback_audit_then_spec_for_substantial_features`) |
| S5 | S3 (verbatim, renumbered) | Non-Claude provider detection + manual override |
| S6 | S4 (verbatim, renumbered) | Polish, README, marketplace publish |

S5 and S6 keep their existing spec text unchanged apart from the
session-number bump and one cross-reference fix (S6 references
"S3's Claude work" — becomes "S2's Claude work").

---

## New S3: Per-session-set identity

### Goal

Move orchestrator-marker identity from per-workspace
(`~/.dabbler/current-orchestrator.json`) to per-session-set
(`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`).
Bump marker schema to v3 with `sessionSetSlug` as an integrity
field. Extract a `SessionSetsModel` data layer from the existing
`SessionSetsProvider` so the future custom tree (S4) and the
current native tree share the same scan/bucket/sort logic.

This session ships a **correctness fix**: the cross-window
contamination bug (per memory `project_consumer_repos` — three
parallel windows on three repos clobbering one global marker) is
eliminated. No user-facing UI change beyond per-set marker
resolution; the existing `WebviewView` orchestrator indicator
continues to render. The renderer reads the per-set marker for
the in-progress set in the current workspace; falls back to its
empty-state CTA when no marker is resolvable.

### Steps

1. **Marker schema v3.** Add top-level `sessionSetSlug` to the
   marker JSON; bump `schemaVersion` to `3`. Reader validates
   `sessionSetSlug` matches the host row's slug before rendering;
   logs and falls back to empty state on mismatch. Schema doc at
   `docs/session-state-schema.md` updated (or a new
   `docs/orchestrator-marker-schema.md` if it warrants its own
   file).
2. **Per-set marker path.** New writer path:
   `<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`.
   `<workspace>/.dabbler/` and `<workspace>/docs/session-sets/<slug>/.dabbler/`
   are both ignored. The init/update flow in
   `scripts/init-workflow.py` (or equivalent) auto-patches
   `.gitignore` **non-interactively** on next workspace init to
   ensure compliance (Gemini must-fix). Existing repos receive
   the patch silently on next `init`.
3. **Hook-to-set resolution algorithm.** In
   `scripts/write-orchestrator-marker.js`, replace the hard-coded
   global path with a walk-up resolver:
   ```
   function resolveSessionSet(cwd):
     current = cwd
     while current != root_of_filesystem:
       candidate = current/docs/session-sets
       if directory_exists(candidate):
         sets = readdir(candidate)
         in_progress = [s for s in sets
                         if status(s) == "in-progress"]
         if len(in_progress) == 1:
           return in_progress[0]
         if len(in_progress) > 1:
           return null   // fail closed (D2)
         return null     // no in-progress set
       current = parent(current)
     return null         // no docs/session-sets/ above cwd
   ```
   **Fail-closed posture (D2 + D3):** when the resolver returns
   null, the writer logs the reason to
   `~/.dabbler/orchestrator-writer.log` (existing log file) and
   **does not write a marker.** The renderer surfaces its
   existing empty-state CTA. No workspace-level orphan marker is
   created (D3 — keeps workspace identity out of the canonical
   model).
4. **Reader path resolution.** The
   `orchestratorIndicatorProvider` reader resolves the marker
   path the same way the writer does: walks from the workspace
   root, looks for the single in-progress set under
   `docs/session-sets/`, reads
   `<set>/.dabbler/orchestrator.json`. The provider's file-system
   watcher binds to the resolved per-set path (re-binds when the
   in-progress set changes — e.g., on close-out).
5. **Multi-writer precedence — unchanged.** The existing
   precedence policy (`current` > `manual` > `last-observed` >
   `configured-default`) and the Windows-aware retry loop
   (5 attempts at 50/200/600/1200ms) continue to apply, now
   scoped to the per-set marker.
6. **`SessionSetsModel` data-layer extraction (mandatory per
   both reviewers).** Extract
   `src/providers/SessionSetsModel.ts` from
   `SessionSetsProvider.ts`: pulls out scan, bucket, sort,
   `progressText`, `isCurrentSessionInFlight`, `iconUriFor`,
   `needsMigrationBadge`. `SessionSetsProvider` becomes a thin
   shim that consumes `SessionSetsModel`. Both the current
   native tree (S3 ship) and the future custom tree (S4) can
   consume `SessionSetsModel`. **Layer-2 tests** at
   `src/test/suite/sessionSetsProvider.test.ts` repointed to
   `SessionSetsModel` and continue to gate bucketing/sort
   invariants.
7. **Backward compatibility.** Pre-existing
   `~/.dabbler/current-orchestrator.json` is silently ignored by
   the new reader. Operators with the v0.14.2 Claude Code hook
   installed must re-run `Dabbler: Install Orchestrator Hook
   (Claude Code)` to pick up the new resolver logic in the
   writer (installer is idempotent; helper-script path
   unchanged). Acceptable because v0.14.2 has not shipped to
   Marketplace — no external consumer is affected.
8. **Playwright smoke updates.** Add scenarios:
   - Two in-progress sets in one workspace → writer skips,
     `orchestrator-writer.log` carries the ambiguity entry,
     indicator shows empty-state CTA.
   - Single in-progress set → writer writes to
     `<set>/.dabbler/orchestrator.json`, indicator renders the
     gauges.
   - Schema-v3 marker with mismatched `sessionSetSlug` → reader
     falls back to empty state and logs.
   - `cwd` outside any `docs/session-sets/` directory → writer
     skips, no orphan marker written.
9. **Version bump:** 0.14.2 → **0.15.0** (minor — identity
   model change per Gemini + GPT-5.4 consensus on D-Q9).

### Creates

- `tools/dabbler-ai-orchestration/src/providers/SessionSetsModel.ts`
  (data-layer extraction)
- `docs/orchestrator-marker-schema.md` _(or appended section in
  the session-state-schema doc)_ — documents the v3 marker
  shape, the per-set path, the fail-closed posture, and the
  walk-up resolver

### Touches

- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
  (walk-up resolver; per-set path; schema-v3 write; fail-closed
  log line)
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  (per-set path resolution; re-bind watcher on in-progress-set
  change; sessionSetSlug validation; existing empty-state CTA
  surfaces on null resolution)
- `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`
  (collapse to thin shim over `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/src/test/suite/sessionSetsProvider.test.ts`
  (repoint to `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts`
  (new scenarios per step 8)
- `tools/dabbler-ai-orchestration/package.json` (version → 0.15.0)
- `tools/dabbler-ai-orchestration/CHANGELOG.md` (new
  `[0.15.0]` section)
- `scripts/init-workflow.py` _(or wherever the canonical
  `.gitignore` template lives)_ — add
  `docs/session-sets/*/.dabbler/` to the ignore pattern; apply
  to existing repos on next `init`

### Ends with

Per-set markers are the canonical identity model. Three parallel
windows on three repos render their own correct orchestrator
state (cross-window contamination bug eliminated). The current
native `TreeView` and `WebviewView` indicator continue to
render — no UI rewrite yet. `SessionSetsModel` exists and is
ready for the S4 custom tree to consume. 0.15.0 packaged, not
yet published.

### Progress keys

`session-003/schema-v3-shipped`, `session-003/per-set-marker-path`,
`session-003/walk-up-resolver`, `session-003/fail-closed-posture`,
`session-003/sessionsetsmodel-extracted`, `session-003/layer2-tests-repointed`,
`session-003/playwright-fail-closed-scenarios`, `session-003/gitignore-autopatch`,
`session-003/version-bumped`

### Estimated cost

$0.10–$0.30 (single end-of-session verification; implementation
is local Claude tokens). Set 029 cumulative after S3 forecast:
$1.46 + $0.10–$0.30 = $1.56–$1.76 of $5.00 NTE.

---

## New S4: Custom-tree pivot

**Status: spec'd at high level in `proposal.md`; full session-level
spec authored via its own pre-session audit closer to S4 start, per
`feedback_audit_then_spec_for_substantial_features`.**

### Why a separate audit before S4

GPT-5.4's review flagged that the reimplementation surface is
larger than the cross-provider proposal scoped: 14 row-context
actions in `package.json`, plus loading-state, scan-state gating,
`viewsWelcome` integration, and ARIA tree semantics — none of which
are free in a custom webview. The split-into-its-own-session
decision (D1) buys the time to spec these properly. The pre-S4
audit will be informed by what S3 has shipped (e.g., the
`SessionSetsModel` extraction will give the audit a concrete
data-layer interface to design against).

### High-level S4 deliverables (will be refined by the S4 audit)

- Re-register `dabblerSessionSets` as a `WebviewViewProvider`
  (same view id, same view container).
- Lift the v0.14.2 gauge HTML/SVG/CSS from
  `orchestratorIndicatorProvider.ts` into the new view's
  accordion body.
- Retire the `dabblerOrchestratorIndicator` view entry from
  `package.json` once the custom tree's accordion body is
  proven.
- Reimplement (must-fix per both reviewers): keyboard nav,
  context-menu parity (all 14 actions), title-bar refresh,
  `viewsWelcome` empty state, loading-state transition, ARIA
  tree semantics, selection/focus styling.
- Auto-expand on SessionStart hook fire (per the S3 marker write);
  collapse on session close; honor manual collapse for the
  current session occurrence only (GPT-5.4 refinement).
- Multi-window observation: both windows render the same
  per-set marker (Gemini + GPT-5.4 concur this is a feature),
  with a freshness cue (GPT-5.4 add).
- Decide on Q3 (orphan-render shape) with the custom tree in
  hand — at that point the choice between "recent activity
  pseudo-section" (GPT-5.4) and just-leave-empty becomes
  concrete.

### Estimated S4 cost

$0.05–$0.20 for the pre-session audit (Gemini Pro via router;
GPT-5.4 via manual paste = $0.00). Implementation cost is local
Claude tokens. End-of-session verification: $0.10–$0.30.

---

## New S5 (was S3): Non-Claude provider detection + manual override

Spec text unchanged from the current spec.md `### Session 3 of 4`
section — verbatim, just renumbered to `### Session 5 of 6`.
Estimated cost unchanged: $0.10–$0.30.

## New S6 (was S4): Polish, README, marketplace publish

Spec text unchanged from the current spec.md `### Session 4 of 4`
section — verbatim, renumbered to `### Session 6 of 6`. One
cross-reference fix in step 3 (CLAUDE.md note): "S3's Claude work"
becomes "S2's Claude work" to match the new numbering.
Estimated cost unchanged: $0.05–$0.15.

---

## Risk table updates

| ID | Change |
|---|---|
| R1 (detection viability) | Unchanged — applies to S5 |
| R2 (hook payload drift) | Unchanged — applies to S2 (shipped) and S3 (the writer's defensive parse stays) |
| R3 (100px gauges) | Unchanged — applies to S2 (shipped) |
| R4 (marker-file race) | **Narrowed scope** — now per-set, not global. Multi-writer precedence still applies but contention surface is much smaller (one Claude session per set vs. all sessions across all windows). |
| **R6 (new)** | **Wrong-set attachment.** If the walk-up resolver picks the wrong in-progress set despite the fail-closed posture (e.g., stale `session-state.json` lingers as in-progress after a forgotten close-out), the operator sees correct-looking data attached to the wrong work. Mitigation: the indicator's hover tooltip surfaces the resolved set slug; the operator can spot the mismatch. Future S4 work may add a small "attached to: <slug>" badge in the gauge frame. |
| **R7 (new)** | **`.gitignore` patch missed.** If a workspace's `.gitignore` is not auto-patched (e.g., operator never re-runs `init`), per-set markers could be staged for commit by mistake. Mitigation: the marker file's content is bounded and harmless if committed; the auto-patch is idempotent on subsequent inits; a one-line note in CHANGELOG [0.15.0] flags it. |

---

## Forecast for Set 029 remainder

| Session | Forecast cost |
|---|---|
| S3 (this delta) | $0.10–$0.30 |
| S4 audit | $0.05–$0.20 |
| S4 verification | $0.10–$0.30 |
| S5 verification | $0.10–$0.30 |
| S6 verification | $0.05–$0.15 |
| **Total forecast** | **$0.40–$1.25** |

Cumulative after Set 029 complete: $1.86–$2.71 of $5.00 NTE.
Comfortable headroom for any Round-B verification rounds.

---

## What I'll do once operator approves this delta

1. Apply the changes above to
   `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`:
   - Insert new S3 section (per "New S3" above)
   - Insert new S4 placeholder (per "New S4" above)
   - Renumber existing S3 → S5 + S4 → S6
   - Update "Sessions: 4" reference to "Sessions: 6" in the
     spec header / overview
   - Update the change-log entry stub if one exists
2. Update `BATON.md` (or delete it; the audit-then-spec flow is
   complete, no more handoff needed mid-session).
3. Update CHANGELOG note pointing at this delta + the proposal.
4. Commit as `Set 029 Session 3 spec: per-session-set identity
   (post-pivot audit)`.

Nothing in this list ships code — just spec changes. The actual
S3 work runs as its own session.

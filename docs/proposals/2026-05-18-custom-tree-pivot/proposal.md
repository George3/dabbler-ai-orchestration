# Custom-tree pivot — design proposal

**Date:** 2026-05-18
**Status:** Authored mid-Set 029 (post-S2 polish, pre-S3 spec) for cross-provider review
**Supersedes:** [`../2026-05-18-per-workspace-orchestrator-markers/proposal.md`](../2026-05-18-per-workspace-orchestrator-markers/proposal.md)
  — the per-workspace-marker path solves a real bug but is the wrong
  scope. The pivot below solves the same bug more naturally as a
  side-effect of changing the identity model.
**Target session:** Set 029 Session 3 (replaces the previously-scoped
  "non-Claude provider detection + manual override" S3)
**Reviewers requested:** GPT-5.4 (manual paste in GitHub Copilot per
  established workaround for the API's current 429 state), Gemini Pro
  (via the `dabbler-ai-router`)

---

## TL;DR

Drop the dedicated `dabblerOrchestratorIndicator` webview. Replace
the native `dabblerSessionSets` `TreeView` with a webview-rendered
custom tree (same view id, same view container). Each in-progress
session-set row becomes an accordion: collapsed header shows what
today's `TreeItem` shows; expanded body shows the orchestrator
gauges + textual sections that v0.14.2 polished. Orchestrator
identity moves from per-workspace to **per-session-set**, which
dissolves the cross-window-contamination bug the per-workspace
audit was trying to solve.

Cost: ~600–1000 LOC of new webview tree code + reimplementation of
keyboard nav, context menus, and `viewsWelcome` semantics.
Gain: full visual fidelity for the gauges (native `TreeItem` can't
render SVG); correct identity model (no more "which window owns the
global marker" race); cleaner architecture (one webview surface for
the whole side bar instead of `TreeView` + `WebviewView`).

The pivot is feasible as a single S3 because v0.14.2 has not been
published to Marketplace; a clean cutover is possible.

---

## Problem statement

The post-S2 v0.14.2 architecture has two structural issues that the
per-workspace audit (now superseded) was trying to patch:

1. **Cross-window contamination.** The operator's workflow runs
   three parallel Claude Code sessions across three VS Code windows
   (`dabbler-ai-orchestration`, `dabbler-platform`,
   `dabbler-access-harvester` — per memory `project_consumer_repos`).
   Every SessionStart hook in every window writes the same
   `~/.dabbler/current-orchestrator.json`. The most-recently-started
   session wins; the others' gauges silently display wrong data
   ("the gauge actively lies about what model each window is
   running"). The per-workspace audit proposed hashing the workspace
   root path into a per-workspace marker filename. That works but
   only addresses one axis of the underlying identity problem.

2. **TreeView rendering ceiling.** The S2 polish rounds delivered
   IBM-palette SVG semi-circle gauges, capacity bars, inverted-band
   headers, container-query wrap behavior, and a mismatch badge with
   tier+effort rank logic. None of that survives in a native
   `TreeItem`, which supports `label` + `description` + `icon` +
   `tooltip` only. The choice to render the gauges in a separate
   `WebviewView` above the tree was forced by `TreeView`'s rendering
   model — not because it was the right anchoring for the data.
   Visually, the gauges feel disconnected from the sets they
   describe.

The pivot below addresses both at once by changing the identity
model: orchestrator info is owned by a **session set**, not by a
**workspace**. Two windows that have the same set open can both
display its current orchestrator. Two sets open in the same window
can each carry independent orchestrator info. The "global marker"
concept disappears.

## Locked context (do not re-litigate)

These pieces survive the pivot unchanged:

- **Marker schema v2** with `signalKind`, `confidence`,
  `effort.signalKind`, `effort.observedAt`, `stalenessMaxSec` —
  the JSON shape is unchanged. Only the path-resolution rule changes.
- **Multi-writer precedence policy** (`current` > `manual` >
  `last-observed` > `configured-default`) with the
  re-read-immediately-before-rename TOCTOU closure — still applies,
  scoped to the per-set marker.
- **Windows-aware retry loop** (5 attempts at 50/200/600/1200ms
  backoff) — unchanged.
- **Confidence-low producer rule** — unchanged.
- **The S2 visual-treatment matrix** — IBM colorblind-safe palette,
  inverted-band headers, capacity bar geometry, mismatch badge,
  container-query wrap. All unchanged; lifted wholesale from the
  retired `WebviewView` into the new accordion body.
- **The SessionStart + UserPromptSubmit hook installer** for Claude
  Code — unchanged. The hook continues to invoke
  `scripts/write-orchestrator-marker.js`; only the helper's
  path-resolution rule changes.
- **The data layer of `SessionSetsProvider`** — scanning, bucketing
  (in-progress / not-started / cancelled / complete), sort,
  file-watch refresh, the `SessionSet` type, the Layer-1/2/3 test
  invariants. All survive intact. Only the rendering surface
  (`getTreeItem` / `getChildren` / the registered `TreeView`)
  retires.

## Proposed solution

### Identity: per-session-set marker

A marker is owned by a session set, not by a workspace and not by
the global filesystem. Storage layout (two candidate shapes; see
Q1 below):

- **Shape A (in-tree):**
  `<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`
  — colocated with the set's other state (`session-state.json`,
  `change-log.md`, `ai-assignment.md`). Operator-visible.
  Survives `git clone` if checked in; gitignorable if not.

- **Shape B (user-global, hashed):**
  `~/.dabbler/orchestrators/<set-slug-hash>.json` — keyed on a hash
  of the absolute path to the set's directory. Invisible to git;
  no per-set policy decision required.

Recommended default: **Shape A**, gitignored. Reasons: discoverable
when troubleshooting; symmetric with the rest of the set's state;
no cross-repo accumulation. Q1 surfaces this for review.

### The custom tree

The view `dabblerSessionSets` (same id, same view container) is
re-registered as a `WebviewViewProvider` instead of a
`TreeDataProvider`. The view container icon, name, ordering, and
`viewsWelcome` schema are preserved.

The webview renders a vertical list of rows grouped under the same
buckets the current tree shows (In progress / Not started /
Cancelled / Complete). Each bucket is a collapsible group; each
row is an accordion.

- **Collapsed row** (always, default state for any non-in-progress
  set): renders the existing `TreeItem` payload — set name,
  per-state icon (`done.svg` / `in-progress.svg` /
  `not-started.svg` / `cancelled.svg`), description string from
  `progressText()`, `(needs migration)` badge when applicable,
  context-menu affordance.

- **Expanded row** (default for in-progress sets with a fresh
  marker; user-toggleable otherwise): renders the v0.14.2
  orchestrator-indicator HTML/SVG inline below the header row.
  Same gauges, same capacity bars, same two-section bottom
  display, same mismatch badge, same theme-aware vars. Pulled
  verbatim from `orchestratorIndicatorProvider.ts`'s render path.

### Auto-expand / collapse behavior

- **On SessionStart hook fire** (marker written): the set the marker
  belongs to auto-expands. If another set was previously expanded
  and the operator hasn't toggled either since, the prior
  auto-expand may collapse (Q5 surfaces this).
- **On session close** (state transitions in-progress → complete,
  or `session-state.json` no longer marks the set in-progress):
  the orchestrator section retires from the row. If
  `ai-assignment.md` carries a recommendation for the next session,
  the row's body shows ONLY that recommendation in a compact
  "next-session suggestion" treatment. Otherwise the row collapses
  back to header-only.
- **Manual toggle:** clicking the header expands/collapses
  regardless of state. The user's manual choice persists in
  workspace state and overrides auto-expand for that row.

### Hook-to-set resolution

The SessionStart hook receives `cwd`. The marker writer needs to
identify which session set the hook fired for. Algorithm:

```
function resolveSessionSet(cwd):
  current = cwd
  while current != root_of_filesystem:
    candidate = current/docs/session-sets
    if directory_exists(candidate):
      # walk each set under candidate, pick the one with
      # session-state.json status="in-progress"
      sets = readdir(candidate)
      in_progress = [s for s in sets if status(s) == "in-progress"]
      if len(in_progress) == 1:
        return in_progress[0]
      if len(in_progress) > 1:
        return most_recently_modified(in_progress)
      return null  # no in-progress set under this workspace
    current = parent(current)
  return null  # no docs/session-sets/ anywhere above cwd
```

If the resolver returns null (Claude session started outside any
workspace with `docs/session-sets/`, or no in-progress set), the
marker goes to a workspace-level orphan path
(`<workspace>/.dabbler/orchestrator-orphan.json`) and renders in a
special "Outside any set" row above the bucket groups (Q4).

### What gets retired

- The `dabblerOrchestratorIndicator` view + container entry in
  `package.json` (the view, not the orchestrator concept).
- `src/providers/orchestratorIndicatorProvider.ts` as a standalone
  `WebviewViewProvider`. Its render helpers
  (`renderGauge`, `describeMarker`, `describeRecommendation`,
  mismatch logic, etc.) move into the new custom-tree provider.
- `~/.dabbler/current-orchestrator.json` as a write target. The
  per-set marker path replaces it.
- The drafted-but-unapplied per-workspace S3 spec delta at
  [`../2026-05-18-per-workspace-orchestrator-markers/s3-spec-delta.md`](../2026-05-18-per-workspace-orchestrator-markers/s3-spec-delta.md).

### What gets reimplemented

The native `TreeView` provides several things for free that a
webview-based custom tree must reproduce. For each, the cost and
the v1-vs-follow-on call:

| Feature | Native | Cost to reimplement | v1? |
|---|---|---|---|
| Keyboard nav (up/down/enter/right/left) | Free | ~50 LOC + ARIA | **Yes** |
| Context menus (right-click → command palette) | Declarative via `package.json` `menus` | ~60 LOC; remap to webview `contextmenu` event + `vscode.postMessage` | **Yes** — operator workflows rely on Open Spec / Open Activity Log / Cancel / Restore |
| Title-bar actions (Refresh) | Declarative | ~10 LOC | **Yes** |
| `viewsWelcome` empty state | Declarative | Render same markdown in webview when no sets present | **Yes** |
| Selection state styling | Free | ~20 LOC CSS + state bookkeeping | **Yes** (cheap) |
| Accessibility (ARIA tree role, screen-reader announce) | Free | ~30 LOC `role="tree"` / `role="treeitem"` + `aria-expanded` | **Yes** — non-negotiable for accessible defaults |
| Drag/drop | Free if declared | N/A — not used today | No |
| Multi-select | Free if declared | N/A — not used today | No |

Reimplementation surface: roughly 600–800 LOC for the tree shell
(message protocol, render, kbd nav, ARIA, context menu plumbing) +
the lifted gauge code (~400 LOC of HTML/SVG/CSS, largely
copy-paste) + Playwright assertions for the new shape.

### What gets reused

- The data layer of `SessionSetsProvider` — `readAllSessionSets`,
  `discoverRoots`, the `SessionSet` type, the bucketing/sort logic,
  the file-watcher wiring. Refactor: extract a `SessionSetsModel`
  that the webview provider consumes; keep `SessionSetsProvider` as
  a thin shim for any remaining callers, or delete it once the
  webview-only path is verified.
- `scripts/write-orchestrator-marker.js` — only the path-resolution
  function changes; the retry loop, multi-writer precedence,
  schema-version write, and `deriveModelDisplayName` all stay.
- The Claude Code hook installer (`SessionStart` +
  `UserPromptSubmit`) — unchanged. The hook still invokes the
  shared writer.
- Marker schema (modulo a `sessionSetSlug` field added, see Q6).
- All S2 visual work: SVG gauges, IBM palette, capacity bars,
  inverted-band headers, theme vars, container queries, mismatch
  detection helpers (`describeMarker`, `describeRecommendation`,
  tier/effort rank logic).
- The S2 Playwright coverage — most scenarios port over with
  assertion-string updates; the underlying behaviors being tested
  (signal kinds, confidence, mismatch badge, "in flight"
  annotation) all survive.

## Migration plan

v0.14.2 is committed (`52aa4eb`) but NOT published to Marketplace.
The pivot ships as a clean cutover under 0.14.3 (or 0.15.0 if
reviewers prefer a minor bump for the architectural change). No
external consumers are affected.

- On first activation after upgrade, the extension silently ignores
  any pre-existing `~/.dabbler/current-orchestrator.json`. The
  provider doesn't read it. Operators do not need to take any
  manual action; old markers age out and can be deleted at any time.
- Operators with the v0.14.2 Claude Code hook installed must re-run
  `Dabbler: Install Orchestrator Hook (Claude Code)` to get the
  updated marker writer. The installer is idempotent; the
  helper-script path is unchanged; only the resolution logic
  inside the helper has changed.
- `docs/session-sets/<slug>/.dabbler/` (if Shape A is chosen) is
  added to the canonical `.gitignore` pattern shipped by
  `scripts/init-workflow.py` or equivalent. Existing repos receive
  a one-time `.gitignore` patch on next `init`.

## Open design questions for the reviewers

**Q1 — Marker storage shape.** A (in-tree under the set directory)
vs. B (user-global hashed). A is more discoverable and symmetric
with other per-set state. B has zero risk of being checked in to git
by accident. Which is the right default? Is there a hybrid (e.g.,
A for the writer, but the reader scans both)?

**Q2 — Hook-to-set resolution under ambiguity.** When `cwd` is
inside a workspace with multiple in-progress session sets, the
resolver picks "most-recently-modified". Is that the right tiebreak?
Alternatives: (a) prompt the operator on first SessionStart per
ambiguous workspace and persist the choice; (b) write to ALL
in-progress sets simultaneously (the operator sees the same marker
on each affected row, which is honest but noisy); (c) require the
hook payload to carry a session-set identifier (not currently in
the payload — would require operator setup work).

**Q3 — Claude sessions started outside any session set.** Three
options for the orphan case:
- (a) Render as a top-level "Recent activity" pseudo-section above
  the bucket groups, no set association.
- (b) Don't render at all; the indicator is set-specific or it
  doesn't show.
- (c) Maintain a workspace-level "orphan" marker
  (`<workspace>/.dabbler/orchestrator-orphan.json`) and render it
  as a special row labeled "Orchestrator (no active set)".

(c) is the proposal's current pick; (a) is also reasonable. Which
fits the operator's workflow?

**Q4 — Auto-expand persistence.** Operator wants auto-expand on
SessionStart fire. Does the expanded state persist across:
- VS Code reloads (workspace state)?
- The session ending (set transitions in-progress → complete)?
- The operator manually collapsing mid-session (should auto-expand
  be suppressed for the remainder of the session)?

Default proposed: persist across reloads; auto-collapse on session
end; honor manual collapse for the remainder of the session
(reset on next SessionStart).

**Q5 — Multi-window observation.** Window A and Window B both have
the same workspace open. Operator starts a Claude session in
Window A (cwd inside Set 029). Both windows' trees now show Set
029 expanded with the orchestrator info populated. Is this
desired (both windows show the same truth)? Or confusing (operator
in Window B didn't start anything)?

Proposed: both windows show it; treat it as a feature, not a bug —
"this set has an active session" is a per-set fact, not a
per-window fact.

**Q6 — Marker schema additions.** Adding a top-level
`sessionSetSlug` field to the marker (so the reader can sanity-check
that the marker it loaded actually belongs to the set whose row
hosts it). Bumps `schemaVersion` to 3. Worth it, or rely on the
path-based association (filename = identity)?

**Q7 — Reimplementation scope: what to defer?** The "reimplement"
table above marks everything as v1 except drag/drop and
multi-select (neither is used today). Is there anything that should
move to v1.1: e.g., ARIA could potentially ship after a quick
accessibility review, context menus could potentially ship with a
command-palette-only fallback for the first day. The operator's
near-term workflow does not appear to lean on any one of these
hard, but a missed regression on context menus (Open Spec,
Cancel, Restore) would be highly noticeable.

**Q8 — Test layer impact.** Today's Layer-1 (`pytest` against the
real CLIs), Layer-2 (`@vscode/test-electron` against the
`SessionSetsProvider`), and Layer-3 (Playwright Electron) coverage
each touch a different surface. The pivot:
- Layer 1: unaffected (data layer, file writes).
- Layer 2: the tree-provider harness exercises code that no longer
  drives rendering. The data-model refactor preserves the
  bucketing/sort invariants, so the tests still pass if pointed at
  the new `SessionSetsModel` extraction. Worth doing in the same
  session?
- Layer 3: completely rewritten. The Playwright `_electron.launch`
  path still works (per memory `project_playwright_electron_works_on_windows`);
  the assertions all need updating because the rendered DOM is now
  webview-generated, not native-tree.

Is the Layer 2 refactor in scope for S3 or a follow-on?

**Q9 — Spec-version + version-bump policy.** The pivot retires
substantial code shipped in v0.14.2 (which itself isn't on
Marketplace, so no external impact). Options:
- 0.14.3 (patch — internally substantial but externally first
  exposure of any of this code)
- 0.15.0 (minor — architectural change deserves a minor bump per
  the established versioning pattern)

Proposed: 0.15.0. The data flow, the surface area, and the
identity model all change. Worth the minor bump even if no
external consumers are affected.

**Q10 — Non-Claude provider work: in or out for S3?** The
previously-spec'd S3 (Codex auto-detect + Gemini/Copilot manual +
universal manual-override quickpick) is a lot of surface. Combined
with the pivot, S3 grows substantially. Two options:
- (a) Pivot-only S3; non-Claude moves to S4; original S4 (README +
  Marketplace publish) becomes S5. Set 029 grows from 4 → 5
  sessions.
- (b) Pivot + non-Claude detection in S3, README+publish stays
  S4. S3 is large but ships a coherent product.

Proposed: (a). The pivot is large enough that bundling
non-Claude work risks an under-cooked v1 of either. The set
expanding by one session is acceptable (operator confirmed comfort
with audit-then-spec for substantive work — memory
`feedback_audit_then_spec_for_substantial_features`).

## Implementation surface (S3 scope, post-pivot)

Estimated LOC and file impact assuming pivot-only S3 (Q10 = a):

- `src/providers/CustomSessionSetsView.ts` (new, ~600 LOC):
  webview provider, message protocol, kbd nav, ARIA, context menu
  plumbing, lifecycle.
- `src/providers/SessionSetsModel.ts` (new, ~150 LOC, extracted
  from `SessionSetsProvider.ts`): the data-layer extraction;
  consumed by the new view.
- `src/providers/SessionSetsProvider.ts`: deleted (or reduced to
  a thin re-export for any back-compat needs).
- `src/providers/orchestratorIndicatorProvider.ts`: retired as a
  view provider; render helpers (~400 LOC of HTML/SVG/CSS
  generation) move into `CustomSessionSetsView.ts` (or a sibling
  `OrchestratorAccordion.ts` if the file gets too large).
- `media/orchestrator-indicator/indicator.css` → renamed to
  `media/session-sets-tree/tree.css` or similar; gauges CSS stays
  intact, tree-shell CSS added (~150 LOC for accordion + bucket
  groups + selection + focus).
- `scripts/write-orchestrator-marker.js` (~60 LOC added): per-set
  resolver, optional `sessionSetSlug` field, orphan path handling.
- `package.json`: `dabblerOrchestratorIndicator` view entry
  deleted; `dabblerSessionSets` view entry changes `type` from
  `tree` to `webview`; `views/title` and `view/item/context` menu
  entries stay (re-targeted from native tree commands to webview
  message-handlers via the same command ids).
- `src/test/playwright/session-sets-tree.spec.ts` (new, replaces
  `orchestrator-indicator.spec.ts`): all of the existing scenarios
  ported plus new ones for bucketing, expand/collapse, kbd nav,
  context-menu invocation. ~400 LOC.
- `src/test/playwright/orchestrator-indicator.spec.ts`: deleted.
- `CHANGELOG.md` entry under [0.15.0]: feature note describing
  the pivot, cross-link to this proposal.
- Schema doc updates (`docs/session-state-schema.md` if the
  per-set marker location is documented there).

Total: ~1100–1400 LOC of new code, ~600 LOC deleted/relocated,
~50 LOC of `package.json` changes. Manageable as a single session
**if** the data-layer extraction (which is mechanical) goes
smoothly. If the kbd-nav / ARIA / context-menu reimplementation
turns out to need a Round-B iteration, splitting into two
sub-sessions is a fallback (per memory
`feedback_split_large_verification_bundles`, the operator is
comfortable with sub-session splits when scope exceeds a
single-session budget).

## Risks

- **R1 — Reimplementation regressions.** Kbd nav, context menus,
  ARIA, and `viewsWelcome` all need to feel native. A user-visible
  regression (e.g., context menu doesn't trigger on right-click)
  is highly noticeable. Mitigation: Layer-3 Playwright scenarios
  cover all four explicitly; manual smoke-test before claiming
  done.
- **R2 — Hook-to-set resolution ambiguity.** Q2 is unresolved.
  Wrong default (e.g., "most-recently-modified" picks the wrong
  set when operator is mid-context-switch) means the orchestrator
  info lands on the wrong row. Mitigation: log the resolution
  decision; surface a "this orchestrator was resolved to <set>
  because…" hover on the gauge.
- **R3 — Performance.** A webview tree may feel slower than the
  native tree for very large workspaces (>50 sets). Today's
  workspaces are nowhere near that. Mitigation: render-budget
  audit before merge; collapse rendering for non-in-progress
  buckets by default.
- **R4 — Theming gaps.** The native tree picks up VS Code theme
  changes automatically. The webview needs explicit
  `--vscode-*` CSS var consumption (the existing gauges already
  do this; the tree shell needs the same discipline). Mitigation:
  light/dark theme parity check in the Playwright smoke.
- **R5 — Discoverability of orchestrator info.** Operators who
  ignore the Session Sets tree (e.g., they live in the file
  explorer) lose visibility into the orchestrator. Today's
  dedicated `WebviewView` is visible alongside the tree even if
  the tree is collapsed. Mitigation: status-bar item showing
  current orchestrator for the focused set (out of scope for v1;
  log as follow-up).

## What to verify in the consensus call

Per the operator's pattern (memory
`feedback_audit_then_spec_for_substantial_features`), please
review:

1. Is the pivot itself the right call, or does the per-workspace
   path retain enough merit that we should consider a hybrid
   (per-workspace markers + dedicated indicator stays)?
2. Open questions Q1–Q10 above — for each, either confirm the
   proposed default or surface a stronger alternative.
3. Reimplementation table — anything missed, anything that should
   move out of v1?
4. Risks R1–R5 — anything missing, anything mis-sized?
5. Scope decision Q10 — pivot-only vs. pivot + non-Claude
   detection in the same S3.

Where the reviewers diverge from each other or from this
proposal, please present the divergence with reasoning so the
operator can decide (per memory
`feedback_prefer_ai_consensus_over_human_prompt`).

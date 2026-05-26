# Set 046 — Explorer Enrichment from Harvest Records — Audit Proposal (Pass A)

**Status:** PASS A DRAFT — awaiting two-pass devil's-advocate cross-provider verification at end-of-Session-1 for scope-lock.

**Authored:** 2026-05-26, Set 046 Session 1.

**Predecessor:** Set 044's `proposal.md` (dual-primary log-harvest design),
locked at S5; implementation shipped end-to-end in Set 045
(`045-log-harvest-implementation`).

**Source-of-truth spec:**
[`docs/session-sets/046-explorer-enrichment-from-harvest-records/spec.md`](../../session-sets/046-explorer-enrichment-from-harvest-records/spec.md)
(stub-mode; this proposal is the audit pass the stub deferred to.)

---

## 1. Purpose of this proposal

The Set 046 spec was deliberately written as a STUB at Set 044/S6 close-out
to park the idea of Explorer enrichment until Set 045's Harvest Record
stream existed in production. Set 045 shipped 2026-05-26
(`dabbler-ai-router 0.8.0` + Marketplace extension `0.21.0`); the Harvest
Record schema, joiner, wrapper, and parsers are now production-grade.
This proposal scope-locks Set 046.

The spec listed six candidate leverage points (some operator-floated, some
drafter-floated) and three parked architectural questions. The operator
also locked three deliverables at the start of Session 1:

- **(a)** "0/?" fraction icon for not-started session sets whose spec.md
  has no defined session breakdown.
- **(b)** Second line under In Progress rows in the Explorer showing
  `engine • model • effort` of the checked-out orchestrator. Suppress
  silently when no data.
- **(c)** README.md update with a mocked screenshot of the Explorer
  showing one In Progress (half-completed), two Not Started, two
  Completed session sets.

This proposal: (i) maps the operator-locked deliverables onto spec
candidates, (ii) prunes / endorses / defers the remaining candidates,
(iii) dispositions the parked architectural questions, and (iv)
proposes a session breakdown.

---

## 2. Code-state grounding (pre-audit)

Before the candidate dispositions, three facts about the current
Explorer surface establish what is **already shipped** vs **net new**:

### 2.1 fractionFor() already returns `N/?` when `totalSessions == null`

[`CustomSessionSetsView.ts:142-147`](../../../tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts#L142-L147)
(added in Set 036 S7) returns `${sessionsCompleted}/?` when the state
file's `totalSessions` is `null`.

Consequence for deliverable (a): the Explorer side is **already correct**.
A true stub-mode set (never `start_session`'d) renders `0/?` today. The
problem is **writer-side** — `start_session` (just observed on this very
set in this session) defaults `totalSessions: 1` when no `--total-sessions`
flag is passed, so as soon as the operator runs `start_session` on an
unscoped stub, the fraction becomes `0/1` and stays that way until
`close_session` writes the real count from `sessions[]`.

### 2.2 "(needs migration)" detector is correct; the remediation is incomplete

Detector at [`fileSystem.ts:373-381`](../../../tools/dabbler-ai-orchestration/src/fileSystem.ts#L373-L381)
flags `set.needsMigration` when either (i) `schemaVersion` is absent
or `!== 3`, or (ii) `schemaVersion === 3` but `sessions[]` is missing
or non-array. The right-click "Migrate to v3 schema" action handles
case (i) but not case (ii) — which is the case observed on
`great-psalms-scroll-font` (a `sessionLog[]` array under a
`schemaVersion: 3` shell).

Consequence: the audit's "(needs migration) one-shot migrator" line item
is a migrator-expansion problem, not a detector-redesign problem.

### 2.3 In-progress row template has a clean attachment point for deliverable (b)

In [`media/session-sets-tree/client.js:241-279`](../../../tools/dabbler-ai-orchestration/media/session-sets-tree/client.js#L241-L279)
(`renderRow`), the title renders at line 271 inside `.row-name`;
harvest badges render at line 273; conflict pills are wrapped in their
own `.conflict-pills` div at line 276. Inserting a new `<div class="row-second-line">…</div>`
between the description span (line 272) and the harvest badges (line 273)
inside `.row-text` does not collide with existing DOM.

Consequence for deliverable (b): the rendering is a small, well-scoped
patch with no architectural exposure.

---

## 3. Candidate dispositions

### 3.1 Spec candidate §1 — Second-line orchestrator badge on in-progress rows

**Disposition: IN SCOPE (locked by operator deliverable (b)).**

Rendering attaches at [client.js:272/273](../../../tools/dabbler-ai-orchestration/media/session-sets-tree/client.js#L272-L273)
per §2.3. Data source is the `orchestrator` block in `session-state.json`
(the Set 033 H1 check-out source-of-truth) — **not** Harvest Records.
Rationale: the orchestrator block is canonical for the
checked-out-as identity; Harvest Records are observed-via-side-channel
evidence and are subject to staleness, ordering, and join-precision
problems. For "what AI is driving this set right now", the canonical
field is `orchestrator.engine + .model + .effort`.

Fallback chain if `orchestrator` block is empty (e.g., a session set
that pre-dates Set 033 check-out):

1. Most recent Harvest Record's `engine + model + effort` for the
   set_slug, **only** if a single distinct triple exists across all
   records (otherwise: suppress).
2. Suppress (per operator's "no error, no missing data, just suppress"
   directive).

Effort field rendering: omit when `effort == "unknown"` (which is the
writer's default when `--effort` is not passed). So `claude • claude-opus-4-7 • high`
when effort is `"high"`, but `claude • claude-opus-4-7` when `"unknown"`.

Long-model-name handling (open question §1 in spec): CSS
`text-overflow: ellipsis` on the second-line span, with the full
identifier in a `title` attribute hover-tooltip. Keeps the row height
constant.

Effort-drift open question (spec §1): not relevant given the data
source is now the canonical orchestrator block, not Harvest Records.

### 3.2 Spec candidate §2 — Live cost surfacing per row

**Disposition: IN SCOPE, but cost source is the router's metric ledger, NOT Harvest Records.**

The router's metric ledger (`ai_router/metrics/`) is the **authoritative**
cost source for router-routed calls. Harvest Records cover IDE-agent
calls (Codex, Gemini Code Assist, Claude Code chat-mode) that bypass
the router — but cost-per-token for those surfaces is approximate at
best (the parsers extract token counts where available but providers
don't always emit them in the rendered transcript).

Recommended posture: render router-ledger cost when available, append
"+ harvest-estimated" with a separate (smaller / dimmer) figure when
harvest records show non-routed activity for the set_slug. Suppress
the harvest-estimated figure entirely when there are no harvest
records (avoid `+ $0.00` clutter).

Honest-display alignment (per `feedback_user_facing_cost_messaging`):
hover-tooltip on the cost cell explains "router-tracked $X.XX +
estimated $Y.YY from harvested logs". Tooltip is the place to be
explicit; the row stays compact.

Cumulative-on-bucket-header (spec §2 secondary): nice-to-have, defer
to a follow-on session if S3 runs long; not a blocker for shipping the
per-row figure.

### 3.3 Spec candidate §3 — Writer-bypass warning surface

**Disposition: DEFER (already partially shipped in 0.21.0; expansion not high-leverage today).**

Per the CLAUDE.md description of 0.21.0: Explorer rows already gain
"writer-bypass" as both a harvested-signal badge (B) and a
coordination-conflict pill. The signal IS visible. The spec §3
asked for a "warning badge" — that is what shipped.

The spec's open questions (sticky vs live-only, dismissal flow) are
real, but they're refinement of an already-visible signal, not the
debut of the signal. Defer to a follow-on set when usage data shows
the pill is being missed.

### 3.4 Spec candidate §4 — Multi-AI-on-same-set conflict warning

**Disposition: DEFER (already shipped as engine-mismatch pill in 0.21.0).**

Same reasoning as §3.3 — 0.21.0 already ships the "engine-mismatch"
conflict pill from the joiner's emission. The spec's open questions
(window length, `--force` legitimate-override handling) are
joiner-side refinements that can land in the next `dabbler-ai-router`
release without touching the Explorer; they don't need a Set 046
session.

### 3.5 Spec candidate §5 — Time-since-last-activity per row

**Disposition: IN SCOPE.**

High-leverage at low cost. Rendering: third element on the second
line (next to `engine • model • effort`), formatted as
`active 2 min ago` / `idle 45 min` / `stale 4 h`. Data source: the
`orchestrator.lastActivityAt` field in `session-state.json` (already
populated by `start_session` — observable in this session's state
file at line 26) for canonical activity; falls back to
`max(ts)` over harvest records when the orchestrator block lacks
`lastActivityAt`.

Threshold open question (spec §5): propose `live < 5 min` (green/no
color),  `idle 5–60 min` (default text color), `stale > 60 min`
(muted/amber). No red — red is reserved for the conflict pill
column.

Tick frequency open question (spec §5): the Explorer already
re-renders on file-watcher events; piggyback on that. Don't add a
timer-driven re-render. Stale "5 min ago" labels are an acceptable
imprecision in exchange for not waking up the webview every minute.

### 3.6 Spec candidate §6 — Tool-touch histogram / scope-creep indicator

**Disposition: DEFER (privacy + low marginal value).**

The privacy concern (file paths) is real. The marginal value is
unclear — operator has direct line-of-sight to tool calls in their
chat surface already. Defer indefinitely; revisit only if a concrete
operational pain (e.g., a real scope-creep incident traced to a
session set) makes the case.

---

## 4. Parked architectural question dispositions

### 4.1 Blocked-on-prereqs lifecycle state

**Disposition: DEFER, bundle with the v4 schema audit (§4.2).**

The question of whether `status: "deferred"` / `"blocked"` deserves a
canonical token is genuinely part of the v4 schema discussion (it
touches every writer and reader). Surfacing it standalone wastes
audit cycles; surfacing it as part of v4 lets the same audit pass
treat the whole status-token set holistically.

### 4.2 v4 schema — derive top-level state from sessions[]

**Disposition: DEFER to its own audit set.**

Per `feedback_audit_then_spec_for_substantial_features`, this is the
class of change that wants its own audit set (cross-provider design
audit) followed by a separate implementation set. Touches: every
writer in `ai_router/`, every reader (gate_checks, reconciler,
session_lifecycle, joiner.parsers), every Explorer consumer
(fileSystem.ts:readSessionSets, fractionFor, cancellation reader),
every test layer, and every Lightweight-tier consumer repo's
ad-hoc emission shape. Absorbing it into Set 046 would balloon
the set beyond its discretionary-enrichment character.

Proposed: open a new stub `047-state-file-schema-v4-audit` at Set
046 close-out (mirroring how Set 046 itself was opened at Set 044/S6
close-out). The §4.1 blocked-on-prereqs question rides along.

### 4.3 "(needs migration)" indicator triage + one-shot migrator

**Disposition: IN SCOPE.**

Per §2.2: the detector is correct; the migrator is incomplete. In
scope is:

1. **Migrator expansion** — extend
   `python -m ai_router.migrate_session_state` (if it exists; new
   module if not) to recognize the `sessionLog[]` shape (and other
   near-conformant v3 shapes harvested from triage; see #2 below) and
   rewrite the file canonically. Idempotent.

2. **Triage of Lightweight orchestrators' emission shapes.** A
   30-minute sweep over the known Lightweight-tier consumers
   (`dabbler-homehealthcare-accessdb`, the `great-psalms-scroll-font`
   case, any others discovered during the sweep) listing which
   non-canonical v3 shapes appear. Output: a one-page catalog at
   `docs/lightweight-tier-emission-drift.md`. The catalog feeds the
   migrator's recognition rules in #1.

3. **Click action on the "(needs migration)" indicator.** Today the
   action only exists on right-click. Add a left-click handler that:
   - For schemaVersion-absent state files: runs the existing v2→v3
     migrator (no behavior change from today's right-click).
   - For schemaVersion===3 + non-canonical-shape state files: runs
     the expanded migrator from #1.
   - Both paths show a confirmation modal before writing.

This is well-scoped to a single session.

---

## 5. README.md screenshot (operator deliverable (c))

**Disposition: IN SCOPE.**

Mocked Explorer screenshot showing:

- **1 In Progress row, half-completed:** e.g., `045-log-harvest-implementation`
  with `3/6` fraction, second line `claude • claude-opus-4-7 • high`,
  `active 2 min ago`, plus an example harvest-signal badge and an
  example conflict pill so the README captures the full surface.
- **2 Not Started rows:** one with `0/?` (stub-mode, deliverable (a)),
  one with a defined breakdown (e.g., `0/5`).
- **2 Completed rows:** one with the bucket-collapse caret, one
  expanded to show per-session list.

Authoring approach: **rendered screenshot from a live VS Code
instance**, not a hand-drawn mock. The mock-data fixture lives at
`tools/dabbler-ai-orchestration/test/fixtures/readme-screenshot/`
so the screenshot can be regenerated when the Explorer surface
evolves. Image stored under
`tools/dabbler-ai-orchestration/media/readme-screenshot.png`
(referenced from the top-level README's marketing section).

---

## 6. Proposed session breakdown

Six sessions, mirroring Set 045's shape (the dual-primary log-harvest
implementation, which had comparable scope):

| # | Title | Scope | Layer |
|---|---|---|---|
| **1** | Audit pass + scope-lock | *(this session)* — proposal, cross-provider verification, spec rewrite, open `047-state-file-schema-v4-audit` stub | docs |
| **2** | Writer-side `totalSessions: null` + Explorer pre-flight | Writer change: `start_session` keeps `totalSessions` null unless `--total-sessions` is passed. Backfill tests. Verify deliverable (a) renders `0/?` end-to-end on a fresh stub. | router + ext |
| **3** | Second-line orchestrator badge (deliverable (b)) | Insert `.row-second-line` between `.row-name` and `.harvest-badges` per §3.1. Suppress-silently fallback. Layer-3 Playwright coverage. | ext only |
| **4** | Live cost surfacing per row | Per §3.2. Router-ledger primary, harvest-estimated secondary, tooltip transparency. Layer-3 coverage. | router + ext |
| **5** | Time-since-last-activity + "(needs migration)" expansion | Per §3.5 + §4.3 combined (both are "second-line column" work for the same row template, plus the migrator expansion is small enough to ride along). | router + ext |
| **6** | README screenshot + cross-tier docs + verification + close-out + dual release | Per §5. Cross-tier consumer notice (mirror `docs/cross-repo-harvest-notice.md`). Cross-provider verification of the full set. PyPI 0.9.0 + Marketplace 0.22.0 release prep. | docs + release |

Session count rationale: 6 is the largest the set should go without
slipping into the v4 schema audit that §4.2 defers. If §3.2 (cost
surfacing) reveals more complexity than estimated, it can split into
its own follow-on set rather than absorbing more S5/S6 oxygen.

---

## 7. Bias cautions for cross-provider verifier

Per the `feedback_devils_advocate_default_for_roadmap_decisions`
memory: the proposal author (me — Claude Opus 4.7) holds an
architectural preference for the canonical `orchestrator` block as
the data source for deliverable (b), and for the router-ledger as
the primary cost source for §3.2. Both choices push Harvest Records
into a **secondary** role, which is a tension with the spec's whole
"Explorer enrichment from harvest records" framing. Pass B should
specifically pressure-test:

- **Bias 1 — overweighting canonical state over observed evidence.**
  The orchestrator-block preference for (b) means Harvest Records
  are only consulted on fallback. Is that actually what the operator
  wants given the spec's framing? Counter-argument: Harvest Records
  show what's *really* happening (including writer-bypass cases); the
  orchestrator block shows what's *supposed* to be happening. Maybe
  showing the most-recent harvest evidence on the second line is more
  honest, with a divergence pill when the two disagree.
- **Bias 2 — overweighting router-ledger over harvest cost.** Same
  pattern. The proposal favors the router-ledger because it's
  accurate, but the harvest-estimated figure is the only signal for
  the growing IDE-agent fraction of usage (Codex / Gemini Code
  Assist). Should the rendered figure default to harvest-estimated
  when available, with router-ledger as the fallback?
- **Bias 3 — defer-bias on §3 / §4.** I marked these "already
  shipped, defer expansion" — but the spec's open questions about
  sticky / dismissable / window-length are real. Is there a
  cheap-but-meaningful refinement that should ride along on Set 046
  rather than waiting for usage data?
- **Bias 4 — under-scoping the migrator.** I bundled §4.3 with §3.5
  in Session 5 because both touch row rendering. But the migrator
  expansion is a router-side change (Python), while §3.5 is
  extension-side (TypeScript). That's two distinct code surfaces in
  one session. Should §4.3 split into its own session?
- **Bias 5 — README screenshot is a Session-6 throwaway.** I parked
  deliverable (c) at the end of the set on a "release prep" session.
  But the operator listed it as one of three locked deliverables —
  giving it a 1/6 share of a single session may under-resource it
  if the mock-fixture infrastructure turns out to be substantial.

Pass B should specifically opine on each of these five biases and
either reinforce or invert the proposal's choice with stated reason.

---

## 8. Open questions for cross-provider verifier (orthogonal to biases)

- **Q1: Should the writer's `totalSessions: null` semantic (S2 deliverable) extend
  retroactively to existing not-started session sets in the repo, via a one-time
  migration?** Or is forward-only sufficient? Forward-only risks `0/1` artifacts
  persisting on sets that get `start_session`'d before their audit pass.
- **Q2: Should deliverable (b)'s second line live in `.row-text` (per §2.3) or in a
  new `.row-meta` div positioned below the entire row's main flex container?**
  The former is closer to the row title and reads naturally; the latter gives
  more room for the future cost cell and idle-time annotation. Long-term
  layout question.
- **Q3: Cross-tier consumer notice (S6): is the publish-side discipline of
  copy-pasting CLAUDE.md addenda into each consumer repo
  (`docs/cross-repo-harvest-notice.md` pattern) still the right adoption model,
  or has Set 045's experience surfaced a better pattern?**
- **Q4: Should the README screenshot be a static PNG (proposed §5) or an
  animated GIF showing the in-progress→completed transition?** Animated GIF
  conveys more, but increases regen friction.

---

## 9. Memory hooks consulted

- `feedback_devils_advocate_default_for_roadmap_decisions` — Pass B is default
  here. See §7.
- `feedback_audit_then_spec_for_substantial_features` — Drove §4.2 defer to
  its own set.
- `feedback_user_facing_cost_messaging` — Drove §3.2 honest-display posture.
- `feedback_ai_router_usage` — Restricts the cross-provider verification to
  end-of-session (i.e., after the operator endorses this Pass A draft, not
  during drafting).
- `feedback_budget_question_scope` — Confirmed $5 NTE locked once at
  set-start, no re-asking per session.
- `feedback_split_large_verification_bundles` — At S6 verification, slice
  bundles ≤500 LOC to avoid the gpt-5-4 cascade pattern.
- `project_marketplace_download_count` — Aggressive defer (e.g., §3.3 / §3.4
  expansion) remains low-risk while download count stays near zero.

# Change log — Set 018 (healthcare-accessdb migration → lightweight-tier abstraction)

> **Status at close-out:** Session 1 of 1 complete. Set reshaped at
> Session 1 mid-stream from "migrate `dabbler-homehealthcare-accessdb`
> to canonical Option B" to "extend the adoption-bootstrap flow with
> a Lightweight adoption tier and an organization-design dialog."
> The reshape was driven by audit findings (the target repo doesn't
> fit the original frame) and operator redirect (move the abstraction
> upstream into the orchestrator, let a downstream orchestrator
> apply it on demand). `dabbler-homehealthcare-accessdb` was **not
> touched** by this set — it remains as found, in active UAT
> cadence, and is now a documented Lightweight-tier candidate.

## Audit findings (Session 1, 2026-05-07)

Probed `dabbler-homehealthcare-accessdb` per spec Step 3. Findings
diverged sharply from spec premise:

- **Not a git repository.** `git rev-parse --show-toplevel` →
  `fatal: not a git repository`. No `.git`, no parent `.git`. The
  "Option A vs. Option D" framing in the spec is not applicable.
- **No Python venv, no `ai_router/`, no `dabbler-ai-router` pip
  install.** Metadata extraction runs from
  `scripts/run_extraction.ps1` driving Access COM via PowerShell.
- **No session-set scaffolding.** Sessions are tracked as a single
  21-row ledger inside `CLAUDE.md` with closing BATONs at
  `docs/sessions/NNN-<slug>.md`. Ledger is mid-stream (sessions
  001–005 complete, 006–021 planned).
- **Custom UAT pattern.** Runs through the standalone HTML UAT
  Checklist Editor at `github.com/darndestdabbler/uat-checklist-editor`
  with per-set checklist JSON at `docs/uat-checklists/`. Distinct
  from the dabbler-ai-orchestration extension's UAT Checklist tree
  feature.
- **Extension state already aligned.** Only
  `darndestdabbler.dabbler-ai-orchestration` installed
  (versions 0.13.2 + 0.13.3); no legacy
  `darndestdabbler.dabbler-session-sets`. The migration spec's
  acceptance criterion #5 was already met.

## Scope reshape (operator redirect)

Operator instructed three stacked redirects on 2026-05-07:

1. **Don't migrate healthcare-accessdb.** It's a working test
   fixture with its own established session protocol. Document it
   as distinct rather than force-fit it.
2. **Lift the lightweight-tier abstraction.** Some projects
   benefit from session-set organization without `ai_router/` and
   the close-out machinery. Make this a first-class adoption
   tier in the bootstrap flow.
3. **Move the work to the downstream orchestrator.** Don't apply
   the new tier to healthcare-accessdb here; teach the
   orchestrator (via the canonical bootstrap doc) to apply it
   when the operator launches the extension's bootstrap prompt
   against any candidate repo. Include an abstract pattern
   catalog so the downstream AI proposes 2–4 cross-cut candidate
   organizations rather than a single shallow decomposition.

The reshaped deliverable plan was authored as
`ai-assignment.md`, presented for explicit operator approval, and
executed end-to-end after approval (operator: "Approve. And the
budget can be $10 for this. Proceed. No more questions.").

## What landed in this commit

### Documentation edits

- [`docs/adoption-bootstrap.md`](../../adoption-bootstrap.md) (386 → 461 lines, +75)
  - **Step 4** rewritten — frame budget and adoption tier as parallel decisions; clarify that cross-provider verification is opt-in via tier choice, not the default for every project.
  - **Step 4.5 inserted (NEW)** — adoption-tier dialog (Lightweight L vs. Full F) with branching guidance: L skips Step 5 entirely, F continues to budget. Coexistence sub-dialog (replace / parallel / index) for projects with their own session protocol. Confirm-and-note close.
  - **Step 5** prologue note added — "Skip this step entirely if Lightweight."
  - **Step 6 rewritten** — the prior 17-line "propose 2–6 sets" framing is replaced with a three-subsection structure: how to derive a decomposition; the abstract pattern catalog (7 patterns × 4 columns); explicit instruction to propose 2–4 cross-cut candidate organizations with one-line tradeoffs and watch-out failure modes; greenfield + existing-protocol guidance.
  - **Step 7** prologue note added — Lightweight checklists are a strict subset (no `budget.yaml`, no `router-config.yaml`, no `ai_router/` scaffolding); the existing example checklist is full-tier.
  - **Step 9** prologue and closing — Lightweight projects skip Budget monitoring + General cost monitoring; new Lightweight closing note replaces the zero-budget reminder for those projects.
- [`docs/ai-led-session-workflow.md`](../../ai-led-session-workflow.md) — one ~10-line callout block at top of "Cost-budgeted verification modes" disambiguating *budget tier* (within-Full-adoption) from *adoption tier* (Lightweight vs. Full); explicit pointer to bootstrap Step 4.5; note that lightweight projects opt out of cross-provider verification by tier choice, not by cost-budgeted exception.

### Spec status

- [`docs/session-sets/018-healthcare-accessdb-migration/spec.md`](spec.md) — "⚠ Scope reshape (2026-05-07)" callout inserted at top, pointing at this set's `ai-assignment.md` as the actual deliverable plan. Original spec body preserved as historical context.

### Memory updates

- **Updated** `project_consumer_repos.md` — healthcare-accessdb section rewritten with the audit findings (no git, no Python, custom protocol, custom UAT path) and explicit Lightweight-tier-candidate note. Drift-status section trimmed to acknowledge Sets 015/016/017 closed the prior drift items for harvester + platform; the original drift catalog is now historical baseline.
- **New** `project_lightweight_tier_added_to_bootstrap.md` — captures Step 4.5 / Step 6 changes, vocabulary watch (budget tier vs. adoption tier), pointer that the prompt at `master` auto-picks-up the doc edit (no version bump needed).
- **MEMORY.md index** — extended consumer-repos line; appended new lightweight-tier entry.

### Set 018 artifacts

- `spec.md` (with reshape callout), `ai-assignment.md`, `budget.json`, `session-state.json`, `session-events.jsonl` — set lifecycle records
- `change-log.md`, `disposition.json`, `activity-log.json` — close-out artifacts

## What did NOT change

By explicit scope:

- **No edits to `dabbler-homehealthcare-accessdb`.** Confirmed by
  inspection at close-out: no files written outside this
  orchestration repo's tree.
- **No extension TypeScript changes.** The prompt constant in
  [tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts](../../../tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts)
  points at `master`; the doc edit is auto-picked up by the next
  paste-into-fresh-chat. No `package.json` version bump, no
  `CHANGELOG.md` update, no `npx vsce package` rebuild.
- **No README edit.** The README's existing bootstrap blurb
  ([README.md:117–138](../../../README.md#L117-L138)) survives at
  the level of abstraction it operates at ("propose a session-set
  decomposition") — the L/F branch is internal to the bootstrap
  flow, transparent to the README reader.
- **No `ai_router/` code touched.**
- **No cross-provider verification route.** Per spec cost
  projection ($0 metered) and per memory
  `feedback_ai_router_usage` (router restricted to end-of-session
  verification, deferred). Operator review of `ai-assignment.md`
  before execution + read-back of doc edits at validation served
  as the verification surface.

## Cost reconciliation

| Phase | Spec projection | Actual | Notes |
|---|---|---|---|
| Audit + plan authoring | $0 | $0 | Read-only canvas of healthcare-accessdb + this repo's bootstrap surfaces |
| Migration execution | $0 | $0 | Reshaped to doc-only edits in this repo |
| Workflow-shape documentation review | $0 metered | $0 | Operator review surface; no LLM verifier route |
| **Set total (metered)** | **$0** | **$0** | Set 018 budget set at $5 then raised to $10 mid-session; budget unspent |

Cumulative across Sets 016 + 017 + 015 + 018: still under $0.20
metered (per Set 017 close-out reconciliation).

## Risks acknowledged at execution

From `ai-assignment.md` § 5; status at close-out:

- **Doc bloat** — adoption-bootstrap.md grew 386 → 461 lines (+19%).
  Acceptable; tables compress well, no replication of full-tier
  prose in lightweight branches.
- **Confusion between adoption tier and budget tier** — explicit
  vocabulary callout at top of `ai-led-session-workflow.md`'s
  tier section; Step 4.5 names the dimension explicitly.
- **Fresh-chat AI may skip Step 4.5** — positioned immediately
  after Step 4's education; tier-choice prompt is short and
  uses bold L/F labels.
- **Pattern catalog mechanical-walk failure mode** — Step 6 has
  explicit "don't enumerate them all" instruction plus
  watch-out failure modes (over-decomposing, forced cuts,
  slight variants of one cut).

## Queued follow-ups

None blocking. Candidates surfaced for future sets:

- **A README mention of the lightweight tier** could be added the
  next time README.md is touched. Not urgent — the README points
  at the canonical bootstrap doc, which now exposes the tier
  choice on the AI's first interaction.
- **A worked Lightweight-tier example** (healthcare-accessdb is
  the natural candidate) could be added to the bootstrap doc as
  a "see also" appendix once a downstream orchestrator has
  actually applied the new flow against a real repo. Premature
  to add here.
- **Extension command palette discoverability** — if operator
  feedback later indicates that the L/F choice would benefit
  from being surfaced in the extension UI (e.g., a tooltip on
  the "Copy adoption bootstrap prompt" command), that's a
  separate set with extension code changes + version bump.

## Operator-decision provenance

- **Reshape decision (audit → lightweight-tier abstraction):**
  Operator turn after Session 1 audit findings posted.
- **Plan approval:** Operator turn — "Approve. And the budget can
  be $10 for this. Proceed. No more questions for me. Let's get
  this done."
- **Tiebreaker / interpretive judgment during execution:**
  None invoked. The plan in `ai-assignment.md` was followed
  end-to-end without scope changes.

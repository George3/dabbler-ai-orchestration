# Set 018 Session 1 — AI Assignment

**Status:** Authored 2026-05-07; awaiting operator approval before any edits.

**Scope reshape from spec.** The original spec framed this set as a layout
migration of `dabbler-homehealthcare-accessdb` to canonical Option B.
Session 1's audit found the repo doesn't fit that frame (not a git
repository, no Python venv, no `ai_router/`, no session-set
scaffolding; uses a custom BATON-based session protocol with the
standalone HTML UAT Checklist Editor; actively running UAT cycles on a
21-session ledger embedded in CLAUDE.md). The operator redirected the
set toward an **abstraction-level change in the orchestrator
itself**: extend the adoption-bootstrap flow so a downstream
AI/orchestrator (running in a *fresh* chat invoked from the extension's
`Dabbler: Copy adoption bootstrap prompt` command in any target repo)
will (a) ask the human whether they want **lightweight adoption
(Explorer + session-set organization only)** or **full adoption
(Explorer + ai_router + close-out machinery)**, and (b) for either
tier, run an organization-design dialog that proposes 2–4 candidate
session-set decompositions cross-cut by an explicit catalog of
abstract patterns.

**This session does NOT touch `dabbler-homehealthcare-accessdb`.** The
healthcare-accessdb work is fully owned by whatever orchestrator the
operator launches via the extension's bootstrap prompt, at the
operator's UAT-pause convenience. Set 018's deliverable is the
upgraded prompt-flow that *prepares* that downstream orchestrator to
do the right thing.

---

## 1. Findings (from Session 1's audit)

The lightweight-adoption tier is a real gap, supported by independent
evidence beyond the healthcare-accessdb case:

- **The Explorer already supports it today.** `readSessionSets` in
  [tools/dabbler-ai-orchestration/src/utils/fileSystem.ts:184–343](../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L184-L343)
  hard-requires only `docs/session-sets/<set>/spec.md` per set. Every
  other artifact (`activity-log.json`, `session-state.json`,
  `change-log.md`, `CANCELLED.md`, `ai-assignment.md`,
  `<set>-uat-checklist.json`) is optional and degrades gracefully.
  No code changes are needed for the Explorer to render an
  Explorer-only project.
- **No co-located `ai_router/` requirement.** `discoverRoots()`
  (same file, lines 30–50) iterates `vscode.workspace.workspaceFolders`
  and looks for `docs/session-sets/` relative to each. There's no
  guard requiring an adjacent `ai_router/`, no requirement on
  `router-config.yaml` presence, no Python introspection.
- **The current bootstrap doc presents only one path.**
  [docs/adoption-bootstrap.md](../../adoption-bootstrap.md) Steps 5–9
  assume `ai_router/` will be installed, a `budget.yaml` will be
  written, and `router-config.yaml` will be tuned. The doc names
  *budget* tiers ($0 / limited / middle / ample) but doesn't expose
  an *adoption* tier (lightweight / full) — those are orthogonal
  dimensions that get conflated today.
- **healthcare-accessdb is a real-world example.** Working test
  fixture, custom session protocol, Access COM workflow, no Python.
  Forcing it through the current flow would either break its
  cadence or produce dead orchestration scaffolding.
- **Step 6 (Plan alignment) underspecifies the proposal step.** It
  says "propose 2–6 session sets" with a one-paragraph framing.
  There's no guidance on *how* to derive a decomposition, no
  catalog of organization patterns, no prompt to consider multiple
  cross-cut alternatives. The operator's call here is that this is
  exactly where the AI most needs structured help.

## 2. Current state of the orchestrator (what exists today)

- **Prompt constant** at
  [tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts](../../../tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts)
  is a 2-line clipboard message: "Read
  `https://raw.githubusercontent.com/.../master/docs/adoption-bootstrap.md`
  and follow it. Gather decisions in dialog. Don't write anything
  until I approve a checklist." All substance lives in the canonical
  doc.
- **Canonical doc** at
  [docs/adoption-bootstrap.md](../../adoption-bootstrap.md) (386 lines).
  Steps 1–9 plus a `budget.yaml` reference and end-of-bootstrap
  notes.
- **Workflow doc** at
  [docs/ai-led-session-workflow.md](../../ai-led-session-workflow.md)
  references the bootstrap's *budget tiers* (lines 87–102) but does
  not yet acknowledge an adoption-tier dimension.
- **README** at
  [README.md:117–138](../../../README.md#L117-L138) has a short
  paragraph pointing at the bootstrap; high-level wording survives
  the doc edit unchanged.

## 3. Drift items vs the operator's redirect

| Drift | What's missing today |
|---|---|
| **Adoption-tier choice** | No question, no dialog, no consequence. The flow assumes full adoption. |
| **Lightweight-tier flow** | Steps 5 (budget), 7 (checklist), 8 (execute), 9 (closing pointers) all assume `ai_router/` will be installed. No abbreviated path exists. |
| **Organization-design rigor** | Step 6 says "propose 2–6 session sets" with a one-line framing. No abstract pattern catalog, no instruction to propose multiple cross-cut candidates with tradeoffs. |
| **Workflow-doc cross-reference** | Workflow doc's tier section (lines 87–102) tacitly equates "tier" with budget tier; needs a one-paragraph note that adoption-tier is a separate dimension and that lightweight-tier projects bypass everything in §"Cost-budgeted verification modes". |

## 4. Edit plan (concrete)

All edits are **text-only** in this orchestration repo. **No
extension TypeScript changes**, **no version bump**, **no VSIX
rebuild**. The prompt constant points at `master`, so a commit to
master is automatically picked up by the next paste-into-fresh-chat.

### 4a. Insert new Step 4.5 in `docs/adoption-bootstrap.md`

Position: between existing Step 4 (Brief education on session sets,
ends at line ~148) and existing Step 5 (Budget-threshold dialog,
starts at line 150). **No renumbering of existing Steps 5–9** —
preserves all inbound links and existing references.

Section title: **`## Step 4.5 — Adoption tier`**.

Content shape (precise wording finalized at execution time, target
~40 lines):

- One paragraph explaining that adoption tier is a different
  dimension from budget tier, and that some projects benefit from
  the Explorer + session-set organization without taking on
  `ai_router/` and the close-out machinery.
- Explicit operator-facing question to ask the human:
  > **Which adoption tier fits this project?**
  >
  > **(L) Lightweight (Explorer + session-set organization only).**
  > Just `docs/session-sets/<set>/spec.md` files visible in the
  > Session Set Explorer. No `ai_router/`, no Python, no budget
  > config, no close-out machinery, no cross-provider verification.
  > Best for: working test fixtures, repos with their own
  > established session protocol, side projects, or any repo where
  > the value is in *organizing* the work rather than running it
  > through the full router.
  >
  > **(F) Full (Explorer + `ai_router/` + close-out + verification).**
  > The complete framework: budgeted cross-provider verification,
  > metrics, cost reports, automated close-out, the works. Best
  > for: projects where AI-led work is the primary mode of
  > development, where reviewable cost tracking matters, or where
  > you want orchestration support beyond just session-set
  > organization.
- Branching guidance: *if (L), skip Step 5 entirely and proceed
  to Step 6; if (F), continue to Step 5*.
- A small note: when the project already exists with a custom
  session protocol (BATON files, ledger in CLAUDE.md, etc.), the
  AI must explicitly ask whether the new session-set tree should
  *replace* the existing protocol, *parallel* it (both coexist —
  ledger as authoritative-per-session record, session-sets as
  thematic grouping), or *index* it (session-sets as pure pointers
  back to BATON files). The downstream orchestrator picks one
  with the human; the bootstrap doc just names the three modes.
- One sentence pointing at Step 6's pattern catalog.

### 4b. Strengthen Step 6 (Plan alignment dialog)

Existing Step 6 is short — just "propose 2–6 session sets, each
with a slug and 1-sentence purpose." The redirect calls for a
real organization-design step. Replace the existing Step 6 body
(lines 209–225 of the doc) with:

- One short paragraph reminding the AI that for lightweight-tier
  projects, the action checklist will only contain
  `docs/session-sets/<set>/spec.md` files and at most a small
  CLAUDE.md amendment — no `ai_router/`, no `budget.yaml`, no
  router-config tuning.
- A subsection **"Abstract patterns the AI should consider"**
  with the catalog (see 4c below).
- An **explicit instruction**: propose **2–4 candidate
  organizations** to the human, each cross-cut by a different
  abstract pattern, each with a one-line tradeoff. Wait for the
  human's pick (or hybrid) before drafting any spec content.
- A reminder that the existing Step 6 "the human steers
  throughout" rule still applies.

### 4c. Add the abstract pattern catalog

Inside Step 6, list these patterns the AI can use to derive
candidate organizations:

| Pattern | What it groups by | Example |
|---|---|---|
| **Input artifacts** | Source materials the work consumes | Schema files, raw data, requirements docs, UAT checklists, BATON ledger, RFCs |
| **Output artifacts** | Things the work produces | Reports, deployable modules, docs deliverables, datasets |
| **Cross-cutting themes** | Concerns spanning multiple components | Access-feature coverage in a migration test fixture; security; observability; performance |
| **Stated objectives** | What the project says it's trying to achieve | Goals from `project-plan.md` / README; OKRs; release criteria |
| **Inferred organizational patterns** | What the existing folder structure / docs already imply | Existing CLAUDE.md ledger, BATON sequence, file-tree groupings, branch naming |
| **Risk / dependency layers** | Foundational vs dependent work | Foundation → fix → test → ship; data prep → pipeline → analysis → reporting |
| **Stakeholder review boundaries** | Where natural review pauses already exist | Per UI section; per release candidate; per regulatory milestone |

Note that the patterns are **non-exclusive** — a single project
will often plausibly cut multiple ways, and the AI should propose
at least two visibly different cuts so the human sees real
alternatives, not slight variants on one cut.

The catalog stays inside Step 6 to keep the bootstrap doc
self-contained; no separate file.

### 4d. Light edits to Steps 7–9

- **Step 7 (Build the action checklist):** add one paragraph noting
  that for lightweight-tier projects the checklist is a strict
  subset (no `budget.yaml`, no `router-config.yaml`, no `ai_router/`
  scaffolding) and that the example checklist in the doc is for
  full-tier — lightweight checklists will typically be just spec.md
  files plus a CLAUDE.md amendment.
- **Step 8 (Execute):** no change needed; the execution discipline
  applies identically.
- **Step 9 (Closing pointers):** add a short branched section.
  Lightweight-tier closing pointers omit budget monitoring,
  `python -m ai_router.report`, the cost dashboard pointer, and
  the budgeted-verification reminder. They retain Session Set
  Explorer pointer, "Start the next session" guidance, and the
  workflow-doc pointer (with a note that Rules 1–2 about
  cross-provider verification are full-tier concerns).

### 4e. One-paragraph note in `docs/ai-led-session-workflow.md`

Near the existing tier section (around line 87, "Cost-budgeted
verification modes"), add a short paragraph clarifying that
*budget tier* is a within-full-tier concept, and that
lightweight-tier projects opt out of cross-provider verification
entirely as part of choosing that tier (not as a cost-budgeted
exception). Cross-link to the bootstrap doc's new Step 4.5.
~10 lines.

### 4f. Spec status update

Add a short "**Scope reshape (2026-05-07)**" section at the top of
[docs/session-sets/018-healthcare-accessdb-migration/spec.md](spec.md)
pointing at this `ai-assignment.md` as the actual deliverable plan.
The original spec body stays readable as historical context. ~8
lines.

### 4g. Close-out artifacts (standard)

- `change-log.md`: summary of the audit + reshape + edits, with
  cumulative-spend reconciliation against the spec's $0 metered
  projection.
- `disposition.json`: completion record.
- Memory updates:
  - **Update** `project_consumer_repos.md`: extend the
    healthcare-accessdb entry to note that this repo is a
    *candidate for lightweight-tier adoption when/if the operator
    runs the bootstrap prompt against it*; do not record the
    adoption itself (since this session doesn't perform it).
  - **New** `project_lightweight_tier_added_to_bootstrap.md`:
    one-line memory recording that the adoption-bootstrap flow
    now offers Explorer-only as a first-class tier (so future
    Set 018 follow-up work or related framework discussions can
    reference it without re-deriving).

## 5. Risk callouts

- **Doc bloat.** Adding Step 4.5, expanding Step 6, and branching
  Steps 7 + 9 adds ~80 lines to a 386-line doc. Mitigation: keep
  prose tight; rely on the table in 4c rather than expansive
  prose; don't replicate full-tier explanations in lightweight
  branches — link to the existing Step 7/8/9 content where
  identical.
- **Confusion between adoption tier and budget tier.** Both use
  the word "tier." Mitigation: use the explicit phrases
  "*adoption* tier" and "*budget* tier" in any cross-references;
  the workflow-doc paragraph (4e) explicitly disambiguates.
- **Fresh-chat AI may skip Step 4.5 if doc is too long.** Mitigation:
  position Step 4.5 immediately after Step 4 (the education step),
  so the tier choice is the first decision the human makes; keep
  Step 4.5's question framing punchy and labelled L/F.
- **Pattern catalog could become a checklist the AI mechanically
  walks.** Mitigation: explicit instruction in Step 6 — "consider
  these patterns; **don't enumerate them all**; pick the 2–4
  cuts that genuinely fit *this* project's evidence and propose
  those."
- **README's bootstrap blurb mentions budget-threshold dialog as
  a built-in step.** It does, but at a level of abstraction that
  survives the change ("propose a session-set decomposition")
  unchanged. No README edit required; will reverify at execution.

## 6. Out of scope

- **Any change to `dabbler-homehealthcare-accessdb`**. The audit
  evidence was used to motivate the abstraction; the actual
  application of lightweight adoption to that repo is the
  downstream orchestrator's job, run by the operator at their
  convenience.
- **Extension TypeScript changes.** The prompt is a thin pointer at
  `master`; pure-doc edits land for free. If a future change
  requires a beefier prompt (e.g., to embed the L/F question
  inline rather than rely on the doc), that's a follow-up set.
- **Workflow-doc rewrite.** The 1624-line workflow doc is unchanged
  except for the ~10-line clarifying paragraph in 4e. Larger
  restructuring of how budget and adoption tiers interact in the
  workflow doc is filed as backlog if the operator wants it.
- **Cross-provider verification of the doc edits.** Per memory
  `feedback_ai_router_usage` (router restricted to end-of-session
  verification) and per spec cost projection ($0 metered), this
  set's deliverable is text-only documentation work. Operator
  review of the edited `adoption-bootstrap.md` is the canonical
  verification surface; if a fresh-eyes second opinion feels
  warranted at close-out, the $5 budget allows one ad-hoc
  consultation — but the default is operator-review-only.

---

## Acceptance criteria for Set 018 (revised)

- [x] `docs/adoption-bootstrap.md` has a new Step 4.5 introducing the
      adoption-tier choice (Lightweight / Full) with branching
      guidance.
- [x] Step 6 (Plan alignment) carries an explicit instruction to
      propose 2–4 cross-cut candidate organizations and the abstract
      pattern catalog as a reference.
- [x] Steps 7 and 9 acknowledge the lightweight branch (subset
      checklist, abbreviated closing pointers).
- [x] `docs/ai-led-session-workflow.md` has a short paragraph
      disambiguating *budget* tier from *adoption* tier.
- [x] `docs/session-sets/018-healthcare-accessdb-migration/spec.md`
      has a "Scope reshape (2026-05-07)" pointer at top.
- [x] Memory entries updated: `project_consumer_repos.md` (extend),
      `project_lightweight_tier_added_to_bootstrap.md` (new).
- [x] Set 018 close-out artifacts authored (`change-log.md`,
      `disposition.json`); close_session passes its gates.
- [x] No changes to `dabbler-homehealthcare-accessdb`. Verified.
- [x] No extension TypeScript changes; no version bump; no VSIX
      rebuild. Verified.

---

## Cost reconciliation

Original spec projection: **$0 metered.** Operator-set Set 018 budget:
**$5.00** (recorded at session start in [budget.json](budget.json)).
Plan above is text-only with no router calls. Optional close-out
consultation if operator wants a fresh-eyes review of the doc edits
sits within the $5 ceiling.

---

**Awaiting operator approval. After approval, edits land in the
order above (4a → 4b → 4c → 4d → 4e → 4f → 4g).**

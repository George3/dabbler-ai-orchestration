# Router-config editor — design alignment audit

You are being asked to review a proposed feature for an open-source
**AI-led-development workflow framework**. The operator wants
*general agreement* from three frontier models (Claude Opus 4.7, you,
and the other of GPT-5.4 / Gemini Pro) before any implementation
session begins. Your role is **independent design review** — concur,
dissent, or raise sharp edges the others may have missed.

You have **no shared context** with the prior conversation; everything
you need is below. Answer each numbered question with: **verdict
(concur / dissent / mixed)**, **reasoning**, and **concrete
suggestions** when applicable.

---

## 1. Framework context (so the design space is grounded)

**The repo** (`dabbler-ai-orchestration`) ships two consumer-facing
artifacts:

1. **`ai_router/`** — Python package on PyPI as `dabbler-ai-router`.
   Routes "reasoning" tasks (analysis, verification, review) from the
   orchestrator agent to the cheapest capable AI provider, enforces
   cross-provider verification, tracks per-session costs. Configured
   via two YAML files at the consumer project's repo root:
   - `ai_router/router-config.yaml` — models, tiers, routing
     thresholds, task-type overrides, generation params, verification
     map.
   - `ai_router/budget.yaml` — tier (`zero-budget` / `limited-budget`
     / `middle-tier` / `ample-budget`), `threshold_usd`,
     `threshold_scope` (currently default `project-lifetime`),
     `verification_method` (`api` / `manual-via-other-engine` /
     `skipped`).
2. **`tools/dabbler-ai-orchestration/`** — VS Code Marketplace
   extension (`DarndestDabbler.dabbler-ai-orchestration`, current
   v0.13.14). Contributes a Session Set Explorer tree view, cancel/
   restore lifecycle commands, an install/update ai-router command,
   a cost dashboard webview, a project-setup wizard webview, an
   adoption-bootstrap-prompt copy command. Currently contributes
   only four operator-tunable settings:
   `dabblerSessionSets.uatSupport.enabled` (`auto|always|never`),
   `dabblerSessionSets.e2eSupport.enabled` (`auto|always|never`),
   `dabblerSessionSets.e2e.testDirectory`, `dabblerSessionSets.pythonPath`,
   `dabblerSessionSets.aiRouterRepoUrl`.

**The session-set workflow** runs per-session by a single
orchestrator (Claude Code / Codex / Gemini Code Assist), one session
per conversation. Every session ends with a mandatory cross-provider
verification routed through `ai_router`. There are currently two
outsource modes declared per session-set in `spec.md`:

- **`outsourceMode: first`** (default, used by **every** session set
  in this repo to date) — synchronous per-call API providers.
- **`outsourceMode: last`** — queue-mediated daemon backed by a
  subscription CLI (Claude Code Max / Codex Max / Gemini Pro
  CLI). Documented in `ai_router/docs/two-cli-workflow.md`. No
  session set has ever declared this mode.

**Just-shipped Set 024** (commit `48aa8c8`, extension v0.13.14):
removed the Provider Queues + Provider Heartbeats tree views from
the extension. They were the only UI surface for the `outsourceMode:
last` workflow. The Python CLIs (`ai_router.queue_status`,
`ai_router.heartbeat_status`) stay so any operator running
outsource-last *in some other repo* can still invoke them from a
terminal.

**Operator's standing preferences** (lived experience from prior sets):

- Routing is currently restricted to **end-of-session
  cross-provider verification only** — mid-session routing is off
  by operator choice ("cost containment, until further notice").
- Operator does **not** want per-write prompts; batch-approve
  action checklists at the start of work is the preferred UX.
- Budget questions today are asked once per session set, not per
  session, and cumulative spend is reported in subsequent sessions
  rather than re-asked.
- Default to lowest-engagement bucket and require evidence to
  escalate.

These preferences are encoded as memory the orchestrator carries
into each session — not in any settings file the operator can edit
or share with collaborators.

---

## 2. The operator's UI sketch (verbatim, with one self-correction)

The operator drew up this rough form layout for the extension's
configuration surface (lightly cleaned for clarity):

```
Checkbox: Enable Pushover notifications at end of sessions?
Textbox:  Pushover API Key env var:           _________________
Textbox:  Pushover User Key env var:          _________________

Dropdown: AI Outsourcing
  [ Outsource with APIs always
  | Whenever helpful (let AI decide)
  | Only for Cross-Provider Verification
  | Never ]

Checkbox: Require human approval of outsourcing budget at the
          beginning of each session?

Checkbox: Suggest outsourcing when a significant decision must be
          made and cross-provider input is needed?

(Table of API keys — ideally rendered as a table, not a flat list.)
Textbox:  Gemini API Key env var:             _________________
Textbox:  Anthropic API Key env var:          _________________
Textbox:  Open AI API Key env var:            _________________
Textbox:  Other A AI API URL:                 _________________
Textbox:  Other A AI API KEY env var:         _________________
```

Self-corrections after the first pass:

- A second routing dropdown the operator initially sketched
  ("AI routing/outsourcing with AI APIs — Whenever Helpful | Ask
  Human in Session (with estimated cost) | Only for
  Cross-Provider Verification | Disabled") was a duplicate of the
  first one; treat them as **one** dropdown.
- The per-session budget approval checkbox should probably be a
  **dropdown** offering three scopes: per session / per session-set /
  per project — with **"optimally intrusive"** behavior (silent
  when there's headroom, prompts only when nearing/exceeding the
  cap).

---

## 3. The architectural recommendation under audit

The Claude Opus orchestrator already gave a position on this, which
you are being asked to concur with, dissent from, or refine:

> **Truth source.** Extension Settings (`package.json` contributions)
> only affect *extension* behavior; routing policy + budget + provider
> keys are actually read by Python `ai_router` out of
> `router-config.yaml` + `budget.yaml`. Putting these in `package.json`
> settings creates two sources of truth that can disagree — the
> extension reads one, the Python verifier reads another. The cleaner
> shape is: the YAML files stay canonical, and the extension grows a
> **custom-webview config editor** (the extension already ships a
> wizard webview, so the precedent exists) that reads/writes those
> YAML files. That also gives us the **table layout** the operator
> wanted for the multi-provider API-keys section — VS Code's native
> Settings UI does not render tables, only an awkward JSON-object
> input.

This recommendation is non-binding; both reviewing models should feel
free to argue for an alternative if they can defend it.

---

## 4. Audit questions

Please answer each. **Brevity is welcome** — verdict + 2–4 sentences
of reasoning + concrete suggestions where you have them. Cite
specifics from §1–§3 if it helps anchor your answer.

### Q1. Outsource-first vs outsource-last bucketing — does it still earn its keep?

The spec-level `outsourceMode: first | last` flag was introduced when
the queue-mediated daemon (subscription CLI) was the alternative
routing path. Set 024 just removed its only UI surface. No session
set has ever declared `outsourceMode: last`. Now that routing-mode
(synchronous-per-call vs. ask-in-session vs. verification-only vs.
disabled) is about to become per-project/per-session configurable
(Q3 below), is `outsourceMode` still earning its keep?

- (a) **Keep as orthogonal flag** — queue-mediated daemon is
  genuinely separate from "how often we route" and "which providers
  we use."
- (b) **Collapse into the new config matrix** — one source of
  routing truth instead of two flags that have to be reconciled.
- (c) **Deprecate entirely** — the recently-removed Provider Queues
  views were its only UI; no consumer has used it; remove the flag,
  remove `ai_router.queue_status` / `heartbeat_status`, remove
  `ai_router/docs/two-cli-workflow.md`.

What would *you* do if starting clean?

### Q2. Truth source — YAML-canonical + webview, vs. `package.json` settings, vs. hybrid?

The recommendation in §3 above is YAML-canonical + custom-webview
editor. Concur? If you'd argue for an alternative:

- A **hybrid** in which purely-extension-behavior settings (e.g.,
  notification toggles, view filters) stay in `package.json` while
  routing/budget/keys live in YAML?
- **Settings-only** with the extension writing through to YAML on
  change (and the YAML files becoming "exported" cache rather than
  canonical truth)?
- Something else?

Where do you draw the line on which dimensions are
"extension-only behavior" vs. "policy that Python reads too"?

### Q3. Budget-approval scope (per session / per session-set / per project) + "optimally intrusive" UX

Two sub-questions:

(a) **Operator-chosen scope.** Is a three-way operator choice the
right UX, or is one scope so dominant in practice that the other two
are noise? If you'd narrow it, which one wins and why?

(b) **"Optimally intrusive."** The goal is *prompt-only-when-needed*.
Candidate triggers:
- Hard cap with warn-at-percent grace zone (warn at 80%, block at
  100%) — operator-configurable percent.
- Per-call estimated-cost preview shown only when projected
  cumulative would cross the threshold.
- Tier-boundary crossings only (e.g., if a routed call would push
  spend from `limited-budget` into `middle-tier` territory).
- Combination of the above.

What's the failure mode of each? Which combination would *you* ship?

### Q4. "Suggest outsourcing on significant decisions" — heuristic feasibility

The operator wants a toggle for "suggest outsourcing when a
significant decision must be made and cross-provider input is
needed." Can the orchestrator self-detect "significance" reliably,
or does the heuristic become either (a) silent gating (false
negatives — orchestrator decides solo on something it shouldn't), or
(b) operator-noise (false positives — every minor refactor prompts)?

What signal would you base "significance" on? Examples to test
against:
- A schema change that affects three consumer repos: clearly
  significant.
- Renaming a variable in one function: clearly not.
- Choosing between two libraries for a new dependency: ???
- Deciding whether to add a defensive check: ???

If you don't think this heuristic can be made reliable, say so.

### Q5. Configurable API-key env-var names — real win, or YAGNI?

Some orgs mandate non-standard naming (e.g., this repo's
`AZURE_VSCODE_MARKETPLACE_TOKEN` precedent). Today the env vars
are **hardcoded**: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`OPENAI_API_KEY`. The operator wants these to be configurable
names. Real win, YAGNI, or something in between?

If you concur: where does the name-resolution live —
Python `ai_router` reading the YAML (so the daemon honors it
end-to-end), or also at the extension level (so the wizard / install
flow can detect missing keys), or both?

### Q6. Variable-length "other providers" table — schema + interaction with `router-config.yaml`

The operator wants the API-keys section rendered as a table so
"Other A," "Other B," etc. can be added without a fixed shape. The
existing `router-config.yaml` already has a `models:` block where
each model declares `provider`, `model_id`, `tier`, costs, and
`generation_params`. Is the new "other providers" table:

- (a) **A UI alias for the existing `models:` block** — operator
  adds a row, extension writes a new entry into `models:` with
  sensible tier defaults.
- (b) **A separate "extra providers" list** with its own schema —
  routes through `models:` at runtime via composition.
- (c) Something else entirely?

What schema should each row carry (API URL, env-var name,
display label, provider family / API protocol, default tier)?

### Q7. What's missing / sharp edges

Open-ended. What did the design surface miss? Candidates worth
considering — feel free to argue some are non-issues:

- **Per-workspace vs per-user scoping.** VS Code Settings naturally
  layer: user → workspace → folder. YAML files are workspace-scoped.
  Does the webview need to surface "this setting is overridden by
  workspace value X"?
- **Secret storage vs env-var-only.** Some orgs forbid storing
  secrets in env vars; they want VS Code's `secretStorage` API.
  Worth supporting now, or YAGNI?
- **Schema-validation feedback in the webview.** Bad YAML written
  by hand can break the daemon. Does the webview round-trip parse +
  validate before write?
- **YAML migration paths.** If schema changes (e.g., adding a
  field), does the webview run a forward migration on load?
- **Multi-orchestrator coordination.** If two engines (Claude /
  Codex / Gemini) hit the same project, they share the YAML. Does
  edit need locking?
- **Anything else.**

### Q8. Sequencing — one session-set or two?

The implementation is non-trivial: parse YAML, render a webview,
write YAML, validate, migrate, surface in the existing wizard, etc.

- (a) **One session-set covering audit + implementation.** Session 1
  is doc-only (this audit + synthesis); Sessions 2..N implement.
  Set 023 used this shape (Session 2 was a doc-only audit inside an
  otherwise-implementation set).
- (b) **Two session-sets.** Audit-only set (this) lands as a single
  proposal document; a separate implementation set is spec'd
  later, after the operator has had time to digest. Operator pace
  is preserved.
- (c) **Three.** Audit set → spec-authoring set → implementation
  set. Probably overkill but worth naming.

Where would *you* draw the boundaries?

---

## 5. Output format request

A markdown document with one section per question (Q1..Q8). Each
section begins with `### Verdict: concur | dissent | mixed`, then
2–4 sentences of reasoning, then a bulleted list of concrete
suggestions (if any). Close with `### Overall: is the design ready
to spec?` (yes / yes-with-conditions / not-yet — with the gating
conditions named).

No need to be exhaustive — be the senior reviewer who'd push back
on something specific rather than a yes-everything reviewer.

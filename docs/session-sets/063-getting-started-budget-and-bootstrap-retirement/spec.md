# Getting Started Budget Step + Adoption-Bootstrap Retirement Spec

> **Purpose:** Consolidate onboarding on the Getting Started form by
> (1) adding the one capability the form lacks — the Full-tier
> **budget / not-to-exceed (NTE) step** that writes `ai_router/budget.yaml`
> — and (2) retiring the parallel "Copy adoption bootstrap prompt" path,
> whose welcome-view button has been unreachable since Set 060 (the host
> always sends a `gettingStarted` block, so the webview's welcome
> fallback never renders; the prompt survives only as a command-palette
> command). One onboarding path, one set of docs, no dual-path drift.
> **Created:** 2026-06-12
> **Session Set:** `docs/session-sets/063-getting-started-budget-and-bootstrap-retirement/`
> **Prerequisite:** None (Set 062 closed; the Getting Started form is
> the shipped 0.29.0+ surface this set extends).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification
> **Origin:** Operator decision 2026-06-12 ("the only unique thing it
> brings to the table is the budget dialog. If we address that in the
> UI approach — and we should — do we need the non-UI approach?"),
> after the README rewrite surfaced that the bootstrap button is
> already invisible in the UI.

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: true
requiresE2E: false
uatStyle: ad-hoc
uatScope: per-set
totalSessions: 3
```

> Rationale: the budget step is a **webview form change** — the layer
> the mechanical test stack (vscode-stub) cannot fully exercise (the
> standing Set 058 lesson) — so `requiresUAT: true`, ad-hoc, per-set,
> walked on a local build before any publish. `requiresE2E: false`:
> the Layer-3 Playwright smokes already pin the form's rendering
> (`loading-state.spec.ts`, `session-sets-tree.spec.ts`, post-CI-repair),
> and webview *interactions* are non-deterministic under Playwright
> (Set 052 precedent); deterministic unit tests on the budget-writer
> and form-state helpers plus the ad-hoc UAT are the gates. Layer 3 is
> part of "suite green" for this set's scope (2026-06-12 lessons-learned
> entry) — run `npm run test:playwright` locally before every close.

---

## Project Overview

### Motivation

Set 060 made the staged Getting Started form the onboarding path a new
user actually sees; the older conversational path ("Copy adoption
bootstrap prompt" → the agent fetches `docs/adoption-bootstrap.md` and
drives setup chat-side) was kept in parallel. Two findings from the
2026-06-12 README pass changed the picture:

1. **The bootstrap button is dead UI.** The viewsWelcome content that
   hosted it only renders through the webview's old-host fallback
   (`client.js`: welcome HTML when the snapshot carries no
   `gettingStarted` block) — and the current host always sends one. The
   command remains reachable solely via the command palette, so
   real-world usage of the conversational path is approximately zero.
2. **The only capability the form lacks is the budget dialog.** The
   bootstrap flow's Full-tier budget-threshold step (set an NTE dollar
   cap; `$0` = the explicit zero-budget opt-out recorded in
   `budget.yaml`, which `disposition.py` treats as manual-review mode)
   has no form equivalent — the form scaffolds `router-config.yaml`
   (and `budget.yaml`?) without asking.

Dual onboarding paths have already cost doc rot once (the README
described the dead button for two releases). Consolidating on the form
removes the drift surface; the remote-fetched
`docs/adoption-bootstrap.md` chain (a raw-URL dependency that can drift
from shipped form behavior) gets a deliberate disposition instead of
indefinite parallel life.

### Known audit surface (starting inventory — Session 1 completes it)

- **Extension:** `src/commands/copyAdoptionBootstrapPrompt.ts` (fetches
  raw `docs/adoption-bootstrap.md`); the `dabbler.copyAdoptionBootstrapPrompt`
  command contribution; the dead viewsWelcome `contents` in
  `package.json`; `loadWelcomeHtmlFromPackageJson` + `welcomeHtml`
  plumbing in `CustomSessionSetsView.ts`; the `client.js` welcome
  fallback branch + `.welcome` CSS; the Marketplace `description` field
  ("…and adoption-bootstrap entry point…"); related unit tests.
- **Budget contract:** `ai_router/budget.yaml` is read by
  `disposition.py` (zero-budget opt-out semantics), migrated by
  `migrate_router_config.py`, edited by the visual config editor, and
  scaffolded Full-only (Set 058 D3). The form's writer must emit a
  shape all three accept.
- **Docs:** `docs/adoption-bootstrap.md` itself; `docs/quick-start.md`
  (≥5 references); `README.md` (extension — already demoted to a
  one-liner 2026-06-12; root README if it references the path);
  `docs/repository-reference.md`; consumer-repo instruction files that
  may cite the bootstrap prompt (audit across the consumer list).

### Design intents (Session 1 locks the details)

- **D1 — budget step in the form (Full tier only).** An inline budget /
  NTE input in the Build-project-structure step (beside the existing
  no-API-key warning pattern): validated dollar amount, explicit `$0`
  semantics copy (manual cross-provider review, no API spend on
  verification), written to `ai_router/budget.yaml` in the
  scaffold-accepted shape. Lightweight never shows it (no router
  config, no budget file — Set 058 D3 divergence stays the sole one).
- **D2 — retire the conversational bootstrap path in the extension.**
  Command + dead welcome plumbing removed per the locked inventory;
  the Set 029-era welcome-HTML pipe goes with it unless the audit
  finds a live consumer.
- **D3 — deliberate disposition for `docs/adoption-bootstrap.md`.**
  Locked at Session 1, not assumed: either retire with redirects to
  quick-start/form docs, or explicitly re-scope as the
  manual/non-VS-Code setup reference (it is referenced by quick-start
  as a standalone path today). Whatever is chosen, no doc may keep
  describing the dead button.
- **D4 — release.** Marketplace **0.31.0 → 0.32.0** through the
  green-Test gate. PyPI only if the audit finds the budget contract
  needs a router-side change (none expected; note it in the S1 lock
  either way).

### Non-goals

- No redesign of the Getting Started form beyond the budget step.
- No change to budget enforcement semantics in the router — the form
  writes the same contract the bootstrap dialog wrote; `disposition.py`
  behavior is unchanged.
- No removal of `docs/adoption-bootstrap.md` without the D3 disposition
  (history and consumer references get redirects, not 404s).
- No consumer-repo file edits beyond what the audit shows actually
  references the retired path (and those via the established
  cross-repo-notice pattern if needed).

---

## Sessions

### Session 1 of 3: Audit & design-lock

**Goal:** Complete the retirement inventory and budget-contract audit
empirically; lock D1–D4.
**Steps:**
1. Inventory every surface that references the adoption-bootstrap path
   (extension code/contributions/tests, docs in this repo, consumer-repo
   instruction files) — record findings with file:line in the session
   notes; confirm empirically that the welcome fallback is unreachable
   with the current host (and note the one path that could resurrect
   it, if any).
2. Audit the `budget.yaml` contract: exact shape the bootstrap flow
   writes today, what `disposition.py` reads (zero-budget opt-out),
   what `migrate_router_config.py` migrates, what the config editor
   expects, and what the Set 058 scaffold emits. Decide whether the
   form's writer is pure-TS or shells to an existing Python writer.
3. Lock D1 (input placement, validation, `$0` copy, write timing),
   D2 (the per-surface retirement list), D3 (adoption-bootstrap.md
   disposition), D4 (release scope: Marketplace-only or +PyPI).
   Route a cross-provider design consult if any lock is contested.
4. Cross-provider verification of the audit record.
**Creates:** `s1-audit.md` (inventory + contract findings + locks).
**Touches:** nothing in shipping code (audit-only session).
**Ends with:** every D1–D4 question answered with file-level evidence;
suite untouched and green.
**Progress keys:** `session-001/inventory`, `session-001/budget-contract`,
`session-001/design-lock`, `session-001/verified`.

### Session 2 of 3: Implement — budget step in, bootstrap path out

**Goal:** Ship D1 and D2 per the locks.
**Steps:**
1. Budget step in the Getting Started form: render (gettingStartedHtml.js
   + tree.css as needed), control state + message wiring (client.js →
   `gettingStartedAction`), handler writing `ai_router/budget.yaml`
   (gettingStartedActions.ts) on the Full path only; inline validation
   and `$0` semantics copy per the D1 lock.
2. Retire the bootstrap surfaces per the D2 list (command, contribution,
   viewsWelcome contents, welcome plumbing, CSS, Marketplace
   description phrase); update or remove their tests.
3. Tests: budget-writer unit matrix (amounts, `$0`, invalid input,
   Lightweight-never-writes, shape accepted by the audited readers),
   form-state rendering tests, golden updates if the cold-start
   snapshot is touched.
4. Full suites green — TS unit, Python, AND Layer 3 locally
   (`npm run test:playwright`; the welcome-fallback removal touches the
   surfaces those smokes pin).
5. Cross-provider verification (point the verifier at the D1 contract
   audit and the D2 inventory).
**Creates:** budget-step module/tests per the lock.
**Touches:** `package.json`, `src/providers/CustomSessionSetsView.ts`,
`media/session-sets-tree/client.js`, `media/session-sets-tree/gettingStartedHtml.js`,
`src/commands/gettingStartedActions.ts`,
`src/commands/copyAdoptionBootstrapPrompt.ts` (removed), tests.
**Ends with:** a Full-tier user sets the budget in the form and
`budget.yaml` lands in the audited shape; the bootstrap command no
longer exists; all three suites green.
**Progress keys:** `session-002/budget-step`, `session-002/retirement`,
`session-002/tests`, `session-002/verified`.

### Session 3 of 3: Docs sweep, UAT, release 0.32.0

**Goal:** Execute D3, walk the UAT gate, ship through the green-Test
release gate.
**Steps:**
1. Docs sweep per the D3 lock: `docs/adoption-bootstrap.md` disposition,
   `docs/quick-start.md` references, extension README Get-started
   alternative paragraph, root README, `docs/repository-reference.md`
   file map, consumer-notice doc if the audit found consumer references.
2. Author `063-getting-started-budget-and-bootstrap-retirement-uat-checklist.json`
   (per-set, ad-hoc): pre-verify every mechanically-covered row
   (named `ProgrammaticVerification`), keep the operator walk short —
   the form's budget step on a fresh empty folder (Full: input,
   validation, `$0` copy, `budget.yaml` on disk; Lightweight: step
   absent), bootstrap command absent from the palette, no welcome
   regression in the Explorer. Build the local `.vsix`; **operator UAT
   on the local build is the pre-publish gate.**
3. On pass: bump to **0.32.0** (package.json + lock + CHANGELOG naming
   the budget step and the retirement), `repository-reference.md` in
   pre-push wording; PyPI bump only if S1 locked a router-side change.
4. Cross-provider verification (state the suite baseline and the
   release contract up front in R1 — the Set 062 calibration);
   close-out (final session → `change-log.md`).
5. Tag push(es) only with explicit operator authorization; the
   `require-green-test` gate must pass; record run ids post-publish.
**Touches:** docs per sweep, version files, the set's UAT checklist.
**Ends with:** one onboarding path, documented everywhere it matters;
0.32.0 published (or held for the operator's tag push) through the
green-Test gate.
**Progress keys:** `session-003/docs-sweep`, `session-003/uat-checklist`,
`session-003/operator-uat-passed`, `session-003/versions-bumped`,
`session-003/verified`, `session-003/change-log-written`.

---

## End-of-set deliverables

- A Full-tier budget / NTE step in the Getting Started form writing
  `ai_router/budget.yaml` in the contract shape `disposition.py`, the
  config editor, and the migrator all accept (D1).
- The adoption-bootstrap extension path fully retired: command,
  contribution, dead viewsWelcome content, and welcome-fallback
  plumbing removed; tests updated (D2).
- A deliberate, documented disposition for `docs/adoption-bootstrap.md`
  with every referencing doc updated (D3).
- A passed per-set ad-hoc UAT on a local build, and Marketplace
  **0.32.0** released through the green-Test gate (D4).

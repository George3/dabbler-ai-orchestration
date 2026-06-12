# Set 063 Session 1 — Audit & design-lock record

> **Session:** 1 of 3 (`063-getting-started-budget-and-bootstrap-retirement`)
> **Date:** 2026-06-12
> **Orchestrator:** Claude Code (`claude-fable-5`, effort high)
> **Method:** empirical (Grep/Read at file:line across the repo and all three
> consumer repos), plus a routed cross-provider design consult on the two
> contested locks (gpt-5-4 + gemini-pro, identical prompt; raw outputs at
> `s1-design-consult-gpt-5-4.md` / `s1-design-consult-gemini-pro.md`).
> **Touches:** nothing in shipping code (audit-only).

---

## 1. Retirement inventory (D2 input) — every live surface, file:line

### 1.1 Extension code (removed in S2)

| # | Surface | Evidence |
|---|---|---|
| 1 | Command implementation (fetch-raw-URL clipboard prompt) | `tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts` (whole file, 21 lines; the prompt constant embeds the raw GitHub URL of `docs/adoption-bootstrap.md`) |
| 2 | Command registration | `tools/dabbler-ai-orchestration/src/extension.ts:13` (import), `:295-296` (`safeRegister`) |
| 3 | Command contribution | `tools/dabbler-ai-orchestration/package.json:184-187` (`dabbler.copyAdoptionBootstrapPrompt`, title "Copy adoption bootstrap prompt") |
| 4 | Dead `viewsWelcome` contribution (the unreachable button) | `tools/dabbler-ai-orchestration/package.json:63-68` (view `dabblerSessionSets`, `when: "dabblerSessionSets.scanState == ready"`, contents embed both the bootstrap command link and an Open Get Started link) |
| 5 | Welcome-HTML pipe, host side | `src/providers/CustomSessionSetsView.ts:196` (`welcomeHtml` field), `:213` (constructor init), `:477` (snapshot payload), `:656-696` (`loadWelcomeHtmlFromPackageJson` + `renderWelcomeMarkdown`), `:746-757` (`escHtml`/`escAttr` — only callers are the welcome path; expected to die with it, confirm at compile in S2) |
| 6 | Welcome-HTML pipe, protocol | `src/types/sessionSetsWebviewProtocol.ts:133-139` (`welcomeHtml` on `SnapshotPayload`) and `:140-145` (`gettingStarted` optionality that exists only to model pre-Set-060 hosts) |
| 7 | Welcome fallback branch, webview | `media/session-sets-tree/client.js:122-128` (fires only when `!gs && !hasAnySets`), comment `:108-112` |
| 8 | `.welcome` CSS | `media/session-sets-tree/tree.css:42-53` |
| 9 | `scanState` **context key** publication | `src/providers/scanState.ts:43` (`CONTEXT_KEY = "dabblerSessionSets.scanState"`), `:72` (`setContext`). Sole consumer is the `viewsWelcome.when` clause (package.json:66) — no other `when` clause, test, or code reads it (repo-wide grep). The ScanState **manager itself stays**: the webview protocol's `scanState` messages (`postScanState`, loading sentinel) are a live consumer. |
| 10 | Marketplace description phrase | `tools/dabbler-ai-orchestration/package.json:4` — "…and adoption-bootstrap entry point…" |
| 11 | Stale comments (no behavior) | `src/extension.ts:96,101,392`; `src/providers/scanState.ts:12-20`; `src/test/suite/activationNoFolder.test.ts:172`; Playwright comments `src/test/playwright/loading-state.spec.ts:2,87`, `session-sets-tree.spec.ts:149`, `electronLaunch.ts:667` |

**Tests:** no mocha unit test asserts the welcome HTML or the bootstrap
command (repo grep over `src/test/suite`); the Layer-3 specs
(`loading-state.spec.ts:61-106`, `session-sets-tree.spec.ts`) already assert
the **new** Getting Started form and reference the old state only in
comments. Retirement therefore requires comment touch-ups, not assertion
rewrites; golden/cold-start fixtures pin the form, not the welcome state.

### 1.2 Docs in this repo (D3-dependent sweep targets, S3)

| Doc | References |
|---|---|
| `README.md` (root) | §"For new projects: adoption bootstrap" (lines 134-157) |
| `tools/dabbler-ai-orchestration/README.md` | lines 103-108 ("Prefer a fully conversational setup instead?…") — the post-2026-06-12 demoted one-liner |
| `docs/quick-start.md` | lines 34, 49, 174, 190, 254 (incl. "standalone path" phrasing at 254) |
| `docs/repository-reference.md` | line 512 (commands file-map row names `copyAdoptionBootstrapPrompt`), line 528 (adoption-bootstrap.md file-map row) |
| `docs/concepts/tier-model.md` | lines 4, 149, 197 |
| `docs/ai-led-session-workflow.md` | lines 95, 102-103, 113 (budget threshold "recorded during the adoption-bootstrap flow"; "see schema in docs/adoption-bootstrap.md") |
| `docs/adoption-bootstrap.md` | the doc itself (D3) |

Historical artifacts (session-set folders, CHANGELOGs, `dist/`) are never
edited and are excluded from the sweep by convention.

### 1.3 Consumer repos

Zero references. Audited `dabbler-access-harvester`, `dabbler-platform`,
`dabbler-homehealthcare-accessdb` (the consumer list per
`docs/repository-reference.md:54-60`) for `adoption.bootstrap` across
`*.md/*.json/*.yaml`: the only hits are vendored
`.venv/Lib/site-packages/ai_router/{budget.yaml,CHANGELOG.md}` copies of the
published package — not consumer instruction files. **No cross-repo notice
is needed for this set.**

### 1.4 Unreachability proof + the one resurrection path

- `postSnapshot()` (`CustomSessionSetsView.ts:474-479`) always populates
  `gettingStarted: this.buildGettingStarted(all)`.
- `buildGettingStarted` (`:555-567`) delegates to `computeGettingStarted`
  (`src/utils/gettingStartedDetection.ts:205-218`), whose mode comes from
  `selectExplorerMode` (`:183-186`) — a total function returning exactly
  `no-folder | getting-started | list`. No path returns `null`/`undefined`.
- The webview's welcome branch (`client.js:122`) requires `!gs`. With the
  current host the snapshot always carries `gs`, so the branch — and the
  `viewsWelcome` contents it renders — is dead. The palette command was the
  only live entry point.
- **Resurrection path:** the protocol type still permits
  `gettingStarted?: GettingStartedPayload | null`
  (`sessionSetsWebviewProtocol.ts:145`), so a future host-side regression
  that ships a null block would silently revive the welcome fallback. D2
  therefore includes making `gettingStarted` **required** on
  `SnapshotPayload` when the fallback is removed (type-level closure).

---

## 2. budget.yaml contract audit (D1 input)

### 2.1 Writers

- **Chat-side bootstrap flow** (being retired) was the only writer; it
  writes the schema documented at `docs/adoption-bootstrap.md:494-509`:
  `threshold_usd`, `threshold_scope`, `mode`, `verification_method`,
  `verification_nte_usd`, `set_at`, `set_by`, `notes`. **This is the
  PRE-migration shape** (see 2.2).
- **The Getting Started form / scaffold writes no budget.yaml today.** The
  Full-tier scaffold materializes only `ai_router/router-config.yaml` from
  the installed wheel (`src/utils/aiRouterInstall.ts:425-447`,
  `ROUTER_CONFIG_REL` at `:23`); Lightweight removes it
  (`src/commands/gitScaffold.ts:96-108`). The spec's open question "(and
  budget.yaml?)" is answered: **no** — the form's budget step will be the
  file's first and only extension-side writer.
- The published wheel incidentally ships *this repo's own*
  `ai_router/budget.yaml` as package data (visible in consumer
  site-packages). The installer never materializes it into workspaces (only
  `router-config.yaml`), so it is inert — a pre-existing packaging quirk,
  noted, not in scope.

### 2.2 Migrator — `ai_router/migrate_router_config.py:_migrate_budget` (lines 131-189)

- `threshold_scope` → `scope` via `_SCOPE_MAP`: `project-lifetime` →
  `per-project`; `per-project`/`per-session-set`/`per-session` pass through;
  `monthly` → `scope: per-project` + `period: monthly` (with deprecation
  warning). Unrecognized values warn and are left as-is.
- Injects `warn_at_percent: 80` when absent.
- Idempotent; comment-preserving (ruamel). **Post-migration canonical shape
  therefore uses `scope` (+ optional `period`) and `warn_at_percent` — not
  `threshold_scope`.**

### 2.3 Readers

- **Python runtime: none.** `disposition.py` references budget.yaml only in
  docstrings (lines 15, 84 — the `skipped` verification method *is recorded
  in* budget.yaml); `close_session.py:349` likewise prose-only. No
  `ai_router` code parses the file at runtime. The "reader" at Step 6 of the
  workflow is the orchestrator (AI) following
  `docs/ai-led-session-workflow.md:159-184` procedurally.
- **Config editor** (`src/configEditor/`): `BUDGET_SCHEMA`
  (`schemaValidator.ts:116-133`) — **requires `threshold_usd`**; validates
  `scope` (enum `per-session-set | per-project | per-session`),
  `warn_at_percent` (int 0-100), `verification_method` (enum
  `api | manual-via-other-engine | skipped`), `verification_nte_usd`
  (number ≥ 0), `mode` (string); **open schema** — legacy fields (`set_at`,
  `set_by`, `notes`) coexist (comment at `:114-115`). The editor reads/writes
  `threshold_usd`, `scope`, `warn_at_percent` (`sections/budgetSection.ts`)
  and `verification_method` (`sections/routingAndVerificationSection.ts`);
  patch paths at `patch.ts:100-136`.
- **This repo's live file** (`ai_router/budget.yaml`) is already
  post-migration shape (`scope: per-project`, `warn_at_percent: 80`).

### 2.4 Contract conclusion (the shape the form's writer must emit)

```yaml
threshold_usd: <number >= 0>          # required by the editor schema
scope: "per-project"                  # post-migration key; editor enum
mode: <derived>                       # 0 -> zero-budget; <20 -> limited-budget;
                                      # 20-99 -> middle-tier; 100+ -> ample-budget
verification_method: <api | manual-via-other-engine | skipped>
verification_nte_usd: <threshold_usd> # explicit, = threshold default
set_at: "<ISO-8601 local with offset>"
set_by: "getting-started-form"
warn_at_percent: 80
```

Field-semantics evidence (each a documented contract, not invention):

- **`mode` bands** — the documented `threshold_usd` → `mode` mapping table
  at `docs/adoption-bootstrap.md:515-522` (`0` → `zero-budget`; `>0 and <20`
  → `limited-budget`; `20-99` → `middle-tier`; `100+` → `ample-budget`).
- **`verification_nte_usd` defaults to `threshold_usd`** —
  `docs/adoption-bootstrap.md:503-504` ("defaults to threshold_usd if
  absent") and `:524`; restated at `docs/ai-led-session-workflow.md:175-180`.
  The writer emits it explicitly so no reader needs the default.
- **`verification_method` enum** — editor schema
  (`schemaValidator.ts:126-129`) and `docs/adoption-bootstrap.md:523`.
- **`warn_at_percent: 80`** — the migrator's own injected default
  (`migrate_router_config.py:184-187`).

No `threshold_scope`, no `period`, `notes` omitted (the form doesn't collect
it). This makes the migrator a no-op and passes the editor schema verbatim.
**Companion doc defect (folded into D3):** `docs/adoption-bootstrap.md`
currently publishes the pre-migration shape as canonical; the relocated
schema doc must publish the post-migration shape (with legacy-compat notes).

---

## 3. Cross-provider design consult

Identical prompt to **gpt-5-4** ($0.3488 per the metrics log; 23,020 output
tokens) and **gemini-pro** ($0.0088); raw outputs saved unedited alongside
this file.

| Q | gpt-5-4 | gemini-pro | Outcome |
|---|---|---|---|
| Q1 D3 disposition | (a) retire as onboarding path; URL-stable compatibility stub; new `docs/budget-yaml-schema.md` canonical | (a) same, same new doc | **CONVERGED** |
| Q2 D1 $0 sub-choice | (i) required inline choice, no silent default | (ii) default `manual-via-other-engine` + copy | **SPLIT** — resolved to (i), see below |
| Q3 writer shape | Confirm (+ publish normalized shape in docs) | Confirm, no defects | **CONVERGED** |

**Q2 resolution rationale (orchestrator synthesis):** the workflow doc's
zero-budget tier is explicit that the method is the **operator's pick**
(`docs/ai-led-session-workflow.md:107-110` — "(a) `manual-via-other-engine`
OR (b) `skipped` — operator picks"). The retired bootstrap dialog asked; a
form that silently defaults would write a policy the operator never chose
and weaken the Rule-2 exception's audit trail. Gemini's friction argument is
scoped to exactly the operators who must make this call anyway (the choice
renders only when the value is 0). Locked to (i); gemini-pro's dissent is
recorded here for the verifier and the operator (overridable before S2).

---

## 4. Design locks

### D1 — budget / NTE step in the Getting Started form (LOCKED)

- **Placement:** inline in the Build-project-structure step, rendered on
  **Full tier only**, beside the existing no-API-key warning pattern
  (`gettingStartedHtml.js` render; state + `data-gs-action` wiring in
  `client.js`; write in `gettingStartedActions.ts` on the Full path).
  Lightweight never renders the input and never writes the file (Set 058 D3
  divergence remains the sole one).
- **Input + validation:** required dollar amount; numeric, `>= 0`; reject
  negative / non-numeric / empty with inline validation that blocks the
  Build action on Full until valid. Placeholder example: `25`.
- **$0 semantics (consult-resolved, option i):** when the parsed value is
  `0`, reveal a required inline radio pair — "Check in another engine"
  (`manual-via-other-engine`) / "Skip verification" (`skipped`) — with copy:
  *"A $0 budget still needs a verification rule. Choose whether to check
  each session in another engine or skip verification."* No silent default;
  Build stays blocked until one is picked. Values `> 0` write
  `verification_method: "api"` with no extra control.
- **Write timing:** written by the Build-project-structure handler at
  scaffold time, Full only; **never clobbers** an existing
  `ai_router/budget.yaml` (skip + report, matching the scaffold's
  no-clobber convention at `gitScaffold.ts:65-67`).
- **Writer:** pure TypeScript (no Python writer exists; matches the
  extension's pure-TS-twin pattern), emitting exactly the §2.4 shape.
- **Tests (S2):** writer unit matrix — amounts across all four mode bands,
  `$0` with each method, invalid input, Lightweight-never-writes,
  no-clobber, shape accepted by the editor schema validator and a no-op
  under `_migrate_budget` (Python-side assertion optional; the TS twin of
  the shape check is the floor).

### D2 — retirement list (LOCKED)

Remove items 1-10 of §1.1 plus comment touch-ups (item 11). Specifically
including:

- the `viewsWelcome` contribution **and** the now-consumerless
  `dabblerSessionSets.scanState` context-key publication
  (`scanState.ts:43,72`) — the ScanState manager and the webview
  `scanState` protocol messages stay;
- the whole welcome-HTML pipe (host loader/renderer, protocol field,
  client.js fallback branch, `.welcome` CSS); `escHtml`/`escAttr` go if the
  compiler confirms no surviving caller;
- `gettingStarted` becomes **required** on `SnapshotPayload` (closes the
  §1.4 resurrection path);
- package.json `description` drops "and adoption-bootstrap entry point"
  (reworded to name the Getting Started form as the onboarding entry);
- Marketplace-visible command count drops by one (`dabbler.copyAdoptionBootstrapPrompt`).

Suites: TS unit + Python + **local `npm run test:playwright`** before the S2
close (the rip touches the surfaces the Layer-3 smokes pin).

### D3 — `docs/adoption-bootstrap.md` disposition (LOCKED, consult-converged)

**Retire-with-redirects via a URL-stable compatibility stub:**

1. Rewrite `docs/adoption-bootstrap.md` to a short deprecation/redirect stub
   (absolute URLs): VS Code users → the extension's Getting Started form;
   non-VS-Code / manual setup → `docs/quick-start.md` + the schema doc
   below. The path stays alive because extension versions ≤ 0.31.0 fetch
   the raw URL at click time (no 404 — the set's non-goal).
2. Create **`docs/budget-yaml-schema.md`** as the canonical budget.yaml
   contract home, documenting the **post-migration** shape (§2.4) with
   legacy-compat notes. Each compat rule is already documented or directly
   derived, with evidence:
   - `threshold_scope` → `scope` and `monthly` → `per-project` +
     `period: monthly`: the migrator's `_SCOPE_MAP`
     (`migrate_router_config.py:131-138`).
   - absent `verification_method` → `api`: the compatibility rule at
     `docs/ai-led-session-workflow.md:117-123` and
     `docs/adoption-bootstrap.md:523`.
   - absent scope → `per-project`: **derived**, marked as such — the
     documented legacy default "absent `threshold_scope` →
     `project-lifetime`" (`docs/ai-led-session-workflow.md:117-123`,
     `docs/adoption-bootstrap.md:514`) composed with the migrator's
     `project-lifetime` → `per-project` mapping
     (`migrate_router_config.py:132-133`).
3. Sweep every §1.2 reference: quick-start drops the bootstrap-prompt path
   from mainline flow (gains a brief "Without VS Code" manual-setup note),
   workflow doc's schema pointer retargets to the new doc, root README
   §134-157 is rewritten around the form, extension README drops the
   "conversational setup" paragraph, repository-reference rows updated,
   tier-model references updated.

### D4 — release scope (LOCKED)

**Marketplace 0.31.0 → 0.32.0 only; no PyPI bump.** Evidence: no Python
runtime reader of budget.yaml exists (§2.3); `disposition.py`,
`migrate_router_config.py`, and every other packaged `ai_router/*` surface
are untouched by D1-D3 (the new/changed docs live under repo-level `docs/`,
which is not packaged). Through the `require-green-test` gate per the
standing release prerequisite.

---

## 5. Session conformance

- Shipping code untouched (audit-only); suites run at close to confirm the
  green baseline (results recorded in the activity log / close artifacts).
- Routed calls this session: 1× `analysis` (ai-assignment authoring), 2×
  `architecture` (design consult), 1× `session-verification` (Step 6).
- Progress keys: `session-001/inventory`, `session-001/budget-contract`,
  `session-001/design-lock`, `session-001/verified`.

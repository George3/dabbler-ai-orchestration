# Getting Started Redesign (extension 0.29.0)

> **Purpose:** Replace the command-palette/QuickPick "Set up a new project" flow
> with a **stateful, two-panel Getting Started**: an interactive form embedded
> in the **Session Set Explorer** that drives setup with live progress and
> inline validation, paired with **static step-by-step instructions** in the
> editor pane. The form removes the unwanted "title of the first session set"
> prompt and makes the path from a fresh repo to a running first session
> obvious and self-validating.
> **Session Set:** `docs/session-sets/060-getting-started-redesign/`
> **Created:** 2026-06-10
> **Workflow:** Full
> **Prerequisite:** Set 059 complete (its activation fix — the view rendering
> with no folder / no session sets — is the foundation this form sits on).
> **Design input:** operator mockup
> [`docs/planning/getting-started-instructions.svg`](../../planning/getting-started-instructions.svg)
> and the operator-approved design lock below (2026-06-10).

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: true
requiresE2E: false
uatScope: per-set
uatStyle: ad-hoc
totalSessions: 4
```

> Rationale: this is an interactive VS Code **webview + activation** redesign —
> the layer the mechanical test stack (`vscode-stub`) can only partially cover,
> and the exact layer where the 0.28.0 defects shipped. `requiresUAT: true`
> because the deliverable is a human-attestable flow ("a fresh operator gets
> from an empty folder to a running first session with no dead-ends, correct
> progress, and correct validation") that must be walked on a **local build
> before any publish** (the hard lesson from Set 058/059). `requiresE2E: false`
> — Session Set Explorer webview form actions are non-deterministic under
> Playwright (Set 052 precedent); the ad-hoc operator UAT is the gate. Ships a
> Marketplace release (**0.29.0**), which also carries the held Set 059
> activation fix.

---

## Project Overview

### Motivation

The published 0.28.0 onboarding is a Command-Palette wizard + a QuickPick
scaffolder that prompts for a folder and a session-set title, with no progress
feedback and no validation. Operator UAT rejected it: the title prompt is
unwanted, there's no sense of "what's done / what's next," and Full-tier setup
can silently lack API keys. The operator's redesign (the SVG mockup) makes the
**Session Set Explorer itself** the setup surface, with live progress and
guardrails, backed by static teaching instructions in the editor.

### The shape (from the mockup)

- **Session Set Explorer — dual mode.** No session sets in the workspace →
  render the **Getting Started form**. One or more sets → the normal session-set
  **list** (today's behavior). No folder open → an **"Open or create a project
  folder"** state.
- **Editor pane — static instructions.** A 5-step Getting Started document
  (Scaffold Project Structure · Create/Import Project Plan · Decompose Plan Into
  Session Sets · Start the First Session · Trust But Verify), copy lifted ~
  verbatim from the operator's SVG. Static — no live checkmarks here.
- **Form controls (live state lives ONLY here).** Three steps, each greying out
  with a green check when complete:
  1. **Build project structure** + a Full / Lightweight radio.
  2. **Import project-plan.md** (file picker) **OR Copy prompt for planning**.
  3. **Build session sets** (copies a decomposition prompt) + a "Create parallel
     session sets where possible" checkbox.

### Non-goals

- **No change to the scaffolding content** (the Set 058 shared writer, template
  bundle, cold-start chain, drift guards stay as-is — this set changes *how the
  scaffold is triggered and presented*, not what it writes).
- **No inline AI decomposition.** "Build session sets" copies a prompt (D4); it
  does not call the router to decompose `project-plan.md`.
- **No new tier semantics.** Full/Lightweight is unchanged; the radio just feeds
  the existing scaffolder.

---

## Design Lock (operator-approved 2026-06-10)

- **D1 — Dual-mode Explorer.** The Session Set Explorer renders the Getting
  Started **form** when the workspace has no session sets, and the session-set
  **list** otherwise. (Builds on the Set 059 fix that makes the view render with
  no folder / no sets.)
- **D2 — Live state in the form only.** Completion greys out + green-checks the
  step in the **form**; the editor instructions are **static** (no checks).
- **D3 — Completion detection rules.** Step 1 complete = `.venv` +
  `dabbler-ai-router` importable + all three engine files present; Step 2 =
  `docs/planning/project-plan.md` exists; Step 3 = ≥1 `docs/session-sets/NNN-*/`.
- **D4 — "Build session sets" copies a prompt** (the existing decomposition
  prompt), not an inline router call.
- **D5 — Folder model (easiest UX).** Build into the **open** workspace folder;
  if none is open, the form shows **"Open or create a project folder"**
  (`showOpenDialog` → `vscode.openFolder`) and then presents the build steps. No
  mid-build window reload forced on the user; **no "session-set title" prompt.**
- **D6 — Env-var validation (Full tier).** Check `process.env` (which merges
  Windows **System + User** vars) for at least one of `ANTHROPIC_API_KEY` /
  `OPENAI_API_KEY` / `GEMINI_API_KEY`. If absent, show a warning **under the
  Build button**: keys are needed for Full, set the var **and reload the window**
  (a var set after launch isn't visible until reload). Lightweight shows no such
  warning.
- **D7 — Parallel checkbox info.** When "Create parallel session sets where
  possible" is checked, show an info note: the AI orchestration uses **git
  worktrees** for parallel session sets, merged back to the main branch when the
  sets complete.
- **D8 — Teaching copy** is lifted ~verbatim from the SVG into the instructions
  doc (the tier explanation, the per-step guidance, "trust but verify").

---

## Sessions

### Session 1 of 4: Completion-detection model + dual-mode Explorer shell

**Goal:** Establish the state model and the dual-mode switch, with the form as a
rendering shell — no actions wired yet.
**Steps:**
1. Implement a **pure completion-detection module** (TS, unit-tested): given a
   workspace root, return `{ structureBuilt, planPresent, sessionSetsPresent }`
   per D3. No VS Code dependency in the core (inject fs).
2. Wire **dual-mode rendering** in `CustomSessionSetsView` (D1): no folder →
   "Open/create a folder" CTA; folder + no session sets → the Getting Started
   **form shell**; folder + ≥1 set → the existing list. Refresh on the existing
   file-watcher signals so the mode flips live as steps complete.
3. Render the form shell (3 steps with the Full/Lightweight radio + parallel
   checkbox) reflecting **live completion state** (greyed/checked per D2/D3) —
   buttons present but inert this session.
4. Tests for the detection module + the mode-selection logic; cross-provider
   verification.
**Creates:** completion-detection module + tests; the form-shell renderer.
**Touches:** `src/providers/CustomSessionSetsView.ts` (+ supporting modules).
**Ends with:** the Explorer shows the right surface for each state, with live
progress, no actions yet.
**Progress keys:** `session-001/detection-model`, `session-001/dual-mode-view`,
`session-001/form-shell-live-state`, `session-001/verified`.

### Session 2 of 4: Wire the three actions

**Goal:** Make the form's three controls do the work, reusing the existing
engines.
**Steps:**
1. **Build project structure** → scaffold into the **open folder** with **no
   title prompt** (D5), tier from the radio; folder-picker fallback when none is
   open. Reuses `scaffoldConsumerRepo` (Set 058) behind a no-prompt entry.
2. **Import project-plan.md** (file picker → copy/import into
   `docs/planning/project-plan.md`) **OR Copy prompt for planning** (reuses the
   adoption-bootstrap / planning prompt).
3. **Build session sets** → **copy the decomposition prompt** (D4), honoring the
   parallel checkbox in the copied prompt text. Reuses `generateSessionSetPrompt`.
4. Form↔host message protocol; the form refreshes its live state after each
   action. Tests for the action handlers (mocked VS Code); cross-provider
   verification.
**Touches:** `src/commands/gitScaffold.ts` (no-prompt entry), the form host, the
planning/decomposition prompt commands.
**Ends with:** the three steps complete a real setup end to end (sans
validation polish).
**Progress keys:** `session-002/build-structure`, `session-002/plan-import`,
`session-002/build-session-sets`, `session-002/verified`.

### Session 3 of 4: Inline validation + static editor instructions + retire old path

**Goal:** Add the guardrails and the teaching doc, and converge the old Get
Started entry on the new surface.
**Steps:**
1. **Env-var validation** (D6): Full-tier Build button shows a "set a key + reload
   window" warning when no provider key is in `process.env`; Lightweight does
   not. Unit-test the predicate (System+User coverage rationale documented).
2. **Parallel worktree info** (D7): checking the box surfaces the worktree note.
3. **Static editor instructions** (D8): a generated `docs/dabbler/getting-started.md`
   (or equivalent) carrying the SVG's 5-step copy, opened in the editor when
   Getting Started is shown. Lift the operator's copy ~verbatim.
4. **Retire / repoint the old path:** `dabbler.getStarted` opens the new form +
   instructions; decide the fate of the old `WizardPanel` / `wizard.html` (retire
   or fold into the instructions doc) and the `setupNewProject` QuickPick (keep a
   Command-Palette entry that drives the same no-prompt scaffold, or remove).
5. Tests; cross-provider verification.
**Touches:** the form host, `WizardPanel.ts` / `wizard.html`, a new instructions
template, `package.json` (command/menu wiring).
**Ends with:** validated form + static instructions; one coherent Get Started
entry point.
**Progress keys:** `session-003/env-validation`, `session-003/worktree-info`,
`session-003/editor-instructions`, `session-003/old-path-retired`,
`session-003/verified`.

### Session 4 of 4: Operator UAT on a local build, then bump 0.29.0 + held release

**Goal:** Gate the release on a passing **local** UAT, then ship.
**Steps:**
1. Build a local `.vsix`; **operator UAT** (ad-hoc, per-set) on the F5 dev host /
   installed build: no-folder state, folder + form, all three steps for **both**
   tiers, the env-var warning (Full, keys unset), the worktree note, the editor
   instructions, and the flip to the session-set list once a set exists. Record
   results in the set's UAT checklist. **This is the pre-publish gate.**
2. On pass: **bump 0.28.x → 0.29.0** (`package.json` + lock + `CHANGELOG.md`,
   noting it also carries the Set 059 activation fix); update
   `docs/repository-reference.md` release status.
3. Cross-provider verification; close-out (final session → `change-log.md`).
4. **Held release:** the operator pushes `vsix-v0.29.0` after the UAT passes.
**Touches:** version files, `CHANGELOG.md`, `docs/repository-reference.md`, the
set's UAT checklist.
**Ends with:** a locally-UAT'd 0.29.0 held for operator tag-push.
**Progress keys:** `session-004/operator-uat-passed`,
`session-004/version-bumped`, `session-004/verified`,
`session-004/change-log-written`.

---

## End-of-set deliverables

- A dual-mode Session Set Explorer: the Getting Started **form** when no sets
  exist (with a no-folder "open a folder" state), the session-set **list**
  otherwise.
- A completion-detection model driving live greyed/checked step state in the
  form (and only there).
- Three working form actions — Build project structure (scaffold the open folder,
  no title prompt), Import/copy-plan, copy build-session-sets prompt — reusing
  the existing scaffolder/planning/decomposition engines.
- Inline validation: Full-tier env-var warning ("set a key + reload window") and
  a git-worktree info note on the parallel checkbox.
- A static editor instructions doc carrying the operator's 5-step teaching copy.
- One coherent Get Started entry point (old wizard/QuickPick retired or
  repointed).
- A locally-UAT'd extension **0.29.0** (also carrying the Set 059 activation fix)
  held for operator tag-push `vsix-v0.29.0`.

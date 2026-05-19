# Set 029 Session 5 — verification Round A

Round A scope: **detection + Codex watcher + shim commands + the
small integration diffs** in OrchestratorAccordion and
CustomSessionSetsView. Round B covers the universal manual-override
quickpick (`setOrchestratorManual.ts`, 533 LOC) as its own bundle.

## Session 5 context

This is the multi-provider feature-complete session for Set 029. The
deliverables are:

1. **Codex auto-detect** via a `~/.codex/config.toml` watcher (writes
   `signalKind: "configured-default"`, `confidence: "medium"`).
2. **Universal manual-override quickpick** (`dabbler.setOrchestrator`)
   — replaces the Session 2 stub. MRU tuples at the top, multi-step
   provider→model→effort→thinking flow, hotkey-bindable args,
   force-override confirmation. (Verified in Round B.)
3. **Gemini Code Assist + GitHub Copilot installer shims** — manual
   only per audit Q2/Q4. Both open the manual-override quickpick
   with `prefillProvider` pre-set.
4. **Smart empty-state CTA** — webview detects which orchestrators
   are installed locally (Claude Code via `~/.claude/`, Codex via
   `~/.codex/`, Gemini Code Assist + GitHub Copilot via the VS Code
   extension registry) and surfaces the right install/preset link.
   MRU-biased when applicable; priority order otherwise.
5. **Version bump 0.16.0 → 0.17.0**; CLAUDE.md + CHANGELOG updated.
6. **Playwright smoke + Layer-2 unit tests** added.

Locked decisions per the audit (do not re-litigate): Codex
auto-detect is config-watcher-only (no installer command);
Gemini + Copilot are manual-only; the manual-override quickpick
delegates marker writes to `scripts/write-orchestrator-marker.js`
via `--mode manual` and that helper handles atomic write +
retry-loop + multi-writer precedence. The empty-state CTA falls
back to the Claude Code installer if no orchestrators are detected.

## What to verify

Respond per question with one of: **VERIFIED** / **MUST-FIX** /
**SUGGEST**. Quote a file:line for MUST-FIX items.

### Q1 — Codex config watcher correctness

Look at `src/codex/configWatcher.ts`. The watcher:
- Reads `~/.codex/config.toml` on extension activate and on file
  events under `~/.codex/`.
- Parses the top-level `model` and `model_reasoning_effort` keys
  with `extractTopLevelScalar` (a hand-rolled regex extractor — full
  TOML parser would balloon the VSIX).
- Spawns the shared marker-writer with `--mode configured-default`,
  passing the parsed snapshot as JSON on stdin.
- Debounces file events to one dispatch per 500 ms.

Verify:
- The TOML extractor handles the formats Codex actually writes
  (quoted, single-quoted, bare, leading whitespace, trailing
  comment). It skips values inside `[sections]`. Edge cases
  hostile to the regex don't false-positive.
- The watcher doesn't crash if `~/.codex/` doesn't exist
  (best-effort silent skip).
- The marker write goes through the helper (so the precedence rules
  apply automatically); the watcher itself doesn't bypass
  precedence.
- The debouncer + dispose path don't leak timers.

### Q2 — Gemini + Copilot shim commands

`src/commands/installOrchestratorHookGemini.ts` and
`installOrchestratorHookCopilot.ts` each register a single command
that invokes `dabbler.setOrchestrator` with `{prefillProvider}` set.
No real hook is installed — per audit Q2/Q4 those orchestrator
surfaces have no documented persisted state to scrape in v1.

Verify:
- The command IDs match the package.json contributes (`dabbler.installOrchestratorHook.gemini`
  and `.copilot`).
- The `prefillProvider` value matches what `setOrchestratorManual`
  expects (`"google"` / `"github"`).
- The shims don't accidentally install any file/setting on the
  user's machine (they should be 100% delegation).

### Q3 — Empty-state CTA detection logic

`src/providers/detectOrchestrators.ts` decides which install/preset
link the "No signal — …" CTA points at:

- Detection: `~/.claude/` directory for Claude Code, `~/.codex/` for
  Codex, `vscode.extensions.getExtension(...)` for Gemini Code
  Assist and GitHub Copilot.
- Ordering: when no MRU is populated, fall back to priority order
  (claude → codex → gemini → copilot). When MRU exists, surface
  the most-recent installed provider first; append other installed
  providers in priority order behind it.
- `pickEmptyStateCta` returns the CTA for the first installed
  provider or `null` (caller falls back to the Claude installer
  default).

Verify:
- The MRU-bias logic correctly ignores MRU entries whose provider
  isn't currently installed.
- Priority-order fallback is `["anthropic", "openai", "google", "github"]`.
- The CTA payloads match the expected command IDs (Claude →
  installer; Codex → `dabbler.setOrchestrator` with
  `{prefillProvider: "openai"}`; Gemini → installer-shim; Copilot →
  installer-shim).
- The detection helpers are best-effort (no thrown exceptions on
  missing directories or absent extensions).

### Q4 — Accordion empty-state plumbing

`src/providers/OrchestratorAccordion.ts` was extended so
`RenderState`'s `empty` variant carries an optional `cta: EmptyCta`.
`renderAccordionEmpty(cta?)` substitutes the passed CTA's command ID
+ label into the "No signal — <label>" link; if `cta?.args` is
present, it's JSON-stringified into a `data-command-args` attribute
on the button. Falls back to the Claude installer when no CTA is
passed (preserves v0.16.0 behavior).

Verify:
- The CTA's command ID and label flow through `escAttr`/`escHtml`
  correctly (no XSS opening if someone seeds a malicious label —
  not currently possible since the labels are hardcoded, but the
  escape path should still apply defensively).
- The `data-command-args` attribute round-trips through
  `JSON.stringify` cleanly.
- The fallback path (`cta === null`) still renders the Claude
  installer link verbatim.

### Q5 — CustomSessionSetsView wiring

`src/providers/CustomSessionSetsView.ts` was changed in three
places:
1. New import of `pickEmptyStateCta`.
2. The command allowlist (`COMMAND_ALLOWLIST`) added the Gemini and
   Copilot installer command IDs.
3. In `scheduleRender()` / `postSnapshot()` (around the marker
   snapshot read), when `snap.state.kind === "empty"` AND
   `snap.resolution.kind === "resolved"`, we call `pickEmptyStateCta()`
   and pass the result into the render state.

Verify:
- The allowlist additions are present and correctly spelled.
- The detection is only invoked when the resolved set actually has
  an empty marker state (don't run detection on every render for
  non-resolved rows).
- The detection result flows through to `renderAccordionBody` as
  expected — the empty-state HTML embeds the detected CTA.

### Q6 — Webview client `data-command-args` forwarding

`media/session-sets-tree/client.js` was extended so the
`[data-command]` click handler reads an optional
`data-command-args` attribute, JSON-parses it, and forwards it as
the `args` field of the `executeCommand` postMessage. The host
already passes `args` through to `vscode.commands.executeCommand`
when present (see `CustomSessionSetsView.dispatchCommand`).

Verify:
- JSON parse errors don't throw — they fall back to `args: undefined`.
- The parsed value must be an array (matches the host's
  `args?: unknown[]` expectation) — non-array values get nulled out.
- The forwarding doesn't break the existing buttons that have no
  `data-command-args` attribute.

### Q7 — Test coverage

Three Playwright scenarios were added:
- configured-default Codex marker → `signal-configured-default`
  class present on at least one gauge cell + "Codex" sublabel.
- Manual Gemini marker → `signal-manual` class present + "Gemini"
  sublabel.
- Empty state (no seeded marker) → "No signal" prefix + an
  `acc-link` button visible (label content varies by host install).

Six new Layer-2 unit suites cover the TOML extractor, MRU
push/dedupe/cap, formatTupleLabel, MRU readers (malformed JSON,
non-tuple filtering), detection priority + MRU-bias, and CTA
selection.

Verify the test coverage matches the spec's mandates (configured-
default visual, manual visual, MRU reordering logic, precedence,
multi-writer skip). Where the spec called for Playwright but the
implementation moved to Layer 2 (MRU reordering, force-override,
multi-writer-skip — all logic-level invariants), confirm that
trade-off is sound vs. the painted-on-screen split established in
S4 (data assertions → unit tests; pixels → Playwright).

### Optional — anything else risky

If anything else stands out as a correctness issue, flag it.

# Session 2 verification — Round B (provider + installer)

## Context

Round A (marker writer + CSS visual matrix) was reviewed by gpt-5-4 and
returned with three must-fix items, all applied:

1. **TOCTOU race in `attemptWriteWithPrecedence`** — added re-read-
   immediately-before-rename in `write-orchestrator-marker.js` per
   audit §"Multi-writer precedence" step 3.
2. **UserPromptSubmit merge/bootstrap clobber risk** — added re-read
   in the merge branch; the latest-marker snapshot wins, merging
   effort onto fresher top-level state rather than overwriting it.
3. **Stale stripes were a `background-image` painted BEHIND the SVG,
   not an overlay** — replaced with a `.stale .gauge-cell::before`
   absolute-positioned pseudo-element painting at 45% alpha above
   the gauge artwork.
4. Plus: superseding note added to `audit-summary.md` D3 + spec.md D3
   documenting the operator's 100→150px revision.

Marker writer smoke-test re-run after the fixes: all six paths still
behave correctly. Playwright suite (8 scenarios) still green after
the CSS overlay change. Round A's blockers are addressed.

This is **Round B of two** — focused on the provider (webview rendering)
and the Claude Code hook installer. Code under review:

1. **`src/providers/orchestratorIndicatorProvider.ts`** (~395 LOC) —
   `WebviewViewProvider` for `dabblerOrchestratorIndicator`. Marker
   reader + FileSystemWatcher + 60s poll backstop + 50ms render
   debounce; renderHtml/renderLoaded/renderEmpty + visual-treatment
   class composition + tooltip text composition + effort/tier needle
   angles + display-name + CSP nonce + webview message-passing for
   the install CTA.

2. **`src/commands/installOrchestratorHookClaudeCode.ts`** (~170 LOC) —
   idempotent edit of `~/.claude/settings.json`. Adds SessionStart
   hooks for all four source matchers (startup/resume/clear/compact)
   + one UserPromptSubmit hook. Both pipe their payload to the
   marker writer. Preserves foreign hooks. Atomic write to the
   settings file.

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Provider — visual-treatment matrix wiring.**
   The provider emits CSS classes that the CSS hooks into for the
   visual treatments. `renderLoaded` composes:
   ```
   modelClasses = "gauge-cell tier-<X> signal-<Y>"
   effortClasses = "gauge-cell effort-<Z> signal-<W>"
   ```
   And then conditionally renders:
   - `modelSuffix` = ` <span class="default-pill">DEFAULT</span>` when
     top-level signalKind is `configured-default`
   - `effortSuffix` = `(last ${native} ${age} ago)` div when
     effort.signalKind is `last-observed`, else `(default)` for
     `configured-default`, else `(manual)` for `manual`, else empty
   - `modelOverlay` / `effortOverlay` = clock-icon span for
     `last-observed`, operator-icon span for `manual`, else empty
   Verify the matrix is wired correctly:
   - Does the model gauge's `configured-default` get the DEFAULT
     pill in its sublabel? (Yes — `modelSuffix` is conditional on
     `marker.signalKind === "configured-default"`.)
   - Does the effort gauge get the time-elapsed sublabel when
     `effort.signalKind === "last-observed"`? (Yes.)
   - Does the model gauge get the clock-icon overlay when its
     top-level `signalKind === "last-observed"`, independently of
     effort? (Yes — `modelOverlay` keys off `marker.signalKind`.)
   - Does the effort gauge's color come from `effort.normalized`
     (low/medium/high/etc.) NOT from `marker.tier`? `effortClasses`
     uses `effort-${marker.effort.normalized}` for the color class
     but separately passes `this.effortColorBucket(...)` to
     `renderGaugeSvg` for the data attribute. Cross-check that the
     SVG's color comes from the CSS `.effort-medium .gauge-arc-fill`
     etc. rules — not from the data-tier attribute. (The data-tier
     attribute on the SVG is informational, not styled — the styled
     classes are on the parent `.gauge-cell`. Verify CSS specificity
     resolves the way the provider intends.)

**Q2. Provider — staleness handling.**
   `computeState` reads the marker, parses it, computes `ageSec =
   (Date.now() - Date.parse(marker.updatedAt)) / 1000`, then
   `stale = ageSec > stalenessMaxSec` (defaulting to 28800s = 8h).
   `renderLoaded` adds `.stale` to `.gauges` when stale and renders
   `last updated Xh ago — stale` annotation; otherwise `updated Xs/m/h
   ago` (no "— stale" suffix). Audit Q6 says no-install-CTA on stale
   (only on missing-marker) — the empty-state CTA only renders when
   `state.kind === "empty"`, which happens when the file is absent
   or unparseable, NOT when the file is stale. Correct?

**Q3. Provider — watcher robustness.**
   - The watcher uses
     `vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(MARKER_DIR), "current-orchestrator.json"))`
   - 60s poll backstop via setInterval
   - 50ms render debounce on each trigger
   - `setUpWatchers` calls `tearDownWatchers` first so a re-resolve
     doesn't double-bind
   Any robustness gaps:
   - Watcher fires on create/change/delete; if the marker file is
     atomically replaced (write tmp + rename onto target), Windows
     fires `create` for the tmp file + `change` or `delete+create`
     for the target. The 50ms debounce coalesces these. Adequate?
   - What if `~/.dabbler` doesn't exist yet (e.g., the operator
     has never invoked the hook)? Does `createFileSystemWatcher`
     fail silently on a non-existent base path, or does it watch
     for the directory to appear?
   - The 60s poll is the failsafe for watcher misses. If the
     operator's filesystem is slow (network drive, antivirus
     scanning), a watcher miss could be 60s late. Acceptable?

**Q4. Provider — render pipeline correctness.**
   - `renderHtml` builds a CSP-restricted HTML doc with a per-render
     nonce; the script block uses `acquireVsCodeApi` to expose
     `vscode.postMessage` to the click handlers; the message-passing
     handler dispatches `dabbler.installOrchestratorHook.claudeCode` /
     `dabbler.setOrchestrator` / `dabbler.openOrchestratorWriterLog`
   - `renderEmpty` uses two grey SVG gauges (tier=unknown,
     signalKind=current, needle=0) plus the install-CTA span
   - `renderGaugeSvg` computes SVG arc geometry using cx=35, cy=35,
     radius=28 on a 70×38 viewBox; the SVG is CSS-scaled to 100×54
     (the viewBox preserves aspect, so stroke-width and arc geometry
     scale uniformly)
   - Tooltips embed confidence per the audit matrix: "live signal
     (high confidence)" / "live signal (low confidence — hook payload
     missing model)" / "configured default (medium confidence —
     does not track runtime changes)" / "last observed Xm ago via
     /think (high confidence in detection, but may not reflect
     current message)" / "set manually (high confidence)"
   - `fmtAge` returns "Xs" / "Xm" / "Xh" / "Xd" depending on
     magnitude
   Any correctness issues with the render pipeline?

**Q5. Hook installer — idempotence.**
   `ensureMatcherEntry` iterates the existing entry array, looks for
   one whose matcher matches AND whose `hooks` contains a command
   referencing "write-orchestrator-marker.js"; if found, upgrades the
   command in place; otherwise appends a new entry.
   Trace cases:
   - **First install (no settings.json):** loadClaudeSettings returns
     `{ exists: false, settings: {} }`. We append SessionStart × 4
     matchers + UserPromptSubmit × 1 (no matcher). Writes a fresh
     `~/.claude/settings.json` with the dabbler entries.
   - **Re-install (extension already installed):** existing dabbler
     entries get their commands replaced in place with the current
     helper path; no duplicates added.
   - **Operator has their own SessionStart hook (foreign):** the
     installer iterates entries and only matches when matcher AND
     write-orchestrator-marker.js substring both check. Foreign
     entries pass through untouched.
   - **Operator has renamed the helper script:** the substring check
     misses the renamed entry, so the installer appends a NEW entry
     instead of upgrading the renamed one. Duplicate hooks fire on
     SessionStart. Is this a material concern?

**Q6. Hook installer — source matcher coverage.**
   Installer adds SessionStart hooks for all four source values:
   `startup`, `resume`, `clear`, `compact`. The R7 pre-implementation
   verification confirmed `/clear` fires SessionStart with
   `source: "clear"` AND `/think*` is per-message (so /clear is a
   fresh-session boundary). For `compact` (mid-conversation context
   compression), is treating it as a session boundary correct? The
   compact-time marker write resets effort to Medium and refreshes
   the model — that's correct if the operator's `/model` selection
   carries through compaction (which it should, per Claude Code
   semantics), but the effort reset may be aggressive if the
   operator had `/megathink`-style escalation that they expected to
   carry through the compaction. Is the spec-intended behavior to
   clobber on `compact` or to preserve effort?

**Q7. Hook installer — command quoting + portability.**
   `buildHookCommand` returns `node "${helperAbsPath}" --mode ${mode}`.
   The double-quote wrapping handles paths with spaces (`C:\Users\Some
   Name\...`). Trace edge cases:
   - **Backslashes in helperAbsPath:** on Windows, the path is like
     `C:\Users\denmi\source\repos\dabbler-ai-orchestration\tools\
     dabbler-ai-orchestration\scripts\write-orchestrator-marker.js`.
     The string is embedded raw in JSON — `JSON.stringify` will
     escape backslashes to `\\`, so the JSON-on-disk has `node
     "C:\\\\Users\\\\..."`. When Claude Code reads the JSON and shells
     out the command, the shell sees `node "C:\Users\..."` (single
     backslashes) which Windows handles correctly. Verify the
     escaping round-trip.
   - **Special chars in the path** (single quotes, double quotes,
     dollar signs, ampersands): the operator's HOME path
     theoretically might contain these. The double-quote wrapping
     handles double quotes if escaped, but doesn't handle them if
     unescaped (would close the quoted region). Practical concern,
     or theoretical?
   - **POSIX shell vs. cmd.exe:** Claude Code hook docs say the
     command is invoked via the OS shell. On Windows, that's cmd.exe
     by default, which handles double-quote wrapping but has its own
     escaping rules. Any portability concern?

**Q8. Hook installer — settings.json atomic write.**
   `writeClaudeSettings` writes to a tmp file with `.tmp.<pid>.<rand>`
   suffix then renames. Same atomic pattern as the marker writer.
   `loadClaudeSettings` reads via `fs.readFileSync` (utf8); throws if
   JSON is malformed (user-facing error message, no clobber).
   `mkdirSync(path.dirname(settingsPath), { recursive: true })` to
   handle a first-install case where `~/.claude/` doesn't exist.
   Concerns:
   - Concurrent writes (two installer invocations racing): the
     atomic rename ensures either write lands, but the LATER one
     overwrites the EARLIER one. Should the installer take a file
     lock or check-and-merge? Likely overkill for an installer
     that runs <1× per install, but call it out.
   - Error path: if `writeClaudeSettings` throws, the show-error-
     message surfaces the error to the operator. The error message
     includes the underlying exception's `.message`. Adequate?

**Q9. Provider <-> installer integration.**
   The webview's empty-state CTA calls `dabbler.installOrchestrator
   Hook.claudeCode` via `webview.postMessage`. The provider receives
   it in `onDidReceiveMessage` and dispatches via
   `vscode.commands.executeCommand`. The command is registered by
   `registerInstallOrchestratorHookClaudeCodeCommand` in
   `extension.ts`. Verify end-to-end:
   - Provider HTML's `.install-cta` has `data-command="installHookClaudeCode"`.
   - Script block listens for clicks on `[data-command]`, posts
     `{ command: "installHookClaudeCode" }`.
   - Provider's `onDidReceiveMessage` maps `installHookClaudeCode`
     → `vscode.commands.executeCommand("dabbler.installOrchestratorHook.claudeCode")`.
   - extension.ts registers `dabbler.installOrchestratorHook.claudeCode`.
   - package.json declares the command in `contributes.commands`.
   Any link in this chain that doesn't resolve?

**Q10. Round B overall verdict.**
   Are the provider + installer ready to close out? Smallest concrete
   must-fix items, if any?

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.

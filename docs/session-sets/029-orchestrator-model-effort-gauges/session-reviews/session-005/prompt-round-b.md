# Set 029 Session 5 — verification Round B

Round B scope: **`src/commands/setOrchestratorManual.ts`** — the
universal manual-override quickpick (533 LOC). Round A covered the
rest of S5's new surface (Codex watcher, detection, shim commands,
integration diffs).

## Session 5 context

This command (`dabbler.setOrchestrator`) is the primary surface for
all non-Claude orchestrator manual overrides, plus the Claude
fallback when an operator wants to override the SessionStart-hook-
driven signal. It replaces the Session 2 stub.

### Expected behavior

- **Top of quickpick**: MRU tuples (one row per `<provider> + <model>
  + <effort> + <thinking>` combination), most-recent first, sorted
  by recency. Stored at `~/.dabbler/orchestrator-mru.json` (capped at
  8 entries).
- **`(set new combination…)`** row: multi-step picker flow —
  provider → model → effort → thinking-on/off. When invoked via the
  Gemini or Copilot shims, the provider step is skipped (pre-filled
  via `prefillProvider`).
- **`(copy keybindings.json snippet for current selection)`** row
  (appears only when MRU non-empty): copies a `keybindings.json`
  JSON fragment to clipboard pre-filled with the most-recent tuple.
- **Hotkey-bindable**: callers can invoke
  `dabbler.setOrchestrator` with `{provider, model, effort, thinking}`
  to bypass the quickpick. (Force-override prompt still applies.)
- **Force-override semantics**: before any write, read the resolved
  set's existing marker. If there's a fresh `current`-precedence
  signal from another writer (i.e., a live SessionStart hook is
  driving the marker), pop a modal "Override existing live signal
  from <writer>?" confirmation. On accept, pass `--force-override`
  to the helper.
- **Marker write delegation**: spawn `scripts/write-orchestrator-marker.js`
  with `--mode manual --writer manual-override`, JSON payload on
  stdin. Helper handles atomic write + retry-loop + multi-writer
  precedence + writer-log appends.
- **MRU update**: after a successful write, push the tuple to MRU.
  Failed writes do NOT update MRU (verify this).
- **User feedback**: success → info notification with formatted
  tuple label. Failure → error notification quoting exit code +
  stderr trimmed.

### Architecture choices already locked

- The set resolution path (`readCurrentMarkerForWorkspace`)
  replicates the helper script's walk-up resolver in TypeScript to
  read the existing marker for the force-override prompt. We
  *could* invoke the helper in a "read-only" mode, but that's a
  larger change and the duplication is small + isolated.
- The PROVIDER_MODELS list is curated (not exhaustive). New models
  can be added without changing surrounding logic. The marker
  writer's `deriveModelDisplayName` normalizer falls back to the
  raw model id, so unknown models still render correctly.

## What to verify

Respond per question with one of: **VERIFIED** / **MUST-FIX** /
**SUGGEST**. Quote a file:line for MUST-FIX items.

### Q1 — Quickpick flow correctness

- Multi-step flow (provider → model → effort → thinking) handles
  user cancellation (`undefined` return from any step) by aborting
  cleanly with no side effects.
- The MRU + new + hotkey items appear in the right order and only
  when applicable (no hotkey row if MRU is empty).
- The `prefillProvider` path correctly skips the provider step and
  filters MRU entries to surface that provider first.

### Q2 — MRU storage correctness

- `readMru()` is tolerant of: missing file, malformed JSON,
  non-array root, and non-tuple entries (filters them out without
  throwing).
- `pushMru()` de-duplicates by full tuple identity (all four fields
  matching), moves the existing entry to the front, and caps at 8
  entries.
- `mruFilePath()` is computed per-call (not cached at module load)
  so unit tests that redirect `$HOME` work correctly. This is
  load-bearing: caching would cause the live extension to keep
  using whatever home directory was active at first activation.

### Q3 — Force-override prompt correctness

`maybeConfirmForceOverride()`:
- Returns `{proceed: true, force: false}` when no existing marker
  resolves (no in-progress set, or multi-in-progress ambiguity).
- Returns `{proceed: true, force: false}` when the existing marker
  is weaker than `current` precedence (configured-default,
  last-observed, manual — all of which the helper will overwrite
  without ceremony).
- Returns `{proceed: true, force: true}` when the existing marker
  is `current` but STALE (age > stalenessMaxSec / default 8h). The
  helper would overwrite a stale marker unconditionally anyway, so
  prompting would be misleading.
- Pops the modal warning and returns based on the user's choice
  when the existing marker is fresh `current`. On accept,
  `force: true` is passed to `dispatchManualWrite`.

Verify the precedence vs. staleness vs. user-confirmation tree is
correct, and that the prompt text quotes the actual writer name
from the marker (not a generic placeholder).

### Q4 — Marker write dispatch

`dispatchManualWrite()`:
- Spawns `process.execPath` (the node binary) + the helper script
  path + args, with stdio configured for piped stdin (payload).
- Wraps in a Promise that resolves with `{exitCode, stderr}`.
- Passes `--force-override` only when `forceOverride === true`.
- The payload's `effort` block uses the right shape for the
  helper's `mode === "manual"` branch (signalKind: "manual",
  confidence: "high", thinking from tuple, normalized/native from
  tuple).
- Doesn't double-write the marker (one helper invocation per call).

### Q5 — Hotkey-bindable args path

When the command is invoked with a complete args object
(`isCompleteArgs(args) === true`), the quickpick is skipped and
`executeWrite` runs directly. The args are normalized to an
`OrchestratorTuple` and pushed to the same write+MRU path as the
picker.

The `isCompleteArgs` type guard validates all four required fields
are present and of the right type — missing or extra fields fall
back to the quickpick.

### Q6 — Keybindings snippet

`buildKeybindingSnippet()`:
- Emits a 3-field JSON object (`key`, `command`, `args`).
- The default key (`ctrl+shift+alt+o`) is a reasonable starting
  point but the operator is expected to edit it.
- The args object is the literal MRU tuple (no transformation).
- Writes to clipboard via `vscode.env.clipboard.writeText`.

### Q7 — Error paths + user feedback

- Helper not found → user-visible error with the absolute helper
  path quoted.
- Helper exit ≠ 0 → user-visible error with exit code + trimmed
  stderr.
- Helper exit 0 → success notification with `formatTupleLabel`
  result + MRU push.
- MRU file write failure is best-effort (silent), so a failed MRU
  write doesn't surface as a user-visible error.

### Optional — anything else risky

If anything else stands out (concurrency, race conditions, encoding
issues, Windows-specific path bugs, accessibility gaps in the
modal, etc.), flag it.

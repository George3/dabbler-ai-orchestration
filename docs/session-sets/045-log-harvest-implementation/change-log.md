# Set 045: log-harvest implementation — change log

**Status:** COMPLETE (6 of 6 sessions; closed 2026-05-25)
**Created:** 2026-05-23 (Set 044 / S5 close-out)
**Cost:** routed verification spend tracked per session in
`activity-log.json` `routedApiCalls`; cumulative through Round A on
S6 = $0.3177 of $5 NTE (S1–S5); S6 verification appended at close.
**Forecast:** Low–medium per `ai-assignment.md` (single Gemini Pro
verification per session, ~$0.05–$0.12 per round). **Actual:**
well under forecast — Gemini Pro routed every session straight
through (no GPT-5.4 429 cascade burn), 6 verification rounds
across S1–S5 (5 VERIFIED + 1 REJECTED-then-fixed), and only S3
required three rounds (Round A surfaced two real defects, Round B
surfaced a single-bind regression, Round C verified).
**NTE ceiling:** $5 (operator-confirmed at S1 start; carried
forward from Set 036's $5 NTE shape).

---

## Context

Set 044 (`044-ai-chat-log-discovery-and-experiments`) ran a
log-discovery and prototype set whose Pass A consensus pivoted
mid-session under Pass B's devil's-advocate framing from a
wrapper-primary architecture (consensus would otherwise have been
2-GO/1-NO-GO) to a **dual-primary** architecture
(wrapper + native-log parsing co-equal, neither a fallback for
the other) that ended with consensus locked at 2-NO-GO/1-conditional
against the original Set 044 S6 spike. The locked design is
captured in
[`docs/session-sets/044-ai-chat-log-discovery-and-experiments/proposal.md`](../044-ai-chat-log-discovery-and-experiments/proposal.md)
and its consensus journal
[`proposal-consensus-journal.md`](../044-ai-chat-log-discovery-and-experiments/proposal-consensus-journal.md).
Set 044 also CANCELLED Sets 037-041 (per-provider launch-adapter
roadmap, retired in favor of the wrapper) and 042-043 (chat-
interface foundations, out of scope), and stubbed Sets 045 + 046.

Set 045 is the implementation half: six sessions ship the
dual-primary log-harvest architecture end-to-end as a cohesive
deliverable — joiner-first, then producer channels (wrapper +
parsers + narration), then Explorer surface, then UAT + release.

The five **locked architectural commitments** from Set 044
proposal v1 (dual-primary channels; session-start-only narration;
wrapper at `ai_router/`; headless-first; ungated-default;
LaunchAdapter retirement; joiner as engineering center of
gravity) were NOT relitigated within Set 045 — that's the
audit-then-spec discipline.

---

## Session 1: Open-question spike + joiner location decision (COMPLETE 2026-05-24)

Spike-only session to resolve the four open empirical questions
from Set 044 proposal v1 §6 before producer-side code lands.
Throwaway prototype code only; production-grade `dabbler-launch`
deferred to S3.

**Shipped:**

- `spike-prototypes/correlation_prototype.py` — synthesizes
  wrapper launch records and joins them against real on-disk
  Claude JSONL (`~/.claude/projects/*`) and Copilot OTel
  `events.jsonl` via `(workspace_cwd canonical, time_window,
  conv_id)` keys. Demonstrated 1:1 deterministic binding for
  both backends at the 30s window on real records;
  negative-case (wrong cwd, far-time launch) correctly produced
  no-match; a 1-hour ambiguity probe still resolved 1:1 (no
  concurrent bracketed sessions in real workspaces).
  Edge case: Claude's first JSONL event lags subprocess spawn by
  ~5s, so a 2s window misses → default production window 30s.
- `spike-prototypes/claude_phrasing_ablation_analysis.md` — diffed
  Set 044 v1 (refused) vs v2 (accepted on session-start, refused
  on per-turn) CLAUDE.md/AGENTS.md texts; identified 7
  distinguishing elements; built a hypothesis matrix ranked by
  Claude's own thinking-event quote ("for data harvesting
  purposes", "an attempt to manipulate my behavior for data
  extraction"). Strongest hypotheses: H1 (harvest lexical family
  alone) and H8 (harvest + pretense composite). Documented four
  defensive canonical-template rules sufficient for S4 to ship
  CLAUDE.md without running the optional A2-A8 ablation.
- `spike-prototypes/bypass_observation_log_schema.md` — per-line
  schema (`ts`, `entry_kind`, `engine`, `launched_via`,
  `workspace_cwd`, `set_slug`, `session_count`, `window_hours`,
  `notes`), three capture mechanisms in priority order
  (end-of-day reflective baseline; per-session higher fidelity;
  wrapper-automated post-S3). Observation window:
  2026-05-24 → 2026-06-07. Wrote the clock-start entry to
  `~/.dabbler/bypass-observation-log.jsonl` (operator-local,
  not committed). Decision-rule table maps bypass-rate buckets
  (<25% / 25-60% / >60%) to S3-vs-S4 investment-split
  implications.
- `spike-prototypes/joiner_python_sketch.py` +
  `spike-prototypes/joiner_typescript_sketch.ts` — two parallel
  joiner sketches detecting orchestrator-engine mismatch.
  Surprise benchmark finding: Python scans 461 native sessions
  in 36 ms; the idiomatic TypeScript port takes 2,589 ms
  (~70× slower) because `fs.readFileSync(...whole file).split()`
  reads everything before iterating — fixable but adds code.
- `joiner-location-decision.md` — LOCKED joiner to Python at
  `ai_router/joiner/`. Decisive criteria: reuse of `ai_router`
  state-file + lifecycle infra, pytest testability, cross-tier
  reusability for Lightweight tier, perf, debuggability.
  TypeScript wins only on IPC-to-Explorer (~50–100 ms savings)
  and in-process file watching — both bounded costs Python can
  absorb at the 1-second Explorer-latency budget. Confirms
  Set 044 Pass A 2-1 Python.
- `open-question-resolution.md` — consolidated the four
  resolutions with carry-forward bullets for S2-S6.

**Verification:** Round A (initially routed via
`task_type='session-verification'` → GPT-5.4 → sustained 429s
on the OpenAI endpoint across two attempts → pivoted to
gemini-pro by in-process router-config monkey-patch — still
cross-provider, no committed config touched). Gemini Pro returned
VERIFIED no must-fix. Endorsed Q2 (window sizing + cwd
canonicalization), Q4 (rubric comprehensive + benchmark powerful),
Q3 (matrix well-reasoned, defensive rules sufficient to ship
without ablation), Q1 (protocol pragmatic). Cost $0.024.

---

## Session 2: Joiner design + canonical schema (COMPLETE 2026-05-24)

Engineering-center-of-gravity per Set 044's locked consensus.

**Shipped:**

- `joiner-spec.md` — 10 sections covering purpose, inputs (3
  sources + bypass log carved out), three conflict modes in full
  (Mode A engine-mismatch high-severity 5min window;
  Mode B bare-touch + stale-checkout-touch medium-severity 2h
  staleness threshold; Mode C writer-bypass high-severity
  mtime + events-ledger ±2s correlation), resolution priorities,
  ConflictReport output shape, the positive join algorithm
  (30s bind window, 1:1 / unbound / ambiguous tri-state), the
  canonical Harvest Record schema (derived from joiner needs,
  5 specific revisions vs the v0 proposal §4.1 stub),
  CoverageSummary for Explorer badges, privacy/redaction
  posture, module layout under `ai_router/joiner/`, and four
  deferred follow-ups for S3-S5.
- `ai_router/joiner/` Python skeleton — `__init__.py` (public
  API re-exports), `schema.py` (HarvestRecord dataclass +
  canonicalize_cwd + normalize_engine + parse_iso helpers +
  harvest() entry point), `parsers.py` (Claude + Copilot JSONL
  scrapers promoted from S1 spike-prototype, hardened with
  explicit root args + NativeSession dataclass +
  SessionStateView reader + LaunchRecord + scan_launch_log
  forward-compat with S3), `conflicts.py` (detect_* + top-level
  scan_conflicts entry), `coverage.py` (CoverageSummary +
  coverage() entry + bypass_inferred derivation), `cli.py`
  (argparse with --conflicts / --coverage / --harvest +
  --set-slug + --workspace + --json), `__main__.py`. Streaming
  I/O preserved from the S1 prototype.
- 59 Layer-1 tests across `test_joiner_{schema,parsers,
  conflicts,coverage,cli}.py` — all using tmp_path-isolated
  synthetic fixtures rather than operator-machine
  `~/.claude` / `~/.copilot` directories.

**Verification:** Round A (gemini-pro, $0.053066) — VERIFIED no
must-fix. Two nice-to-have doc refinements applied in-flight:
joiner-spec.md §3.2 staleness-vs-CheckoutPollService-poll-timeout
distinction; §3.2 false-positive mitigation rule clarified to
include exact-match-on-workspace-root.

---

## Session 3: Wrapper + Copilot per-event parser (COMPLETE 2026-05-24)

Three producer-side gaps from S2: the `dabbler-launch` wrapper,
the Copilot OTel parser hardened to per-event emission, and the
harvest() join wire-up that consumes both.

**Shipped:**

- `ai_router/dabbler_launch.py` — headless-mode wrapper CLI per
  Set 044 commitment 4. `build_record()` emits the canonical
  Harvest Record §5 shape (event_type='launch', source='wrapper',
  engine + provider + model + effort + raw_ref.launch_id=uuid4).
  `append_launch_record()` does an atomic JSONL append BEFORE
  subprocess spawn so failed spawns still surface as unbound
  launches downstream. Engine validated against
  {claude, copilot, codex, gemini}; `--dry-run` for record-only
  invocations; `parse_args` strips a leading `--` separator.
- `ai_router/joiner/parsers.py` — `read_copilot_session_events()`
  per-event HarvestRecord emission for session.start / session.end
  / turn.* / tool.* / usage event types (unknown skipped,
  forward-compat). Sticky context (cwd, conv_id, model, provider)
  propagates from session.start through subsequent events.
  `_summarize_tool_args()` enforces §7 redaction (file path +
  line count + arg arity only, never raw payloads). The session-
  level `_read_copilot_events` scrape preserved for the
  NativeSession projection used in candidate matching.
- `ai_router/joiner/schema.py` — wired wrapper launches into
  `harvest()` per joiner-spec.md §4: 30s bind_window default,
  candidate matching by engine + cwd_canonical + time delta,
  three binding states (bound / unbound / ambiguous). Free-running
  natives still emit session_start records. LaunchRecord parser
  projection renamed `target_backend → engine` for §5 consistency;
  scan_launch_log reads both canonical and v0-stub field names.
- 18 new tests: `test_dabbler_launch.py` (9 L1), `test_dabbler_launch_join_e2e.py`
  (4 L2 covering bound + unbound + ambiguous + free-running), 5
  additions to `test_joiner_parsers.py`.

**Verification:** Round A (gemini-pro, $0.053125) — REJECTED on
two must-fix: (1) `harvest()` candidate predicate used raw engine
equality instead of `normalize_engine` (vendor variants like
'claude-code' would miss the join); (2) bound natives emitted only
session_start instead of the full per-event stream with launch
context merged per §4, and bound natives were re-emitted in the
free-running loop causing duplicate session_start. Round B
(gemini-pro, $0.031689) — REJECTED on three new must-fix:
(1) single-bind invariant violated — two launches could both
claim a native; (2) workspace_cwd / since filters applied AFTER
binding so a filtered launch could consume a native that should
appear free-running; (3) normalize_engine too narrow for vendor
variants outside the -code/-cli suffix pattern. Round C
(gemini-pro, $0.022486) — VERIFIED. Issues 1 + 2 fixed in-flight;
issue 3 deferred to joiner-spec.md §9 row 5 (expanding §3.1
in-flight would have broadened the audited contract without an
audit pass; one nice-to-have flagged: consider a pre-S5 spec audit
for normalize_engine breadth).

---

## Session 4: Claude per-event parser + narration v1.1 template (COMPLETE 2026-05-24)

Claude-side counterpart to S3's Copilot per-event parser plus the
narration v1.1 template authoring.

**Shipped:**

- `ai_router/narration.py` — canonical narration v1.1 module.
  `MARKER_REGEX` (anchored single-line per Set 044
  narration-design.md §2.3 verbatim — ASCII + 4 Unicode
  curly-quote variants). `ParsedMarker` dataclass +
  `detect_marker()` with the full §5.5 semantic-check enumeration
  (placeholder-leakage, unknown-phase, unknown-effort-enum,
  session-exceeds-total, non-integer-{session,total},
  version skipped, incomplete). `render_template(kind, set_slug,
  session_number, total_sessions, effort)` with strict input
  validation that refuses to emit placeholder strings.
  `project_state_for_template()` reading session-state via the
  D13-compliant `ai_router.progress.read_progress` reader.
  CLI (`python -m ai_router.narration`) with
  `--kind {claude,agents}`, `--state-file` XOR
  (`--set-slug + --session + --total`), `--effort`, `--output`.
  Template prose obeys the four Q3 defensive rules verbatim.
- `ai_router/joiner/parsers.py` — `read_claude_session_events()`
  per-event HarvestRecord emission for
  `~/.claude/projects/<slug>/<conv>.jsonl`. Maps Claude types to
  §5.1: first user/assistant record → session_start (once);
  each assistant record → turn; `tool_use` content blocks →
  tool_call (redacted via `_summarize_claude_tool_args` —
  preserves file_path / path / file / filename + line_count +
  Bash command_head; strips old_string / new_string / argv body);
  `assistant.message.usage` → usage (tokens_in = input +
  cache_creation + cache_read; tokens_out = output); text blocks
  matching MARKER_REGEX → marker event with source='narration'.
  Noise types (queue-operation, ai-title, last-prompt,
  file-history-snapshot, attachment) skipped. Sticky context
  propagates; provider defaults to 'anthropic' on first model
  sighting. Tolerant streaming: malformed JSONL skips, OSError
  yields nothing.
- `ai_router/joiner/schema.py` — `_native_events_for()` Claude
  branch dispatches to `read_claude_session_events`; Copilot
  branch unchanged; future-engines fallback retained.
- `tools/dabbler-ai-orchestration/src/commands/regenerateNarrationTemplates.ts`
  — `Dabbler: Regenerate Narration Templates` Command Palette
  action. Picks the in-progress session set (auto-select on 1;
  quickpick otherwise via `readAllSessionSets`), shells out to
  `python -m ai_router.narration` twice (claude + agents kinds)
  inside a `vscode.window.withProgress` wrapper, writes outputs
  to `<set-dir>/narration-templates/{CLAUDE.md,AGENTS.md}`, then
  surfaces a toast with `Open Rendered CLAUDE.md` + `Copy to
  consumer workspace…` actions (quickpick + `showOpenDialog`
  folder picker + `fs.copyFileSync` with overwrite confirm).
  Python resolver mirrors the existing `installAiRouterCommands`
  + `checkOutOrchestrator` patterns. Wired into `extension.ts`
  via `safeRegister`; declared in `package.json`
  contributes.commands.
- `docs/narration-templates.md` — operator-facing reference doc
  (when to use templates, how to regenerate via extension + CLI,
  marker anatomy, four defensive rules with Q3 cross-refs,
  malformed-marker diagnostic flags, optional ablation pointer).
- 18 new Layer-1 tests (`test_narration.py`: TestMarkerRegex 3 +
  TestDetectMarker 9 + TestRenderTemplate 6 + TestProjectStateForTemplate 4
  + CLI smoke 2; `test_joiner_parsers.py`: +5 Claude per-event
  scenarios + 1 Bash-argv redaction). Test fixture update:
  `_write_claude_jsonl` in `test_dabbler_launch_join_e2e.py` now
  writes a proper type=user record (the no-type minimal fixture
  survived the old fallback but the strict per-event parser
  correctly treats it as noise).

**Verification:** Round A (gemini-pro, $0.063053) — VERIFIED no
must-fix. Two nice-to-have refinements applied in-flight:
`vscode.window.withProgress` wrap of the two Python invocations
and an explicit `Copy to consumer workspace…` toast action with
file-picker + overwrite confirm. Verifier explicitly endorsed
the four S4 design judgment calls (no synthetic session_end
emission; sticky-cwd / overwriting-conv_id asymmetry;
first-user-or-assistant session_start trigger; summed tokens_in
incl. cache reads); plus the strict `project_state_for_template`
fail-loud posture.

---

## Session 5: Explorer integration + Layer-3 coverage (COMPLETE 2026-05-24)

Wired the S2 joiner's coverage + conflict outputs into the
Session Set Explorer webview.

**Pre-S5 operator decisions:** Copilot-side
`gen_ai.output.messages` marker scanning DEFERRED (structural
marker channel is the OTel session_start attribute already parsed
in S3; chat-output scanning only catches the corner case where
content-capture is enabled AND Copilot literally typed the
marker). Q3 phrasing-trigger ablation pre-S6 DEFERRED post-release
(templates round-trip cleanly through `detect_marker`; defensive
rules baked in; Marketplace download count = 3 makes a real-world
refusal a cheap patch).

**Shipped:**

- `ai_router/joiner/coverage.py` — fixed the S2-era
  `narration_present=False` hardcode. `coverage()` now consults a
  new `_any_narration_marker()` helper that scans relevant native
  sessions via `parsers.read_claude_session_events()` for any
  `event_type='marker'` record. Matches on `set_slug` when bound;
  falls back to workspace-scoped match for unbound markers.
  Copilot branch skipped per the deferred decision.
- `tools/dabbler-ai-orchestration/src/providers/HarvestService.ts`
  (281 LOC, NEW) — async shell-out to
  `python -m ai_router.joiner --coverage --json` and
  `--conflicts --json`. 30s TTL cache with `onUpdate` callback
  that triggers a re-render when fresh data lands. Graceful-fail:
  when both shell-outs fail, an empty snapshot is cached so the
  service does not hot-spin the subprocess. Dev-mode PYTHONPATH
  discovery: walks up from `extensionUri.fsPath` looking for an
  `ai_router/__init__.py` sibling (present under
  `--extensionDevelopmentPath` and Playwright; absent in
  Marketplace install where `pip install dabbler-ai-router`
  provides the import path); `resolveDevPythonPath` cap of 5
  ancestor levels keeps the search bounded.
  `SpawnResult.diagnostic` field
  (`'missing-ai-router' | 'spawn-failed' | 'non-zero-exit' | 'json-parse'`)
  — `spawnJson()` inspects stderr on non-zero exit and matches
  `/ModuleNotFoundError.*ai_router|No module named ['"]ai_router['"]/`
  to set diagnostic. `HarvestService.fetch()` fires a one-time
  `vscode.window.showWarningMessage` with an `Open settings`
  action when this diagnostic appears (sticky per-session via
  `missingDependencyNotified` flag).
- `tools/dabbler-ai-orchestration/src/types/sessionSetsWebviewProtocol.ts`
  — extended `RowPayload` with `harvestSignals` (`HarvestSignalsPayload | null`)
  and `conflicts` (`ConflictPayload[]`). Added type unions for
  `ConflictKind` (`'engine-mismatch' | 'bare-touch' | 'stale-checkout-touch' | 'writer-bypass'`)
  and `ConflictSeverity` (`'high' | 'medium' | 'low'`). Null/empty
  when the harvest service has no data yet — preserves pre-S5
  single-line row rendering as the cold-cache state.
- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
  — instantiated `HarvestService` in the constructor with
  `() => this.scheduleRender()` and
  `this.context.extensionUri`; disposed in `dispose()`;
  invalidated in `refresh()`. `buildRow()` reads
  `snapshot.signalsBySlug.get(set.name)` and
  `snapshot.conflictsBySlug.get(set.name)` synchronously,
  attaching harvestSignals + conflicts to the row payload.
- `media/session-sets-tree/client.js` — `renderRow()` emits a
  `.harvest-badges` span (inside `.row-text`, after description)
  with four fixed-position badges (W / N / M / B; `is-on` / `is-off`
  CSS class drives color) and a sibling `.conflict-pills` div
  (after `.row-header`) with one `.conflict-pill` per detected
  conflict (`data-kind` / `data-severity` / hover title).
- `media/session-sets-tree/tree.css` — IBM colorblind-safe palette
  (blue/purple/orange/magenta for the four signals;
  magenta/orange/yellow for the three severities) per the
  operator's prior `gauges_sizing_followup` preference; pill
  border-radius + tabular-nums for badges. `.conflict-pills`
  padding-left uses `calc(12px + var(--row-fraction-width) +
  var(--row-fraction-margin-right))` where 12px is the row-header
  left padding — indent now tracks the fraction column above
  through font-size changes (Round A must-fix #1 resolution;
  replaced the initial brittle hard-coded 60px).
- `src/test/playwright/harvest-signals.spec.ts` — 3 new
  scenarios: (1) harvest badges render in off-state for a fresh
  set; (2) writer-bypass conflict pill renders when state-file
  mtime drifts from events ledger (uses `fs.utimesSync` to push
  the state-file mtime ~60s into the past, outside the joiner's
  ±2s tolerance); (3) conflict pills wrap onto their own line
  below the row header (`.conflict-pills` direct child of
  `.treeitem`; `.harvest-badges` inside `.row-header` — two-tier
  layout invariant).
- 3 new Layer-1 coverage tests
  (`test_coverage_narration_present_when_marker_in_workspace`,
  `test_coverage_narration_absent_when_no_marker_text`,
  `test_coverage_narration_unbound_marker_in_workspace_still_counts`).

**Verification:** Round A (gemini-pro, $0.058361) — REJECTED on
2 must-fix: (1) hard-coded 60px conflict-pill indent brittle vs.
font-size changes; (2) HarvestService silent-degraded when
dabbler-ai-router is not pip-installed, hiding the setup gap from
operators. Both resolved in-flight per the operator's "don't hide
behind out-of-scope" directive (CSS custom properties + calc();
SpawnResult.diagnostic + one-time warning toast with `Open
settings` action). One spawn-warn-with-cwd nice-to-have also
applied. Three other recommendations DEFERRED:
HarvestService → singleton (architectural, no second view in this
set); missing-events-ledger ConflictKind (spec-touching, revisit
in S6); CONTRIBUTING.md `npm run test:playwright` rebuild-trap
note (doc-only, S6 doc-scope). Round B (gemini-pro, $0.012289)
— VERIFIED narrow re-check of the two resolutions.

---

## Session 6: UAT + change-log + cross-tier docs + release (COMPLETE 2026-05-25)

Set-closing release-and-documentation session.

**Pre-S6 operator decisions (recorded 2026-05-25):**
Of the three S5-deferred Round-A recommendations, only
**CONTRIBUTING.md rebuild-trap note** folded in.
**Singleton HarvestService refactor** DEFERRED — no current pain
point; CLAUDE.md "don't refactor beyond what the task requires"
applies. **Missing-events-ledger ConflictKind** DEFERRED — would
touch Set 044-locked spec §3 without an audit pass; Marketplace
download count = 3 makes a follow-on cheap if real-world feedback
wants it. Release posture confirmed: publish after verifier
VERIFIED, operator-gated.

**Shipped:**

- `CONTRIBUTING.md` (NEW) — top-level contributor doc covering
  the three test layers (pytest Layer 1, `npm run test:unit`
  Layer 2, `npm run test:playwright` Layer 3) with explicit
  per-layer command + scope guidance. Includes the
  **rebuild-trap note** flagged by S5 Round A: do NOT skip
  `npm run compile` or invoke `npx playwright test` directly
  when iterating on TypeScript changes — Playwright loads the
  extension from `dist/extension.js` and a stale bundle silently
  produces assertion failures that look like behavioral
  regressions but are really just unbuilt code. Always invoke
  through `npm run test:playwright`. Also covers build + publish
  + CI matrix + license pointer.
- `docs/session-sets/045-log-harvest-implementation/045-log-harvest-implementation-uat-checklist.json`
  (NEW) — 27 ad-hoc UAT scenarios across six functional areas
  (dabbler-launch wrapper, Joiner CLI, Narration templates,
  Explorer signal badges, Explorer conflict pills, Missing-
  dependency degradation, Documentation). Schema combines the
  UAT Checklist Editor's `Passes`/`Feedback` canonical fields
  with the Dabbler extension parser's `Result` field (set to
  'pending') so both tools render the checklist correctly.
- `docs/cross-repo-harvest-notice.md` (NEW) — cross-tier
  consumer-repo notice covering the new harvest surface
  (`pip install dabbler-ai-router>=0.8.0`; wrapper invocation;
  narration template regeneration; Explorer signal badges +
  conflict pills). Parallel structure to the existing
  `cross-repo-checkout-notice.md`; operator pulls the snippet
  into each consumer's CLAUDE.md manually per the established
  pattern.
- `docs/session-sets/045-log-harvest-implementation/change-log.md`
  (this file).
- `pyproject.toml` — `dabbler-ai-router` version bump
  `0.7.0` → `0.8.0`.
- `tools/dabbler-ai-orchestration/package.json` — extension
  version bump `0.20.0` → `0.21.0`.
- `tools/dabbler-ai-orchestration/CHANGELOG.md` — new `[0.21.0]`
  section under `[Unreleased]` summarizing the harvest surface +
  narration command + the CSS / diagnostic in-flight fixes.
- `CLAUDE.md` — extension-versioning block updated to promote
  0.20.0 to "Previous" and add 0.21.0 as "Current" with the
  Set 045 walk summary.

**Releases (operator-gated after VERIFIED):**

- PyPI: `dabbler-ai-router 0.8.0` — adds `ai_router.dabbler_launch`,
  `ai_router.narration`, and `ai_router.joiner.*` packages; new
  CLI entries `python -m ai_router.dabbler_launch`,
  `python -m ai_router.joiner`, `python -m ai_router.narration`.
- VS Code Marketplace: `DarndestDabbler.dabbler-ai-orchestration 0.21.0`
  — adds Session Set Explorer harvest signal badges + conflict
  pills, `Dabbler: Regenerate Narration Templates` command,
  graceful-degradation toast when `dabbler-ai-router` is not
  installed.

**Verification:** Round A (gemini-pro, $0.068716) —
VERIFIED no must-fix (one nice-to-have on CONTRIBUTING.md `cd` duplication applied in-flight). Raw verdict at
`session-reviews/session-006.md`.

---

## Cumulative routed spend (Set 045)

| Session | Cost (USD) | Verdict |
|---|---|---|
| S1 | $0.024 | VERIFIED Round A |
| S2 | $0.053066 | VERIFIED Round A |
| S3 | $0.107300 | VERIFIED Round C (two must-fix waves caught and fixed) |
| S4 | $0.063053 | VERIFIED Round A |
| S5 | $0.070650 | VERIFIED Round B (two must-fix resolved in-flight) |
| S6 | $0.068716 | VERIFIED no must-fix (one nice-to-have on CONTRIBUTING.md `cd` duplication applied in-flight) |
| **Total** | **$0.386416** | of $5 NTE ceiling |

## What did not ship (deferred by operator decision)

- **Codex / Gemini per-event parsers** — Set 044 non-goal; deferred
  until a real consumer needs them. The `_native_events_for`
  dispatch in `ai_router/joiner/schema.py` carries a fallback
  branch so future engines can plug in without breaking the join.
- **Interactive TTY-passthrough mode** for `dabbler-launch` on
  Windows — Set 044 non-goal; deferred. Headless mode is the
  shipped surface in S3.
- **Hook-channel per-turn narration on Claude** — Set 044 non-goal;
  per-turn narration is permanently OUT of the v1.1 contract.
- **A Dabbler-owned chat-replay UI** — Set 044 non-goal; separate
  question, was scoped to the cancelled Sets 042-043.
- **Copilot-side `gen_ai.output.messages` marker scanning** —
  DEFERRED at pre-S5 (bounded value vs. parser+test cost).
- **Q3 phrasing-trigger ablation pre-Marketplace-release** —
  DEFERRED at pre-S5 + reconfirmed pre-S6 (post-release follow-on
  if a real refusal surfaces).
- **Singleton HarvestService refactor** — DEFERRED at pre-S6
  (no current pain point; only matters with a second consumer
  view).
- **Missing-events-ledger ConflictKind** — DEFERRED at pre-S6
  (audit-touching; revisit in a proper audit-then-implement
  follow-on set).
- **Q1 bypass-rate fraction computation** — observation log only
  started 2026-05-24; needs 1–2 weeks of data before a meaningful
  fraction renders. Lands as a follow-on patch once the log has
  accumulated.

# Set 029 Session 5 — review

**Date:** 2026-05-19
**Orchestrator:** Claude Code (Claude Opus 4.7 @ effort=high)
**Verifier:** Gemini Pro (pinned per S3/S4 escape pattern)

## Summary

Session 5 ships multi-provider orchestrator-detection feature-
completeness for v0.17.0:

- **Codex auto-detect** via `~/.codex/config.toml` watcher
  ([src/codex/configWatcher.ts](../../../../tools/dabbler-ai-orchestration/src/codex/configWatcher.ts), 213 LOC)
- **Universal manual-override quickpick** with MRU + multi-step +
  hotkey args + force-override confirmation
  ([src/commands/setOrchestratorManual.ts](../../../../tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts), 533 LOC) — replaces the S2 stub
- **Gemini + Copilot installer-shim commands** (24 + 27 LOC) that
  delegate to the universal quickpick
- **Smart empty-state CTA detection** in the accordion empty state
  ([src/providers/detectOrchestrators.ts](../../../../tools/dabbler-ai-orchestration/src/providers/detectOrchestrators.ts), 136 LOC)
- Integration diffs in `OrchestratorAccordion.ts`,
  `CustomSessionSetsView.ts`, `client.js`, `package.json` contributes
- Version bump 0.16.0 → 0.17.0; CHANGELOG.md + CLAUDE.md updated
- 3 Playwright scenarios + 6 Layer-2 unit suites (21 new tests)

## Verification

Two-round verification per memory `feedback_split_large_verification_bundles`:

| Round | Scope | Bundle size | Cost | Verdict |
|---|---|---|---|---|
| A | configWatcher + detectOrchestrators + shims + integration diffs | 752 lines / 27.5k chars | $0.019 | All 7 questions VERIFIED |
| B | setOrchestratorManual.ts (manual-override quickpick) | 699 lines / 24k chars | $0.016 | All 7 questions VERIFIED + 2 SUGGEST |

**Total verification cost: $0.035** — well under the $0.10–$0.30
forecast. Both rounds converged cleanly without MUST-FIX items.

### SUGGEST items (deferred to hygiene PR / S6 fold-in)

1. **MRU file race condition** (round B): `pushMru` is a
   read-modify-write without serialization. Realistic UI-bound
   concurrency window is essentially zero (operator can't fire
   `dabbler.setOrchestrator` twice within milliseconds), so SUGGEST
   not MUST-FIX. If we ever wire programmatic callers, revisit.
2. **Sync fs in `readCurrentMarkerForWorkspace`** (round B): uses
   `statSync` / `readdirSync` / `readFileSync` on the
   force-override prompt path. Same UI-bound pattern as #1 — not
   a hot path. Reasonable to revisit if the helper script grows
   an async API we can call instead of replicating the walk-up.

## Build & test results

- **`npx tsc --noEmit`**: clean (no errors, no warnings)
- **`npm run test:unit`**: 397 passing / 2 failing
  - The 2 failures are the same 2 pre-existing failures the S4
    actuals noted (`configEditor-foundation` ViewColumn stub gap,
    `notificationsSection` HTML assertion). S5's 21 new tests all
    green.

## Net code

- New source: ~933 LOC (configWatcher + manual + detection + 2 shims)
- New tests: 3 Playwright scenarios + 6 unit suites (~340 LOC tests)
- Diff: ~+1,290 LOC additions, ~-44 LOC deletions (10 files changed)
- Retired: `setOrchestratorManualStub.ts` (32 LOC, the S2 stub)

## Open follow-ups (NOT S5 ship blockers)

1. SUGGEST items 1+2 above — MRU mutex + async fs.
2. Spec.md Session 6 step 0 added mid-session per operator request
   (2026-05-19): HTML-preview iteration cycle for explorer styling,
   mirroring the v0.14.2 gauge-styling iteration that ran for ~11
   rounds. Memory `project_029_s6_html_preview_iteration` records
   the request.
3. S6's spec already calls out: README screenshot, CHANGELOG
   consolidation, CLAUDE.md expansion, marketplace publish (only
   after the HTML-preview iteration converges).

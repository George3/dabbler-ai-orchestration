# Set 051 Change Log

**ai_router Hygiene & Dead-Code Audit — audit & removal-plan lock (S1),
execute removals + packaging fixes (S2), retire the superseded Claude
`SessionStart` hook in the extension (S3), then docs + changelog + dual
version bumps + close-out (S4).**

This set arrests the slow growth of `ai_router/` by removing code proven
unreachable, fixing a broken packaging entry point, and consolidating
scattered tests — **without touching any live code path** (the one
deliberate behavior change is S3's retirement of a superseded,
non-load-bearing convenience hook). Audit-first: nothing was deleted
until a session proved zero live callers. The largest target was the
`ai_router/joiner/` subpackage + `dabbler_launch.py`, orphaned when Set
049 reverted the Explorer harvest surface (its only live caller,
`HarvestService`). The extension's Set 050 Claude-only `SessionStart`
hook was retired because Set 053 moved schema-drift detection into the
router session lifecycle (`summarize_drift`), which fires for every
orchestrator on every host.

The audit-locked spec at [`spec.md`](spec.md) scopes 4 sessions. S1
proposal + verdict at
[`docs/proposals/2026-05-29-ai-router-hygiene/`](../../proposals/2026-05-29-ai-router-hygiene/).
Companion PyPI release: `dabbler-ai-router 0.14.0`. Companion Marketplace
release: `DarndestDabbler.dabbler-ai-orchestration 0.26.0`.

## Session 1 — Audit & removal plan

Closed 2026-05-29 with disposition `completed`.

- Re-ran the usage scan; proved the joiner/`dabbler_launch` orphan claim
  (no reflective load, no `__init__` re-export, no entry-point or
  consumer caller). Two-pass devil's-advocate cross-provider consensus
  (`gemini-pro` + `gpt-5-4`) over the 6 open design questions.
- **Verdict (LOCKED):** delete the island outright (no `_archived/`;
  both providers judged it an anti-pattern) but **salvage the D3
  writer-bypass detector first** (both providers' single strongest
  objection — Set 049 deliberately retained it); repoint/fix the
  `backfill` entry point + add an entry-point acceptance test; move the
  two stray `scripts/test_*` files to `tests/`; add a wheel-contents
  regression assertion; keep the four migrators split (no logic merge);
  **drop the proposed `migrate --from/--to` front door** in favor of
  docstrings + `MIGRATIONS.md` (Q6 disposition changed — both judged the
  engine over-engineering). New scope added: V8 live-docs reconciliation,
  V9 dependency audit. The audit added a 4th session for the hook
  retirement.
- S1 routed cost: **$0.0272** of $10 NTE (0.27%).
- Commits:
  [`6565e2e`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/6565e2e)
  (audit + consensus + locked plan) and close-out artifacts
  ([`cea2555`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/cea2555),
  [`dccb272`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/dccb272),
  [`1b55cd3`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/1b55cd3),
  [`0a9ad62`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/0a9ad62)).

## Session 2 — Execute removals + packaging fixes

Closed 2026-05-30 with disposition `completed`.

- **Deleted the island** (V1): `ai_router/joiner/` (7 files) +
  `dabbler_launch.py` + 7 dead tests (~3,734 LOC). Parent tagged
  `pre-joiner-removal` for zero-cost recovery.
- **Salvaged D3** (V2): new self-contained `ai_router/writer_discipline.py`
  (`detect_writer_bypass` + the needed island symbols inlined; no
  `joiner` import) + `test_writer_discipline.py`.
- Added `test_packaging_hygiene.py` (V6 wheel-contents guard) +
  `test_entry_points.py` (V3 entry-point acceptance) + `MIGRATIONS.md`
  (V7). Dependency audit (V9): nothing droppable.
- **Two deviations from the locked verdict** (flagged for the S4
  verifier): (1) V3 — *retired* the broken `backfill` entry point rather
  than repointing it, because `scripts/` has no `__init__.py` and is
  excluded from the wheel, so the declared target is not importable from
  an installed package either (repointing would still ship a broken
  console script — an empirical correction in the spirit of Set 050 S2's
  three-migrator fix). (2) V4 — the two stray `scripts/` tests had never
  run (`pytest.ini` `testpaths` excluded `scripts/`) and were bit-rotted;
  on operator direction (relocate **and fix**) the fix surfaced three
  latent bugs in the live `scripts/` utilities (`_FIELD_COMMENTS` carried
  7 legacy v4-dropped keys; both utilities' `sys.path` bootstrap inserted
  the wrong dir) — corrected, so "runnable from a source checkout" is now
  true.
- Suite 1029 passed / 1 skipped; wheel `dabbler_ai_router-0.13.0`
  inspected clean.
- No router invoked; $0 added.
- Commits:
  [`f0797ad`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/f0797ad)
  (removals + packaging + relocations),
  [`f820616`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/f820616),
  [`4eee949`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/4eee949),
  [`ba6b71d`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/ba6b71d).

## Session 3 — Retire the superseded Claude `SessionStart` hook (extension)

Closed 2026-05-30 with disposition `completed`.

- **Premise re-verified before deleting:** Set 053's `summarize_drift`
  is imported and called in both `ai_router/start_session.py` and
  `close_session.py`, so retiring the Claude-only hook loses no drift
  coverage — it removes a redundant, divergence-prone duplicate. (The
  `close_session` gate run itself emitted the Set 053 drift advisory —
  live-mechanism confirmation.)
- **Deleted (4 files):** `scripts/claude-session-start-invoker.js` (incl.
  its `scanSchemaDrift` + `CURRENT_SCHEMA_VERSION`),
  `src/commands/installOrchestratorHookClaudeCode.ts` (installer command
  + "Copy manual setup" toast), `ai_router/tests/test_invoker_schema_constant.py`
  (dead JS-constant pin), and `src/test/suite/claudeSessionStartInvoker.test.ts`
  (the Layer-2 suite that dynamic-imported the deleted JS — a
  spec-implied consequence, flagged for the S4 verifier).
- Removed the `package.json` command contribution + `extension.ts`
  import/wiring; bumped the `watcherInventory.test.ts` allowlist line pin
  154→153 for the one-line import shift (no watcher added/removed);
  recompiled the dist bundle.
- Reconciled docs as historical pointing at the Set 053 lifecycle
  advisory (CLAUDE.md, `ai-led-session-workflow.md`,
  `session-state-schema.md`, `cross-repo-migration-guard-notice.md`
  superseded banner); created `docs/cross-repo-hook-retirement-notice.md`
  (consumer/operator remediation — documents removing the
  `~/.claude/settings.json` `SessionStart` entry; does not edit machine
  settings).
- Python 1028 passed / 1 skipped (−1 = the deleted pin test); TS `tsc`
  clean + `test:unit` 554 passing with only the 2 known pre-existing
  Set-026 scaffolding failures.
- No router invoked; $0 added.
- Commits:
  [`d533b28`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/d533b28)
  (hook retirement),
  [`dac7a22`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/dac7a22),
  [`44e8455`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/44e8455).

## Session 4 — Docs, changelog, version bumps, close-out

Closed 2026-05-30 with disposition `completed`.

- **`ai_router/CHANGELOG.md`** — new `[0.14.0]` entry (joiner/island
  removal, D3 salvage, backfill entry-point retirement, stray-test
  relocation + the three latent fixes, wheel/entry-point guards,
  `MIGRATIONS.md`, dependency audit). **Extension `CHANGELOG.md`** — new
  `[0.26.0]` entry (Claude `SessionStart` hook retirement).
- **Live-docs reconciliation finished (V8):** corrected the remaining
  present-tense `ai_router/joiner/` references in `CLAUDE.md` (the
  post-Set-049 contract section + the historical Set-049 walk entry) and
  `docs/ai-led-session-workflow.md` to point D3 at
  `ai_router/writer_discipline.py` and record the joiner subpackage's
  Set 051 S2 removal. (`narration-templates.md` +
  `cross-repo-harvest-notice.md` already carried Set 051 "removed"
  banners from S2.)
- **Dual version bumps:** `dabbler-ai-router` 0.13.0 → **0.14.0**
  (`pyproject.toml` + `__init__.__version__`); extension 0.25.0 →
  **0.26.0** (`package.json` + `package-lock.json`); the `CLAUDE.md`
  version walk; this set-level change-log. (The intervening ai_router
  `0.13.0` shipped by Set 053 was never tagged to PyPI; the single
  `0.12.0 → 0.14.0` release carries both sets.)
- Cross-provider verification of the whole set (scrutinizing the S2
  V3/V4 deviations + the S3 spec-implied `claudeSessionStartInvoker.test.ts`
  deletion + the watcher-allowlist line bump).
- Publishes **held** for operator-initiated tag-push per established
  release discipline (`v0.14.0` for PyPI; `vsix-v0.26.0` for
  Marketplace). Note: `VSCE_PAT` was expired 2026-05-28 — confirm PAT
  freshness before pushing the vsix tag.

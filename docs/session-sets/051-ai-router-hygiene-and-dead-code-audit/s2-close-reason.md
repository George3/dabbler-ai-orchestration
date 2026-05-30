Set 051 Session 2 (2 of 4) close-out — execute ai_router removals + packaging fixes.

Executed the S1 audit-locked plan (verdict.md V1-V9). Commit 59e2405.

V1 — Deleted the orphaned joiner/dabbler_launch island: ai_router/joiner/
{__init__,__main__,cli,conflicts,coverage,parsers,schema}.py +
dabbler_launch.py + 7 dead tests (15 files, ~3,734 LOC). pre-joiner-removal
tag preserved for recovery; removed the now-empty joiner/ dir (the V6
hygiene test caught it lingering).

V2 — Salvaged the D3 writer-bypass detector BEFORE deleting conflicts.py
(both providers' #1 objection; operator-confirmed). New self-contained
ai_router/writer_discipline.py (no residual joiner import) inlining
detect_writer_bypass + SessionStateView/scan_session_states/parse_iso/
canonicalize_cwd, with test_writer_discipline.py.

V3 — EMPIRICAL CORRECTION to the locked verdict (flag for S4 verifier):
the verdict said REPOINT backfill_session_state -> ai_router.scripts.
backfill_session_state:main. I confirmed empirically that ai_router/scripts/
has no __init__.py and pyproject sets namespaces=false, so
`import ai_router.scripts.backfill_session_state` raises ModuleNotFoundError
even from the built wheel — repointing would still ship a broken console
script. Disposition changed to RETIRE the entry point (it never resolved
since Set 021). The v1->v2 utility stays runnable from a source checkout
(now actually true — see V4 bootstrap fix). New test_entry_points.py
import-checks every remaining [project.scripts] target.

V4 — Relocated the two stray scripts/ tests into ai_router/tests/. They
NEVER RAN (pytest.ini testpaths=ai_router/tests excluded scripts/), so
relocating them surfaced real latent issues. Operator chose "relocate +
fix all" (AskUserQuestion) over the prior turn's silent delete. Fixed:
  * dump_session_state_schema.py _FIELD_COMMENTS still carried the 7
    legacy top-level keys dropped at the Set 047 v4 migration -> trimmed
    to the 5 canonical v4 keys (+ the missing 'sessions' comment).
  * BOTH scripts/ utilities had a broken standalone sys.path bootstrap
    (inserted the script's own dir; session_state lives one level up in
    ai_router/) -> corrected parent -> parent.parent. `python
    ai_router/scripts/<util>.py` now actually runs in both source-checkout
    and installed-wheel layouts; the pyproject "runnable from a source
    checkout" claim is now true (was false).
  * Updated test_session_state_backfill.py's stale pre-v4 assertions
    (legacy top-level shape; mtime-derived completedAt) to v4 shape.
  * conftest.py adds ai_router/scripts to sys.path for the relocated
    bare-filename imports.

DEVIATION-FROM-NON-GOAL NOTE for S4 verifier: the spec's non-goal says
"No behavior changes to any live ai_router code path." The two sys.path
bootstrap fixes (V4) ARE behavior changes — but to already-broken
standalone-execution paths that no caller could have used (they
ModuleNotFoundError'd). They make a documented-but-false capability true.
Judged in-scope hygiene under the operator's relocate+fix direction;
flagged here for explicit scrutiny.

V5 — Kept the four migrators split (no logic consolidation).
V6 — test_packaging_hygiene.py regrowth guard (no test_* outside tests/;
dead modules stay removed; wheel-exclude config present).
V7 — MIGRATIONS.md documents the version-specific migrator sequence; the
four migrator docstrings already state from->to. --from/--to front door
dropped per consensus.
V8 — Marked cross-repo-harvest-notice.md (SUPERSEDED) and
narration-templates.md (joiner consumer removed) as historical so no
release documents the deleted dabbler_launch/joiner CLIs as live.
V9 — Dependency audit: deleted code used only stdlib; pyyaml/httpx used
broadly -> no pyproject dependency droppable.

VERIFICATION: MANUAL. Quality bar per spec = existing suite stays green
(minus tests removed with their dead code) + wheel inspection. Results:
- Full suite: 1029 passed, 1 skipped (was ~952 pre-set; +50 relocated/new
  hygiene tests minus 7 deleted joiner tests).
- Wheel built (dabbler_ai_router-0.13.0) + inspected: no test_*.py ships
  (F3 resolved); joiner/ + dabbler_launch.py absent; writer_discipline.py
  + 4 console scripts present; backfill entry point absent.
- Empirical validations: standalone `python ai_router/scripts/{dump,
  backfill}*.py` now run; `import ai_router.scripts.backfill_session_state`
  confirmed non-importable (validates the V3 retire).
Cross-provider verification of the whole set (incl. these V3/V4 deviations)
is scoped to S4 per the spec.

COST: S2 invoked no router (all local work) — $0 routed this session.
Cumulative set spend: $0.0272 of $10 NTE (0.27%, from S1 consensus).

NEXT (S3): retire the superseded Set 050 Claude SessionStart hook in the
extension (invoker JS + installer command + dead test_invoker_schema_
constant.py); drift coverage rides Set 053's lifecycle advisory. Extension
change -> Marketplace release.

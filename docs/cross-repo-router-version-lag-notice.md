# Cross-repo notice — stale installed `dabbler-ai-router` masks shipped fixes (verificationVerdict case)

**Authored:** 2026-06-12 (Set 063 Session 3, operator-reported consumer incident)
**Audience:** every consumer repo's operator and agent-instruction
authors (dabbler-platform, dabbler-access-harvester,
dabbler-homehealthcare-accessdb, and any consumer not yet listed).

## The incident

A consumer repo observed `close_session` leaving per-session
`verificationVerdict: null` in `session-state.json` for **every**
session of a set, even though each close's `disposition.json` carried
`verification_verdict: "VERIFIED"`. The consumer's diagnosis was
correct: the workspace `.venv` had **`dabbler-ai-router` 0.10.0**
installed, which predates the verdict-persistence feature
(`resolve_close_verdict`, shipped in **0.15.0**, Set 054, 2026-06-02).
The canonical code is sound — the same code path persists `VERIFIED`
correctly on current versions (re-confirmed on 0.18.0, 2026-06-12).

The root hazard is general: consumer requirement pins use `>=`
(e.g. `dabbler-ai-router>=0.10.0`), and `pip install` **never
upgrades** an already-satisfied `>=` pin. A consumer venv silently
ages while the canonical repo ships fixes, and the failure presents as
"the feature is broken," not "my install is old."

## Remediation (per consumer repo, one-time)

1. **Check the installed version** against PyPI:

   ```bash
   .venv/Scripts/pip show dabbler-ai-router   # POSIX: .venv/bin/pip show ...
   ```

2. **Upgrade** (either path):
   - VS Code: run **`Dabbler: Update ai-router`** from the command
     palette; or
   - CLI: `.venv/Scripts/pip install -U dabbler-ai-router`

3. **Historical sessions stay null.** The upgrade fixes persistence
   for closes from now on; it does not rewrite history. Already-closed
   sessions whose verdict was lost can either be left `null` (honest
   "not recorded by the closing version") or hand-backfilled: each
   session's raw verdict is preserved in its
   `docs/session-sets/<slug>/sN-verification*.md`, and the per-session
   `verificationVerdict` field may be set to that exact token
   (`"VERIFIED"` / `"ISSUES_FOUND"`) by hand. Hand-backfill is
   cosmetic; nothing gates on historical verdicts.

4. **What a clean upgrade looks like.** 0.10.0 → 0.18.0 is a
   read-compatible jump: state-file reads route through the
   `normalize_to_v4_shape` shim (accepts v1/v2/v3/v4), so existing
   sets render unchanged in the Explorer and `get_progress`. Two new
   behaviors are expected, both benign: (a) `start_session` /
   `close_session` may print the one-line **schema-drift advisory**
   when older sets are below schema v4 — non-blocking, fail-open;
   run `python -m ai_router.check_migrations --verbose` to review,
   and migrate on your own schedule; (b) closes now persist
   `verificationVerdict` per
   [`docs/session-state-schema.md`](session-state-schema.md). If
   anything *else* changes shape on disk after the upgrade, that is a
   defect — report it.

5. **Recommended habit until tooling exists:** when a router-side
   behavior looks broken in a consumer repo, compare
   `pip show dabbler-ai-router` against the canonical
   [release status](repository-reference.md#current-release-status)
   **before** filing it as a code defect.

## Why no automated guard ships with this notice

A runtime "installed version is N releases behind PyPI" advisory needs
a network call (or a cached index) inside the `start_session` /
`close_session` lifecycle, with offline and fail-open semantics — a
design question, not a hotfix. It is recorded as a follow-up set
candidate in this set's close-out; until then this notice and the
habit in step 5 are the mitigation.

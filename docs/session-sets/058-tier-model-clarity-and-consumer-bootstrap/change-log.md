# Change Log — Set 058: Tier-model clarity & consumer-repo bootstrap

**Status:** COMPLETE (3 of 3 sessions) — 2026-06-09
**Release:** Extension `0.28.0` (Marketplace, held for operator tag-push
`vsix-v0.28.0`). No companion PyPI release — the packaged `ai_router` surface
was unchanged this set; `dabbler-ai-router 0.16.0` (Set 057) remains held.

## Why this set existed

A human scaffolded a new **Lightweight** consumer repo and was left stuck: no
engine files, no `.venv`, generated specs missing the `tier:` field, and no
next step. The root cause was one architectural drift — four setup surfaces
still encoded a stale, pre-Set-048 tier model. The code-verified truth
(`ai_router/runtime_mode.py`): **Lightweight is router-off, not Python-off;
`tier:` in `spec.md` is the single declarative switch; `start_session`,
`close_session`, the blessed writer, state derivation, and the close-out gate
all still run.** This set reconciled every setup and documentation surface to
that truth and made it un-driftable.

## What shipped

### Session 1 — Canonical contract + documentation SSoT (docs/templates only)

- `docs/concepts/tier-model.md` — the single source of truth for the tier model
  (router-off-not-Python-off; what is the same across tiers; the one
  divergence; runtime resolution; a banned-framing catalogue).
- The canonical consumer-bootstrap template bundle under
  `docs/templates/consumer-bootstrap/` — `spec.md.template` (schemaVersion 4,
  `NNN-` slug, required `tier` + `verificationMode`), `session-state.json.template`,
  `start-here.md.template` (the cold-start operative doc with the verbatim
  active-set-resolution rule), and the three engine files (one shared body +
  per-engine tails).
- `tier` + `verificationMode` documented in `docs/spec-md-schema.md`.
- `README.md`, `docs/adoption-bootstrap.md`, `docs/quick-start.md`, and the
  Get Started wizard reduced to pointers into the SSoT; stale framing scrubbed.

### Session 2 — Extension code: shared writer, scaffolder, generator, wizard

- `src/utils/consumerBootstrap.ts` — one shared template writer rendering the
  six consumer artifacts from the bundle (token substitution, N-session
  expansion, CRLF normalization, a `totalSessions >= 1` guard). esbuild copies
  the canonical bundle into `dist/templates/consumer-bootstrap/`; the `.vsix`
  ships it (`vsce ls`-verified).
- `gitScaffold.ts` (`dabbler.setupNewProject`) — uniform tier-aware scaffolding:
  both tiers get `.venv` + `pip install dabbler-ai-router` + the three engine
  files + `start-here.md` + a templated `spec.md`; **only** Full writes router
  config (the sole D3 divergence).
- `sessionGenPrompt.ts` — routes through the shared writer; emits the canonical
  shape, never the legacy `schemaVersion: 2` / bare-slug shape.
- The Get Started wizard gained an explicit "start the next session" closure (D7).

### Session 3 — Cold-start acceptance, drift CI, UAT, held release

- **Cold-start acceptance test** (`ai_router/tests/test_cold_start_acceptance.py`,
  both tiers): boots a throwaway repo from the committed golden render and walks
  engine file → `start-here.md` → active `spec.md` → tier resolved → the **real**
  `start_session.main()` entry point deriving the router mode from `tier:`
  (routed for Full, `--no-router` for Lightweight) → close via the shared gate.
- **Golden render snapshot** (`coldStartSnapshot.test.ts`): renders the writer
  output for both tiers and byte-compares it to committed goldens under
  `test-fixtures/cold-start/`; regenerate with `UPDATE_GOLDEN=1 npm run test:unit`.
- **CI drift guards** (`ai_router/scripts/drift_guard.py` + tests): (1) a
  stale-framing guard forbidding the banned "Lightweight = no Python / no venv /
  docs-only" phrasing in any live doc (with an auditable, file-allowlisted
  `<!-- drift-guard:allow-begin/end -->` escape hatch); (2) a one-active-set
  guard (≤1 in-progress set, D6); (3) a dist-bundle-in-sync guard (committed
  `dist/` bundle byte-matches the canonical source, D8). Wired into CI as a
  dedicated `drift-guards` job plus a `template-snapshot` job that enforces the
  golden snapshot.
- **Operator UAT checklist** (ad-hoc, per-set) for the end-to-end Get Started →
  scaffold → "start the next session" flow on both tiers.
- **Extension `0.28.0`** bump (held); `docs/repository-reference.md`
  release-status + version-walk updated.

## Verification

- **Session 1:** gpt-5-4 cross-provider, 3 rounds → VERIFIED.
- **Session 2:** gpt-5-4 cross-provider, 3 rounds → VERIFIED_WITH_NOTES (the lone
  R3 Major — "the .vsix may exclude `dist/templates`" — was empirically
  disproven via `vsce ls`).
- **Session 3:** gpt-5-4 cross-provider, 3 rounds → VERIFIED. R1 raised 4
  findings; 3 were fixed in-flight (CI-enforce the D8 snapshot; drive the real
  `start_session` entry rather than the internal writer + fix an overclaiming
  comment; restrict the allow-marker escape hatch to an explicit file
  allowlist) and 1 (full `repository-reference.md` staleness) was deferred as
  pre-existing and outside S3's release-status scope — a judgment the verifier
  confirmed reasonable. R2/R3 confirmed all fixes closed.

## Tests at close

- Python: 1184 passed, 1 skipped (Windows / py3.11), 0 failures.
- TS unit suite: 638 passing; 2 pre-existing Set-026 failures in untouched
  specs (`configEditor-foundation` vscode-stub `ViewColumn.One`,
  `notificationsSection` disabled-label). New snapshot specs pass.
- `python ai_router/scripts/drift_guard.py` exits 0.
- `npx vsce ls` lists all eight `dist/templates/consumer-bootstrap/` files.

## Known follow-ups (not in this set)

- `docs/repository-reference.md` has pre-existing staleness outside the
  release-status section (retired Provider Queues/Heartbeats, the old
  TreeDataProvider Session Sets view, obsolete state-derivation prose) — a full
  reconciliation is recommended as a separate docs-audit set.
- Backfilling **existing** consumer repos with engine files / `start-here.md` /
  `tier:` in their specs is operator-scoped, not automated here.
- Held releases pending operator tag-push: `vsix-v0.28.0` (this set),
  `v0.16.0` (Set 057), `v0.15.0` (Set 054).
- See `next-set-recommendation.md` (routed): a `059-release-and-stabilize` set
  to ship the held releases and validate the end-to-end UX is the recommended
  next move.

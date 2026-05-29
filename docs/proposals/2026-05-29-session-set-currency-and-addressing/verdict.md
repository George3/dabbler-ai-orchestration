# Verdict — Session-Set Currency & Addressing (Set 050 S1 audit, LOCKED)

**Date:** 2026-05-29
**Set:** `050-schema-drift-detection-and-migration-guard`
**Consensus:** devil's-advocate two-pass, `gemini-pro` + `gpt-5-4`, both passes
each. Total S1 consensus spend **$0.2829** (gemini $0.0128 + $0.0226;
gpt-5-4 $0.1167 + $0.1309). Artifacts: `pass-a-*.md`, `pass-b-*.md`,
`proposal.md`.
**Outcome:** the proposal was materially **improved** by consensus. Eight of
eleven dispositions changed; the changes are refinements, not reversals, and
all fit inside the existing 5-session structure.

---

## The one correction that mattered most

GPT-5-4 (pass-b) surfaced a flaw fatal to the proposal as written:

> "The drift check is trivial deterministic filesystem logic. It does not
> need the router at all… prefer a JS-side fallback so stale/no-router repos
> still get protection. If the router is stale/missing, `python -m
> ai_router.check_migrations` is unavailable."

The incident repo (`dabbler-access-harvester`) had an **ancient router
(0.1.1) with no `check_migrations`**. If the SessionStart drift scan
required the Python CLI, the exact repo that caused this set would still be
unprotected. **The hot-path scan must be pure Node (no router, no network),
embedded in the existing JS invoker.** This is now the locked architecture.

Both engines, across both passes, independently reached two more
convergent conclusions:
1. **Do not fetch a manifest on every session start.** Runtime truth is a
   locally-bundled constant; the GitHub manifest is *advisory*,
   off-hot-path, cached, release-coupled.
2. **A network manifest must not carry executable shell commands.** It is
   declarative only; command resolution lives in local code.

---

## Locked dispositions

### Feature 1 — schema-drift guard

**Q1 — Source of current-version truth → CHANGED (refined).**
Two distinct values, never conflated:
- `localSupportedSchemaVersion` — the schema this installation can actually
  read/write. **This is the runtime truth** for the hot-path scan and for
  `check_migrations`'s default mode. Sourced from a constant bundled into
  the JS invoker/extension, kept equal to `ai_router`'s
  `SESSION_STATE_SCHEMA_VERSION` by a CI test.
- `upstreamCurrentSchemaVersion` — what the canonical repo currently
  publishes. Sourced from `docs/schema-current.json`. **Advisory only**,
  consulted off the hot path (explicit `check_migrations --manifest-url` /
  a future Explorer "check for newer schema" action), so a stale pinned
  consumer can still *learn* a newer schema exists without a code bump —
  the original out-of-band goal, now off the startup path.

**Q2 — Network-failure posture → CHANGED (refined).**
The **hot-path scan never touches the network** (it uses the bundled
constant), so it cannot be blocked by GitHub. The *advisory* manifest
fetch is **fail-open + cached** (use cache → then local constant on
failure; warn only when falling past the cache). An opt-in
`--strict-manifest` flips advisory fetches to fail-loud for CI.

**Q3 — Manifest schema & location → CHANGED.**
`docs/schema-current.json`, **declarative only — no executable commands**:
```json
{
  "manifestVersion": 1,
  "currentSchemaVersion": 4,
  "minimumAiRouterVersion": "0.10.0",
  "schemaDocUrl": "https://raw.githubusercontent.com/darndestdabbler/dabbler-ai-orchestration/master/docs/session-state-schema.md",
  "migrationGuideUrl": "https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/v3-to-v4-rollback-procedure.md",
  "migrators": [
    { "id": "lightweight-to-v4", "fromMax": 2, "to": 4 },
    { "id": "v3-to-v4",          "fromMax": 3, "to": 4 }
  ]
}
```
Migrators are **symbolic IDs + version ranges**, not shell strings;
`check_migrations` maps an ID to the actual local CLI. **Source: raw URL on
`master`**, NOT a frozen tag — a tag pinned to the consumer's own version
reintroduces the stale-blindness this set exists to fix; a tag pinned to
"latest" is just `master` with extra steps. The tag-vs-master risk
(branch-head skew: manifest ahead of published code) is defused three ways,
so it is acceptable: (a) the manifest is **advisory, never authoritative
runtime input**; (b) **release-coupling discipline** — `currentSchemaVersion`
is bumped only in the same commit/release that ships the code, never ahead;
(c) a **CI test** asserts `manifest.currentSchemaVersion ==
SESSION_STATE_SCHEMA_VERSION` on every push so a bad/ahead manifest cannot
merge. (Recorded dissent: gemini-pro pass-b argued strongly for a frozen
tag; rejected for reason (a) — a frozen tag cannot teach a stale consumer
about a newer schema, which is the manifest's only reason to exist.)

**Q4 — Hook output contract → CHANGED (tightened).**
Hot-path default = **one summary line** when drift exists
(`⚠ N session set(s) on an older schema (current: v4) — old schema is OK; run <bulk cmd> to upgrade`),
plus up to ~5 set names then `… and N more`; **nothing** when clean. Full
per-set listing is reserved for `check_migrations --verbose` / `--json`.
Restates "old schema is acceptable" so it never reads as a nag.

**Q5 — Scan scope → STANDS.**
Single workspace root, walk-up resolved from cwd to the nearest
`docs/session-sets/`. Cross-root detection stays the Explorer's job.

**Q6 — Extension surface / install path → CHANGED.**
- The drift scan is a **separate, single-purpose concern**: pure-JS scan
  logic (its own module, independently testable) **plus** the richer
  `python -m ai_router.check_migrations` CLI. They do not depend on each
  other.
- **One** SessionStart hook (not two competing matchers). The installed
  invoker **chains two independent steps** — orchestrator session-start,
  then the JS drift scan — each independently installable/configurable.
  This satisfies both "no second hook / no ordering bugs" (gpt-5-4 pass-a)
  and "single responsibility / composable" (gemini pass-b): the *concern*
  is separate, the *hook registration* is shared.
- Install path = the **existing** `dabbler.installOrchestratorHook.claudeCode`
  command (extended to write the chained step). Narration-template command
  is NOT overloaded. Copy-paste fallback (the JS snippet + settings.json
  stanza) covers repos not running the extension — and because the scan is
  pure JS, it works with **no router installed at all**.

**Q7 — `--apply` → CHANGED (cut).**
`check_migrations` is **detect-only** — the name matches the function and
the "no silent auto-migration" non-goal stays clean. The Explorer
"Upgrade older session sets" bulk action and the documented bulk command
run the **two existing migrators in sequence**:
`python -m ai_router.migrate_lightweight_to_canonical_v4 --in-place` then
`python -m ai_router.migrate_v3_to_v4 --in-place`. Both are idempotent
no-ops on already-current files and the sequence correctly handles a v2
set that needs *both* steps (gemini pass-a risk #2). No new migrator
logic, no `--apply` mutator. An optional thin wrapper (`upgrade_sets`)
that gives a single confirm + summary is an S5 implementer's-choice nicety,
not required.

### Feature 2 — number-prefix addressing

**Q8 — Resolver matching → STANDS (minor tighten).**
Exact integer-prefix match within the active repo, leading-zeros
normalized (`50` ≡ `050-…`). No fuzzy matching. Collision (two slugs, same
numeric prefix) → error naming both (repo-authoring bug). No-match → error
listing the **available numeric prefixes** (and `--next`), not heuristic
"nearest" suggestions (gpt-5-4: nearest risks nudging to the wrong set).

**Q9 — Surfaces → CHANGED.**
Deliver **both**, not CLI-only:
- **Load-bearing:** an `ai_router` resolver consumed by `start_session`'s
  `--session-set-dir` (accepts a bare number) + a standalone
  `python -m ai_router.resolve_set <n>` / `--next`.
- **Extension affordance (the spec deliverable):** a Command-Palette
  command that takes a number via `showInputBox` quick-input and resolves
  to the slug, reusing the existing copy logic (copy slug / copy
  start-next-session prompt). Keep it minimal — one quick-input command,
  no Explorer rebuild. The Explorer already shows the full slug, which now
  begins with the number, so "Explorer surfaces the number" is satisfied
  by the `NNN-` prefix being visible. (gemini pass-b: leaving the human
  surface out is scope-dodging when the deliverable list names it.)

**Q10 — Authoring-guide reconciliation → CHANGED (reconciled split).**
Permit a monotonic zero-padded numeric **sequence** prefix; keep banning
**semantic** names (dates, `phase-3-week-2`, session counts). Authority:
- **Required** for newly-created sets in the canonical repo and any future
  scaffolder output (gpt-5-4: soft adoption leaves addressing spotty).
- **Recommended, forward-only** for consumer repos — no retroactive
  renames (gemini: avoid churn; breaks `prerequisites:` refs /
  `sessionSetName` / git history).

**Q11 — Numbering authority → STANDS (concretized).**
Next = `max(existing numeric prefix) + 1`, via
`next_session_set_number(scan_root)` returning **both** the integer and a
zero-padded string with `width = max(3, widest existing numeric prefix)`;
start at `001` when none exist. Slugs without a numeric prefix are ignored
for max-finding. No new "create set" command invented; the orchestrator
(or a future scaffolder) calls the helper.

---

## Net change list (8 of 11 changed)

| Q | Was (proposal) | Now (locked) |
|---|---|---|
| Q1 | manifest authoritative when reachable | local constant = runtime truth; manifest advisory, off-hot-path |
| Q2 | fail-open warn, fetch every start | hot path never networks; advisory fetch fail-open **+ cached** |
| Q3 | manifest carries shell commands, master | **declarative** (symbolic migrator IDs), master + release-coupling + CI guard |
| Q4 | bounded block, per-set names | **one-line** default; per-set under `--verbose`/`--json` |
| Q5 | single root walk-up | unchanged |
| Q6 | fold into invoker (Python check on hot path) | **pure-JS scan** (no router), separate concern, one chained hook |
| Q7 | `--apply` on check_migrations | **cut**; bulk = two existing migrators in sequence |
| Q8 | exact integer match | unchanged (+ list available, not "nearest") |
| Q9 | resolver in ai_router only | **+ minimal extension quick-input command** |
| Q10 | recommended everywhere | **required** for new/scaffolded; recommended (forward-only) for consumers |
| Q11 | max+1 helper | unchanged (+ zero-pad width rule) |

---

## Carried risks → S2–S5 work items

1. **Constant drift (the source-of-truth risk).** The bundled JS constant
   and `SESSION_STATE_SCHEMA_VERSION` must never diverge → **CI test
   asserting equality** (S3) + the manifest==constant test (S2).
2. **Multi-step v2 migration** (gemini pass-a #2): the bulk sequence must
   be ordered lightweight→v3→v4 and verified on a v2 fixture (S2 test).
3. **Adoption is not enforced** (both engines): the guard only protects
   repos that install the chained hook. The pure-JS fallback lowers the
   adoption bar (no router needed); the cross-repo notice (S5) carries the
   install step. Recurrence remains possible in an un-onboarded repo — an
   accepted residual.
4. **Warning fatigue** (gpt-5-4): the one-line clean-suppressed output
   (Q4) is the mitigation; revisit if operators report noise.

---

## Scope-lock for S2–S5 (refined, still 5 sessions)

- **S2 — manifest + `check_migrations` CLI (detect-only).** Declarative
  `docs/schema-current.json`; `check_migrations` (scan, compare to local
  constant, terse/`--verbose`/`--json`, optional `--manifest-url` advisory
  fetch fail-open+cached, `--strict-manifest`); symbolic-ID→local-CLI map;
  exit-code-on-drift for CI. Tests: clean / mixed v2-v3-v4 / corrupt file /
  manifest success+failure / offline fallback / **manifest==constant** /
  **v2-needs-both-migrators** sequence.
- **S3 — pure-JS hot-path scan + install path.** JS scan module (no
  router/network, bundled current-version constant), wired as a chained
  step in `claude-session-start-invoker.js`; extend
  `installOrchestratorHook.claudeCode` to write it; **CI test:
  JS constant == `SESSION_STATE_SCHEMA_VERSION`**; copy-paste fallback;
  no-router/stale-router graceful message; invoker + install tests.
- **S4 — Feature 2.** Authoring-guide wording (required-for-new / recommended-
  for-consumers split); `resolve_set` + `next_session_set_number`;
  `start_session --session-set-dir <n>`; minimal extension quick-input
  resolver command; match/collision/no-match/`--next`/zero-pad-width tests.
- **S5 — rollout, Explorer UX, close-out.**
  `docs/cross-repo-migration-guard-notice.md`; Explorer UX (asterisk +
  "Ran under schema v\<N\>" tooltip replacing `(needs migration)`;
  title-bar "Upgrade older session sets" running the two-migrator sequence,
  gated on sub-current sets existing); harvester first-adopter install
  (operator-scoped); publish held v0.24.1 Copy-Slug fix; version bumps +
  CHANGELOG + CLAUDE.md walk + change-log; cross-provider verification;
  publishes held for operator tag-push.

**`requiresUAT`:** stays **`false`**. Reconsidered post-consensus: the
Explorer change is a small render tweak (asterisk/tooltip + one title-bar
icon) fully covered by Layer-3 Playwright; neither engine called for a UAT
flag and the operator-directed framing is explicitly "less intrusive, not
more ceremony." If S5 finds the title-bar bulk action grows a multi-step
confirm UX, S5 re-evaluates `"suggested"` at that point.

---

## Consensus journal

Recorded to `ai_router/consensus-decisions.jsonl` (category
`spec-clarification`, agreement level `partial` — convergent direction,
several author dispositions flipped; applied, no operator escalation
needed). See that line for the per-call token/cost breakdown.

# Proposal — Session-Set Currency & Addressing (Set 050 S1 audit)

**Date:** 2026-05-29
**Author (Pass-A orchestrator):** Claude Opus 4.8
**Set:** `050-schema-drift-detection-and-migration-guard`
**Status:** draft for cross-provider consensus (devil's-advocate two-pass)

This proposal records the orchestrator's *recommended* disposition for each
of the eleven open design questions in `spec.md`. It is the input to the
S1 cross-provider consensus pass; the locked answers live in `verdict.md`.

---

## Context the audit must respect

- **The incident.** `dabbler-access-harvester` hand-authored two
  `session-state.json` files at `"schemaVersion": 2` on 2026-05-29 while
  its other 45 sets were v4. Root cause: no `SessionStart` hook + an
  ancient pinned router (0.1.1), so the AI orchestrator wrote the shape
  *from memory* and only fetched the canonical schema doc (a GitHub
  **blob** URL) when it remembered to. It did not. **Relying on AI memory
  or on the AI remembering to fetch a URL is the failure mode this set
  eliminates.**
- **Old schema is acceptable (operator-directed 2026-05-29).** The
  `normalize_to_v4_shape` reader shim (`ai_router/progress.py:312`)
  consumes v1/v2/v3/v4 transparently. A set on an older schema is *not*
  broken. Therefore: **no forced per-set migration, no per-row nagging.**
  Replace the intrusive `(needs migration)` row text with an unobtrusive
  asterisk + "Ran under schema v\<N\>" tooltip, plus one repo-level bulk
  "Upgrade older session sets" action.
- **No new migrator logic.** `migrate_v3_to_v4` (`.v3.bak.json` backup)
  and `migrate_lightweight_to_canonical_v4` (`.lwbak.json` backup)
  already exist and both scan `docs/session-sets/*` with
  `--scan/--in-place/--only/--json`. This set *surfaces and orchestrates*
  them.
- **Cost discipline.** The drift check is a **non-LLM deterministic
  script**, never a routed call (`feedback_ai_router_usage`). The only
  router spend this set incurs is this S1 consensus + end-of-session
  verification.
- **Canonical current-version fact** already lives in code:
  `SCHEMA_VERSION_V4 = 4` (`ai_router/progress.py:31`), re-exported as
  `ai_router.SESSION_STATE_SCHEMA_VERSION`. The manifest must agree with
  this constant; a test should assert they never diverge.

---

## Feature 1 — Schema-drift guard

### Q1 — Source of "current version" truth

**Recommend: BOTH — GitHub manifest authoritative when reachable, the
installed-router constant as the offline fallback.**

The incident was *a stale local router*. If truth lived only in the
installed router, a consumer pinned to 0.1.1 would never learn that v4
exists — exactly the regression. So the authoritative source must be a
**fetchable** artifact (`docs/schema-current.json` on `master`, raw URL).
But a transient network failure must not blind the check, so when the
manifest is unreachable the CLI falls back to the locally installed
router's `SESSION_STATE_SCHEMA_VERSION` constant and says so. A unit test
asserts manifest `schemaVersion` == local constant in *this* repo so they
can never silently drift here at the source.

### Q2 — Network-failure posture

**Recommend: FAIL OPEN with a visible one-line warning.**

A SessionStart hook that blocks because GitHub is briefly unreachable
would be worse than the disease — it would make every session fragile.
On manifest-fetch failure the CLI prints `⚠ could not reach schema
manifest (<reason>); using locally-known schema v<N>` and proceeds on the
local constant. Exit code stays 0 on network failure (the *drift* exit
code is separate, Q-CLI-contract). A `--strict-manifest` opt-in can flip
this to fail-loud for CI, but the default and the hook are fail-open.

### Q3 — Manifest schema & location

**Recommend:** `docs/schema-current.json` at the canonical repo, fetched
via **raw** URL on `master` (not a blob URL — the blob URL is what the
harvester orchestrator couldn't machine-fetch; not a pinned tag — the
manifest is forward-compatible and a tag would freeze consumers to a
stale schema, reintroducing the very problem). Shape:

```json
{
  "manifestVersion": 1,
  "currentSchemaVersion": 4,
  "schemaDocUrl": "https://raw.githubusercontent.com/darndestdabbler/dabbler-ai-orchestration/master/docs/session-state-schema.md",
  "migrationGuideUrl": "https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/v3-to-v4-rollback-procedure.md",
  "migrators": [
    {
      "fromMax": 2,
      "to": 3,
      "command": "python -m ai_router.migrate_lightweight_to_canonical_v4 --in-place",
      "note": "v1/v2 and non-canonical Lightweight shapes → canonical v3/v4."
    },
    {
      "fromMax": 3,
      "to": 4,
      "command": "python -m ai_router.migrate_v3_to_v4 --in-place",
      "note": "v3 → v4 (also sweeps post-049 orchestrator-block fields)."
    }
  ]
}
```

Migrators are an **ordered chain** keyed by `fromMax` (the highest
schemaVersion the step applies *up to*), not a flat map, because the real
migrators are range-based (anything ≤2 goes through the Lightweight
migrator; 3 goes through the v3→v4 migrator). `manifestVersion` lets the
manifest schema itself evolve. Both migrator commands already accept
`--scan`/`--only`, which the CLI appends for per-set or bulk runs.

### Q4 — Hook output contract

**Recommend: TERSE by default; structured + bounded.**

This runs at *every* session start, so token budget matters. Contract:

- **No drift:** a single quiet line — `✓ session sets on current schema
  (v4)` — or, under `--quiet`, nothing. (Hook uses the quiet success.)
- **Drift found:** a bounded block, never the full guide:
  ```
  ⚠ 2 session set(s) on an older schema (current: v4)
    • harvester-cli-distribution — v2
    • harvester-manifest-index-and-batch-readiness — v2
  Old schema is acceptable; the reader shim consumes it. To upgrade all:
    python -m ai_router.migrate_lightweight_to_canonical_v4 --in-place && python -m ai_router.migrate_v3_to_v4 --in-place
  Details: <migrationGuideUrl>
  ```
- Caps at the first ~10 drifted sets, then `… and N more` so a wildly
  out-of-date repo can't blow the context budget.
- The message restates **"old schema is acceptable"** so the hook does
  not read as a nag — consistent with the operator directive.

### Q5 — Scan scope

**Recommend: SINGLE workspace root, walk-up resolved from cwd.**

The hook only sees its own repo. It resolves the repo root by walking up
from cwd to the nearest `docs/session-sets/` (reuse the
`claude-session-start-invoker.js` walk-up pattern), then scans
`docs/session-sets/*/session-state.json`. Cross-root detection across a
merged multi-root VS Code workspace stays the **Explorer's** job (it
already enumerates all roots). One scope, one responsibility per surface.

### Q6 — Extension surface / install path

**Recommend: FOLD the check into the existing SessionStart invoker; do
NOT add a new hook and do NOT overload the narration-template command.**

A `SessionStart` hook already exists and already walks up + runs at
session start: `scripts/claude-session-start-invoker.js`, installed by the
`dabbler.installOrchestratorHook.claudeCode` command. Adding a *second*
SessionStart hook would double the startup work and risk ordering bugs.
Instead the invoker gains a second step: after spawning `start_session`,
it runs `python -m ai_router.check_migrations --quiet-when-clean` and
relays the output into the session context. The **install path is the
command that already installs that hook** — no new command, no narration
overload (narration writes CLAUDE.md/AGENTS.md, a different concern). A
copy-paste fallback (the invoker snippet + the settings.json stanza)
covers repos not running the extension.

**Explorer UX (operator-directed, separate from the hook):** replace the
`(needs migration)` description in `SessionSetsModel.ts:17` with an
asterisk on the row + a `tooltip`/`MarkdownString` "Ran under schema
v\<N\>"; remove the per-row `migrate`/`migrateToV4` flat actions as an
*obligation* (they may survive as right-click escape hatches) and add a
single **view title-bar** action "Upgrade older session sets" (a
`menus.view/title` contribution gated `when` sub-current sets exist) that
shells the bulk migrator chain once across all drifted sets.

**`requiresUAT`:** the Explorer asterisk/tooltip/title-bar-icon *is* a
rendered surface, so I recommend flipping `requiresUAT: false → "suggested"`
for the Explorer bits only, covered by Layer-3 Playwright (asterisk
renders, tooltip text, icon enable/disable + dispatch). The hook + CLI
have no rendered surface and stay test-by-pytest. (Open for consensus —
the change is small; "suggested" not "true".)

### Q7 — `--apply` convenience

**Recommend: the hook is DETECT-ONLY (locked non-goal); add an opt-in
`--apply` to the *CLI* that dispatches each drifted set to the correct
migrator, default OFF, confirmation required when run on a TTY.**

The Explorer's "Upgrade older session sets" bulk action needs *something*
to invoke; rather than the Explorer reimplementing the per-set
v2-vs-v3 routing, `check_migrations --apply` does it: for each drifted
set it picks the migrator by current schemaVersion (≤2 → Lightweight
migrator, 3 → v3→v4 migrator) and runs it `--in-place --only <set>`,
preserving each migrator's existing `.bak` contract. Default off; the
hook never passes `--apply`; on a TTY `--apply` confirms unless
`--yes` is given. This keeps "detect and instruct" the default while
giving the operator one button that does the safe, reversible thing.

---

## Feature 2 — Number-prefix addressing

### Q8 — Resolver matching rules

**Recommend: exact integer-prefix match within the active repo,
leading-zeros normalized.** Parse the leading `\d+` from each slug;
compare as integers so `50` ≡ `050-…`. No fuzzy/partial matching (integer
equality is unambiguous). No-match → a clear error listing the nearest
numbers. Collision (two slugs with the same numeric prefix in one repo)
is a repo-authoring error → error out and name both. Cross-repo
collisions don't exist for the resolver because it is **per-repo** (scoped
to one `docs/session-sets/`); the merged multi-root Explorer view is the
only place two repos' "Set 50" coexist and the Explorer already shows
full slugs, so no resolution happens there.

### Q9 — Surfaces the handle applies to

**Recommend: the primary resolver lives in `ai_router` and is consumed by
`start_session`'s `--session-set-dir` (accept a bare number) plus a
standalone `python -m ai_router.resolve_set <n>`; the AI-orchestrator
convention ("Set 50" / "the next session of 50") is documented; the
extension copy-prompt commands are NOT changed (they already operate on a
clicked row that carries the full slug).**

The buildable, load-bearing piece is the **CLI-side** resolver: the
orchestrator runs `start_session --session-set-dir 50` and it resolves to
the full path. That is where a number actually needs to become a slug.
The copy-prompt commands take their slug from the right-clicked row — they
have no number-input surface to add without inventing a text prompt, which
is scope creep. The trigger phrase stays `Start the next session of
\`<slug>\`.` as the canonical *written* form, but the orchestrator (and
`start_session`) additionally **accept** a bare number. This keeps
Feature 2 mostly convention + one small resolver, not a UI rebuild.
(Open for consensus: whether to also teach `copySlug`/the Explorer a
number badge — I lean *no* for this set, forward as a follow-up.)

### Q10 — Authoring-guide reconciliation

**Recommend: permit a monotonic zero-padded numeric *sequence* prefix;
keep banning *semantic* names (dates, `phase-3-week-2`).** Proposed
wording added to `docs/planning/session-set-authoring-guide.md` slug
section:

> A monotonic, zero-padded numeric **sequence** prefix (`050-`) that
> encodes only creation order is **recommended**. It is not a semantic
> name — it carries no meaning beyond "this set came after 049" — so it
> does not violate the rule below. What remains banned is encoding
> *content* in the slug: dates (`2026-05-29-…`), phase/week descriptors
> (`phase-3-week-2`), or session counts. The descriptive part still
> follows the prefix (`050-schema-drift-detection-…`).

**Mandatory vs recommended:** **recommended** for consumer repos
(forward-only, no enforcement, no mass-rename) to avoid the churn this set
explicitly avoids. This repo already follows it; consumers adopt going
forward.

### Q11 — Numbering authority per repo

**Recommend: next number = (max existing numeric prefix) + 1, computed by
a helper `next_session_set_number(scan_root)` in `ai_router`; surface it
via the standalone resolver CLI (`python -m ai_router.resolve_set
--next`).** Do **not** invent a new "create set" command — none exists
today; set creation is an orchestrator action (it writes `spec.md` +
scaffolds the dir). The orchestrator calls the helper to learn the next
number. If the extension later grows a "new set" scaffolder it reuses the
same helper. Slugs without a numeric prefix are ignored for max-finding
(so a mixed repo still computes a sane next number).

---

## Recommended S2–S5 scope (unchanged from spec, confirmed)

- **S2** — `docs/schema-current.json` manifest + `python -m
  ai_router.check_migrations` (scan, compare, terse/JSON report, fail-open
  network posture, optional `--apply` dispatcher). Tests: clean / mixed
  v2-v3-v4 / corrupt file / manifest success+failure / offline fallback /
  manifest-vs-constant agreement.
- **S3** — extend `claude-session-start-invoker.js` to run the check +
  relay output; ensure the install command writes it; no-router/stale-router
  graceful message; tests for invoker logic + install writes.
- **S4** — authoring-guide wording; `resolve_set` resolver +
  `next_session_set_number`; `start_session --session-set-dir <n>`
  acceptance; resolver match/collision/no-match tests.
- **S5** — `docs/cross-repo-migration-guard-notice.md`; Explorer UX
  revision (asterisk/tooltip + title-bar bulk-upgrade icon); harvester
  first-adopter install (operator-scoped); version bumps + CHANGELOG +
  CLAUDE.md walk + change-log; publish the held v0.24.1 Copy-Slug fix;
  cross-provider verification; publishes held for operator tag-push.

> Note: the Explorer UX revision (Q6) is a rendered surface; it is grouped
> into **S5** with its Layer-3 Playwright coverage. If consensus flips
> `requiresUAT` to `"suggested"`, S5 also produces a short UAT checklist
> for the Explorer bits.

---

## Questions explicitly deferred (out of scope, recorded)

- Number-badge in the Explorer rows / number-aware copy commands → follow-up
  if the convention proves useful (Q9).
- Retroactive mass-rename / numeric-prefix backfill of existing slugs →
  permanent non-goal (breaks `prerequisites:` refs, `sessionSetName`,
  git history).
- A drift-detector that also lints consumer `CLAUDE.md` for stale blob
  URLs → separate audit-then-spec set.

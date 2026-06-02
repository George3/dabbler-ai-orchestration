# Engine-Agnostic Documentation Authority And Version Status Spec

> **Purpose:** Shared operational facts a future orchestrator needs were
> split across engine-specific bootstrap files, and `AGENTS.md` / `GEMINI.md`
> drifted badly stale while `CLAUDE.md` kept moving. Promote a durable
> principle: if a fact matters to more than one orchestrator, it must live
> in an engine-agnostic doc or canonical package metadata. Centralize the
> current consumer table and version/release walk in
> `docs/repository-reference.md`, and make the root engine files point
> there instead of carrying independent version histories.
> **Created:** 2026-06-02
> **Session Set:** `docs/session-sets/056-engine-agnostic-doc-authority-and-version-status/`
> **Prerequisite:** None. Independent of Set 055 (`structured
> verification issue artifacts`), which stays focused on verification
> artifact shape.
> **Workflow:** Orchestrator-maintained docs / release-discipline hygiene

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
```

> Rationale: shared documentation architecture and root-instruction-file
> cleanup only. No browser-visible UI, no runtime behavior change.

---

## Project Overview

### Motivation

The repo's documentation authority is currently underspecified in one
important way:

- `CLAUDE.md` carried a long current version walk.
- `AGENTS.md` and `GEMINI.md` carried a much older copy of the same kind
  of information, plus stale extension path/build facts.
- Live planning/review docs pointed reviewers and release operators at
  `CLAUDE.md` for shared repo facts such as current consumers and the
  version walk.

That is exactly the failure mode a future orchestrator cannot safely
recover from: a shared fact exists, but only in one engine-specific file,
so another engine starts from stale or contradictory guidance.

### What this set delivers

1. A durable guiding principle in the shared GitHub docs: shared
   operational facts belong in engine-agnostic docs or canonical package
   metadata, not only in `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`.
2. A canonical `docs/repository-reference.md` section for:
   current consumer repos, current release status, and a concise shared
   version walk.
3. Root engine bootstrap docs that point to the canonical shared-doc
   section rather than maintaining independent version histories.
4. Live planning/review docs updated to cite the engine-agnostic source,
   not `CLAUDE.md`, for release/version/consumer facts.
5. **Complete centralization (Session 3, added 2026-06-02 by operator
   directive).** No shared operational fact may live *only* in one
   engine-specific bootstrap file. Every such fact has an engine-agnostic
   canonical home, and `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` are
   reduced to symmetric thin bootstrap files that differ only in
   engine-specific bootstrap (API-key export syntax, router import) and
   otherwise carry the *same* pointer set into the engine-agnostic docs.

### Non-goals

- **No package version bump.** This set changes documentation authority,
  not shipped code.
- **No rewrite of historical closed session-set artifacts.** Old specs,
  change-logs, and verification files remain historical records.
- **No consumer-repo mass sync.** This set fixes the canonical repo; any
  cross-repo notice is a follow-on only if needed.
- **Centralization is the goal, not triplication.** "Complete
  centralization" means the canonical copy of every shared fact lives in
  an engine-agnostic doc (or package metadata) and the three engine files
  *point* to it — **not** that the same prose is copied into all three
  engine files (that would create exactly the three-way drift this set
  exists to kill). When an engine file currently carries inline-only
  shared content, the fix is to relocate that content to an
  engine-agnostic doc and leave a pointer, not to mirror it.

### Open design questions (S1 audit)

1. **Where the canonical section lives.** Keep it inside
   `docs/repository-reference.md` vs split to a dedicated
   `docs/version-status.md`. Recommendation: keep it in
   `repository-reference.md` because that file already serves as the deep
   engine-agnostic reference page.
2. **How much history to carry.** Full prose walk vs concise recent walk
   plus package changelog pointers. Recommendation: concise recent walk +
   changelog pointers, to reduce maintenance burden.
3. **How much shared factual content stays in root engine files.** Keep
   current-consumer and build/test summaries vs strip them to bare
   bootstrap. Recommendation: keep only concise stable facts and ensure
   the canonical release/version source is engine-agnostic.
4. **Secondary docs to retarget.** Which live planning/review docs should
   cite the canonical shared-doc section. Recommendation: at minimum the
   release-process docs and review-criteria templates.

---

## S1 Audit Lock (2026-06-02)

Authoritative record: [`s1-audit-record.md`](s1-audit-record.md).

- **Situational finding:** the substantive migration was applied out of
  band in commit `e5a3476 "misc fixes to guidance."` before the audit
  ran; `session-state.json` still showed both sessions `not-started`.
  Session 1 became audit-and-ratify rather than design-from-scratch.
- **All four open design questions** resolved to their *recommended*
  option (which `e5a3476` implemented): canonical section lives in
  `docs/repository-reference.md`; concise recent walk + changelog
  pointers; root engine files carry only stable bootstrap facts + a
  pointer; release-process + review-criteria + project-guidance +
  workflow docs retargeted.
- **Contract LOCKED:** shared operational facts live in engine-agnostic
  docs or package metadata; `docs/repository-reference.md` →
  `Documentation authority and release status` is the canonical home;
  root engine files carry no independent version history.
- **Migration verified complete & faithful;** no live straggler treats
  an engine file as canonical (grep clean except this spec + one
  historical closed-set artifact).
- **Residual S2 scope:** validate the version-walk migration (markdown
  render check + grep sweep for version-walk / consumer-table
  stragglers). The consumer-table header drift and the broader engine-file
  symmetrization are owned by Session 3.
- **Verifier IMPORTANT finding "incomplete centralization" re-scoped IN
  (2026-06-02, operator directive).** S1's end-of-session verifier
  (`gemini-2.5-pro`) flagged that `CLAUDE.md` still carries richer shared
  content (orchestrator-block contract, session-state schema, build/test
  + e2e harness, router-config editor) than `AGENTS.md` / `GEMINI.md`.
  S1 dispositioned it OUT-OF-SCOPE per the then-current non-goal. The
  operator has since directed that incomplete centralization is *not*
  acceptable; that finding is the charter for the new **Session 3**, and
  the non-goal that excused it has been removed (see § Non-goals).

---

## Sessions

### Session 1 of 3: Audit & design-lock

**Steps:**
1. Re-survey the live shared-doc surfaces (`CLAUDE.md`, `AGENTS.md`,
   `GEMINI.md`, `docs/repository-reference.md`, shared review/planning
   docs) and confirm exactly where shared repo facts are duplicated.
2. Lock the guiding principle text, the canonical section location, and
   the scope of the shared version walk.
3. Decide whether any shared facts should remain duplicated in root
   engine docs after the canonical section exists.
4. Capture the audit record and lock the migration plan.

**Creates:** proposal / verdict if the audit needs a formal record.
**Ends with:** a locked documentation-authority contract.
**Progress keys:** principle text locked; canonical location locked;
root-doc scope locked.

### Session 2 of 3: Validate the version-walk migration

> The substantive version-walk migration (deliverables 1–4) was committed
> out of band in `e5a3476` and ratified by the S1 audit. Session 2 is the
> independent validation checkpoint for *that* migration; the broader
> engine-file symmetrization (deliverable 5) is Session 3's charter.

**Steps:**
1. Confirm the canonical `docs/repository-reference.md` →
   `Documentation authority and release status` section is present and
   well-formed (principle + consumer table + release-status table +
   recent walk).
2. Markdown render check on the canonical section and the three engine
   files' `Shared repo facts` pointers (tables, links, the
   `#documentation-authority-and-release-status` anchor).
3. Grep sweep for any live reference that still treats an engine file as
   the canonical source of the version walk / consumer table / release
   status (excluding historical closed-set artifacts and this spec).
4. Record the validation result; hand off to Session 3.

**Ends with:** the version-walk migration is independently confirmed
clean; no live straggler treats an engine file as canonical for
release/version/consumer facts.
**Progress keys:** canonical section confirmed; render clean; straggler
grep clean.

### Session 3 of 3: Complete centralization + close

Charter: the S1 verifier's IMPORTANT finding — `CLAUDE.md` carries shared
operational content that `AGENTS.md` / `GEMINI.md` lack, so those facts
are effectively sole-sourced in one engine file. Operator directive:
incomplete centralization is not acceptable. Approach is fixed by the
guiding principle — relocate inline-only shared content to engine-agnostic
docs and make the three engine files symmetric thin pointers; do **not**
mirror prose into all three.

**Steps:**
1. **Enumerate.** Diff `CLAUDE.md` against `AGENTS.md` / `GEMINI.md` and
   list every shared operational fact that is richer-in or sole-sourced-in
   one engine file. Known candidates from the S1 verifier: the
   orchestrator-block contract, the session-state-schema summary, the
   `Building & testing` detail including the Layer-1/2/3 e2e harness and
   CI section, and the router-config-editor section.
2. **Locate or create a canonical home for each.** For each enumerated
   fact, confirm an engine-agnostic canonical home exists (e.g.
   `docs/session-state-schema.md`, `docs/repository-reference.md`,
   `docs/ai-led-session-workflow.md`, `ai_router/docs/close-out.md`). For
   any fact with no engine-agnostic home (e.g. the e2e harness layer
   guidance, the router-config-editor walkthrough), relocate that content
   into the appropriate engine-agnostic doc.
3. **Symmetrize the engine files.** Reduce `CLAUDE.md`, `AGENTS.md`, and
   `GEMINI.md` so each carries only (a) engine-specific bootstrap
   (API-key export syntax, router import snippet) and (b) the *same*
   pointer set into the engine-agnostic docs. Fix the consumer-table
   header drift (`ai_router` vs `ai_router copy`) as part of this.
4. **Validate.** Grep proves no shared operational fact is sole-sourced in
   an engine file; a structural diff confirms the three engine files
   differ only in their bootstrap sections; markdown renders clean.
   Cross-provider end-of-session verification.
5. **Close the set.** Change-log, disposition, final close (flip the set
   to `complete`).

**Optional design check:** the mechanism (relocate-and-point) is dictated
by the locked S1 contract, so no fresh design-lock is required; if a
specific relocation target is genuinely ambiguous, route it through
decision-time cross-provider consensus before falling back to
`AskUserQuestion`.

**Ends with:** every shared operational fact has an engine-agnostic
canonical home; the three engine files are symmetric thin bootstrap +
identical pointers; no fact is recoverable only from one engine's file.
**Progress keys:** sole-sourced facts enumerated; each relocated to /
confirmed in an engine-agnostic home; engine files symmetric; validation
+ verification clean; set closed.

---

## End-of-set deliverables

- A durable guiding principle for documentation authority in the shared
  GitHub docs.
- Canonical current-consumer and version-status information in
  `docs/repository-reference.md`.
- Root engine instruction files that point to the shared authority
  instead of carrying their own version walk.
- Live review/planning docs retargeted to the engine-agnostic source.
- **Complete centralization:** no shared operational fact sole-sourced in
  any engine-specific file; `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`
  symmetric thin bootstrap files with identical pointer sets into the
  engine-agnostic docs.
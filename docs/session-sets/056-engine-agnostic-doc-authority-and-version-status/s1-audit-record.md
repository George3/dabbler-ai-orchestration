# Session 1 Audit Record — Documentation-authority contract lock

**Set:** `056-engine-agnostic-doc-authority-and-version-status`
**Session:** 1 of 2 — Audit & design-lock
**Orchestrator:** claude / anthropic / claude-opus-4-8 (effort: high)
**Date:** 2026-06-02

---

## 0. Situational finding (read first)

The substantive migration that Session 2 was scoped to perform was
**already applied out of band** before this audit ran, in commit
`e5a3476 "misc fixes to guidance."` (authored by the operator,
2026-06-02 11:01). That single commit touched all the surfaces the set
targets:

| File | Change in `e5a3476` |
|---|---|
| `CLAUDE.md` | −445 lines: the full `Extension versioning` walk removed; replaced with a `Shared repo facts` pointer to `docs/repository-reference.md` |
| `AGENTS.md` | Stale `Extension versioning` (frozen at v0.8.0) removed; extension path / role / consumer table refreshed; `Shared repo facts` pointer added |
| `GEMINI.md` | Same refresh + `Shared repo facts` pointer |
| `docs/repository-reference.md` | +51 lines: new canonical `Documentation authority and release status` section (guiding principle + consumer table + release-status table + recent version walk); file-map rows reworded |
| `docs/planning/project-guidance.md` | New `Documentation authority` principle subsection |
| `docs/planning/release-process.md` | Consumer-list citation retargeted `CLAUDE.md` → `docs/repository-reference.md` |
| `docs/planning/marketplace-release-process.md` | Same retarget |
| `docs/review-criteria/set.md` | Version-bump-correctness criterion retargeted to the canonical section |
| `docs/review-criteria/spec.md` | "Repo conventions" deference retargeted off `CLAUDE.md` to the three engine-agnostic docs |
| `docs/ai-led-session-workflow.md` | Doc-authority sentence added to the bootstrap paragraph |

`session-state.json` still showed both sessions `not-started` when this
session began. Session 1's job therefore became **audit-and-ratify the
already-committed migration** rather than design-from-scratch, and to
lock the contract so Session 2's residual scope is unambiguous.

This is itself an instance of the failure the set guards against
(out-of-band edits to shared docs without a recorded decision trail);
this record supplies the missing trail.

---

## 1. Audit scope

Surveyed every live shared-doc surface named in the spec for where
shared repo facts live and whether any engine-specific file is still the
*sole* home of a fact a future orchestrator needs:

- Root engine bootstrap files: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`
- Canonical reference: `docs/repository-reference.md`
- Shared planning/review docs: `docs/planning/project-guidance.md`,
  `docs/planning/release-process.md`,
  `docs/planning/marketplace-release-process.md`,
  `docs/review-criteria/set.md`, `docs/review-criteria/spec.md`,
  `docs/ai-led-session-workflow.md`

Method: read each file at HEAD; diffed `e5a3476`; ran a repo-wide grep
for live references treating an engine file as the canonical source of
shared/version/consumer facts.

---

## 2. Open design questions — dispositions (LOCKED)

All four S1 questions are resolved to the spec's *recommended* option,
which is exactly what `e5a3476` implemented. The audit **ratifies**
them; no design reversal.

1. **Where the canonical section lives** → **inside
   `docs/repository-reference.md`** (section `Documentation authority and
   release status`). Not a separate `docs/version-status.md`. Ratified:
   that file already serves as the deep engine-agnostic reference.

2. **How much history to carry** → **concise recent walk + changelog
   pointers**, not a full prose history. Ratified: the `Recent version
   walk` list carries ~6 recent entries and explicitly defers older
   history to the package CHANGELOGs and closed-set change-logs.

3. **How much shared content stays in root engine files** → **only
   concise stable facts** (purpose, role, portability rule, consumer
   table, build/test); the canonical release/version source is
   engine-agnostic. Ratified: the version walk is gone from all three
   engine files, each replaced by a one-paragraph `Shared repo facts`
   pointer.

4. **Secondary docs to retarget** → at minimum the **release-process
   docs and review-criteria templates**. Ratified: both release-process
   docs, both review-criteria templates, project-guidance, and the
   workflow doc were retargeted.

---

## 3. Documentation-authority contract (LOCKED)

1. **Guiding principle.** If a fact matters to more than one
   orchestrator (or to a human reviewer/release operator), it must live
   in an engine-agnostic doc (`docs/…`) or canonical package metadata
   (`pyproject.toml`, `package.json`, the CHANGELOGs) — never *only* in
   `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`. The principle text is
   recorded in both `docs/planning/project-guidance.md` →
   `Documentation authority` and `docs/repository-reference.md` →
   `Documentation authority and release status`.

2. **Canonical home for shared operational facts.**
   `docs/repository-reference.md` → `Documentation authority and release
   status` is the single canonical home for: the current consumer-repo
   table, current release status, and the concise recent version walk.

3. **Root-engine-file scope.** The three engine files carry only
   concise, stable bootstrap facts and a pointer to the canonical
   section. They do **not** carry an independent version history. A
   short consumer table may be duplicated in the engine files for
   convenience, but the canonical copy is the one in
   `repository-reference.md`, and any divergence is resolved in favor of
   the canonical copy.

4. **Secondary-doc citations.** Live planning/review docs cite the
   canonical engine-agnostic section (not `CLAUDE.md`) for
   shared/release/consumer facts.

**Progress keys (spec):** principle text locked ✅ · canonical location
locked ✅ · root-doc scope locked ✅.

---

## 4. Verification of the committed migration

- **Canonical section present and well-formed** in
  `docs/repository-reference.md` (principle + consumer table + release
  status + recent walk). ✅
- **All three engine files** point to the canonical section; the version
  walk is removed from each. ✅
- **No live straggler** treats an engine file as the canonical source
  for shared facts. Repo-wide grep returns only: (a) `spec.md` of this
  set (problem statement — expected), and (b)
  `docs/session-sets/048-…/s4-verification-prompt.md` (a historical
  closed-set artifact — explicit non-goal to rewrite). ✅
- **Stale-fact removal:** `AGENTS.md`'s `Extension versioning` section,
  previously frozen at v0.8.0 (the 19-versions-behind drift that
  motivated the set, per `feedback_engine_agnostic_docs`), is gone. ✅

---

## 5. Residual scope for Session 2 (validation + nits)

The migration is committed, so Session 2 collapses to validation plus
two cosmetic clean-ups. None are blocking.

1. **Consumer-table header drift (nit).** `CLAUDE.md` uses the column
   header `ai_router`; `AGENTS.md` and `GEMINI.md` use `ai_router copy`.
   `copy` is vestigial wording from the retired vendoring model (all
   three rows now read `pip install dabbler-ai-router`). Aligning the
   three headers removes exactly the kind of cross-engine drift this set
   exists to prevent.

2. **Markdown validation.** Confirm the edited markdown renders cleanly
   (tables, links, no broken anchors to
   `#documentation-authority-and-release-status`).

3. **Final grep sweep** for any remaining live reference treating one
   engine file as canonical (re-run §4's grep at S2 close).

Non-goals reaffirmed: no package version bump; no rewrite of historical
closed-set artifacts; no consumer-repo mass sync.

---

## 6. Audit conclusion

The documentation-authority contract is **LOCKED** as in §3. The
out-of-band migration in `e5a3476` is **complete and faithful** to the
locked contract and to all four recommended dispositions. Session 2's
remaining work is validation and the two cosmetic nits in §5.

---

## 7. End-of-session cross-provider verification & dispositions

**Verifier:** gemini-2.5-pro (google), independent of the
claude/anthropic orchestrator. Raw output: [`s1-verification.md`](s1-verification.md).
**Verdict:** VERIFIED_WITH_NOTES. **Cost:** $0.0346.

All four claim-checks returned `holds: true` (canonical section present
and complete; all three engine files point to it with no independent
version walk; principle recorded in `project-guidance.md`; the stale
v0.8.0 `Extension versioning` block is gone). The contract was judged
"sound and internally consistent."

**Disposition of findings (in-flight):**

- **IMPORTANT — "Incomplete Centralization of Shared Facts"** (CLAUDE.md
  still carries richer shared content — orchestrator-block contract,
  session-state schema, build/test/e2e-harness detail — than AGENTS.md /
  GEMINI.md). **Disposition: ACKNOWLEDGED, OUT OF SCOPE for Set 056.**
  Rationale: (1) it is the set's *explicit non-goal* — "No attempt to
  eliminate every duplicate fact; the goal is to avoid a fact living
  *only* in an engine-specific doc and to define one canonical source for
  the shared operational history." (2) The motivating symptom (the
  version walk frozen at v0.8.0 in AGENTS.md) is fixed. (3) The specific
  CLAUDE.md sections the verifier named are **not** sole-sourced: the
  orchestrator-block contract points to
  `docs/session-state-schema.md § Writer Contract` (CLAUDE.md:65), the
  session-state schema names `docs/session-state-schema.md` as the
  "authoritative reference" (CLAUDE.md:177), and close-out points to
  `ai_router/docs/close-out.md` (CLAUDE.md:212) — their canonical home is
  already engine-agnostic; CLAUDE.md is a richer echo, which the contract
  permits. The one genuinely fuller inline block is the Layer-1/2/3 e2e
  harness guidance under "Building & testing". **Follow-on candidate:** a
  future audit-then-spec set could run a systematic shared-fact sweep
  across the three engine files and either (a) thin CLAUDE.md's echoes to
  pointers or (b) bring AGENTS.md/GEMINI.md to parity, with any
  inline-only operational detail (e.g. the e2e harness layers) relocated
  to an engine-agnostic doc. Not blocking; deliberately deferred.

- **NICE-TO-HAVE — consumer-table header drift** (`ai_router` in
  CLAUDE.md vs `ai_router copy` in AGENTS.md / GEMINI.md). **Disposition:
  ACCEPTED into Session 2 residual scope** (already §5 item 1); the
  verifier independently confirmed the drift is real.

No critical findings. No design reversal. Contract stands as locked.

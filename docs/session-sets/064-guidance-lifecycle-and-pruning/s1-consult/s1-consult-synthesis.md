# Set 064 Session 1 — design-lock consult synthesis

> **Date:** 2026-06-14
> **Providers:** gpt-5.4 (OpenAI) + gemini-2.5-pro (Google), cross-provider
> from the Claude orchestrator. Raw verdicts: `s1-consult-gpt-5-4.md`,
> `s1-consult-gemini-pro.md` (never edited).
> **Scope:** Lock the *mechanics* of D1–D8. The 2026-06-14 prior consult
> referenced in `spec.md` (which locked the *direction*) was **not present
> in the repo** — `s1-consult/` did not exist before this session. This
> synthesis stands as the Session-1 consult of record; the direction is
> re-summarized from the spec and unchanged.

## Verdict matrix

| Deliverable | gpt-5.4 | gemini-2.5-pro | Resolution |
|---|---|---|---|
| D1 cost reporter | AGREE-W-MOD (header stamping opt-in) | AGREE | **Adopt the mod** — `--write-headers` opt-in; default report read-only |
| D2 metadata serialization | AGREE-W-MOD (strict grammar, fixed order, formatter) | AGREE-W-MOD (double-quote values) | **Adopt both** — HTML-comment trailer, fixed field order, **double-quoted values**, ship parser + validator |
| D3 citation-at-close seam | AGREE (+ validate IDs in close) | AGREE | **Adopt** — agent-run `cite_lessons` in the commit; close_session validates + records only |
| D4 active/archive split | AGREE | AGREE | **Adopt as proposed** |
| D5 triggers + ceiling | AGREE-W-MOD (N=12) | AGREE (N=20 fine) | **Lock N=20 default, configurable** (rationale below); 10k/6k ceilings confirmed by both |
| D6 backlog remediation | AGREE-W-MOD (bankruptcy heavily gated) | AGREE (offer it) | **Adopt** — bankruptcy is opt-in, projection-first, owner-signoff |
| D7 ship to consumers | AGREE | AGREE | **Adopt as proposed** (Marketplace bump confirmed) |
| D8 docs + release | AGREE | AGREE | **Adopt as proposed** |

**No DISAGREE on any deliverable.** Every modification is a refinement,
not a reversal.

## Convergent additions adopted into the locks

Both providers independently raised these; all are now part of the locked
design:

1. **Header stamping is opt-in, not a side effect of reporting (D1).**
   `guidance_report` defaults to a read-only report; `--write-headers`
   mutates the in-file freshness block. Prevents every report run from
   dirtying tracked docs / creating merge churn.
2. **A metadata validator (D2).** `python -m ai_router.validate_guidance_meta`
   (CI / pre-commit wireable) rejects malformed trailers. Hand-editing the
   trailer is the main fragility; the validator is the guard.
3. **Double-quoted values + fixed field order (D2).** Trailer grammar:
   `<!-- lesson: id="L-064-1" added-set="064" last-used-set="064" status="active" scope="portable" -->`.
   Fields appear in a fixed canonical order; absent/empty fields are
   omitted; multi-value fields (e.g. `encoded-in`) are comma-separated
   inside the quotes. A formatter normalizes order/spacing on write.
4. **ID governance (D2).** `id` format `L-<set>-<seq>` (e.g. `L-064-1`),
   assigned once and **permanent** across heading renames. On **merge**,
   the survivor keeps its id and absorbs the others; the absorbed entries
   get `status="archived"` + `superseded-by="<survivor-id>"` and move to
   the archive. IDs are never regenerated casually.
5. **close_session validates cited IDs (D3).** When `disposition.lessons_cited`
   names an id that does not exist in either guidance file, close_session
   records the mismatch in the `closeout_succeeded` event (non-blocking
   advisory) rather than silently accepting it.
6. **Define "referenced by active guidance" (D5).** A lesson is *referenced*
   when its `id` appears in `project-guidance.md`, or in another active
   lesson's `superseded-by` / `encoded-in`, or in active prose. The sweep /
   triage tooling builds this id dependency graph across **both** files
   before proposing any archive, so a still-referenced lesson is never
   archived. This means `project-guidance.md` prose may cite lesson ids.
7. **Archive search helper.** `python -m ai_router.guidance_search --archive
   <term>` so the archive is grep-assisted, not a write-only black hole.
   Folded into the D1 reporter family (ships in S2/S3, ASCII-only).
8. **Backstop enforcement seam (D5).** Two non-blocking surfaces, mirroring
   the Set 053 drift advisory: (a) a soft over-ceiling advisory printed by
   `start_session` / `close_session` (fail-open, never changes exit
   status); (b) `guidance_report --check` returns non-zero when over
   ceiling, for any consumer who wants a hard CI gate. "Sweep required
   before adding" is thus *surfaced*, never silently enforced.
9. **Archived-lesson reactivation loop (D3/D5).** `cite_lessons` on an
   archived id updates its `last-used-set` in the archive **and** warns
   "cited id X is archived — consider reactivating," surfacing it for an
   operator move-back. Keeps the loop closed without auto-mutating tiers.

## The one split — disuse window N

- **gpt-5.4:** N=12 (N=20 "too inert" for repos already carrying large
  context tax).
- **gemini-2.5-pro:** N=20 is fine ("a generous signal for human review,
  not an automated axe").

**Locked: N=20 default, configurable in `router-config.yaml`.** Rationale:
the disuse trigger is the *steady-state* mechanism, and it is gated three
ways — it requires *also* "not referenced by active guidance," it is
*operator-reviewed* (never an automatic axe), and rare-but-critical
disaster lessons can legitimately fire once in ~50 sets, so a larger
window protects exactly the highest-value edge-case knowledge. The
"already over budget" case gpt worried about is handled by **D6 backlog
remediation**, not by the steady-state disuse window — so the window can
afford to be conservative. The value is configurable; an operator who
finds steady-state pruning too inert can lower it (gpt's 12 is a
reasonable alternative) without a code change.

## Ship-ordering note (gpt blind spot #8) — adopted for S2

Build tools before policy/docs so repos never hand-edit inconsistent
metadata. Session-2 internal order: **D2 parser/formatter/validator →
D3 cite path → D1 reporter + `--check` + search → D4 split → D5 policy
text**. This is now the S2 plan-of-record.

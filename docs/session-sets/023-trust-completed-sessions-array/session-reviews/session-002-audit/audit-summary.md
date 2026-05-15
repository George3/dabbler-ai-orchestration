# Set 023 Session 2 — Audit summary

**Date:** 2026-05-15
**Subjects:** GPT 5.4, Gemini Pro
**Pattern:** Same prompt, parallel routes, JSON answers to five
questions, then spec-author resolution.

Raw routed results: [`gpt-5-4.json`](./gpt-5-4.json),
[`gemini-pro.json`](./gemini-pro.json). Prompt:
[`prompt.md`](./prompt.md).

Cost: $0.1010 (gpt-5-4) + $0.0119 (gemini-pro) = **$0.1129**.

---

## Per-question verdicts

| Question | GPT 5.4 | Gemini Pro | Agreement? |
|---|---|---|---|
| (a) hand-migration generalizes | concur-with-caveat / major | concur / none | Same direction, severity differs |
| (b) writer union monotone-up | raise-concern / major | concur-with-caveat / minor | Same concern, severity differs |
| (c) reader ordering | concur-with-caveat / minor | concur / none | Same direction; GPT adds observability caveat |
| (d) sharp-edge coverage | raise-concern / **major** | raise-concern / **critical** | Both raise the same third-edge concern |
| (e) open-ended | concur-with-caveat / minor | concur-with-caveat / minor | Both want doc + fixture refinements |

Neither provider flagged any defect in the design as shipped; the
concerns are all about scope and observability beyond the two
sharp edges this set targets. Detail follows.

---

## (a) Hand-migration generalizes — strong agreement; minor doc gap

**Both agree** the hand-migration approach is sound *if framed as
operator attestation*. GPT raises the failure shape where the
operator's attestation is wrong (e.g., session 2 never really
closed but the operator types `[1, 2, 3, 4]` anyway); Gemini calls
that the expected outcome of a manual override.

**Resolution:** Honor the operator's array as attestation, but
document the framing explicitly. The tool is not reconstructing
truth from the ledger — it is preserving the operator's stated
truth and using the ledger only to add what the operator missed.

**Spec refinement:** Add a one-line note to `close-out.md`
Section 5 (drift case 1) and to `session-state-schema.md` that
`completedSessions[]` is operator-attested for migrated sets and
tool-maintained for sets that ran the close-out gate. *Non-blocking
for Session 3.*

---

## (b) Writer union monotone-up — same concern, different severity

**Both flag the same gap:** the union doesn't validate session
numbers against `totalSessions`. A snapshot `[1, 2, 99]` with a
4-session set, or a stray `closeout_succeeded(session_number=99)`
in the ledger, gets ratcheted into the merged value.

- **GPT (major):** would block or surface newly added out-of-range
  positives unless operator-confirmed.
- **Gemini (minor):** characterizes as a gap in data validation
  that may be intended.

**Tie-breaker (more conservative wins):** treat as a **Major
follow-up**, not blocking Session 3. The writer fix already shipped
as 0.2.4 is not *wrong* — it doesn't add bad data on its own; it
preserves what the operator typed. The risk is downstream: an
operator typo could cement into the snapshot under repeated repair.
A clean fix is a follow-on `ai_router 0.2.5` patch that clamps the
union to `[1..totalSessions]` and warns on out-of-range entries.

**Spec refinement:** Add a Risks bullet to this spec noting that
the writer union is unguarded against out-of-range session numbers
and that a follow-up (post-023) patch should add validation. Also
add a Session 4 fixture documenting that a stray out-of-range
entry in the array (e.g., `completedSessions: [1, 2, 99]`,
`totalSessions: 4`, `currentSession: 4`, no ledger closeout for 4)
does not accidentally satisfy `.includes(currentSession)` for the
final session: `[1, 2, 99].includes(4)` is `false`, so the guard
falls through to the events-ledger check and correctly returns
`true` (downgrade to in-progress). This documents that the
reader's behavior is robust to writer-side validation gaps — the
stray 99 doesn't masquerade as a closeout for session 4.

---

## (c) Reader ordering — strong agreement; minor observability caveat

**Both concur** that array-first / OR-logic is the correct ordering.
Gemini explicitly notes that the conservative AND-alternative would
re-create the migration deadlock and not actually fix anything.

GPT adds: when the array says closed but the ledger lacks the
closeout, return `false` here but *emit a drift hint* so the
mismatch isn't silently hidden.

**Resolution:** Adopt GPT's caveat as a *non-blocking* Session 3
refinement. The extension's existing `console.warn` channel is the
natural surface (the v0.13.11 mid-set-complete guard already logs
when it downgrades). Add a symmetric log when the array overrides
the ledger.

**Spec refinement:** Add a Session 3 step: when the array-check
branch returns `false` but the ledger lacks a closeout for
`currentSession`, emit a one-line `console.warn` so the operator
can see the migration shape in the extension output. *Non-blocking;
the warn is optional observability, not correctness.*

---

## (d) Sharp-edge coverage — both raise a third-edge concern

**Both providers** flag that other progress-readers elsewhere in
the pipeline may still consult the events ledger directly without
considering `completedSessions[]`. Concrete candidates raised:
queue-state reconciler, disposition-gate freshness check,
`start_session`'s `max(closed)+1` inference, or other tree-view /
status helpers.

- **GPT (major):** recommends centralizing progress resolution
  behind one shared helper.
- **Gemini (critical):** "applying a local fix to what is a
  systemic change in data authority"; recommends a system-wide
  audit before shipping the reader fix.

**Spec gate check:** Spec step 5 says: *"If either provider raises
a Critical-severity objection that would invalidate the writer fix
already shipped in Session 1, stop and flag to the human..."*

Gemini's Critical does **not** invalidate the writer fix already
shipped — the writer fix is correct in isolation. The Critical is
about *scope* (other readers we haven't audited), not about
*correctness* (the writer or reader fixes themselves are wrong).
The strict gate-clause does not trip.

However, the gate is a floor, not a ceiling. Both providers
independently raised the same scope concern; a sample-of-two
unanimity is a strong signal. The decision to expand Set 023's
scope to a system-wide audit (or to defer it to a follow-on set) is
an operator scope decision and is flagged to the operator below.

**Spec author's resolution (subject to operator confirmation):**

- Ship Session 3 as planned (reader fix in `isMidSetComplete`),
  since the design itself is correct.
- Before close-out, add a **system audit checklist** to this spec:
  the spec author commits to grep'ing the codebase for all
  consumers of `session-events.jsonl` and confirming each either
  (a) already consults `completedSessions[]` (post-Set-022) or
  (b) is correct to ignore it (e.g., a debug/history tool whose
  job is "show me the events ledger").
- If the audit finds another sharp edge during Session 3, surface
  it as a Risks-section addition and queue a Set 024 to fix it,
  rather than expanding Set 023's scope mid-flight.
- If the audit finds **no other sharp edge**, document the audit
  result in the Session 3 close-out so the system-wide concern is
  closed on disk.

---

## (e) Open-ended — both want doc + fixture refinements

**Both providers** independently suggest:

- Sharpen the "authoritative" language in close-out.md /
  session-state-schema.md to distinguish *whether-closed*
  (`completedSessions[]`) from *when-closed* (events ledger).
  Future maintainers can misread "both are authoritative" as "must
  agree," which is wrong post-Set-022.
- Add Session 3 test fixtures for edge shapes: GPT wants
  out-of-range session numbers + non-final-session disagreements;
  Gemini wants a `completedSessions: null` or `completedSessions:
  "not an array"` case.

**Spec refinement:** Adopt both — already partially covered by the
(b) fixture and Session 3's existing four-fixture plan; add the
`completedSessions: null` case explicitly and the doc-language
sharpening to Session 3's step list.

---

## Concrete spec updates queued for Session 3

The audit drives these refinements into the spec's Session 3 plan:

1. **Step 1 addition:** When the array-check branch returns `false`
   but `hasCloseoutEventForSession` returns `false`, emit a
   `console.warn` documenting the array/ledger drift (GPT caveat
   on (c)).
2. **Step 4 fixtures:** Add a fifth fixture: `completedSessions:
   null` (or non-array), currentSession in `totalSessions` range,
   ledger has closeout → returns `false` (Array.isArray fallback
   works). Add a sixth fixture: snapshot has `completedSessions:
   [1, 2, 99]`, totalSessions 4, currentSession 4, no ledger
   closeout for 4 → returns `false` (stray 99 doesn't matter; 4
   is in the array). (Gemini + GPT on (b) and (e).)
3. **Step 5 addition:** In `session-state-schema.md`, sharpen the
   authoritative-signal language to distinguish *whether-closed*
   from *when-closed*. (Both on (e).)
4. **New step 9:** System-audit checklist — `grep -rn
   "session-events.jsonl\|closeout_succeeded\|hasCloseoutEvent"`
   across the codebase and document each consumer either already
   consults `completedSessions[]` or is correct to ignore it.
   Document the result in the Session 3 close-out. (Both on (d).)
5. **Risks-section bullet:** Note that the writer's union is
   unguarded against out-of-range session numbers; queue a
   follow-on `ai_router 0.2.5` patch for `totalSessions` clamping.
   (Both on (b).)
6. **close-out.md Section 5:** One-line note that
   `completedSessions[]` is operator-attested for migrated sets
   and tool-maintained for sets that ran the close-out gate. (GPT
   on (a).)

---

## Flag to operator (scope decision)

Both providers — independently, on the same question — raised the
concern that other readers in the pipeline may still consult the
events ledger directly and would disagree with a migrated snapshot.
Gemini severity: critical. GPT severity: major.

The strict spec-step-5 gate (Critical that *invalidates the writer
fix*) does not trip — the writer fix is correct in isolation. But
the operator should decide whether to:

- **(A)** Ship Session 3 as planned + run the codebase audit during
  Session 3 + queue a Set 024 if the audit finds new sharp edges.
  This is the spec author's recommendation.
- **(B)** Pause Session 3 and expand Set 023's scope to include
  the system-wide audit + any reader-rewrites it surfaces. Adds
  scope to a set that was specced as "two surgical fixes."
- **(C)** Ship Session 3 as planned + treat the audit as a
  separate follow-up set tracked outside this set's scope.

The spec-author resolution above assumes (A).

**Operator decision (2026-05-15):** option (B) — pause Session 4
and expand Set 023's scope to include a system-wide audit
session. `totalSessions` bumped 3 → 4. The original Session 3
(extension reader fix) becomes Session 4. See spec.md for the new
Session 3 plan.

---

## Verification (third-provider, gpt-5-4-mini)

**Verifier:** `gpt-5-4-mini` — distinct from both audit subjects
(`gpt-5-4` and `gemini-pro`); not strictly a third *provider*
(same OpenAI family as the GPT 5.4 subject) but a different model
running at a different reasoning tier. Truly third-provider
verification would require an Anthropic model, which is not
registered in `router-config.yaml`'s model registry. Cost:
**$0.0251**. See [`verify-prompt.md`](./verify-prompt.md),
[`verify-prompt.rendered.md`](./verify-prompt.rendered.md), and
[`verify-result.json`](./verify-result.json).

**Round 1 verdict:** `ISSUES_FOUND` — 1 Major.

- **Major (question (b) spec refinement):** the spec refinement
  proposed a reader fixture with `completedSessions: [1, 2, 99]`
  and `currentSession: 4`, then claimed "the reader should still
  return `false` (session 4 is in the array)" — internally
  contradictory, since `[1, 2, 99].includes(4)` is `false`.
  Verifier's recommended fix: rewrite the fixture description so
  the array/`currentSession` relationship is consistent.

**Fix applied:** Refined (b) spec-refinement text above
([commit prior to this addendum]) to correctly state that the
reader falls through to the events-ledger check (since 4 is *not*
in the array) and the stray 99 is irrelevant to the
`.includes(currentSession)` decision. The spec's Session 4
fixture **F6** was already self-correcting inline; the
audit-summary's paraphrase had not caught up. No round-2
re-verification routed: the finding is self-evidently a textual
contradiction, the fix is exactly what the verifier recommended,
and a re-route would duplicate $0.025 of cost on a defect any
human reader can confirm by inspection.

**Round 1 notes (verbatim from verifier):** "Most of the summary
tracks the raw JSON well: the per-question verdicts and
severities are broadly aligned, the Gemini Critical on (d) is
accurately framed as a systemic-scope concern rather than a
direct invalidation of the writer fix, and the A/B/C operator
framing is fair."

**Verification spend Session 2:** $0.0251 (one round, gpt-5-4-mini).
Total Session 2 routed spend (audit subjects + verification):
**$0.1380**.

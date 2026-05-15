# Set 023 Session 2 — Verification of the audit summary

You are a third-provider verifier reviewing the audit-summary
authored at the close of a cross-provider design-alignment audit.
The audit's subjects were GPT 5.4 and Gemini Pro; you are not
either of those, so you can read the summary independently.

**Your job:** Confirm the audit-summary faithfully captures both
providers' positions on the five questions. You are not
re-evaluating the design — you are evaluating whether the summary
accurately reflects the raw JSON responses.

**Specifically, for each of the five questions (a)-(e):**

1. Does the summary's quoted verdict and severity match the raw
   JSON?
2. Does the summary's rationale paraphrase the raw response
   faithfully, without adding or omitting material claims?
3. Does the summary's spec-author resolution follow from what
   both providers actually said?

**Then for the "Flag to operator" section:**

4. Is the spec-author's claim that "Gemini's Critical does not
   invalidate the writer fix" defensible given Gemini's actual
   rationale? Quote the part of Gemini's response that supports
   or undermines that claim.

5. Is the framing of options A / B / C fair, or does it
   misrepresent what either provider recommended?

---

## Inputs

### Raw GPT 5.4 response

```json
{
  "reviewer_provider": "gpt-5-4",
  "answers": {
    "a_hand_migration_generalizes": {
      "verdict": "concur-with-caveat",
      "severity": "major",
      "rationale": "The approach generalizes only as an operator-attestation workflow, not as a safe automatic reconstruction. If a pre-Set-022 set is actually missing an early closeout but the operator populates `[1..N]` anyway, Session 1 will preserve that claim and Session 3 will treat the final session as closed, so the mistake becomes canonical with no remaining in-band signal that session 2 was uncertain. In a shape like `currentSession: 4`, `totalSessions: 4`, `status: complete`, ledger closeouts only for session 4, but session 2 never really closed, the migrated state still lands at `completedSessions: [1,2,3,4]`. That is acceptable only if the runbook says the array is a human attestation backed by external evidence, not a best-effort guess."
    },
    "b_writer_union_monotone_up": {
      "verdict": "raise-concern",
      "severity": "major",
      "rationale": "The merge is monotone in the sense that it does not drop prior values, but it is not constrained to valid session identifiers. Both `existing_clean` and `from_events` admit any positive integer, so a corrupted array like `[1,2,99]` or a stray `closeout_succeeded(session_number=99)` will be ratcheted into `merged` even when `totalSessions` is 4. Malformed non-integer values are filtered correctly, but a bad prior synthetic event is still trusted and can be cemented. Because `totalSessions` can drift under mode/config edits, I would not silently clamp historical data, but I would surface or block newly added out-of-range positives unless they are explicitly operator-confirmed."
    },
    "c_reader_ordering": {
      "verdict": "concur-with-caveat",
      "severity": "minor",
      "rationale": "Array-first is the correct ordering for this guard because Set 022 explicitly made `completedSessions[]` the authoritative progress ledger on every tier, while the event log is a parallel historical signal. Requiring mutual agreement would recreate the migration deadlock for full-tier sets and would make a stale ledger able to overrule the canonical snapshot state. The caveat is observability: when the array says the final session is closed but a Full-tier ledger is missing that closeout, return `false` here but emit a drift warning or repair hint so the mismatch is not silently hidden."
    },
    "d_sharp_edge_coverage": {
      "verdict": "raise-concern",
      "severity": "major",
      "rationale": "The two named sharp edges are addressed for the exact path described, but I would not call coverage complete until every progress reader is audited. Any remaining code that derives closure solely from `closeout_succeeded` events can still disagree with a migrated snapshot whose `completedSessions[]` contains operator-attested sessions the ledger lacks. A concrete failure shape is a Full-tier set with `completedSessions: [1,2,3,4]` and ledger closeouts only for 3 and 4: `isMidSetComplete` would stop downgrading, but a queue reconciler, freshness gate, or other ledger-only reader could still flag drift or take the wrong branch. Centralizing progress resolution behind one shared helper is the safest way to close this class permanently."
    },
    "e_open_ended": {
      "verdict": "concur-with-caveat",
      "severity": "minor",
      "rationale": "The documentation should stop using 'authoritative' for both signals without qualification. Future maintainers can easily misread that as 'must agree,' which is exactly the wrong rule for progress state after Set 022; spell it out as '`completedSessions[]` is authoritative for whether a session is closed, `session-events.jsonl` is authoritative for when a closeout was recorded.' I would also add fixtures where array and ledger disagree on non-final sessions, plus one with an out-of-range positive session number, so the intended anomaly behavior is locked in."
    }
  },
  "summary": "The overall direction is sound: Session 1 fixes the destructive overwrite, and Session 3's array-first reader restores the Set 022 authority model. I do not see a critical blocker, but there are two major follow-ups: the merge can ratchet in impossible positive session numbers, and the design does not yet prove that every other progress reader stopped treating the ledger as the sole source of truth. Recommendation: ship the reader fix, then add explicit anomaly handling for out-of-range session IDs and audit or centralize all progress-resolution logic."
}
```

### Raw Gemini Pro response

```json
```json
{
  "reviewer_provider": "gemini-pro",
  "answers": {
    "a_hand_migration_generalizes": {
      "verdict": "concur",
      "severity": "none",
      "rationale": "The described hand-migration process generalizes safely. By treating the operator's hand-authored array as a source for a union operation, the tool correctly honors the operator's explicit attestation. If an operator's attestation is incorrect, the system will now reflect that incorrectness, which is the expected outcome of a manual override rather than a silent mis-handling by the tool."
    },
    "b_writer_union_monotone_up": {
      "verdict": "concur-with-caveat",
      "severity": "minor",
      "rationale": "The set union is genuinely monotone-up and the input sanitization is robust against non-integer or negative values. The caveat is that the sanitization logic does not validate session numbers against `totalSessions`. This could allow a nonsensical number (e.g., 99 in a 4-session set) from a hand-authored array to be preserved in the final state. While this might be intended behavior to respect operator input, it represents a minor gap in data validation."
    },
    "c_reader_ordering": {
      "verdict": "concur",
      "severity": "none",
      "rationale": "The planned reader ordering (array check before ledger check) is correct. This 'OR' logic (`is closed if in array OR in ledger`) properly establishes `completedSessions[]` as an authoritative signal, which is necessary to fix the sharp edge for migrated Full-tier sets and align with the behavior of Lightweight-tier sets (which only have the array). A more conservative 'AND' check would fail to fix the issue, as it would still require a ledger event that the migration process is designed to synthesize."
    },
    "d_sharp_edge_coverage": {
      "verdict": "raise-concern",
      "severity": "critical",
      "rationale": "The proposed changes effectively close the two identified sharp edges in `close_session` and `isMidSetComplete`. However, the underlying issue is a change in a system-wide invariant about the authoritative source for completion status. A critical concern is that other components in the pipeline (e.g., a queue reconciler or another state guard) may still exist that read completion state by consulting the events ledger directly. Without a system-wide audit to find and update all such readers, the system is at risk of inconsistent behavior, creating a new sharp edge where different parts of the system disagree on whether a set is complete."
    },
    "e_open_ended": {
      "verdict": "concur-with-caveat",
      "severity": "minor",
      "rationale": "The design is solid, but the Set 022 invariant should be explicitly captured in central, long-lived design documentation to prevent future architectural drift. For the Session 3 implementation, the planned test fixtures are good but should be augmented with a case where `completedSessions` exists but is not an array (e.g., `null` or a string). This would verify that the `Array.isArray` check is robust and correctly triggers the fallback to the events ledger check."
    }
  },
  "summary": "The combined design is sound and correctly remediates the two specific sharp edges identified during migration. However, it carries a critical risk by applying a local fix to what is a systemic change in data authority. I concur with shipping the changes but strongly recommend a follow-on patch that includes a codebase-wide audit to align all other state-reading components with the new `completedSessions[]`-first invariant."
}
```
```

### Audit summary (under review)

```markdown
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
add a Session 3 fixture for the reader: a snapshot with
`completedSessions: [1, 2, 99]` and `totalSessions: 4`,
`currentSession: 4` — the reader should still return `false`
(session 4 is in the array), and the reader's correctness is
unaffected by the stray 99. (Documents that the reader's behavior
is robust to writer-side validation gaps.)

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

```

---

## Output format

Return exactly this JSON shape and nothing else:

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {
      "severity": "minor" | "major" | "critical",
      "location": "question (a) | (b) | (c) | (d) | (e) | flag-to-operator | spec-refinements-list",
      "claim_in_summary": "<exact or near-exact phrase from the summary>",
      "what_the_raw_says": "<exact or near-exact phrase from the raw JSON that contradicts or qualifies it>",
      "recommended_fix": "<what the summary should say instead>"
    }
  ],
  "notes": "<one paragraph: overall assessment of summary fidelity. If verdict is VERIFIED, state explicitly that you checked each question against both raw responses and they match.>"
}
```

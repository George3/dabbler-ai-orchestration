# Set 023 Session 2 — Cross-provider design-alignment audit

You are an independent design reviewer for the
`dabbler-ai-orchestration` framework. We are running the same
design-round pattern that informed Set 022's spec: two providers
(GPT 5.4 and Gemini Pro), the same prompt, JSON answers to five
specific questions. Where the two providers disagree, the spec
author records both positions; where one raises an objection we
hadn't considered, the planned Session 3 implementation is updated
before it lands.

You are reviewing **design**, not code style. Be willing to flag a
sharp edge even if the fix already shipped. Critical-severity
objections trigger a follow-on patch; non-Critical refinements
update the Session 3 plan.

---

## Background — the Set 022 invariant

Set 022 (`ai_router 0.2.3` + extension `v0.13.12`, released
2026-05-15) made `completedSessions[]` the **authoritative progress
ledger** for both Full-tier sets (with `session-state.json` +
`session-events.jsonl`) and the planned Lightweight tier (snapshot
only, no events ledger).

The three-line state interpretation rule Set 022 established:

1. `currentSession` is the session currently in flight (or the next
   one to start if the set is mid-set but no session is active).
2. `completedSessions[]` is the sorted, unique array of session
   numbers whose close-out gate succeeded. It is written/maintained
   on every close, on every tier.
3. The `closeout_succeeded` event in `session-events.jsonl` (Full
   tier only) remains a parallel authoritative signal, present
   because the events ledger pre-dates the array and is still the
   record-of-record for *when* each closeout happened.

The Lightweight tier was added 2026-05-07 (Set 018). It has no
events ledger; `completedSessions[]` is the only progress signal it
carries.

---

## What Set 022's migration surfaced (the two sharp edges)

Migrating two pre-Set-022 sets on this repo (Set 004, Set 006) on
2026-05-15 exposed two related defects:

### Sharp edge 1 — Writer overwrote a hand-authored array

`close_session --repair --apply` Case 1 (state-says-closed-but-no-
closeout-event for the final session) was synthesizing the missing
closeout event correctly, then overwriting `completedSessions[]`
with what the events ledger alone could reconstruct.

Concrete failure on Set 004:
- Before repair: events ledger has only a session-3 closeout.
  Snapshot has `currentSession: 4`, `status: complete`. Operator
  hand-adds `completedSessions: [1, 2, 3, 4]` (the operator's
  attestation that all four sessions did happen).
- After `--repair --apply`: ledger gains a synthetic session-4
  closeout (good); snapshot's `completedSessions` is overwritten to
  `[3, 4]` (the events-only view) — **dropping sessions 1 and 2 from
  the operator's attestation.**

### Sharp edge 2 — Reader ignored `completedSessions[]`

The extension's `isMidSetComplete` guard (added in v0.13.11 as a
defense against mixed-mode drift) consults *only* the events ledger.
It correctly downgrades a snapshot that claims complete-but-the-
ledger-disagrees, but it ignores a clean `completedSessions[]` array
on the snapshot. The migration symptom: hand-adding the array isn't
enough to clear the guard; the operator still has to run
`--repair --apply` to synthesize the ledger event, which then
triggers sharp edge 1.

---

## The Set 023 design (under review)

### Session 1 (already shipped as `ai_router 0.2.4`) — writer fix

The repair's `completedSessions[]` backfill is now a **monotone-up
union** of (a) the snapshot's existing array (sanitized) and
(b) the events-ledger reconstruction (post-synthesis). Repair never
drops a session number the operator hand-authored.

Four apply outcomes are distinguished in the messages line:
- `backfilled` — no array before, write the events view
- `merged` — clean array unioned with events
- `normalized` — malformed array (e.g., `[1, -1]`) cleaned + unioned
- `preserved` — no rewrite, raw on-disk array already equals the
  canonical merged form

Round-1 verifier finding (a Major correctness regression) drove the
`normalized` branch: an earlier implementation compared
`existing_clean` (sanitized) to `merged` to decide rewrite, which
let a malformed snapshot survive a `preserved` outcome. The fix
compares `existing_raw_list` (the literal on-disk value) to
`merged`. Three new regression tests cover preserved, merged, and
normalized paths; the full suite is 702/702.

Core diff in `ai_router/close_session.py` `_run_repair` Case 1:

```python
events_now = read_events(session_set_dir)
from_events = sorted({
    ev.session_number for ev in events_now
    if ev.event_type == "closeout_succeeded"
    and isinstance(ev.session_number, int)
    and not isinstance(ev.session_number, bool)
    and ev.session_number > 0
})
existing_completed = (state or {}).get("completedSessions")
existing_raw_list = (
    existing_completed if isinstance(existing_completed, list) else None
)
existing_clean = (
    sorted({
        c for c in existing_completed
        if isinstance(c, int) and not isinstance(c, bool) and c > 0
    })
    if isinstance(existing_completed, list)
    else []
)
merged = sorted(set(existing_clean) | set(from_events))
needs_rewrite = bool(merged) and existing_raw_list != merged
if needs_rewrite:
    ...  # write merged
```

### Session 3 (planned — extension `v0.13.13`) — reader fix

Teach `isMidSetComplete` to treat
`currentSession in completedSessions[]` as authoritative, **before**
falling through to the events-ledger check. Pseudo-code:

```
isMidSetComplete(statePath):
    sd = readSnapshot(statePath)
    if sd.currentSession < sd.totalSessions:
        return true  # genuinely mid-set; unchanged

    # NEW: completedSessions[] is an alternative authoritative signal
    if Array.isArray(sd.completedSessions) and
       sd.completedSessions.includes(sd.currentSession):
        return false  # array agrees that the final session is closed

    # Existing events-ledger check
    eventsPath = <dirname>/session-events.jsonl
    if exists(eventsPath) and
       not hasCloseoutEventForSession(eventsPath, sd.currentSession):
        return true  # ledger disagrees → drift → downgrade

    return false
```

The array check fires *before* the ledger check. A snapshot whose
array agrees that the final session is closed is treated as
authoritative regardless of what the ledger says — that's the
migration case the guard needs to recognize. A snapshot without
the array falls through to the existing ledger-only behavior,
preserving the v0.13.11 contract for legacy sets that haven't been
migrated.

Four planned `fileSystem.test.ts` fixtures: array-says-closed-no-
ledger (→ false), array-says-not-closed-ledger-also-not (→ true),
no-array-ledger-closeout (→ false, legacy unchanged), no-array-no-
ledger-closeout (→ true, legacy unchanged).

---

## The five questions

Answer in JSON. Each question gets:
- `verdict`: one of `"concur"`, `"concur-with-caveat"`, `"disagree"`,
  `"raise-concern"`.
- `severity`: one of `"none"`, `"minor"`, `"major"`, `"critical"`.
  Use `"none"` when verdict is `"concur"`.
- `rationale`: 2-5 sentences. Cite the specific shape or scenario
  you have in mind. If you flag a counter-example, walk through the
  state it would land in.

(a) **Hand-migration generalizes.** Does the hand-migration approach
applied to Sets 004 and 006 (add `completedSessions: [1..N]` to the
snapshot, then `--repair --apply` to synthesize the missing ledger
event) generalize safely to other pre-Set-022 sets? Or are there
shapes — e.g., a set where the operator's attestation actually is
wrong about an early session — that this approach would silently
mis-handle?

(b) **Writer union is monotone-up only.** Is the union computation
in Session 1's diff genuinely monotone-up? I.e., is there any
scenario where the union would incorrectly *add* a session number to
`completedSessions[]` that should not be marked closed? Consider:
events ledger with a `closeout_succeeded` event written by an
earlier `--repair --apply` (so a "synthetic" event), a snapshot with
a session number outside `[1..totalSessions]`, a malformed
`session_number` field, mode-config changes mid-set.

(c) **Reader ordering: array before ledger.** Is the planned reader
ordering (consult `completedSessions[]` first; fall through to the
events-ledger check only if the array doesn't include
`currentSession`) correct? Or should the two signals require
**mutual agreement** before the guard returns `false`? The
conservative alternative is: "array says closed AND ledger says
closed" → not mid-set; otherwise downgrade. The proposed design is:
"array says closed OR ledger says closed" → not mid-set.

(d) **Sharp-edge coverage.** Does the combined writer + reader fix
close the two sharp edges Set 022 surfaced — or is there a third
sharp edge somewhere else in the pipeline (e.g., the queue-state
reconciler, the disposition-gate freshness check, the start_session
inference of "max(closed)+1"; or some other reader that consults the
ledger directly without considering `completedSessions[]`) that this
set leaves unfixed?

(e) **Open-ended.** Anything else — design, naming, documentation,
test coverage, ordering of sessions in this set, anything that would
trip up a future maintainer. Empty string is a valid answer.

---

## Output format

Return exactly this JSON shape and nothing else:

```json
{
  "reviewer_provider": "<your provider name, e.g. gpt-5-4 or gemini-pro>",
  "answers": {
    "a_hand_migration_generalizes": { "verdict": "...", "severity": "...", "rationale": "..." },
    "b_writer_union_monotone_up":   { "verdict": "...", "severity": "...", "rationale": "..." },
    "c_reader_ordering":            { "verdict": "...", "severity": "...", "rationale": "..." },
    "d_sharp_edge_coverage":        { "verdict": "...", "severity": "...", "rationale": "..." },
    "e_open_ended":                 { "verdict": "...", "severity": "...", "rationale": "..." }
  },
  "summary": "2-4 sentences: is the combined design sound; any critical concern; one-line recommendation."
}
```

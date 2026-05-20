# Audit-resolution request: lock the five remaining design items

> **Date:** 2026-05-19 (Set 032 Session 1 — audit cycle for
> orchestrator check-out / check-in)
> **Context:** Round-1 (both engines) and round-2 (GPT-5.4) consensus
> on the orchestrator-tracking architecture is DONE. Direction is
> locked: migrate from multi-writer precedence to check-out /
> check-in. Five design items remain unresolved from GPT-5.4's
> round-2 must-fix list — three Highs and two open questions. This
> packet asks you to CONFIRM, REFINE, or REFUTE the pre-audit
> recommended verdict for each item.
>
> **Read order:** Section 1 (direction recap, 1 paragraph) →
> Section 2 (five items + recommended verdicts) → response template
> at the bottom.
>
> **You are one of two reviewers.** The other is **__OTHER__**. We
> want three-way agreement (you + the other reviewer + the operator).
> Where you and the other reviewer disagree, the operator
> adjudicates. Where you both confirm, the verdict locks and Set 032
> Session 2 drafts the Set 033 implementation spec accordingly.
>
> **This is the AUDIT phase, not the design phase.** We are NOT
> asking you to reopen direction. We are asking you to either
> sign off on a specific verdict or counter-propose a better one
> *for that item*. If you think the framing of an item is wrong,
> say so — but don't redesign the whole architecture.

---

## Section 1 — Direction recap (1 paragraph)

The dabbler-ai-orchestration repo's per-session-set marker today
(`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`)
is written by FOUR ranked writers (Claude `SessionStart` hook,
manual quickpick, `/think*` listener, Codex config-toml watcher)
with precedence-aware skipping and a writer log for diagnostics.
The migration replaces this with check-out / check-in semantics: at
session start the orchestrator CHECKS OUT the set (recording its
identity + a timestamp); at session close `close_session` CHECKS IT
IN; mid-session attach attempts by a different orchestrator surface
a conflict prompt instead of silent precedence-based override. The
v1 proposal + addendum + both engines' round-1 verdicts plus
GPT-5.4's round-2 verdict have all converged on this direction. The
five items below are the *implementation-shaping* decisions still
to lock before Set 033 can be honestly specced.

---

## Section 2 — The five items

### H1 — Writer authority (Full tier)

**The question:** Under check-out semantics, can hooks (Claude
`SessionStart`, Codex config-toml watcher) become PEER WRITERS of
the canonical lifecycle field (`session-state.json`), or must they
remain DETECTORS / INVOKERS that call the existing router-driven
boundary CLIs (`start_session`, `close_session`)?

**Pre-audit recommended verdict:** **router-only writes; hooks
become invokers.** The current Full-tier contract per
`ai_router/docs/close-out.md` names exactly two router-driven
boundary writes (`start_session.py` + `close_session.py`). Allowing
hooks to write the lifecycle field directly would re-introduce the
multi-writer model the migration is supposed to eliminate. Hooks
should DETECT the session start / end signal and INVOKE the
canonical writer; they should not race the writer.

**Implication if confirmed:** Set 033's writer pair stays exactly
two. The Claude `SessionStart` hook shells out to `start_session`
(non-blocking; failure → user-visible toast, not a silent retry).
Codex's config-toml watcher does the same on session-active
transitions. The marker file's writers shrink from four to zero
(see H2).

### H2 — Single source of truth

**The question:** Where does check-out state live — in
`session-state.json` (existing lifecycle authority per
`docs/session-state-schema.md`) or in
`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`
(per-set marker introduced in Set 029 Session 3)?

**Pre-audit recommended verdict:** **`session-state.json` is
canonical; the `.dabbler/orchestrator.json` marker is RETIRED.**
Rationale: (a) the lifecycle authority is already there; adding a
parallel store invites drift; (b) the marker file's reason to exist
was the precedence model the migration eliminates; (c) the
`session-state.json` lifecycle state machine already encodes
"in-flight vs. between sessions" — augmenting it with a single
`orchestrator` block (already present, see OQ1) is the natural fit;
(d) Set 033's resolver refactor (`resolveActiveSet()` →
`listInProgressSets()`) reads `session-state.json` per set
directly, so the marker file has no remaining consumer.

**Alternative considered and rejected:** keep the marker file as
DERIVED UI CACHE. Rejected because cache invalidation adds
complexity and the read cost from `session-state.json` is already
trivial (one file per in-progress set, file-watcher-backed).

**Implication if confirmed:** Set 033 retires the marker
file + the `MarkerWatchService` precedence logic. The tree-provider
reads `session-state.json` directly for each in-progress set's row.

### H3 — Hard coordination vs. advisory

**The question:** Is check-out a HARD COORDINATION primitive
(`start_session` refuses to write when a different orchestrator
holds the check-out; operator must `--force` or invoke a "Release
Check-Out" command) or an ADVISORY MARKER (writes always succeed;
the UI shows a warning if the holder differs but does not block)?

**Pre-audit recommended verdict:** **HARD COORDINATION at write
time, with explicit operator override as the safety valve.** The
failure mode the migration exists to prevent is "two orchestrators
inadvertently driving the same in-flight session set." An advisory
marker does not prevent that failure — it only annotates it after
the fact. The override exists for the legitimate "I purposely want
to switch orchestrators mid-session" case: a `--force` flag on
`start_session` + a Command Palette "Release Check-Out" action +
the conflict prompt in the queueing/polling flow. The advisory-only
framing in the addendum's §5 sentence ("No data is at stake — the
marker is purely advisory") is RETRACTED — there IS coordination
state at stake (the implicit "who owns the next write" question).

**Implication if confirmed:** `start_session` grows a refusal path
when the existing `orchestrator` block in `session-state.json` is
populated AND identity differs from the new caller's identity. The
refusal returns a clear error that names (a) the current holder
and (b) the two release paths (`--force` or Release Check-Out
Command Palette action).

### OQ1 — Field merge

**The question:** How do the proposed `checkedOut` / `checkedOutBy`
fields relate to the existing top-level `orchestrator` field in
`docs/session-state-schema.md`?

**Pre-audit recommended verdict:** **THEY MERGE.** The existing
`orchestrator: { engine, provider, model, effort }` block ALREADY
carries identity. Set 033 augments it with `checkedOutAt`
(timestamp set on transition to `status: in-progress`) and
`lastActivityAt` (bumped on same-orchestrator re-attach / `/think*`
effort-change events). `currentSession` already names the active
session number. No new top-level fields — `orchestrator` becomes
"the active check-out record when `status=in-progress`, null
otherwise."

**Implication if confirmed:** schema diff is +2 fields nested under
the existing `orchestrator` block, not a new top-level structure.
Lightweight tier's hand-maintenance burden grows by the same +2
fields, which the operator confirmed is acceptable
(`proposal-addendum.md` §3 cites this directly).

### OQ2 — Events as new types or aliases

**The question:** Are `work_checked_out` / `work_checked_in` NEW
ledger event types in `session-events.jsonl`, or ALIASES for the
existing `work_started` / `closeout_succeeded` events?

**Pre-audit recommended verdict:** **ALIASES.** No new event types
are needed. Check-out semantics are DERIVED from the existing
event progression: `work_started` IS the check-out moment;
`closeout_succeeded` IS the check-in moment. The lifecycle
derivation logic in `session_events.py` (per GPT R2 reference)
already reads this progression — the audit doc and any
documentation can describe these events under the new
"check-out / check-in" terminology without changing the ledger
schema or the derivation logic.

**Implication if confirmed:** no schema changes to
`session-events.jsonl`. Documentation in `docs/session-state-
schema.md` and `ai_router/docs/close-out.md` adopts the new
terminology. No code change in the events ledger writer.

---

## Section 3 — Response format (per item)

For each of H1, H2, H3, OQ1, OQ2, return:

```
Item: H1
Verdict: confirm | refine | refute
Reasoning: 2-5 sentences.
If refine/refute: proposed alternative + reason it beats the
  pre-audit recommendation.
```

Plus a brief overall recommendation (1 paragraph) on whether this
set of verdicts is ready to drive Set 033's implementation spec,
or whether something else is still missing.

Plain text or JSON — your call.

---

## Section 4 — What is NOT in scope for this audit

To save your tokens: do NOT re-litigate direction (migration vs.
status-quo), the queueing/polling feature, the within-set-
sequential invariant (already locked, see addendum §1), or the
Lightweight-tier check-in requirement (already locked, see
addendum §3). All four are settled. Focus on H1, H2, H3, OQ1, OQ2
only.

If you see a *new* must-resolve item we missed, raise it as a
sixth bullet (call it "H4 — <name>" or "OQ3 — <name>") with the
same structure. Otherwise the five above are the complete set.

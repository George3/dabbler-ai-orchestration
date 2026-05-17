# Set 030: Session-state v3 `sessions` ledger + terminology alignment

**Status:** In progress (1 of 5 sessions complete)
**Created:** 2026-05-17
**Cost so far:** $0.28 (Session 1 verification: gpt-5-4, Round A)

---

## Context

`session-state.json` v2 carries three independent progress fields
(`currentSession`, `totalSessions`, `completedSessions`) that drift
in real failure modes — most notably the ctelr-spec N-1/N display
drift (2026-05-12) and the fresh-set `completedSessions` schema gap
fixed in Set 028 Session 1.

Set 030 introduces schema v3 with a single canonical `sessions[]`
array. All summary values are derived from it. Phased migration
preserves backward compatibility through Phase 3, then drops legacy
field writes. Terminology unifies on "Complete" across the JSON
schema and the Session Set Explorer display (retiring "Done").

Origin: proposal at
`docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`
authored by/with GPT-5.4, strong-approved by Gemini Pro.

---

## Session 1: Schema doc + `get_progress()` helper + v2-read synthesizer

**Status:** Complete (2026-05-17)
**Orchestrator:** Claude Opus 4.7 @ effort=high
**Verification:** gpt-5-4, $0.275525, found 6 issues — all addressed

### Shipped

1. **`ai_router/progress.py`** — canonical Python reader. Exports
   `get_progress()`, `synthesize_v3_from_v2()`,
   `validate_invariants()`, `canonicalize_status()`,
   `extract_session_titles_from_spec()`, plus `ProgressView` /
   `SessionRecord` dataclasses and the
   `SessionStateInvariantError(rule, message)` exception class.
2. **`ai_router/tests/test_progress.py`** — 48 pytest cases covering
   all 8 invariants, v3 happy paths, v2 read synthesis, edge cases
   (bool/float in v2 numbers, contiguous-from-1, session-level
   cancelled rejection, rule 8 fires without top-status,
   alias canonicalization).
3. **`tools/dabbler-ai-orchestration/src/utils/progress.ts`** —
   TypeScript mirror with the same API, same invariants, same
   default-to-not-started semantics.
4. **`tools/dabbler-ai-orchestration/src/types.ts`** — adds
   `SessionStatus`, `SessionRecord`, `ProgressView`,
   `SessionStateV3` interfaces.
5. **`tools/dabbler-ai-orchestration/src/test/suite/progress.test.ts`** —
   46 mocha cases mirroring the pytest coverage.
6. **`docs/session-state-schema.md`** — full rewrite for v3.
   Sections: shape, derived values, 8 invariants, status glossary,
   Lightweight-tier worked example (one-field-flip per transition),
   migration notes, reader contract, bucketing rules.
7. **`docs/session-state-schema-example.{json,md}`** — v3 closed-shape
   example + side-by-side v2-vs-v3 narrative.
8. **`docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`** —
   patched two lingering `done` references (lines 139, 246) to
   `complete`; Revisions footer already documented the
   terminology-lock + GPT-5.4-revisions.
9. **`ai_router/router-config.yaml`** — registered
   `spec-title-extraction` task type per spec D14 (Session 5's AI
   fallback depends on it; landing in S1 removes a dependency risk).
   Pinned to `gemini-flash`, not auto-routed, not auto-verified.
10. **`ai_router/tests/test_spec_title_extraction_registered.py`** —
    6-test guard suite asserting the routing wiring stays correct.

### The 8 invariants (locked in code + doc)

1. `sessions[]` required and non-empty.
2. Numbers are positive ints, unique, **contiguous starting at 1**
   (tightened from "ascending" after Round A — per spec D12 "strict
   sequential invariant"). Session-level `"cancelled"` is rejected
   (reserved for a future schema).
3. At most one session in-progress.
4. Complete sessions form a contiguous prefix.
5. Top-level `"not-started"` requires every session to be
   `"not-started"`.
6. Top-level `"in-progress"` allows exactly one in-progress OR a
   between-sessions state (≥1 complete, ≥1 not-started, 0
   in-progress).
7. Top-level `"complete"` requires every session to be `"complete"`
   — synthesizer no longer papers over contradictions.
8. `lifecycleState: "closed"` pairs only with `"complete"` or
   `"cancelled"` top-level status. Rule 8 fires even when top-level
   status is absent.

### Round A verification fixes applied

gpt-5-4 verifier flagged 6 must-fix issues; all addressed:

1. **`synthesize_v3_from_v2()` force-promote removed.** Earlier
   draft promoted every session to complete when top-level status
   was `"complete"`. Now defaults stay `"not-started"` and the
   contradiction surfaces as rule 7 on `get_progress()`. "Fail
   loud, never silently recover" per spec D6.
2. **Strict-int filtering.** Python treats `bool` as `int`
   (`isinstance(True, int)` is `True`); both helpers now require
   `type(v) is int` (Python) / `Number.isInteger(v) && typeof v
   !== "boolean"` (TS) before using a v2 field for membership or
   status escalation. JS/Python divergence on `1.0` is documented.
3. **Rule 2 tightened to contiguous-from-1.** `[1, 3]` and `[2, 3]`
   are now rejected. Aligns code with spec D12.
4. **Session-level `"cancelled"` rejected.** `SESSION_STATUSES`
   tuple no longer includes `"cancelled"`; top-level
   `"cancelled"` is still accepted.
5. **Rule 8 always fires.** Hoisted above the `top_status is None`
   guard so `lifecycleState: "closed"` with missing top-level
   status no longer bypasses the check.
6. **Unknown top-level status now reports rule 2 (not rule 5).** The
   error is a shape/enum problem, not an inconsistency between
   top-level and per-session states.

### Test results

- pytest: **484 passed, 1 skipped, 8 e2e deselected** (was 476
  pre-Session-1; +8 from new edge-case coverage).
- mocha (Session 1's progress.test.ts): **46 passed**.
- TypeScript `tsc --noEmit`: clean.

### What did NOT ship in Session 1

- No writer changes (`register_session_start`, `close_session`
  unchanged). Writer dual-write ships in Session 2.
- No reader migration (close-out gates, tree provider, etc., still
  read legacy fields). Reader migration + Explorer label
  ("Done" → "Complete") ships in Session 3.
- No bulk migrator, no in-repo state-file migration. Ships in
  Session 4.
- No in-extension migration UX, no loading state, no GA release.
  Ships in Session 5.

### Decisions reified (from spec.md)

- **D2** — terminology unified on "complete" across schema + display
  labels (proposal doc patched; schema doc rewritten).
- **D7** — regex-first title extraction lives in
  `extract_session_titles_from_spec()`; AI fallback wires up in
  Session 5 via the now-registered `spec-title-extraction` task
  type.
- **D10** — Lightweight one-field-flip worked example shipped in
  the schema doc; Session 4 will dry-run it against a real
  homehealthcare-accessdb state file.
- **D13** — "no application reader may read legacy fields except
  through approved compatibility helpers" — `progress.py` /
  `progress.ts` ARE those helpers. Session 3 ships the lint rule.
- **D14** — `spec-title-extraction` registered in S1, not S5.
- Synthesizer hardened: default-to-not-started, fail-loud on
  contradictions, strict-int filtering.

## Session 2: (pending — dual-write writers + scaffolding)

(populated at session close)

## Session 3: (pending — reader migration + Explorer label)

(populated at session close)

## Session 4: (pending — bulk migrator + in-repo migration + RC build, NO publish)

(populated at session close)

## Session 5: (pending — alignment migration UX + loading state + final release)

(populated at session close)

---

## Final cost summary

(populated after Session 5 close-out)

# Set 049 Session 2 — §4 survey findings

Per spec §4, S2 opens with a 30-min re-survey of non-runtime consumers
flagged by Pass B. Findings recorded here so the rip-out decisions in
S2 are auditable.

## 1. `tools/dabbler-ai-orchestration/src/types/sessionSetsWebviewProtocol.ts`

**Finding:** Declares `ConflictKind` Literal as the 4-kind union
including the 3 retiring kinds (`engine-mismatch`, `bare-touch`,
`stale-checkout-touch`). Also declares `HarvestSignalsPayload` (Non-goal 2,
survives) and `RowPayload.accordionUpdatedAt` (typed `string | null`,
documented to carry `orchestrator.lastActivityAt`).

**Disposition:** Defer to S4 (Extension TS cleanup). The protocol shape
narrowing to `"writer-bypass"` only, removal of `accordionUpdatedAt`
documentation references, and the comment scrub are all part of the
spec §5 S4 scope. Not a blocker for S2 code-deletion.

## 2. `tools/dabbler-ai-orchestration/src/providers/HarvestService.ts`

**Finding:** HarvestService consumes `python -m ai_router.joiner
--coverage --json` (per-set coverage signals, Non-goal 2 survives) and
`--conflicts --json` (per-set conflicts). Its `parseConflicts`
silently drops unknown kinds via `VALID_CONFLICT_KINDS.has` filter.

**Disposition:** NOT BLOCKING. After S2 retires D1/D2 in
`ai_router/joiner/conflicts.py`, the joiner CLI emits only
`writer-bypass` kind; `parseConflicts` continues to accept that kind.
TS-side cleanup of the now-unreachable `ConflictKind` members and
`VALID_CONFLICT_KINDS` entries is S4 scope. The infra (cache, spawn,
toast on missing dep) survives intact per Non-goal 2.

## 3. Consumer-repo hooks (platform / harvester / homehealthcare-accessdb)

**Finding:** Grep across `c:/Users/denmi/source/repos/{dabbler-platform,
dabbler-access-harvester, dabbler-homehealthcare-accessdb}` for both
`chat-session-id` and `chatSessionId` returns **zero matches** in all
three repos.

**Disposition:** No consumer hook calls `start_session
--chat-session-id` directly. The Claude SessionStart hook
(`claude-session-start-invoker.js`) is the single invoker, shipped
inside this repo (`tools/dabbler-ai-orchestration/scripts/`) and
installed into consumer workspaces. T2 accept-with-warning still ships
as a safety blanket for any older copy of the invoker that might
linger in a consumer's `~/.claude/hooks/` directory or be revived from
git history. No-op for the current consumer set.

## 4. `ai_router/scripts/dump_session_state_schema.py` + committed reference

**Finding:** Confirmed hit. `build_example_state()` emits
`s1_orch` and `s2_orch` dicts that include all 3 retiring fields
(`chatSessionId`, `checkedOutAt`, `lastActivityAt`). The committed
reference at `docs/session-state-schema-example.json` mirrors that
shape. The `--check` drift-detection test
(`scripts/test_dump_session_state_schema.py`) will fail after the
writer reshape unless this file + the reference are updated in lock-step.

**Disposition:** ADD TO S2 SCOPE. Reshape `build_example_state()` to
emit the 4-field omit-null orchestrator block, regenerate the
committed reference with `python -m ai_router.scripts.dump_session_state_schema
--write docs/session-state-schema-example.json`, and confirm
`--check` exits 0. Added to S2 todo list as task #12 ("Update
dump_session_state_schema.py + reference for 4-field omit-null").

---

**Net survey conclusion:** No blockers surface. S2 proceeds with the
core ai_router code removal as scoped in spec §5. The only adjustment
to S2 scope is the dump_session_state_schema.py + reference update —
genuinely trivial (a few lines + a regenerated reference) and stays
in scope because the writer reshape forces it.

# Set 049 Session 1 — close-reason

S1 is the audit-S1 deliverable per the operator's audit-then-spec
discipline ([[audit-then-spec-for-substantial-features]]) and the
[[devils-advocate-default-for-roadmap-decisions]] devil's-advocate
pattern.

## What S1 produced

- **Audit artifacts** at
  `docs/proposals/2026-05-27-set-049-orchestrator-coordination-removal/`:
  - `proposal.md` — the input given to both passes (operator-locked
    premises P1-P5, open topics T1-T7, discovered collisions D1-D3,
    read-site survey, feature roll-call FR1-FR5)
  - `pass-a.md` — gemini-pro, primary author framing ($0.0175)
  - `pass-b.md` — gpt-5-4-mini, devil's advocate framing ($0.0300;
    fell back from gpt-5-4 which timed out)
  - `verdict.md` — synthesis with topic-by-topic decision and
    reasoning
  - `run_audit.py` + `run_pass_b.py` — reproduction scripts

- **Audit-locked spec** at
  `docs/session-sets/049-orchestrator-coordination-removal/spec.md`
  replacing the STUB. 5-session arc locked.

- **Memory** at
  `~/.claude/projects/.../memory/project_set_049_s1_audit_locked.md`;
  predecessor `project_set_049_stubbed.md` marked SUPERSEDED in
  MEMORY.md index.

- **Hygiene patch** addressing two Set-048-era context-menu defects
  the operator surfaced during S1 close-out review:
  1. "Copy Eval ▸" → "Copy Prompt ▸" rename (user-visible label only;
     internal `copyEval` identifier preserved)
  2. "Start New Parallel Session" submenu entry added (the
     `dabblerSessionSets.copyStartCommand.parallel` command existed
     but had no ActionRegistry surfacing)

  Per operator selection: shipped as a tiny hygiene patch in the same
  commit cycle as S1 close, NOT as scope creep into the Set 049 spec.

## Cost

Cumulative routed spend: **$0.0475 / $10 NTE (0.48%)**. Plenty of
headroom for S2-S5.

## What S2 picks up

Per the locked spec §5, S2 opens with the §4 survey gap close (30-min
re-survey of non-runtime consumers per Pass B's finding) before
code-deletion begins. Then ships the core ai_router code removal:

- `start_session.py` H3/H4 paths
- `new_chat_id.py` whole-file retire
- `close_session.py` check-in branch
- `joiner/conflicts.py` retire D1 (bare-touch) + D2 (engine-mismatch,
  stale-checkout-touch); decouple D3 (writer-bypass) into a general
  writer-discipline check
- `session_events.py` retire `holder_change` and `checkout_conflict`
  emit
- Retire chatSessionId-specific test files

## Why this S1 differs from prior audit-S1 sessions

This is the **first** S1 to ship a hygiene patch alongside the audit.
Prior audit-S1s (Set 047, Set 048) shipped audit-only. The operator's
2026-05-27 feature roll-call accountability mechanism (added to the
Set 049 stub memory) plus a same-session bug report drove the change:
when the operator surfaces a defect inline during S1 review and it's
trivially scoped, ship it as a separate commit in the same close-out
rather than deferring to a separate PR cycle.

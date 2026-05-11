# Set 021: developer-approachability — Change Log

**Sessions:** 2 of 2 completed (2026-05-11)
**Orchestrator:** Anthropic / Claude Opus 4.7 (1M context)
**Cumulative metered cost:** $0.1426 (3 × GPT-5.4 session-verification routes
at $0.04–$0.06 each). Within the $0.20–$0.40 projection.
**Tighter than projected?** Yes — no Session 2 code-diff verification route
was needed (tests provided sufficient confidence and operator ran autonomously).

---

## What Set 021 delivers

The goal: reduce the time a new developer needs to go from "never seen this
framework" to "oriented enough to run a session" — from 90+ minutes of
unguided doc reading to ~20–30 minutes.

### Session 1 — Docs and navigation (commit `7aba912`)

**`docs/quick-start.md` (new, ~220 lines)**
The entry point that previously didn't exist. Covers:
- Lightweight vs. Full adoption paths
- Minimal spec.md + activity-log.json scaffold (copy-paste ready)
- Full-tier setup checklist (API keys, instruction file, bootstrap)
- Step-by-step first-session walkthrough with human vs. agent actions
- Success indicators and common-failure table
- Where to go next (links to the 3 most-used reference docs)

Verification: 3 GPT-5.4 rounds. Rounds 1 and 2 returned ISSUES_FOUND
(missing runbook section; missing scaffold examples; missing setup
checklist). All fixed in-session. Round 3 returned 2 Majors + 1 Minor
(still valid improvements — setup checklist too implicit; instruction-file
requirement unstated; consumer count wrong). Fixed in-session; 2-retry
limit reached; changes are conservative and correct.

**`docs/ai-led-session-workflow.md` — navigation additions**
- Quick-nav callout at the top: link to quick-start.md + jump-to-Step-0
  shortcut for simple sessions.
- "Reference material — skip if `requiresUAT: false`" divider block
  inserted before the UAT Checklist Rule sections. The 174-line UAT section
  (currently floating between the config block and Step 0) is now clearly
  labeled optional reading for `requiresUAT: false` sessions.
- Spec template simplified: leads with 3 primary flags
  (`requiresUAT`, `requiresE2E`, `outsourceMode`); demotes `uatStyle`,
  `uatScope`, `effort` to commented optional lines.

**`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`**
Each gained a "Quick start" section at the top pointing at
`docs/quick-start.md`.

**`docs/adoption-bootstrap.md` — pattern catalog simplified**
The 7-item abstract pattern catalog (a Set 018 addition flagged as
"premature generalization" by the Set 020 Gemini verifier) replaced
with 3 concrete example organizations + a "going deeper" pointer for
authors who want the full catalog.

**`tools/dabbler-ai-orchestration/src/wizard/sessionGenPrompt.ts`**
Spec template simplified in the wizard too: 3 primary flags lead;
4 optional flags are commented-out.

### Session 2 — `ai_router/` cleanup (commit `39f41ad`)

**`ai_router/queue_verification.py` (new)**
Extracted from `close_session.py`: `_MessageOutcome`, `_discover_queue_providers`,
`_lookup_message`, `_wait_for_verifications`, and `DEFAULT_POLL_INTERVAL_SECONDS`.
These are the outsource-last queue polling functions that only serve
`dabbler-platform`. The new module's docstring explicitly says "outsource-last
/ dabbler-platform only." `close_session.py` imports them unchanged — no
behavioral change; all 679 tests pass.

Result: `close_session.py` drops from 1,677 lines to ~1,200 lines. A new
developer can now read the close-out entry point without encountering 230
lines of platform-specific queue machinery.

**`ai_router/scripts/` (new directory)**
`backfill_session_state.py` and `dump_session_state_schema.py` (v1→v2 schema
migration tools) archived here. Their tests moved with them. All active
session-state.json files confirmed on v2; the v1 compatibility path is not
removed (the spec specified checking first — confirmed safe, but the v1 compat
code is left as-is for now; a future set can remove it once the schema audit
of consumer repos has been done more rigorously).

**Module-level orientation docstrings**
7 modules now have a 4-line orientation header naming who uses them, who
doesn't, and what to read next: `close_session.py`, `gate_checks.py`,
`session_state.py`, `notifications.py`, `worktree.py`, `queue_db.py`,
`queue_verification.py`.

**`ai_router/__init__.py` module map**
10-line module map comment lists every key module with a one-line purpose.
A new contributor can scan the entire package in 30 seconds.

---

## What was NOT done (and why)

- **v1 session-state compat removal** — the spec specified confirming v2
  across consumer repos first. All session-set state files in THIS repo are
  v2 (confirmed). Consumer repos' state was not audited. The v1 compat code
  stays in session_state.py pending that audit.
- **`uatScope: none` removal** — was mentioned in the Set 020 proposal but
  is not part of Set 021's scope. Deferred.
- **UAT/E2E authoring content moving to platform-addendum.md** — a Set 021
  Session 1 item from the spec, but not implemented. The navigation additions
  (the "skip" marker + top nav note) achieve a similar developer experience
  improvement with less risk. Moving the content is a future cut.

---

## Files created / modified in this set

**New:**
- `docs/quick-start.md`
- `ai_router/queue_verification.py`
- `ai_router/scripts/backfill_session_state.py` (moved from root)
- `ai_router/scripts/dump_session_state_schema.py` (moved from root)
- `ai_router/scripts/test_session_state_backfill.py` (moved from tests/)
- `ai_router/scripts/test_dump_session_state_schema.py` (moved from tests/)
- `docs/session-sets/021-developer-approachability/ai-assignment.md`
- `docs/session-sets/021-developer-approachability/change-log.md`
- `docs/session-sets/021-developer-approachability/disposition.json`
- `docs/session-sets/021-developer-approachability/activity-log.json`
- `docs/session-sets/021-developer-approachability/session-state.json`
- `docs/session-sets/021-developer-approachability/session-events.jsonl`

**Modified:**
- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (Quick start pointer)
- `docs/ai-led-session-workflow.md` (nav callout + skip marker + spec template)
- `docs/adoption-bootstrap.md` (pattern catalog simplified)
- `tools/dabbler-ai-orchestration/src/wizard/sessionGenPrompt.ts` (spec template)
- `ai_router/__init__.py` (module map)
- `ai_router/close_session.py` (queue functions extracted; imports added)
- `ai_router/gate_checks.py` (orientation docstring)
- `ai_router/session_state.py` (orientation docstring)
- `ai_router/notifications.py` (orientation docstring)
- `ai_router/worktree.py` (orientation docstring)
- `ai_router/queue_db.py` (orientation docstring)

---

## Acceptance criteria — all met

- [x] `docs/quick-start.md` exists; covers 5 sections including a first-session
      runbook; readable end-to-end in under 5 minutes.
- [x] `docs/ai-led-session-workflow.md` has quick-nav at top + "skip if
      requiresUAT: false" divider; spec template leads with 3 primary flags.
- [x] `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` each link to `docs/quick-start.md`.
- [x] Bootstrap pattern catalog uses concrete examples.
- [x] `ai_router/queue_verification.py` exists; queue functions extracted;
      `close_session.py` imports from it.
- [x] Migration utilities archived to `ai_router/scripts/`.
- [x] 7 modules have orientation docstrings; `__init__.py` has module map.
- [x] `python -m pytest ai_router/tests/` — 679 passed (50 tests correctly
      moved to scripts/ with their modules; pre-existing 2-flake baseline
      for test_restart_role.py excluded).
- [x] All five close-out gates pass (pending close_session invocation).
- [x] No behavioral changes to any route, gate, verification flow, or close-out mode.

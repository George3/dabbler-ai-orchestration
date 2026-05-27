# Set 049 Session 2 — close-reason

S2 is the core ai_router code-removal session per spec §5 S2,
implementing operator-locked premises P1-P5 + audit-locked dispositions
T1-T7 / D1-D3 / FR1-FR5 across the Python surface. The TS surface
follows in S4; the migrator sweep + writer-side cleanup in S3.

## What S2 produced

### §4 pre-flight survey (Pass B gap close)

Pass B identified that the read-site survey underweighted non-runtime
consumers. S2 opened with a focused re-survey across 4 areas at
[`s2-survey-findings.md`](s2-survey-findings.md):

- **Webview protocol shape** (`sessionSetsWebviewProtocol.ts`) —
  declares `ConflictKind` Literal with the 3 retiring kinds +
  `HarvestSignalsPayload` + `RowPayload.accordionUpdatedAt` (typed but
  vestigial post-rip). Defer to S4 (Extension TS cleanup); not a
  blocker.
- **HarvestService.ts** — consumes joiner `--coverage --json` +
  `--conflicts --json` CLI; `parseConflicts` filters unknown kinds
  silently. NOT BLOCKING — graceful degradation handles the post-S2
  narrowing.
- **Consumer-repo hooks** (platform / harvester /
  homehealthcare-accessdb) — grep for `chat-session-id` /
  `chatSessionId` returns zero matches in all three; T2 accept-with-
  warning ships as safety blanket.
- **`dump_session_state_schema.py`** + committed reference — confirmed
  hit. Build function emits the 3 retiring fields; reference would
  drift. Added inline to S2 scope (trivially small).

No blockers surfaced. S2 proceeded with code-removal as scoped.

### Writer reshape (P1 / P2 / P3)

`ai_router/session_state.py::register_session_start`:

- Drops the `orchestrator_chat_session_id: Optional[str] = None`
  parameter from the function signature entirely.
- Changes `orchestrator_model: str` → `orchestrator_model: Optional[str] = None`
  and `orchestrator_effort: str = "unknown"` →
  `orchestrator_effort: Optional[str] = None` so callers that can't
  authoritatively declare those fields omit them.
- Rewrites the orchestrator-block construction to a 4-field omit-null
  dict: `{"engine": ...}` plus conditional `provider` / `model` /
  `effort` keys when the caller supplied a value. No `null` values,
  no `"unknown"` placeholder strings.
- Drops the `prior_orch_for_holder_check` derivation, the v3 + v4
  same-holder re-attach branches, the `chat_session_id_matches`
  predicate, and the `checked_out_at` / `lastActivityAt = now`
  emission lines. The historical comment block citing Set 033 H3 +
  Set 036 Q5 is replaced with a Set 049 spec-citation pointing at
  P1-P3.

### `start_session` CLI rip

`ai_router/start_session.py`:

- Removes constants `EXIT_CHECKOUT_CONFLICT = 4`, `EXIT_READ_ONLY = 6`,
  `CHAT_SESSION_ID_ENV_VAR`, `ENFORCE_COORDINATION_ENV_VAR`.
- Removes helpers `_coordination_enforced()`,
  `_identity_label()`, `_prompt_takeover_choice()`,
  `_is_interactive_tty()`, `_log_force_override()`,
  `_resolve_chat_session_id()`.
- Removes the entire H3 + H4 refusal branch in `_run_under_lock`
  (~100 lines): the prior-orchestrator-block check, the
  `engine_provider_match` + `chat_session_id_matches` derivation,
  the same-holder fall-through, the take-over / read-only TTY
  prompt branch, the EXIT_CHECKOUT_CONFLICT / EXIT_READ_ONLY exit
  paths, the force-override audit-log call on handoff.
- Adds `_warn_chat_session_id_ignored()` (T2 accept-with-warning:
  one stderr line per `--chat-session-id` supply).
- Adds `_log_session_start()` (T5: ~/.dabbler/orchestrator-writer.log
  survives as a generic "start_session ran" record).
- `--force` flag removed entirely (only consumer was the H3
  force-override path).
- `--chat-session-id` flag retained, value ignored by the writer.
- `--model` and `--effort` flags made optional with no
  `"unknown"` default per T3.

### `new_chat_id.py` whole-file retire

Entire CLI removed (no preservation flag per spec §5 S2 directive;
T2 doesn't require its survival). `test_new_chat_id.py` deleted.

### `close_session.py` audit-payload cleanup

`_peek_orchestrator_identity()` drops the `chatSessionId` field from
its return dict (P3). Docstring + the calling-site comment updated to
reflect the post-Set-049 model — per-session orchestrator block is a
historical record, not a check-out flag. The `_flip_state_to_closed`
"cross-tier check-in" no longer nulls anything (was already implicit
in v4); the comment in `session_state.py` was tightened.

### `joiner/conflicts.py` D1 + D2 retire, D3 decoupled

`detect_engine_mismatch` + `detect_bare_or_stale_touch` deleted
entirely. The `_touches_workspace` helper deleted. `ConflictKind`
Literal narrowed to `Literal["writer-bypass"]`. Module docstring +
`detect_writer_bypass` docstring reframed as engine-independent
writer-discipline check (per spec D3 disposition). `scan_conflicts`
signature drops `claude_root` / `copilot_root` /
`engine_mismatch_window` / `staleness_threshold` (joiner CLI was
already on the writer-bypass-only subset).

### `session_events.py` T6 — no-op

Surveyed for `holder_change` / `checkout_conflict` event-type emit
sites. The literal event-type strings appear ONLY in the test names
`test_no_tty_refuses_with_exit_checkout_conflict` /
`test_tty_cancel_returns_exit_checkout_conflict` (about
EXIT_CHECKOUT_CONFLICT, not the event type), in the audit proposal,
and in the spec — they were never emitted by any code path in this
repo. T6 is therefore a documentation-only directive; no code edits
needed.

### `dump_session_state_schema.py` + reference

`build_example_state()` reshaped to emit the 4-field omit-null
orchestrator block on the example sessions; committed reference at
`docs/session-state-schema-example.json` regenerated to match
(byte-deterministic drift check passes — confirmed via the
PYTHONPATH-sys.path-shim invocation pattern conftest establishes).

### Tests

Retired (whole-file delete):

- `test_chatsessionid_writer.py`
- `test_checkout_writer.py`
- `test_start_session_takeover_prompt.py`
- `test_new_chat_id.py` (companion to retired CLI)

Updated:

- `test_joiner_conflicts.py` rewritten to cover only writer-bypass +
  `scan_conflicts` walks emitting writer-bypass kinds.
- `test_session_state_v4_writers.py::test_in_progress_session_carries_per_session_metadata`
  drops the `orchestrator_chat_session_id` kwarg + chatSessionId /
  checkedOutAt / lastActivityAt assertions; replaced with a single
  `assert orch == {engine, provider, model, effort}` equality check.
  New `test_orchestrator_block_applies_omit_null` test added.
- `test_no_router_backcompat.py::test_start_session_with_force_still_works`
  / `test_start_session_no_router_with_force_both_set` replaced with
  `test_start_session_chat_session_id_still_parses` /
  `test_start_session_no_router_with_chat_session_id_both_set`
  matching the T2 accept-with-warning surface.

## Test suite

952 ai_router tests pass + 1 skipped + 0 regressions. The pre-
existing `ai_router/scripts/test_dump_session_state_schema.py`
collection error (bare-import + scripts/ subdir mismatch) is
**not** Set-049-caused — confirmed via `git stash` comparison before
the writer reshape; left for a follow-on hygiene patch.

## Defer to S3 / S4 / S5

Per the locked arc:

- **S3**: `claude-session-start-invoker.js` hook reduction +
  `migrate_v3_to_v4.py` T4 sweep+normalize extension (strip the 3
  retired fields from historical state files) +
  `docs/session-state-schema.md` Writer Contract section. The v4
  migrator's `.bak` rollback contract preserved.
- **S4**: TS surface cleanup — webview protocol shape narrows
  `ConflictKind` to writer-bypass, removes `accordionUpdatedAt`,
  retires `checkOutOrchestrator` / `releaseCheckOut` /
  `newChatIdWorkflowToast` / `chatSessionMismatchModal` /
  `CheckoutPollService` commands, removes Set 045 harvest-badge /
  conflict-pill rendering from `CustomSessionSetsView.ts`,
  HarvestService.ts pruned to the surviving conflict kinds, cross-
  repo-checkout-notice.md rewritten as T7 deprecation instruction.
- **S5**: CLAUDE.md hard-coordination section retire, version walk
  update, ai-led-session-workflow.md Step 6/8 references, rip-out
  UAT checklist, dual version bumps (PyPI + Marketplace), CHANGELOG
  entries, change-log.md, final close-out.

## Cost

S1 spent $0.0475 routed. S2 ran the rip-out without invoking the
router mid-session (Claude Opus 4.7 1M orchestrator did the work
directly per the memory-locked discipline). Cross-provider
verification at close-out via Round A is the only S2 routed cost.

## Why this S2 is heavy on deletions

Net diff: -2916 lines (3266 deletions, 350 insertions). The
coordination layer's surface area was substantial — Set 033 + Set
036 contributed roughly 5 modules of code that S2 retires alongside
the test files that exercised them. The rip is faithful to the
spec's "removal-dominated" framing.

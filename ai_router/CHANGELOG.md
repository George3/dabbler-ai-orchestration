# Changelog — `dabbler-ai-router`

All notable changes to the `ai_router` Python package are documented
here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.3.0] — 2026-05-15

### Removed — BREAKING

- **`outsourceMode: last` daemon infrastructure (Set 026 Session 1).**
  The queue-mediated verifier daemon path is gone end-to-end. Modules
  deleted: `queue_status`, `heartbeat_status`, `queue_db`,
  `queue_verification`, `daemon_pid`, `orchestrator_role`,
  `restart_role`, `role_status`, `capacity`, `verifier_role`.
- **Mode-config public surface:** `ModeConfig`, `OUTSOURCE_MODES`,
  `ROLE_VALUES`, `DEFAULT_OUTSOURCE_MODE`, `parse_mode_config`,
  `read_mode_config`, `validate_mode_config`.
- **Queue/daemon public surface:** `QueueDB`, `QueueMessage`,
  `DuplicateIdempotencyKeyError`, `VerifierDaemon`,
  `OrchestratorDaemon`, `FollowUpRequested`,
  `ORCHESTRATOR_TASK_TYPES`, `TASK_VERIFICATION_FOLLOWUP`,
  `TASK_VERIFICATION_REJECTED`, `UnknownTaskTypeError`,
  `make_dispatch_verifier`, `make_worker_id`, `process_one_message`,
  `run_verification`, `HEARTBEAT_INTERVAL_SECONDS`,
  `DEFAULT_POLL_INTERVAL_SECONDS`, the `daemon_pid` PID-file helpers,
  and `QUEUE_DEFAULT_BASE_DIR`.
- **`route()` parameters:** `mode=` and `queue_base_dir=` are gone.
  `route()` is now synchronous-only. `RouteResult` no longer has
  `pending`, `message_id`, or `queue_provider` fields.
  `VerificationResult` no longer has those fields either.
- **`close_session` CLI:** `--timeout` flag removed; exit code 4
  (`verification_timeout`) removed; queue-message-citation repair
  case removed; `_wait_for_verifications` no longer called.
- **`disposition.verification_method`:** value `"queue"` removed.
  Surviving methods are `"api"`, `"manual"`, and `"skipped"`.
  `verification_message_ids` is now required to be empty for every
  method (kept as a list field for schema stability).
- **`ai_router/docs/two-cli-workflow.md`** removed.
- **`reconciler.py`:** `rerun_verification_timeout` action removed.

### Changed

- **`cost_report.py`** simplified — removed the subscription-utilization
  block (`_build_subscription_utilization`, `_print_outsource_last_report`)
  and the mode-aware branch in `get_costs` / `print_cost_report`. JSON
  output no longer carries the `outsource_mode` or
  `subscription_utilization` keys.
- **`close_out.py`** simplified — single-path implementation that
  routes a fresh turn via `route_fn`. The mode-aware
  outsource-last-skip-route branch is gone; `close_session_runner`
  injection point is gone.

### Notes — Partial state

Set 026 Session 1 also intended to scrub docs (workflow doc, adoption-
bootstrap, authoring-guide, close-out.md, spec-md-schema) and 26
historical `spec.md` files' `outsourceMode:` configuration lines. That
work is **deferred to a follow-up session**; the acceptance criterion
`git grep -i 'outsourcemode\|queue_db\|verifier daemon\|subscription cli'`
returning zero hits is NOT yet satisfied. The code surface, however,
is clean of the removed symbols. Sessions 2–6 of Set 026 will continue
the work and ship the canonical 0.3.0 release alongside extension
v0.13.15.

## [0.2.x] and earlier

Prior versions of `ai_router` did not maintain a CHANGELOG.md. The
0.3.0 entry above is the first formal release-notes entry. Refer to
`docs/session-sets/0NN-*/change-log.md` for the per-set narrative
history.

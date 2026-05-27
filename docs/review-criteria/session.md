<!--
  Repo-specific review criteria for the MOST RECENT SESSION's
  accomplishments.

  This file is read by the Dabbler extension's `Copy: Session-
  accomplishments review prompt` command and embedded into the
  clipboard payload under "Operator review criteria (from
  docs/review-criteria/session.md)".

  - Edit the bullets below to teach reviewers what THIS repo cares
    about most when judging a finished session.
  - Keep it short (≤ ~30 lines).
  - Delete this file to fall back to the extension's default English
    session-review instructions.
-->

When reviewing a finished session, weight the following:

- **Spec alignment.** Compare the session's commits and activity-log
  entries against the spec's promised deliverables for THIS session
  number. Flag scope creep (commits unrelated to the stated goal) and
  missing deliverables.
- **Activity-log honesty.** Each entry should correspond to a real
  artifact (commit hash, file change, command invocation). Entries
  that summarize work without naming concrete outputs are weak audit
  trail.
- **Round-A in-flight fixes.** If the session ran a cross-provider
  verification, were Round-A findings addressed in-flight rather
  than deferred? Per `feedback_dont_hide_behind_out_of_scope`, small
  fixes belong in the same session.
- **Test coverage.** New or behavior-changing code should ship with
  at least unit-test coverage. Note any new code paths without a
  matching test.
- **Documentation drift.** If the session changed a public interface
  (CLI flag, command ID, schema field), the relevant doc file must
  be updated in the same session.
- **Budget discipline.** Cumulative routed spend should be reported
  in the session's close-out notes (per
  `feedback_budget_question_scope`).

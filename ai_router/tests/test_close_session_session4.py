"""Set 3 Session 4 — ``--manual-verify``, ``--repair``, full integration.

Three test groups:

1. **``--manual-verify`` event emission and validation.** Beyond Session 3's
   "the queue wait is bypassed" check, Session 4 owns the attestation
   audit trail: a ``verification_completed`` event with
   ``method=manual`` and the operator's attestation text must land in
   ``session-events.jsonl``. Also covers the validation rule that
   ``--manual-verify`` requires either ``--interactive`` or
   ``--reason-file`` (no silent bypass) and rejects empty attestations.

2. **``--repair`` drift detection and ``--apply`` correction.** The
   four drift cases from ``_run_repair`` docs: state-says-closed-but-
   no-event, event-says-closed-but-state-not-flipped, stranded
   mid-closeout, and disposition-references-missing-queue-message.
   Each is exercised with both diagnostic (default) and ``--apply``
   modes so the idempotency story is visible.

3. **Four end-to-end scenarios from the Set 3 acceptance criteria.**
   Outsource-first happy path, outsource-last happy path, bootstrapping
   recovery via ``--repair --apply``, and ``--manual-verify`` skipping
   the queue. Sessions 1-3 already covered the first two at the unit
   level; here they run as the integration scenarios the spec calls
   out (clean fixture → run close_session → assert end state).

The fixture in this file matches the Session 3 wait fixture (real git
repo + bare remote so the deterministic gates pass) so test data
stays comparable across files.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest

import close_session
from disposition import Disposition, write_disposition
from queue_db import QueueDB
from session_events import (
    SessionLifecycleState,
    append_event,
    current_lifecycle_state,
    read_events,
)
from session_state import (
    NextOrchestrator,
    NextOrchestratorReason,
    _flip_state_to_closed,
    mark_session_complete,
    read_session_state,
    register_session_start,
)


# ---------------------------------------------------------------------------
# Helpers (mirrored from test_close_session_verification_wait.py — kept local
# so the two test files don't develop a fixture-sharing coupling)
# ---------------------------------------------------------------------------

def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc


def _ns(**overrides):
    parser = close_session._build_parser()
    args = parser.parse_args([])
    for k, v in overrides.items():
        setattr(args, k, v)
    return args


def _valid_next_orc() -> NextOrchestrator:
    return NextOrchestrator(
        engine="claude-code",
        provider="anthropic",
        model="claude-opus-4-7",
        effort="high",
        reason=NextOrchestratorReason(
            code="continue-current-trajectory",
            specifics="stay on opus for the heavy lifting",
        ),
    )


@pytest.fixture
def closeable_set(tmp_path: Path) -> Path:
    """Real git repo + bare remote + session 1-of-2, ready for close-out."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "baseline")

    bare = tmp_path / "repo.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "-b", "main")
    _git(root, "remote", "add", "origin", str(bare))
    _git(root, "push", "-u", "origin", "main")

    set_dir = root / "docs" / "session-sets" / "test-set"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    register_session_start(
        session_set=str(set_dir),
        session_number=1,
        total_sessions=2,
        orchestrator_engine="claude-code",
        orchestrator_model="claude-opus-4-7",
        orchestrator_effort="high",
        orchestrator_provider="anthropic",
    )
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "sessionSetName": "test-set",
            "createdDate": "2026-04-30T00:00:00-04:00",
            "totalSessions": 2,
            "entries": [{
                "sessionNumber": 1,
                "stepNumber": 1,
                "stepKey": "session-1/work",
                "dateTime": "2026-04-30T01:00:00-04:00",
                "description": "did work",
                "status": "complete",
                "routedApiCalls": [],
            }],
        }, indent=2),
        encoding="utf-8",
    )
    return set_dir


def _commit_and_push_set(set_dir: Path) -> None:
    repo_root = set_dir
    while not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-m", "land work")
    _git(repo_root, "push", "origin", "main")


def _enqueue(queue_dir: Path, provider: str, *, idempotency_key: str) -> str:
    qdb = QueueDB(provider=provider, base_dir=str(queue_dir))
    return qdb.enqueue(
        from_provider="orchestrator",
        task_type="session-verification",
        payload={"task_type": "session-verification", "content": "x"},
        idempotency_key=idempotency_key,
    )


# ===========================================================================
# Group 1: ``--manual-verify`` event emission and validation
# ===========================================================================

def test_manual_verify_emits_attestation_event(
    closeable_set: Path, tmp_path: Path,
):
    """``--manual-verify --reason-file`` lands the operator's attestation
    in the events ledger as a ``verification_completed`` with
    ``method=manual``.
    """
    queue_dir = tmp_path / "queues"
    mid = _enqueue(queue_dir, "gpt-5-4-mini", idempotency_key="m1")

    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="manually-verified",
        verification_method="queue",
        files_changed=[],
        verification_message_ids=[mid],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))
    _commit_and_push_set(closeable_set)

    reason_path = tmp_path / "reason.md"
    reason_path.write_text(
        "verified out-of-band via paired live walkthrough on 2026-04-30",
        encoding="utf-8",
    )

    args = _ns(
        session_set_dir=str(closeable_set),
        manual_verify=True,
        reason_file=str(reason_path),
        timeout=1,
    )
    outcome = close_session.run(
        args,
        queue_base_dir=str(queue_dir),
        sleep=lambda _s: pytest.fail(
            "manual-verify must not enter queue wait"
        ),
    )

    assert outcome.result == "succeeded", outcome.messages
    assert outcome.verification_method == "manual"

    events = read_events(str(closeable_set))
    manual_completed = [
        e for e in events
        if e.event_type == "verification_completed"
        and e.fields.get("method") == "manual"
    ]
    assert len(manual_completed) == 1, (
        "expected exactly one manual verification_completed event"
    )
    assert manual_completed[0].fields.get("attestation") == reason_path.read_text(
        encoding="utf-8",
    )
    assert manual_completed[0].fields.get("verdict") == "manual_attestation"


def test_manual_verify_interactive_prompts_for_attestation(
    closeable_set: Path, tmp_path: Path,
):
    """``--manual-verify --interactive`` (no reason file) prompts on stdin
    and the prompted text becomes the attestation.
    """
    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="manually-verified",
        verification_method="api",
        files_changed=[],
        verification_message_ids=[],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))
    _commit_and_push_set(closeable_set)

    captured_prompts: List[str] = []

    def fake_prompt(message: str) -> str:
        captured_prompts.append(message)
        return "verified live by the human at 2026-04-30T17:00Z"

    args = _ns(
        session_set_dir=str(closeable_set),
        manual_verify=True,
        interactive=True,
    )
    outcome = close_session.run(args, prompt_fn=fake_prompt)

    assert outcome.result == "succeeded", outcome.messages
    assert len(captured_prompts) == 1
    assert "attestation" in captured_prompts[0].lower()

    events = read_events(str(closeable_set))
    request = next(
        e for e in events if e.event_type == "closeout_requested"
    )
    # Reason came from the prompt rather than a file, so it lands as
    # manual_attestation rather than reason on the request event.
    assert request.fields.get("manual_attestation") == (
        "verified live by the human at 2026-04-30T17:00Z"
    )


def test_manual_verify_requires_attestation_source(closeable_set: Path):
    """``--manual-verify`` without ``--interactive`` or ``--reason-file``
    is invalid invocation — silent bypass would defeat the audit trail.
    """
    args = _ns(
        session_set_dir=str(closeable_set),
        manual_verify=True,
    )
    outcome = close_session.run(args)
    assert outcome.result == "invalid_invocation"
    assert outcome.exit_code == 2
    assert any(
        "--manual-verify requires" in m for m in outcome.messages
    )


def test_manual_verify_empty_attestation_rejected(
    closeable_set: Path, tmp_path: Path,
):
    """Empty / aborted attestation is invalid invocation."""
    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="manually-verified",
        verification_method="api",
        files_changed=[],
        verification_message_ids=[],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))

    args = _ns(
        session_set_dir=str(closeable_set),
        manual_verify=True,
        interactive=True,
    )
    # Operator hits Enter without typing anything.
    outcome = close_session.run(args, prompt_fn=lambda _msg: "")

    assert outcome.result == "invalid_invocation"
    assert outcome.exit_code == 2
    assert any(
        "non-empty attestation" in m for m in outcome.messages
    )


# ===========================================================================
# Group 2: ``--repair`` drift detection and ``--apply`` correction
# ===========================================================================

# Set 022 invariant: _flip_state_to_closed appends currentSession to
# completedSessions[] on every close (sorted, unique), and the
# SET-level status flip is gated on
# len(completedSessions) == totalSessions AND change-log.md present.
# These tests pin the writer behavior independently of the repair
# path so a regression in either branch is caught.

def test_flip_state_appends_completed_sessions_mid_set(
    closeable_set: Path,
):
    """Mid-set close: session number is appended to
    ``completedSessions[]`` but the SET status stays in-progress.
    """
    # closeable_set is totalSessions=2 with session 1 in-flight.
    # Direct _flip_state_to_closed simulates the session-close
    # boundary write that mark_session_complete performs after the
    # gate passes; here we exercise the writer in isolation.
    _flip_state_to_closed(str(closeable_set))
    state = read_session_state(str(closeable_set)) or {}
    assert state.get("completedSessions") == [1], (
        f"expected completedSessions=[1] after mid-set close; got "
        f"{state.get('completedSessions')!r}"
    )
    assert state.get("status") == "in-progress"
    assert state.get("lifecycleState") == "work_in_progress"
    assert state.get("completedAt") is None


def test_flip_state_idempotent_completed_sessions(
    closeable_set: Path,
):
    """A second flip for the same currentSession does not duplicate
    entries in ``completedSessions[]`` — the append is sorted+unique.
    """
    _flip_state_to_closed(str(closeable_set))
    _flip_state_to_closed(str(closeable_set))
    state = read_session_state(str(closeable_set)) or {}
    assert state.get("completedSessions") == [1]


def test_flip_state_flips_set_on_final_session(closeable_set: Path):
    """Final close (len(completedSessions) == totalSessions AND
    change-log.md present): the SET flips to complete/closed.
    """
    # Close session 1 first.
    _flip_state_to_closed(str(closeable_set))
    # Register and close session 2 (the final session). Author
    # change-log.md as required.
    register_session_start(
        session_set=str(closeable_set),
        session_number=2,
        total_sessions=2,
        orchestrator_engine="claude-code",
        orchestrator_model="claude-opus-4-7",
        orchestrator_effort="high",
        orchestrator_provider="anthropic",
    )
    (closeable_set / "change-log.md").write_text(
        "# change log\n\nSet done.\n", encoding="utf-8",
    )
    _flip_state_to_closed(str(closeable_set))

    state = read_session_state(str(closeable_set)) or {}
    assert state.get("completedSessions") == [1, 2]
    assert state.get("status") == "complete"
    assert state.get("lifecycleState") == "closed"
    assert state.get("completedAt") is not None


def test_flip_state_no_change_log_does_not_flip_set(
    closeable_set: Path,
):
    """Belt-and-suspenders: even when len(completedSessions) ==
    totalSessions, a missing change-log.md keeps the SET at
    in-progress. The math signal alone is not sufficient.
    """
    _flip_state_to_closed(str(closeable_set))
    register_session_start(
        session_set=str(closeable_set),
        session_number=2,
        total_sessions=2,
        orchestrator_engine="claude-code",
        orchestrator_model="claude-opus-4-7",
        orchestrator_effort="high",
        orchestrator_provider="anthropic",
    )
    # Deliberately do NOT write change-log.md.
    _flip_state_to_closed(str(closeable_set))

    state = read_session_state(str(closeable_set)) or {}
    assert state.get("completedSessions") == [1, 2]
    assert state.get("status") == "in-progress", (
        "change-log.md absence must keep the SET at in-progress "
        "even when sessionsCompleted >= totalSessions"
    )


def test_register_session_start_preserves_completed_sessions(
    closeable_set: Path,
):
    """Set 022 invariant: register_session_start preserves
    ``completedSessions[]`` across the snapshot rewrite. The array
    is the progress ledger and survives session boundaries.
    """
    # Close session 1 so completedSessions=[1] lands on disk.
    _flip_state_to_closed(str(closeable_set))
    state = read_session_state(str(closeable_set)) or {}
    assert state.get("completedSessions") == [1]

    # Register session 2's start — the snapshot is overwritten,
    # but completedSessions[] must survive.
    register_session_start(
        session_set=str(closeable_set),
        session_number=2,
        total_sessions=2,
        orchestrator_engine="claude-code",
        orchestrator_model="claude-opus-4-7",
        orchestrator_effort="high",
        orchestrator_provider="anthropic",
    )
    state = read_session_state(str(closeable_set)) or {}
    assert state.get("currentSession") == 2
    assert state.get("completedSessions") == [1], (
        "register_session_start must preserve completedSessions[] "
        "across the start-of-session snapshot rewrite"
    )


def test_repair_no_drift_clean_session(closeable_set: Path):
    """A freshly-started, never-closed session has no drift to report."""
    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args)
    assert outcome.result == "succeeded"
    assert any("no drift detected" in m for m in outcome.messages)


def test_repair_detects_state_says_closed_but_no_event(
    closeable_set: Path,
):
    """Bootstrapping drift: state.json shows complete/closed but the
    events ledger has no ``closeout_succeeded``. Diagnostic mode reports
    drift; ``--apply`` appends synthetic events so the ledger and the
    snapshot agree.
    """
    # Simulate the legacy bootstrapping path: orchestrator hand-wrote
    # session-state.json to complete/closed without emitting the
    # closeout ledger trio. Set 022 made _flip_state_to_closed
    # conditional on len(completedSessions) == totalSessions AND
    # change-log present, so it can no longer be (mis)used as a
    # "force-flip" shortcut. The fixture is mid-set (totalSessions=2,
    # only session 1 registered), and a legitimate bootstrapping
    # drift in the wild always looked like a hand-edit anyway — so
    # the test now reproduces that directly.
    (closeable_set / "change-log.md").write_text(
        "# change log\n\nlast-session marker for the drift fixture.\n",
        encoding="utf-8",
    )
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-04-30T01:00:00-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Diagnostic: drift surfaces, exit 5, ledger untouched.
    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args)
    assert outcome.result == "repair_drift"
    assert outcome.exit_code == 5
    assert any(
        "session-state.json reports closed/complete" in m
        for m in outcome.messages
    )
    events_before = read_events(str(closeable_set))
    assert not any(
        e.event_type == "closeout_succeeded" for e in events_before
    )

    # --apply: ledger gets the synthetic events.
    args2 = _ns(
        session_set_dir=str(closeable_set), repair=True, apply=True,
    )
    outcome2 = close_session.run(args2)
    assert outcome2.result == "succeeded"
    events_after = read_events(str(closeable_set))
    repaired_succeeded = [
        e for e in events_after
        if e.event_type == "closeout_succeeded"
        and e.fields.get("repaired") is True
    ]
    assert len(repaired_succeeded) == 1
    assert (
        repaired_succeeded[0].fields.get("repair_reason")
        == "state_says_closed_but_no_closeout_event"
    )

    # Idempotent: a second --apply pass has nothing more to do.
    outcome3 = close_session.run(args2)
    assert outcome3.result == "succeeded"
    assert any(
        "no drift detected" in m for m in outcome3.messages
    )


def test_repair_detects_mixed_mode_drift(closeable_set: Path):
    """Mixed-mode drift: sessions 1..N-1 went through close_session
    (events ledger has their closeouts) but session N was hand-authored
    — session-state.json was edited to currentSession=N / status=complete
    without anyone running the gate for session N. The pre-Set-020 trigger
    (``lifecycle != CLOSED``) missed this because the ledger's most-recent
    lifecycle was already CLOSED for an earlier session. Trigger is now
    session-number-specific: ``has_closeout_succeeded(state_session_number)``.

    Reproduces the unified-master-details-composite drift (2026-05-12):
    sessions 1-4 had closeout_succeeded events, session-state.json claimed
    complete/VERIFIED for currentSession=5, ledger had no session-5 events.
    """
    # Session 1 went through close_session — append its closeout trio.
    append_event(str(closeable_set), "closeout_requested", 1)
    append_event(str(closeable_set), "closeout_succeeded", 1, verdict="VERIFIED")

    # Hand-author session 2's state without invoking close_session. The
    # orchestrator wrote currentSession=2 / status=complete / lifecycleState
    # =closed and called it done. No session-2 events in the ledger.
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["currentSession"] = 2
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-05-12T15:20:00.000000-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Diagnostic: drift surfaces for session 2 specifically.
    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args)
    assert outcome.result == "repair_drift"
    assert outcome.exit_code == 5
    assert any(
        "no closeout_succeeded for the current session (session 2)" in m
        for m in outcome.messages
    ), outcome.messages

    # --apply: synthetic closeout trio lands against session 2.
    args2 = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
    outcome2 = close_session.run(args2)
    assert outcome2.result == "succeeded"
    events_after = read_events(str(closeable_set))
    session2_closeouts = [
        e for e in events_after
        if e.event_type == "closeout_succeeded" and e.session_number == 2
    ]
    assert len(session2_closeouts) == 1
    assert session2_closeouts[0].fields.get("repaired") is True
    assert (
        session2_closeouts[0].fields.get("repair_reason")
        == "state_says_closed_but_no_closeout_event"
    )
    # Session 1's original (non-repaired) closeout is untouched.
    session1_closeouts = [
        e for e in events_after
        if e.event_type == "closeout_succeeded" and e.session_number == 1
    ]
    assert len(session1_closeouts) == 1
    assert session1_closeouts[0].fields.get("repaired") is not True

    # Set 022: --apply also backfills completedSessions[] from the
    # (now-repaired) events ledger. With sessions 1 and 2 both
    # showing closeout_succeeded after --apply, the snapshot should
    # record both as closed.
    state_after = read_session_state(str(closeable_set)) or {}
    assert state_after.get("completedSessions") == [1, 2], (
        f"expected completedSessions=[1, 2] after --apply backfill; "
        f"got {state_after.get('completedSessions')!r}"
    )
    assert any(
        "backfilled completedSessions=[1, 2]" in m
        for m in outcome2.messages
    ), outcome2.messages

    # Idempotent.
    outcome3 = close_session.run(args2)
    assert outcome3.result == "succeeded"
    assert any("no drift detected" in m for m in outcome3.messages)


def test_repair_preserves_snapshot_completed_sessions_superset(
    closeable_set: Path,
):
    """Set 023: ``--repair --apply`` Case 1 must preserve a snapshot's
    hand-authored ``completedSessions[]`` when it is a superset of what
    the events ledger can reconstruct.

    Reproduces the Set 022 migration shape on Set 004 (2026-05-15): a
    pre-Set-022 set's snapshot was hand-migrated to declare
    ``status: complete`` with ``completedSessions: [1, 2, 3, 4]`` even
    though the events ledger only ever recorded one closeout (session
    3, forced). Under the pre-Set-023 overwrite-from-events behavior,
    ``--repair --apply`` regressed the array to ``[3, 4]`` (events
    [3] + synthetic [4]), losing the operator's intent for sessions
    1 and 2. Under Set 023 the repair takes the union and preserves
    the snapshot's claim.
    """
    # Events ledger: only a single forced session-3 closeout (the
    # legacy shape).
    append_event(
        str(closeable_set),
        "closeout_succeeded",
        3,
        forced=True,
        method="snapshot_flip",
        verdict="VERIFIED",
    )

    # Snapshot: operator hand-migrated to declare the full 4-of-4
    # completion with completedSessions[] but events ledger never
    # caught up.
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["currentSession"] = 4
    state["totalSessions"] = 4
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-04-30T15:03:35-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state["completedSessions"] = [1, 2, 3, 4]
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # --apply: synthetic closeout trio lands against session 4; the
    # snapshot's completedSessions=[1, 2, 3, 4] is preserved verbatim
    # (the union of [1, 2, 3, 4] and ledger view {3, 4} is still
    # [1, 2, 3, 4]).
    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
    outcome = close_session.run(args)
    assert outcome.result == "succeeded"

    state_after = read_session_state(str(closeable_set)) or {}
    assert state_after.get("completedSessions") == [1, 2, 3, 4], (
        f"expected completedSessions=[1, 2, 3, 4] preserved across "
        f"--apply; got {state_after.get('completedSessions')!r}"
    )

    # Message distinguishes the "preserved" outcome so the operator
    # can tell at a glance.
    assert any(
        "preserved completedSessions=[1, 2, 3, 4]" in m
        for m in outcome.messages
    ), outcome.messages

    # Events ledger now has both the original forced session-3
    # closeout and the synthetic session-4 closeout.
    events_after = read_events(str(closeable_set))
    session4_closeouts = [
        e for e in events_after
        if e.event_type == "closeout_succeeded" and e.session_number == 4
    ]
    assert len(session4_closeouts) == 1
    assert session4_closeouts[0].fields.get("repaired") is True


def test_repair_merges_snapshot_completed_sessions_with_events(
    closeable_set: Path,
):
    """Set 023: ``--repair --apply`` Case 1 takes the union when the
    snapshot's ``completedSessions[]`` and the events-ledger
    reconstruction disagree on different sessions. The union is
    monotone-up: every session number from either source survives.
    """
    # Events ledger: closeout for an earlier session that the
    # snapshot's hand-authored array does not mention.
    append_event(
        str(closeable_set),
        "closeout_requested",
        1,
    )
    append_event(
        str(closeable_set),
        "closeout_succeeded",
        1,
        verdict="VERIFIED",
    )

    # Snapshot: declares session 2 complete with a partial
    # completedSessions array (only session 2, not session 1) — the
    # operator hand-edited mid-migration.
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["currentSession"] = 2
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-05-12T15:20:00.000000-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state["completedSessions"] = [2]  # partial; missing session 1
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # --apply: synthetic session-2 closeout lands; completedSessions[]
    # becomes the union of snapshot [2], events {1}, and the
    # synthetic {2} → [1, 2].
    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
    outcome = close_session.run(args)
    assert outcome.result == "succeeded"

    state_after = read_session_state(str(closeable_set)) or {}
    assert state_after.get("completedSessions") == [1, 2], (
        f"expected completedSessions=[1, 2] (union of snapshot [2] and "
        f"events {{1}} ∪ synthetic {{2}}); got "
        f"{state_after.get('completedSessions')!r}"
    )

    # Message line explicitly reports the union framing so the
    # operator sees both sources.
    assert any(
        "merged completedSessions=[1, 2]" in m
        and "union of snapshot [2]" in m
        and "events [1, 2]" in m
        for m in outcome.messages
    ), outcome.messages

    # Idempotent: a second --apply run produces no further snapshot
    # rewrite (the array is already correct under the new union).
    outcome2 = close_session.run(args)
    assert outcome2.result == "succeeded"
    assert any("no drift detected" in m for m in outcome2.messages), (
        outcome2.messages
    )


def test_repair_normalizes_malformed_snapshot_completed_sessions(
    closeable_set: Path,
):
    """Set 023 round-1 verifier finding: when the snapshot's
    ``completedSessions`` contains malformed entries (booleans,
    negatives, non-ints), ``--repair --apply`` Case 1 must rewrite
    the snapshot with the canonical merged form rather than taking
    the no-rewrite "preserved" branch and leaving the malformed
    array in place.
    """
    # Events ledger: a clean session-1 closeout from a prior close.
    append_event(str(closeable_set), "closeout_requested", 1)
    append_event(str(closeable_set), "closeout_succeeded", 1, verdict="VERIFIED")

    # Snapshot: hand-migrated by an operator with a typo or two —
    # the array contains -1 (negative, nonsensical) alongside the
    # legitimate sessions 1 and 2.
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["currentSession"] = 2
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-05-15T12:00:00.000000-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state["completedSessions"] = [1, -1, 2]
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # --apply: must normalize the malformed entry away while writing
    # the union with the events-ledger reconstruction (+ synthetic
    # session-2 closeout).
    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
    outcome = close_session.run(args)
    assert outcome.result == "succeeded"

    state_after = read_session_state(str(closeable_set)) or {}
    assert state_after.get("completedSessions") == [1, 2], (
        f"expected malformed [-1] to be normalized away, leaving "
        f"completedSessions=[1, 2]; got "
        f"{state_after.get('completedSessions')!r}"
    )

    # Message line specifically reports the "normalized" outcome so
    # an operator can see the malformed entries were dropped.
    assert any(
        "normalized completedSessions=[1, 2]" in m
        and "raw snapshot [1, -1, 2]" in m
        for m in outcome.messages
    ), outcome.messages


def test_repair_detects_event_says_closed_but_state_lagging(
    closeable_set: Path,
):
    """Inverse drift: events ledger shows ``closeout_succeeded`` but
    ``session-state.json`` has not recorded the session in
    ``completedSessions[]``. ``--apply`` backfills the array via
    ``_flip_state_to_closed``.

    Set 022 reshapes this test: under the new completedSessions[]
    invariant, "state lagging" means session-level lag (a closed
    session missing from the array) rather than set-level lag
    (status field not flipped). The fixture is mid-set
    (totalSessions=2, only session 1 closed in the ledger), so
    _flip_state_to_closed correctly leaves the SET status at
    in-progress while recording session 1 as closed. The repair
    becomes idempotent because Case 2's trigger now reads
    completedSessions[].
    """
    append_event(
        str(closeable_set), "closeout_requested", 1,
    )
    append_event(
        str(closeable_set), "closeout_succeeded", 1,
    )

    state_before = read_session_state(str(closeable_set)) or {}
    assert state_before.get("status") == "in-progress"
    assert 1 not in (state_before.get("completedSessions") or [])

    # Diagnostic.
    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args)
    assert outcome.result == "repair_drift"
    assert any(
        "session-state.json is not flipped" in m for m in outcome.messages
    )

    # --apply: completedSessions[] is healed; SET-level status stays
    # in-progress because session 1 of 2 is not the final session.
    args2 = _ns(
        session_set_dir=str(closeable_set), repair=True, apply=True,
    )
    outcome2 = close_session.run(args2)
    assert outcome2.result == "succeeded"
    state_after = read_session_state(str(closeable_set)) or {}
    assert state_after.get("completedSessions") == [1], (
        f"expected completedSessions=[1] after --apply; got "
        f"{state_after.get('completedSessions')!r}"
    )
    assert state_after.get("status") == "in-progress", (
        "mid-set session close-out via repair must not flip the SET "
        "to complete (Set 022 invariant)"
    )
    assert state_after.get("lifecycleState") == "work_in_progress"

    # Idempotent: a second --apply pass sees session 1 in
    # completedSessions[] and Case 2's narrowed trigger does not
    # fire. The set still has no other drift.
    outcome3 = close_session.run(args2)
    assert outcome3.result == "succeeded", outcome3.messages
    assert any("no drift detected" in m for m in outcome3.messages)


def test_repair_reports_stranded_mid_closeout(closeable_set: Path):
    """``closeout_requested`` without a terminal companion → stranded.
    Reported, but ``--apply`` does NOT re-run the gate (that's the
    reconciler's job). Drift remains on a follow-up pass.
    """
    append_event(str(closeable_set), "closeout_requested", 1)

    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args)
    assert outcome.result == "repair_drift"
    assert any(
        "closeout did not reach a terminal state" in m
        for m in outcome.messages
    )

    # --apply: still drift, repair declines to re-run the gate.
    args2 = _ns(
        session_set_dir=str(closeable_set), repair=True, apply=True,
    )
    outcome2 = close_session.run(args2)
    # Stranded mid-closeout cannot be safely auto-resolved by repair —
    # it stays in the messages list but the result becomes succeeded
    # because there are no apply-eligible cases left.
    assert any(
        "closeout did not reach a terminal state" in m
        for m in outcome2.messages
    )


def test_repair_reports_missing_queue_messages(
    closeable_set: Path, tmp_path: Path,
):
    """A disposition that references a queue message id absent from
    every provider queue is reported as drift; repair declines to
    auto-fix because verifier verdicts can't be synthesized.
    """
    queue_dir = tmp_path / "queues"
    # Create the queue dir but enqueue against a different id than the
    # one we put in the disposition.
    real_mid = _enqueue(queue_dir, "gpt-5-4-mini", idempotency_key="real")
    fake_mid = "msg-does-not-exist-anywhere"

    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="phantom-message",
        verification_method="queue",
        files_changed=[],
        verification_message_ids=[fake_mid],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))

    args = _ns(session_set_dir=str(closeable_set), repair=True)
    outcome = close_session.run(args, queue_base_dir=str(queue_dir))
    assert outcome.result == "repair_drift"
    assert any(
        fake_mid in m and "do not resolve" in m
        for m in outcome.messages
    )

    # --apply: repair refuses to fabricate a verdict.
    args2 = _ns(
        session_set_dir=str(closeable_set), repair=True, apply=True,
    )
    outcome2 = close_session.run(args2, queue_base_dir=str(queue_dir))
    assert any(
        "Auto-repair declined" in m for m in outcome2.messages
    )

    # Sanity: repair never opened the real (unrelated) message.
    qdb = QueueDB(provider="gpt-5-4-mini", base_dir=str(queue_dir))
    real_msg = qdb.get_message(real_mid)
    assert real_msg is not None
    assert real_msg.state == "new"


def test_repair_apply_without_repair_rejected(closeable_set: Path):
    """Already covered at the validation layer in skeleton tests; this
    is the end-to-end form."""
    args = _ns(session_set_dir=str(closeable_set), apply=True)
    outcome = close_session.run(args)
    assert outcome.result == "invalid_invocation"
    assert any("--apply requires --repair" in m for m in outcome.messages)


# ===========================================================================
# Group 3: Four end-to-end scenarios from the Set 3 acceptance criteria
# ===========================================================================

def test_e2e_outsource_first_happy_path(closeable_set: Path):
    """Scenario 1 — outsource-first: api method → close-out passes
    gates → session is closed on the events ledger.
    """
    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="api-verified happy path",
        verification_method="api",
        files_changed=[],
        verification_message_ids=[],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))
    _commit_and_push_set(closeable_set)

    args = _ns(session_set_dir=str(closeable_set))
    outcome = close_session.run(args)

    assert outcome.result == "succeeded"
    assert outcome.exit_code == 0
    assert outcome.verification_method == "api"
    assert all(g.passed for g in outcome.gate_results)

    events = read_events(str(closeable_set))
    assert current_lifecycle_state(events) == SessionLifecycleState.CLOSED


def test_e2e_outsource_last_happy_path(
    closeable_set: Path, tmp_path: Path,
):
    """Scenario 2 — outsource-last: queue method → verifier completes
    during the wait → close-out unblocks → gates pass → session closed.
    """
    queue_dir = tmp_path / "queues"
    mid = _enqueue(queue_dir, "gpt-5-4-mini", idempotency_key="e2e")

    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="queue-verified happy path",
        verification_method="queue",
        files_changed=[],
        verification_message_ids=[mid],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))
    _commit_and_push_set(closeable_set)

    qdb = QueueDB(provider="gpt-5-4-mini", base_dir=str(queue_dir))
    poll = {"n": 0}

    def fake_sleep(_seconds: float) -> None:
        poll["n"] += 1
        if poll["n"] == 1:
            qdb.claim(worker_id="verifier-daemon")
        elif poll["n"] == 2:
            qdb.complete(mid, "verifier-daemon", {"verdict": "VERIFIED"})

    args = _ns(session_set_dir=str(closeable_set), timeout=5)
    outcome = close_session.run(
        args,
        queue_base_dir=str(queue_dir),
        poll_interval_seconds=0.001,
        sleep=fake_sleep,
    )

    assert outcome.result == "succeeded", outcome.messages
    assert outcome.verification_method == "queue"
    assert outcome.verification_wait_outcome == "completed"

    events = read_events(str(closeable_set))
    assert current_lifecycle_state(events) == SessionLifecycleState.CLOSED


def test_e2e_bootstrapping_recovery_via_repair_apply(
    closeable_set: Path,
):
    """Scenario 3 — a session got stranded because the legacy close-out
    path wrote ``session-state.json: complete`` without emitting the
    events trio. ``--repair --apply`` brings the ledger into agreement
    so the reconciler / dashboards stop treating the set as stranded.
    """
    # Legacy close-out: state-only, no events. Hand-write the
    # snapshot to status/lifecycleState=closed — Set 022 made
    # _flip_state_to_closed conditional on
    # len(completedSessions)==totalSessions AND change-log present,
    # so it can no longer be (mis)used as a force-flip helper. The
    # actual legacy bootstrapping drift in the wild was always a
    # hand-edited snapshot anyway.
    (closeable_set / "change-log.md").write_text(
        "# change log\n\nlast-session marker for the bootstrapping fixture.\n",
        encoding="utf-8",
    )
    state_path = closeable_set / "session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "complete"
    state["lifecycleState"] = "closed"
    state["completedAt"] = "2026-04-30T01:00:00-04:00"
    state["verificationVerdict"] = "VERIFIED"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    events_before = read_events(str(closeable_set))
    assert not any(
        e.event_type == "closeout_succeeded" for e in events_before
    )

    args = _ns(
        session_set_dir=str(closeable_set), repair=True, apply=True,
    )
    outcome = close_session.run(args)
    assert outcome.result == "succeeded"

    events_after = read_events(str(closeable_set))
    assert current_lifecycle_state(events_after) == SessionLifecycleState.CLOSED
    repair_events = [
        e for e in events_after if e.fields.get("repaired") is True
    ]
    assert {e.event_type for e in repair_events} == {
        "closeout_requested", "closeout_succeeded",
    }


def test_e2e_manual_verify_skips_queue_gate_runs_session_closes(
    closeable_set: Path, tmp_path: Path,
):
    """Scenario 4 — ``--manual-verify`` skips the queue, gate still
    runs, session closes via the events ledger.
    """
    queue_dir = tmp_path / "queues"
    # Stranded message: would block forever in queue mode, must be
    # bypassed here.
    mid = _enqueue(queue_dir, "gpt-5-4-mini", idempotency_key="m2")

    write_disposition(str(closeable_set), Disposition(
        status="completed",
        summary="manual override",
        verification_method="queue",
        files_changed=[],
        verification_message_ids=[mid],
        next_orchestrator=_valid_next_orc(),
        blockers=[],
    ))
    _commit_and_push_set(closeable_set)

    reason_path = tmp_path / "manual-attest.md"
    reason_path.write_text(
        "verified out-of-band; queue path was unavailable",
        encoding="utf-8",
    )

    args = _ns(
        session_set_dir=str(closeable_set),
        manual_verify=True,
        reason_file=str(reason_path),
        timeout=1,
    )
    outcome = close_session.run(
        args,
        queue_base_dir=str(queue_dir),
        # Asserts the queue wait is never entered.
        sleep=lambda _s: pytest.fail(
            "manual-verify must not enter queue wait"
        ),
    )

    assert outcome.result == "succeeded", outcome.messages
    assert outcome.verification_method == "manual"
    assert all(g.passed for g in outcome.gate_results)

    events = read_events(str(closeable_set))
    assert current_lifecycle_state(events) == SessionLifecycleState.CLOSED
    manual_events = [
        e for e in events
        if e.event_type == "verification_completed"
        and e.fields.get("method") == "manual"
    ]
    assert len(manual_events) == 1

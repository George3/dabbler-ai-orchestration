"""Tests for SessionLog.log_step's routedApiCalls handling.

The canonical source of routed-call cost is ``router-metrics.jsonl``
(written by ``record_call``). The activity log's ``routedApiCalls`` is a
supplemental channel; an always-empty ``[]`` read as "no routed calls
happened" when in fact none were ever logged to this field, so the
writer now omits the key entirely when there is nothing to record.
"""

import json

from ai_router.session_log import SessionLog


def _entries(session_set_dir):
    with open(f"{session_set_dir}/activity-log.json", encoding="utf-8") as f:
        return json.load(f)["entries"]


def test_log_step_omits_routed_api_calls_when_empty(tmp_path):
    log = SessionLog(str(tmp_path))
    log.log_step(
        session_number=1,
        step_number=1,
        step_key="session-001/work",
        description="did work",
        status="complete",
    )
    entry = _entries(tmp_path)[-1]
    assert "routedApiCalls" not in entry


def test_log_step_omits_routed_api_calls_when_empty_list(tmp_path):
    log = SessionLog(str(tmp_path))
    log.log_step(
        session_number=1,
        step_number=1,
        step_key="session-001/work",
        description="did work",
        status="complete",
        api_calls=[],
    )
    entry = _entries(tmp_path)[-1]
    assert "routedApiCalls" not in entry


def test_log_step_records_routed_api_calls_when_present(tmp_path):
    log = SessionLog(str(tmp_path))
    calls = [{"model": "gpt-5-4", "provider": "openai", "costUsd": 0.05}]
    log.log_step(
        session_number=1,
        step_number=1,
        step_key="session-001/verify",
        description="verified",
        status="complete",
        api_calls=calls,
    )
    entry = _entries(tmp_path)[-1]
    assert entry["routedApiCalls"] == calls


def test_cost_summary_tolerates_omitted_key(tmp_path):
    """get_cost_summary must not assume the key is present."""
    log = SessionLog(str(tmp_path))
    log.log_step(
        session_number=1,
        step_number=1,
        step_key="session-001/work",
        description="did work",
        status="complete",
    )
    summary = log.get_cost_summary()
    assert summary["total_calls"] == 0
    assert summary["total_cost"] == 0.0

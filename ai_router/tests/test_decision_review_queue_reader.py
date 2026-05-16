"""Tests for ai_router.decision_review_queue — read and clear."""

import json

import pytest

import decision_review_queue as drq  # type: ignore[import-not-found]


def write_queue(tmp_path, entries):
    """Write a JSONL queue file at ``tmp_path/decision-review-queue.jsonl``."""
    path = tmp_path / "decision-review-queue.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path


def write_raw(tmp_path, text):
    """Write raw text to the queue file."""
    path = tmp_path / "decision-review-queue.jsonl"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# read_queue
# ---------------------------------------------------------------------------


def test_read_queue_returns_empty_list_when_file_absent(tmp_path):
    assert drq.read_queue(tmp_path) == []


def test_read_queue_returns_empty_list_when_file_empty(tmp_path):
    write_raw(tmp_path, "")
    assert drq.read_queue(tmp_path) == []


def test_read_queue_returns_all_entries_in_order(tmp_path):
    entries = [
        {"ts": "2026-05-16T00:00:00Z", "reason": "first", "source": "command",
         "file": None, "line": None},
        {"ts": "2026-05-16T00:00:01Z", "reason": "second", "source": "annotation",
         "file": "src/foo.py", "line": 42},
        {"ts": "2026-05-16T00:00:02Z", "reason": "third", "source": "command",
         "file": None, "line": None},
    ]
    write_queue(tmp_path, entries)
    result = drq.read_queue(tmp_path)
    assert len(result) == 3
    assert [r["reason"] for r in result] == ["first", "second", "third"]


def test_read_queue_skips_blank_lines(tmp_path):
    text = (
        '{"ts":"t1","reason":"a","source":"command"}\n'
        '\n'
        '   \n'
        '{"ts":"t2","reason":"b","source":"command"}\n'
    )
    write_raw(tmp_path, text)
    result = drq.read_queue(tmp_path)
    assert [r["reason"] for r in result] == ["a", "b"]


def test_read_queue_skips_malformed_line_and_keeps_valid_ones(tmp_path, caplog):
    text = (
        '{"ts":"t1","reason":"good","source":"command"}\n'
        'this is not json at all\n'
        '{"ts":"t2","reason":"also-good","source":"command"}\n'
    )
    write_raw(tmp_path, text)
    # The module's logger has propagate=False (matching session_events.py),
    # so route caplog through propagation explicitly for this assertion.
    drq._logger.propagate = True
    try:
        with caplog.at_level("WARNING", logger="ai_router.decision_review_queue"):
            result = drq.read_queue(tmp_path)
    finally:
        drq._logger.propagate = False
    assert [r["reason"] for r in result] == ["good", "also-good"]
    assert any("malformed JSON" in rec.message for rec in caplog.records)


def test_read_queue_skips_non_object_lines(tmp_path, caplog):
    # JSON arrays / numbers / strings are valid JSON but not valid queue entries.
    text = (
        '{"ts":"t1","reason":"good","source":"command"}\n'
        '["not", "an", "object"]\n'
        '42\n'
        '"a bare string"\n'
        '{"ts":"t2","reason":"also-good","source":"command"}\n'
    )
    write_raw(tmp_path, text)
    drq._logger.propagate = True
    try:
        with caplog.at_level("WARNING", logger="ai_router.decision_review_queue"):
            result = drq.read_queue(tmp_path)
    finally:
        drq._logger.propagate = False
    assert [r["reason"] for r in result] == ["good", "also-good"]
    assert any("expected object" in rec.message for rec in caplog.records)


def test_read_queue_preserves_arbitrary_extra_fields(tmp_path):
    # Schema is intentionally open — extra keys should pass through unmodified.
    entry = {
        "ts": "2026-05-16T00:00:00Z",
        "reason": "test",
        "source": "command",
        "file": None,
        "line": None,
        "issue_ref": "DAB-123",
        "priority": "high",
    }
    write_queue(tmp_path, [entry])
    result = drq.read_queue(tmp_path)
    assert result == [entry]


def test_read_queue_handles_unicode(tmp_path):
    entry = {
        "ts": "2026-05-16T00:00:00Z",
        "reason": "résumé — café",
        "source": "command",
    }
    write_queue(tmp_path, [entry])
    result = drq.read_queue(tmp_path)
    assert result[0]["reason"] == "résumé — café"


# ---------------------------------------------------------------------------
# clear_queue
# ---------------------------------------------------------------------------


def test_clear_queue_on_absent_file_returns_zero(tmp_path):
    assert drq.clear_queue(tmp_path) == 0
    # Idempotent — file still absent.
    assert not (tmp_path / "decision-review-queue.jsonl").exists()


def test_clear_queue_removes_file_and_returns_entry_count(tmp_path):
    entries = [
        {"ts": "t1", "reason": "a", "source": "command"},
        {"ts": "t2", "reason": "b", "source": "annotation",
         "file": "f.py", "line": 1},
        {"ts": "t3", "reason": "c", "source": "command"},
    ]
    write_queue(tmp_path, entries)
    count = drq.clear_queue(tmp_path)
    assert count == 3
    assert not (tmp_path / "decision-review-queue.jsonl").exists()


def test_clear_queue_is_idempotent_after_clear(tmp_path):
    write_queue(tmp_path, [{"ts": "t", "reason": "x", "source": "command"}])
    assert drq.clear_queue(tmp_path) == 1
    # Second call: file is gone, returns 0.
    assert drq.clear_queue(tmp_path) == 0


def test_clear_queue_counts_only_parseable_entries(tmp_path):
    # Malformed lines are skipped during the read-then-count, so they
    # do not inflate the return value.
    text = (
        '{"ts":"t1","reason":"good","source":"command"}\n'
        'not json\n'
        '{"ts":"t2","reason":"also-good","source":"command"}\n'
    )
    write_raw(tmp_path, text)
    assert drq.clear_queue(tmp_path) == 2


def test_queue_path_returns_expected_filename(tmp_path):
    p = drq.queue_path(tmp_path)
    assert p.name == "decision-review-queue.jsonl"
    assert p.parent == tmp_path

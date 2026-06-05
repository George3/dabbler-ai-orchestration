"""Set 057 Session 3 — end-to-end dedicated-verification flow.

Drives the full Lightweight dedicated-sessions lifecycle through the real
blessed writers, the seeded findings envelope, the seven-state derivation,
the close-time validator, and the terminal snapshot flip:

    work (x2, complete)
      -> verification round 1  (different engine; finds issues)
      -> remediation round 1   (fixes the finding)
      -> verification round 2  (re-verify the fix; VERIFIED)
      -> terminal close        (set finalized: closed-verified)

It asserts the derived workflow state at each boundary and that the
content-aware close-out gate would PASS at the terminal close (a
cross-provider verification ran), with no rule-6 violation along the way.
"""
from __future__ import annotations

import json
from pathlib import Path

import dedicated_verification as dv
import session_state as ss
from progress import normalize_to_v4_shape

WORK_ENGINE = "claude-code"
VERIFY_ENGINE = "gpt-5-4"


def _seed_two_complete_work_sessions(tmp_path: Path) -> Path:
    d = tmp_path / "057-e2e"
    d.mkdir()
    (d / "spec.md").write_text(
        "# spec\n\n## Session Set Configuration\n\n"
        "```yaml\ntier: lightweight\nverificationMode: dedicated-sessions\n```\n\n"
        "### Session 1 of 2: Build A\n\n### Session 2 of 2: Build B\n",
        encoding="utf-8",
    )

    def _w(n):
        return {
            "number": n,
            "title": f"Build {n}",
            "status": "complete",
            "startedAt": f"t{n}a",
            "completedAt": f"t{n}b",
            "orchestrator": {"engine": WORK_ENGINE, "provider": "anthropic"},
            "verificationVerdict": None,
        }

    state = {
        "schemaVersion": 4,
        "sessionSetName": d.name,
        "status": "in-progress",
        "sessions": [_w(1), _w(2)],
    }
    (d / "session-state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (d / "activity-log.json").write_text(
        json.dumps({"entries": []}, indent=2), encoding="utf-8"
    )
    # Operator opts in once at set start (seeded from spec, recorded).
    dv.resolve_and_record_verification_mode(d, cli_choice=None)
    return d


def test_full_dedicated_verification_lifecycle(tmp_path):
    d = _seed_two_complete_work_sessions(tmp_path)
    assert dv.read_verification_mode(d) == dv.VERIFICATION_MODE_DEDICATED

    # Work complete, no verification yet -> awaiting-verification.
    assert dv.derive_workflow_state(d) == dv.STATE_AWAITING_VERIFICATION

    # --- Verification round 1 (different engine) ---
    _p, vnum = ss.register_typed_session_start(
        str(d), "verification", VERIFY_ENGINE, orchestrator_provider="openai"
    )
    assert vnum == 3
    assert dv.derive_workflow_state(d) == dv.STATE_AWAITING_VERIFICATION

    # Round 1 finds an issue -> seed the envelope, then hand off to remediation.
    dv.seed_issues_envelope(
        d,
        session_number=3,
        verification_round=1,
        verification_verdict="ISSUES_FOUND",
        issues=[
            {
                "issueId": "S057-E2E-1",
                "issueType": "deterministic-defect",
                "verificationMethod": "run the new helper on the empty input",
                "description": "helper raises on empty input",
            }
        ],
    )
    _p, closed, rnum = ss.register_typed_session_handoff(
        str(d),
        "remediation",
        WORK_ENGINE,
        orchestrator_provider="anthropic",
        verification_verdict="ISSUES_FOUND",
    )
    assert (closed, rnum) == (3, 4)
    # Verification closed with issues -> awaiting-remediation.
    assert dv.derive_workflow_state(d) == dv.STATE_AWAITING_REMEDIATION

    # --- Remediation round 1 fixes the finding ---
    issues_path = d / "s3-issues.json"
    env = json.loads(issues_path.read_text(encoding="utf-8"))
    env["issues"][0]["resolution_status"] = "fixed"
    issues_path.write_text(json.dumps(env, indent=2), encoding="utf-8")

    # A fix was made -> hand off to re-verification.
    _p, closed, v2num = ss.register_typed_session_handoff(
        str(d), "verification", VERIFY_ENGINE, orchestrator_provider="openai"
    )
    assert (closed, v2num) == (4, 5)
    assert dv.derive_workflow_state(d) == dv.STATE_AWAITING_VERIFICATION

    # --- Verification round 2: VERIFIED -> terminal close ---
    # The gate would pass: the session being closed (5) is a cross-provider
    # verification session.
    res = dv.validate_dedicated_verification(d, closing_session_number=5)
    assert res.applicable is True and res.ok is True

    # Finalize the set via the real snapshot-flip writer (terminal close
    # requires change-log.md present).
    (d / "change-log.md").write_text("e2e set complete\n", encoding="utf-8")
    ss._flip_state_to_closed(str(d), verification_verdict="VERIFIED")

    out = json.loads((d / "session-state.json").read_text(encoding="utf-8"))
    assert out["status"] == "complete"
    norm = normalize_to_v4_shape(out, d / "spec.md")
    assert norm["totalSessions"] == 5
    assert [s["number"] for s in norm["sessions"]] == [1, 2, 3, 4, 5]
    types = {s["number"]: s.get("type") for s in norm["sessions"]}
    assert types[3] == "verification"
    assert types[4] == "remediation"
    assert types[5] == "verification"

    # Final derived state.
    assert dv.derive_workflow_state(d) == dv.STATE_CLOSED_VERIFIED

    # The gate still confirms a different-engine verification post-flip.
    res2 = dv.validate_dedicated_verification(d)
    assert res2.applicable is True and res2.ok is True

"""Session 1 verification — orchestrator e2e harness foundation.

Single slice covering all Session 1 production-code changes:
  - ai_router/tests/e2e/conftest.py — sys.path + env-var isolation
  - ai_router/tests/e2e/fixtures.py — fixture generator (git repo + bare remote,
    drive_start_session, drive_close_session, make_disposition,
    make_activity_log_entry, make_change_log, read helpers)
  - ai_router/tests/e2e/test_happy_3session.py — 3-session happy path
  - ai_router/tests/e2e/test_register_session_start_regression.py — v0.1.1 pin
  - pytest.ini — register e2e marker

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access — per
the memory `feedback_ai_router_route_result_handling`.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_ai_router():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import ai_router
    return ai_router


SESSION_1_FILES = [
    "ai_router/tests/e2e/conftest.py",
    "ai_router/tests/e2e/fixtures.py",
    "ai_router/tests/e2e/test_happy_3session.py",
    "ai_router/tests/e2e/test_register_session_start_regression.py",
    "pytest.ini",
]


def main() -> int:
    parts = []
    for rel in SESSION_1_FILES:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "".join(parts)

    context = (
        "Set 027 Session 1 of 4 — orchestrator end-to-end harness foundation.\n"
        "Reference: `docs/session-sets/027-orchestrator-e2e-harness/spec.md`\n"
        "Session 1 section.\n\n"
        "Goal: build the fixture generator and the first end-to-end scenario.\n"
        "Ship one passing 3-session happy-path test that drives both\n"
        "`start_session` and `close_session` CLIs against a tmpdir-scoped\n"
        "fixture and asserts on every state-file invariant. Plus a regression\n"
        "test pinning the v0.1.1 `completedSessions[]`-loss bug (the\n"
        "`register_session_start` writer in 0.1.1 wiped the progress array\n"
        "on every rewrite; Set 022 fixed it; this test makes it impossible\n"
        "to drop the fix again).\n\n"
        "Architectural choice the implementer had to make at session start:\n"
        "the spec said the harness uses `--manual-verify` throughout, but on\n"
        "inspection `--manual-verify` only skips the verification API call —\n"
        "the five close-out gates (`check_working_tree_clean`,\n"
        "`check_pushed_to_remote`, `check_activity_log_entry`,\n"
        "`check_next_orchestrator_present`, `check_change_log_fresh`) all\n"
        "still fire. The harness therefore builds a real git repo with a\n"
        "local bare remote in tmpdir per test and auto-commits/pushes\n"
        "between every fixture step. This matches what\n"
        "`test_close_session_integration.py`'s `closeable_set` fixture does\n"
        "for single-session tests, generalized to multi-session sequences\n"
        "via the `HarnessHandle` dataclass. No production code paths or\n"
        "gate-check signatures were modified — the harness exercises the\n"
        "real CLI surface end-to-end.\n\n"
        "Pytest config change: the spec said to register the `e2e` marker\n"
        "in pyproject.toml, but the project's actual pytest config lives in\n"
        "pytest.ini. Marker registered there instead. Test counts:\n"
        "  - `pytest`                  → 430 passed, 1 skipped\n"
        "  - `pytest -m e2e`           → 3 passed in ~5.6s\n"
        "  - `pytest -m 'not e2e'`     → 427 passed, 1 skipped, 3 deselected\n"
        "Baseline 427 preserved; no churn in existing tests.\n\n"
        "Verification asks:\n"
        "1. Does the harness correctly exercise the CLI contract end-to-end?\n"
        "   In particular: are the subprocess invocations of\n"
        "   `python -m ai_router.start_session` / `ai_router.close_session`\n"
        "   passing the right argument set, and is the PYTHONPATH-injection\n"
        "   approach in `_subprocess_env()` sound for a system-Python test\n"
        "   runner that does not have ai_router pip-installed?\n"
        "2. Is the auto-commit / auto-push loop in `_commit_and_push()`\n"
        "   correct? Specifically:\n"
        "   a. `--allow-empty` on the commit — does the fallback path\n"
        "      ('nothing to commit' detection) correctly handle the case\n"
        "      where there is genuinely nothing to commit (e.g., an\n"
        "      idempotent second invocation)?\n"
        "   b. Is there any window where the working tree could be dirty\n"
        "      when the next gate-check runs? The fixture commits after each\n"
        "      helper call, but close_session itself writes to\n"
        "      session-events.jsonl (ignored by the gate's IGNORE_PATTERNS)\n"
        "      and to session-state.json (not committed until\n"
        "      `commit_after=True` runs in drive_close_session). Is the\n"
        "      ordering of (write → gate-check → flip → commit) sound?\n"
        "3. The happy-path test asserts on:\n"
        "   - in-flight snapshot shape after start_session\n"
        "   - `completedSessions[]` preservation across the start_session\n"
        "     rewrite (the same invariant the regression test pins\n"
        "     directly)\n"
        "   - exactly-one work_started + closeout_succeeded per session\n"
        "   - status/lifecycleState transitions: in-progress/work_in_progress\n"
        "     on non-final close, complete/closed on final close\n"
        "   - completedAt set only on final close\n"
        "   Is anything important missing from this assertion bundle?\n"
        "4. The regression test directly invokes `register_session_start()`\n"
        "   (not the CLI) on a tmpdir state with `completedSessions: [1]`\n"
        "   pre-populated, then asserts the rewritten state still has it.\n"
        "   Is the test setup sufficient to actually reproduce the v0.1.1\n"
        "   regression if the preserve logic were removed from\n"
        "   `session_state.py:208-218`? Are there any code paths in\n"
        "   `register_session_start` the test doesn't exercise that could\n"
        "   regress independently?\n"
        "5. The fixture's `make_session_set` calls\n"
        "   `synthesize_not_started_state()` after writing spec.md, because\n"
        "   the start_session CLI reads `totalSessions` from the state file\n"
        "   (start_session.py:264), not the spec. Without this, every\n"
        "   first-session snapshot would land with `totalSessions: null`.\n"
        "   Is this approach correct? Is there a cleaner alternative (e.g.,\n"
        "   patching the CLI to fall back to the spec parser)?\n"
        "6. Test naming and structure: the e2e module uses bare-filename\n"
        "   imports (`from fixtures import ...`) via a sys.path mutation\n"
        "   in the e2e conftest. The parent `ai_router/tests/conftest.py`\n"
        "   does the same trick for the package modules. Is this\n"
        "   consistent with the project's convention?\n"
        "7. Any security, correctness, or maintainability issues not\n"
        "   covered above? Especially: failure modes the harness will\n"
        "   surface as confusing rather than diagnosable errors.\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise list\n"
        "each finding with severity (Blocker / Major / Minor) and\n"
        "file:line references. Out-of-scope for this slice: the Session 2\n"
        "scenarios (cancel/restore, force-close, worktree, multiset) and\n"
        "the Session 3/4 TS/Playwright layers."
    )

    content = (
        "Review the Session 1 bundle below against the criteria above.\n"
        "Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )

    ar = load_ai_router()
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="027-orchestrator-e2e-harness",
        session_number=1,
    )

    dump_path = REPO_ROOT / "scripts" / "verify_session_027_1_result.json"
    try:
        as_dict = dataclasses.asdict(result)
    except TypeError:
        as_dict = {k: v for k, v in vars(result).items()}
    cleaned = {}
    for k, v in as_dict.items():
        try:
            json.dumps(v)
            cleaned[k] = v
        except TypeError:
            cleaned[k] = repr(v)
    dump_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"Dumped result to {dump_path.as_posix()}")

    data = json.loads(dump_path.read_text(encoding="utf-8"))
    print("=== VERIFIER RESPONSE ===")
    print(data.get("content", "<no content>"))
    print()
    print("=== COST ===")
    print(
        f"model={data.get('model_name')} "
        f"input_tokens={data.get('input_tokens')} "
        f"output_tokens={data.get('output_tokens')} "
        f"cost_usd={data.get('total_cost_usd')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

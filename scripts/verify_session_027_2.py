"""Cross-provider verification for Set 027 Session 2.

Verifies the four new test files and the extended fixtures.py written
in Session 2. Split into three sub-rounds (~420 LOC each) per the
memory note about >700 LOC bundle timeouts with gpt-5-4.

Usage:
    python scripts/verify_session_027_2.py [--round A|B|C]

Default: all three rounds sequentially.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_router as ar  # type: ignore[import-not-found]


SESSION2_CONTEXT = (
    "Set 027 Session 2 of 4 — extended Python e2e scenarios.\n"
    "Reference: `docs/session-sets/027-orchestrator-e2e-harness/spec.md`\n"
    "Session 2 section.\n\n"
    "Goal: add four scenario test files covering cancel/restore mid-set,\n"
    "force-close, worktree discovery, and multi-set sequential. Also\n"
    "extends `ai_router/tests/e2e/fixtures.py` with helpers:\n"
    "  - cancel_set() / restore_set() — delegate to production\n"
    "    session_lifecycle.cancel_session_set / restore_session_set\n"
    "  - drive_close_session(force=True, inject_force_env=False) —\n"
    "    --force and --manual-verify are mutually incompatible; force\n"
    "    path omits --manual-verify, injects AI_ROUTER_ALLOW_FORCE_CLOSE_OUT\n"
    "    into subprocess env, and has inject_force_env=False for the guard\n"
    "    test (flag present, env var absent).\n"
    "  - make_sibling_worktree(handle, slug) — runs git worktree add\n"
    "    at <repo>-worktrees/<slug> with branch session-set/<slug>\n"
    "  - make_additional_set(base_handle, new_slug, new_total) — adds a\n"
    "    second set dir to an existing fixture repo, sharing same\n"
    "    repo_root/bare_remote.\n\n"
    "Key behavioral facts established from reading production code:\n"
    "  1. --force short-circuits is_last_session=True regardless of\n"
    "     session number (session_state.py line 437). A non-final session\n"
    "     force-close flips the set to status=complete.\n"
    "  2. cancel renames RESTORED.md → CANCELLED.md (if RESTORED exists);\n"
    "     restore renames CANCELLED.md → RESTORED.md (never both present\n"
    "     after restore completes).\n"
    "  3. worktree.enumerate_worktrees uses git worktree list --porcelain;\n"
    "     classification='canonical' requires path.parent == <repo>-worktrees/\n"
    "     AND branch == session-set/<slug>.\n\n"
    "Test counts: 436 passed, 1 skipped (was 430+1 in Session 1).\n"
    "Runtime: pytest -m e2e → 7 passed in 37.82s."
)

VERIFICATION_ASKS = (
    "Verification asks:\n"
    "1. cancel_set / restore_set: Do the harness helpers correctly exercise\n"
    "   the cancel/restore lifecycle? Specifically: (a) is the assertion\n"
    "   order (cancel → assert CANCELLED.md+preCancelStatus → restore →\n"
    "   assert RESTORED.md+no CANCELLED.md) correct for the production\n"
    "   session_lifecycle implementation? (b) Does the test correctly assert\n"
    "   that preCancelStatus is cleared after restore?\n"
    "2. force_close guard: The guard test calls drive_close_session(force=True,\n"
    "   inject_force_env=False). The conftest scrubs AI_ROUTER_ALLOW_FORCE_CLOSE_OUT\n"
    "   before every test. Is there any env leak path that could let the guard\n"
    "   test accidentally pass? Is the error message assertion robust?\n"
    "3. force_close forensic state: The test asserts status='complete' after\n"
    "   force-closing session 2 of 3. Is this correct per the production\n"
    "   code (session_state._flip_state_to_closed line 437:\n"
    "   is_last_session = forced or (sessions_done and change_log_present))?\n"
    "   Are there any missing assertions (e.g., events ledger history stability)?\n"
    "4. worktree: make_sibling_worktree does 'git worktree add <path> -b\n"
    "   session-set/<slug>'. Is this sufficient for enumerate_worktrees to\n"
    "   classify it as 'canonical'? Does the classification depend on\n"
    "   anything beyond path.parent and branch name?\n"
    "5. multiset: make_additional_set shares the same bare remote as the\n"
    "   primary handle. When sessions are driven sequentially across three\n"
    "   sets in one repo, is there any git state contention — e.g., does\n"
    "   committing session-state.json for set B produce a commit that\n"
    "   overwrites set A's state file in the working tree?\n"
    "6. Any missing edge cases in any of the four scenario tests?\n"
    "   Especially: cancel-without-prior-start, force-close on final session\n"
    "   (vs. non-final), or multiset where set B starts before A finishes.\n"
    "7. Any issues with test isolation, fixture cleanup, or flakiness not\n"
    "   covered above?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list each\n"
    "finding with severity (Blocker / Major / Minor) and file:line references."
)


def _run_round(label: str, bundle: str, session_number: int = 2) -> dict:
    context = f"{SESSION2_CONTEXT}\n\n{VERIFICATION_ASKS}"
    content = (
        f"Review the following Session 2 code ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="027-orchestrator-e2e-harness",
        session_number=session_number,
    )
    dump_path = (
        REPO_ROOT / "scripts" / f"verify_session_027_2_result_{label.lower()}.json"
    )
    try:
        as_dict = dataclasses.asdict(result)
    except TypeError:
        as_dict = {k: v for k, v in vars(result).items()}
    cleaned: dict = {}
    for k, v in as_dict.items():
        try:
            json.dumps(v)
            cleaned[k] = v
        except TypeError:
            cleaned[k] = repr(v)
    dump_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"  Dumped to {dump_path.name}")
    data = json.loads(dump_path.read_text(encoding="utf-8"))
    print("  === VERIFIER RESPONSE ===")
    print(data.get("content", "<no content>"))
    print()
    print(
        f"  model={data.get('model_name')} "
        f"input_tokens={data.get('input_tokens')} "
        f"output_tokens={data.get('output_tokens')} "
        f"cost_usd={data.get('total_cost_usd')}"
    )
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", choices=["A", "B", "C"], default=None)
    args = parser.parse_args()

    fixtures_text = (REPO_ROOT / "ai_router/tests/e2e/fixtures.py").read_text("utf-8")
    cancel_text = (REPO_ROOT / "ai_router/tests/e2e/test_cancel_restore_midset.py").read_text("utf-8")
    force_text = (REPO_ROOT / "ai_router/tests/e2e/test_force_close_path.py").read_text("utf-8")
    worktree_text = (REPO_ROOT / "ai_router/tests/e2e/test_worktree_discovery.py").read_text("utf-8")
    multiset_text = (REPO_ROOT / "ai_router/tests/e2e/test_multiset_sequential.py").read_text("utf-8")

    fixtures_lines = fixtures_text.splitlines()
    fixtures_a = "\n".join(fixtures_lines[:500])
    fixtures_b = "\n".join(fixtures_lines[500:])

    rounds = {
        "A": (
            "Round A: fixtures.py lines 1-500",
            f"=== ai_router/tests/e2e/fixtures.py (lines 1-500) ===\n{fixtures_a}\n",
        ),
        "B": (
            "Round B: fixtures.py lines 501+ + test_cancel_restore_midset.py",
            (
                f"=== ai_router/tests/e2e/fixtures.py (lines 501-end) ===\n{fixtures_b}\n\n"
                f"=== ai_router/tests/e2e/test_cancel_restore_midset.py ===\n{cancel_text}\n"
            ),
        ),
        "C": (
            "Round C: test_force_close_path.py + test_worktree_discovery.py + test_multiset_sequential.py",
            (
                f"=== ai_router/tests/e2e/test_force_close_path.py ===\n{force_text}\n\n"
                f"=== ai_router/tests/e2e/test_worktree_discovery.py ===\n{worktree_text}\n\n"
                f"=== ai_router/tests/e2e/test_multiset_sequential.py ===\n{multiset_text}\n"
            ),
        ),
    }

    to_run = [args.round] if args.round else ["A", "B", "C"]
    all_ok = True
    for key in to_run:
        label, bundle = rounds[key]
        print(f"\n{'='*60}")
        print(f"Running {label} ...")
        try:
            _run_round(key, bundle)
        except Exception as exc:
            print(f"ERROR: {exc}")
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

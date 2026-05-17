"""Session 1 verification driver — Set 030.

Splits the verification into focused rounds to stay under the
gpt-5-4 effective-bundle-size threshold (per memory
`feedback_split_large_verification_bundles`: bundles over ~700 LOC of
mixed code+docs have hit 429/timeout in prior sessions).

Per memory `feedback_ai_router_route_result_handling`, the RouteResult
is dumped to JSON before any attribute access — past sessions lost
$0.34 on wrapper-crash bugs from accessing fields directly.

Both rounds use task_type='session-verification' which router-config
pins to gpt-5-4 (the cross-provider verifier for a Claude orchestrator).
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from pathlib import Path

# Local import shim — package root sits two levels above docs/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent

SPEC_PATH = SET_DIR / "spec.md"

# Files to pin into each round's prompt context.
# Reduced bundles after the original Round A bundle (2,000+ LOC) hit
# a 3-attempt read timeout on gpt-5-4. Per memory
# `feedback_split_large_verification_bundles`, slices kept to ~500 LOC
# of content each.
ROUND_A_PATHS = [
    REPO_ROOT / "ai_router" / "progress.py",
]

ROUND_B_PATHS = [
    REPO_ROOT / "tools" / "dabbler-ai-orchestration" / "src" / "utils" / "progress.ts",
]


def read_files(paths):
    blocks = []
    for p in paths:
        rel = p.relative_to(REPO_ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        blocks.append(f"=== FILE: {rel} ({len(text.splitlines())} LOC) ===\n{text}")
    return "\n\n".join(blocks)


def dump_route_result_to_json(result) -> dict:
    """Coerce a RouteResult to a plain dict for safe access.

    Tries dataclasses.asdict first; falls back to __dict__; finally
    falls back to a verbose repr probe.
    """
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


def run_round(label: str, system_summary: str, code_block: str, focus_prompt: str, out_path: Path):
    """Run one verification round and write the response to out_path."""
    print(f"\n{'='*60}\n[{label}] sending verification call...\n{'='*60}")
    result = ai_router.route(
        content=focus_prompt,
        task_type="session-verification",
        context=f"{system_summary}\n\n--- FILES ---\n{code_block}",
        session_set="030-session-state-v3-sessions-ledger",
        session_number=1,
    )
    # Per memory feedback_ai_router_route_result_handling: dump before access
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    # Print the verifier's verdict text directly for the operator's review.
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


SYSTEM_SUMMARY = """
Set 030 Session 1 ships the read-side schema-v3 foundation for the
`sessions[]` ledger. The session does NOT change any writer behavior;
all writer changes ship in Session 2. Session 1 deliverables:

1. ai_router/progress.py — get_progress(), synthesize_v3_from_v2(),
   validate_invariants(), ProgressView/SessionRecord dataclasses,
   canonicalize_status(), extract_session_titles_from_spec().
2. tools/dabbler-ai-orchestration/src/utils/progress.ts — TypeScript
   mirror of the Python helper. Same API, same invariants.
3. tools/dabbler-ai-orchestration/src/types.ts — adds SessionStatus,
   SessionRecord, ProgressView, SessionStateV3 interfaces.
4. ai_router/router-config.yaml — registers `spec-title-extraction`
   task type (per spec D14 / GPT-5.4 revision: register in S1 not S5
   to remove dependency risk).
5. docs/session-state-schema.md — full v3 rewrite.
6. docs/session-state-schema-example.{json,md} — v3 examples.
7. proposal terminology drift fixes (lines 139, 246: `done` → `complete`).

The 8 invariants come straight from the spec at
docs/session-sets/030-session-state-v3-sessions-ledger/spec.md
(`## Invariants` section). They are the load-bearing contract for
every later session.

The default-to-not-started rule (per memory
`feedback_default_not_started_evidence_to_escalate`) is critical for
the v2->v3 synthesizer: a hand-edited v2 file with ambiguous fields
should read as LESS progressed, not more.

40 pytest tests + 38 mocha tests + 6 config tests all pass; full
suite is 476 passed + 1 skipped, no regressions.
""".strip()


def main():
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) > 1 and sys.argv[1] == "round-a":
        focus = (
            "ROUND A — Python helper correctness (ai_router/progress.py).\n\n"
            "The 8 invariants this helper must enforce (from spec.md):\n"
            "  1. sessions[] required and non-empty.\n"
            "  2. session number values are positive ints, unique, sorted ascending.\n"
            "  3. At most one session may be 'in-progress'.\n"
            "  4. No session may be 'complete' if an earlier session is 'not-started' or 'in-progress'.\n"
            "  5. Top-level status 'not-started' requires every session to be 'not-started'.\n"
            "  6. Top-level status 'in-progress' allows either exactly one in-progress session OR a between-sessions state (>=1 complete, >=1 not-started, 0 in-progress).\n"
            "  7. Top-level status 'complete' requires every session to be 'complete'.\n"
            "  8. lifecycleState 'closed' pairs with top-level status 'complete' or 'cancelled' only.\n\n"
            "Verify:\n"
            "A. Does validate_invariants() correctly enforce each of the 8 rules? "
            "Identify any rule that would silently pass an invalid state, OR "
            "any rule whose error message references a wrong rule number / "
            "wrong session number.\n"
            "B. Does synthesize_v3_from_v2() follow the default-to-not-started "
            "rule? (Per the default-to-not-started rule: every session "
            "defaults to 'not-started' and only escalates to 'complete' if "
            "in completedSessions[], or to 'in-progress' if equal to "
            "currentSession AND top-level status is in-progress AND not "
            "already complete.) Identify any v2 input shape that would "
            "incorrectly escalate.\n"
            "C. Are there any edge cases the validators miss? (e.g., a "
            "session with status='cancelled' in a sequence; a state with "
            "session numbers that skip — e.g., [1, 3]; a Python bool slipping "
            "through as session.number.)\n\n"
            "Format the verdict as one of:\n"
            "  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)\n"
            "  - REJECTED: <bulleted list of must-fix issues with line numbers>.\n\n"
            "Skip stylistic nits. Be specific about line numbers when citing."
        )
        code_block = read_files(ROUND_A_PATHS)
        run_round(
            "Round A",
            SYSTEM_SUMMARY,
            code_block,
            focus,
            out_dir / "round-a-result.json",
        )

    elif len(sys.argv) > 1 and sys.argv[1] == "round-b":
        focus = (
            "ROUND B — documentation correctness (schema doc + examples + "
            "proposal patch). Verify:\n"
            "1. Does docs/session-state-schema.md accurately describe the v3 "
            "shape produced by the Round-A-verified helpers? Identify any "
            "field/type/value drift between doc and helper.\n"
            "2. Does the Lightweight-tier one-field-flip worked example "
            "actually work end-to-end? Walk through the sequence and "
            "identify any transition that requires more than one field "
            "edit OR violates an invariant mid-transition.\n"
            "3. Does docs/session-state-schema-example.json represent a "
            "*valid* v3 state per the 8 invariants? (It claims schemaVersion: "
            "3 + status: complete + every session complete.)\n"
            "4. Does the proposal-doc patch (lines 139, 246) leave any "
            "lingering 'done' references that should also be 'complete'? "
            "Note: lines 91, 310, 313 are intentional historical citations "
            "in the Revisions footer — those are correct as-is.\n"
            "5. Is the 'reader contract' section (forbidden to read legacy "
            "fields directly) consistent with the spec's D13 narrowing "
            "('No application reader may read legacy fields except through "
            "approved compatibility helpers')?\n\n"
            "Cite specific line numbers. Distinguish 'must fix' from 'nice "
            "to have'. Skip stylistic nits."
        )
        code_block = read_files(ROUND_B_PATHS)
        run_round(
            "Round B",
            SYSTEM_SUMMARY,
            code_block,
            focus,
            out_dir / "round-b-result.json",
        )

    else:
        print("Usage: python verify_session1.py [round-a|round-b]", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

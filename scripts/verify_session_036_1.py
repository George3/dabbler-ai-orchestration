"""Cross-provider verification for Set 036 Session 1.

Verifies the chatSessionId writer migration + per-set lifecycle lock
shipped in Session 1. The work touches five Python modules in
ai_router/ plus one new test file (12 unit tests, all green).

Split into two sub-rounds so each bundle stays under the ~500-LOC
slice that gemini-pro / gpt-5-4 reliably reason about per the
split-large-bundles memory (large bundles 429 / time out under
sustained reasoning):

* Round A: writer code (close_lock + start_session + session_state +
  close_session + session_events deltas). ~400 LOC.
* Round B: test file + docs changes. ~500 LOC.

Usage:
    python scripts/verify_session_036_1.py [--round A|B]

Default: Round A only (Round B is opt-in per the routing notes in
docs/session-sets/036-.../spec.md — gemini-pro Round A is the
default verification path; Round B only when must-fix surfaces).
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


SESSION_CONTEXT = (
    "Set 036 Session 1 of 7 — Writer migration + per-set lifecycle\n"
    "lock (Q5 prerequisite). Reference:\n"
    "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/\n"
    "spec.md (Session 1 section).\n\n"
    "Audit-locked proposal:\n"
    "docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/\n"
    "proposal-addendum.md. The composite-identity verdict from that\n"
    "addendum (engine + provider + chatSessionId) and the\n"
    "hybrid-migration-safety verdict (Q5: hybrid only with explicit\n"
    "cross-process serialization via a shared per-set lifecycle lock)\n"
    "are what this session implements at the writer layer.\n\n"
    "Goal: extend H4 from engine+provider to\n"
    "engine + provider + chatSessionId, add tolerant-on-read for\n"
    "missing chatSessionId on prior state, rename the close-session\n"
    "lock to .lifecycle.lock and have both start_session and\n"
    "close_session acquire it, wire EXIT_LOCK_CONTENTION=5 to\n"
    "start_session, and persist chatSessionId+engine+provider+model\n"
    "in the closeout_succeeded event payload (Q4 audit trail).\n\n"
    "Test results on this host:\n"
    "  * ai_router/tests/test_chatsessionid_writer.py — 12 passed\n"
    "  * full ai_router/tests/ unit suite — 644 passed, 1 skipped\n"
    "  * ai_router/tests/e2e — 8 passed\n\n"
    "Out of scope for this session (per the 7-session split):\n"
    "  * new_chat_id CLI + Claude Code hook-invoker (Session 2).\n"
    "  * signalKind retirement + Codex config-toml watcher retirement\n"
    "    (Session 3).\n"
    "  * Takeover UX modal/CLI prompt + watcher-inventory test\n"
    "    (Session 4).\n"
    "  * Layer-3 Playwright coverage + cross-tier docs + cross-repo\n"
    "    notice (Session 5).\n"
    "  * Orchestrator-agnostic UI audit + empty-state refactor\n"
    "    (Session 6).\n"
    "  * Final test sweep + change-log + dual-registry release\n"
    "    (Session 7).\n"
    "  * R1 alias retirement window — both the new and legacy lock\n"
    "    filenames are honored on read for one release per the spec\n"
    "    risk; legacy retirement is a follow-on set."
)


VERIFICATION_ASKS_A = (
    "Verification asks for Round A (writer code):\n\n"
    "1. close_lock.py — lifecycle lock rename + migration sweep:\n"
    "   (a) `LOCK_FILENAME = '.lifecycle.lock'` plus\n"
    "       `LEGACY_LOCK_FILENAME = '.close_session.lock'`. Legacy\n"
    "       handling lives only in `acquire_lock()`'s prelude: sweep\n"
    "       a stale legacy file or raise LockContention against a\n"
    "       live legacy holder. Is the sweep correct against a\n"
    "       concurrent pre-Set-036 close_session that just crashed?\n"
    "       Race window: legacy file exists at our read, then the\n"
    "       new-name acquisition succeeds — could a parallel\n"
    "       pre-Set-036 close_session that crashed before unlinking\n"
    "       its .close_session.lock but somehow restarted with the\n"
    "       same PID look 'live' to our `_is_stale` check?\n"
    "   (b) `acquire_lock_with_timeout(timeout_seconds=30, ...)`:\n"
    "       polls `acquire_lock` every 250 ms until success or the\n"
    "       deadline. On the final failure, raises LockContention\n"
    "       with the last observed holder record. Is the\n"
    "       `time.monotonic()` deadline computation correct in the\n"
    "       face of process-scheduler delays? The timeout==0 case\n"
    "       short-circuits to a single attempt — useful for the\n"
    "       no-waiting test recipe.\n"
    "   (c) Module docstring updated to call out the Set 036 rename\n"
    "       (R1 alias-on-read for one release). Are the surfaced\n"
    "       semantics ('start_session uses the polling variant;\n"
    "       close_session keeps immediate-failure') accurately\n"
    "       described for a reader who only reads the docstring?\n\n"
    "2. start_session.py — chatSessionId composite identity + lock:\n"
    "   (a) `--chat-session-id <value>` argument added; default\n"
    "       falls back to $CHAT_SESSION_ID env var via\n"
    "       `_resolve_chat_session_id`. Empty-string values from\n"
    "       either source collapse to None (so a wrapper that\n"
    "       exported the var empty does not write empty-string\n"
    "       identity into the state file). Is that the right\n"
    "       collapse semantic? Or should empty-string be treated as\n"
    "       a deliberate 'no identity' that should land in the state\n"
    "       file verbatim?\n"
    "   (b) New `EXIT_LOCK_CONTENTION = 5` constant. The boundary +\n"
    "       H3 + register_session_start flow now runs inside\n"
    "       `_run_under_lock(args)`, with the lock acquired+released\n"
    "       in the outer `run(args)`. Tests can drive the inner\n"
    "       function directly to assert behavior without lock\n"
    "       semantics. Is the split clean enough that callers don't\n"
    "       accidentally bypass the lock by calling\n"
    "       `_run_under_lock` directly?\n"
    "   (c) H3 composite-identity check now consults\n"
    "       `engine + provider + chatSessionId`. Tolerance: a prior\n"
    "       block missing the chatSessionId field entirely (legacy)\n"
    "       OR with the field present and null (Set 036+ writer that\n"
    "       had no ID at write time) is treated as same-holder for\n"
    "       engine+provider matches. Refusal message includes the\n"
    "       full composite via `_identity_label`. Is the asymmetry\n"
    "       between 'field absent' and 'field present=null' useful,\n"
    "       or should both collapse to the same audit-trail line in\n"
    "       the writer log? (Current rendering: '<no chat session ID\n"
    "       recorded>' vs '<null>' — Set 036 readers can tell them\n"
    "       apart.)\n"
    "   (d) Force-override log line now includes both chatSessionIds\n"
    "       (`_log_force_override`). Audit-trail format is\n"
    "       documented in close-out.md (Set 033 S6 — Set 036 S5 will\n"
    "       extend the docs to mention the chatSessionId segment).\n"
    "       Is the new line format greppable by the same\n"
    "       `awk`/`rg` recipes the prior shape used?\n\n"
    "3. session_state.py — orchestrator block + same_holder predicate:\n"
    "   (a) `register_session_start` gains\n"
    "       `orchestrator_chat_session_id: Optional[str] = None`.\n"
    "       The block always carries the `chatSessionId` key on a\n"
    "       new write (strict-on-write), with value None when the\n"
    "       arg is omitted. Existing same_holder predicate now\n"
    "       factors in chatSessionId equality with the same\n"
    "       tolerance branches as the start_session.py H3 check —\n"
    "       does the symmetry hold? (If the two diverge, force\n"
    "       overrides would preserve checkedOutAt incorrectly OR\n"
    "       rewrite it when they shouldn't.)\n"
    "   (b) `_flip_state_to_closed` already sets `orchestrator: None`\n"
    "       on close (Set 033 Session 6 behavior), so chatSessionId\n"
    "       is naturally cleared as part of nulling the block — no\n"
    "       new code needed here. Confirm by reading the existing\n"
    "       implementation: is the clear unconditional within the\n"
    "       function, or are there caller-driven branches that\n"
    "       could leave a stale chatSessionId on a closed snapshot?\n\n"
    "4. close_session.py — Q4 audit trail extension:\n"
    "   (a) New `_peek_orchestrator_identity(session_set_dir)` reads\n"
    "       the orchestrator block snapshot BEFORE the flip nulls\n"
    "       it. Returns a dict with chatSessionId/engine/provider/\n"
    "       model keys (with None values when the block was already\n"
    "       null-recorded) or an empty dict when the block was\n"
    "       absent entirely. Caller `**`-unpacks the dict so legacy\n"
    "       paths produce a closeout_succeeded payload without the\n"
    "       new keys, while Set 036+ paths produce one with them.\n"
    "       Is the empty-dict fallback correct? Or should we always\n"
    "       emit the keys with None values for forensic uniformity?\n"
    "   (b) Snapshot happens immediately after\n"
    "       `_peek_session_number`, BEFORE the gate runs. Could the\n"
    "       orchestrator block change between the snapshot and the\n"
    "       closeout_succeeded emission (e.g., a force-override\n"
    "       start_session racing the close_session and the lock\n"
    "       briefly contended)? With the new lifecycle lock, no —\n"
    "       both sides serialize on it. Confirm.\n"
    "   (c) The closeout_succeeded payload now carries chatSessionId\n"
    "       + engine + provider + model alongside the existing\n"
    "       'method' field. The session_events.py event-type\n"
    "       docstring is updated to document the contract\n"
    "       extension. Are downstream readers (the reconciler, the\n"
    "       reports module) tolerant of the larger payload? The\n"
    "       Event dataclass passes unknown fields through verbatim,\n"
    "       so this should be additive-only.\n\n"
    "5. gate_checks.py — working-tree-clean ignore patterns:\n"
    "   * Added '.lifecycle.lock' to the ignored patterns alongside\n"
    "     the existing '.close_session.lock' entry (legacy honored\n"
    "     for one release). Are both ignore strings exact-match or\n"
    "     glob? (Current implementation uses fnmatch / glob.)\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references. Be concrete about the line numbers — Set\n"
    "036 Sessions 2–7 will reference your verdict for downstream\n"
    "design decisions."
)


VERIFICATION_ASKS_B = (
    "Verification asks for Round B (Round A fix confirmation + tests + docs):\n\n"
    "Round A surfaced one Blocker (legacy-lock serialization), one\n"
    "Major (empty-string CLI semantics), and one Minor (docstring\n"
    "exit code). All three are addressed in the bundle below. The\n"
    "primary ask for Round B is: confirm the fixes are correct AND\n"
    "exercise the tests + docs that didn't fit in Round A.\n\n"
    "0. ROUND A FIX VERIFICATION:\n\n"
    "   (a) BLOCKER fix: `acquire_lock()` now dual-acquires the new\n"
    "       `.lifecycle.lock` AND the legacy `.close_session.lock`\n"
    "       atomically. Both must succeed for the call to return a\n"
    "       handle; a failed legacy-file acquisition rolls back the\n"
    "       new-name file. `release_lock()` removes both. The\n"
    "       per-file `_try_create_with_stale_reclaim()` helper\n"
    "       encapsulates the O_EXCL + stale-reclaim-retry pattern\n"
    "       so the dual-acquire orchestration in `acquire_lock` is\n"
    "       readable as two sequential gate-checks.\n"
    "       Questions:\n"
    "       - Acquisition order: new-name first, then legacy. If a\n"
    "         legacy holder takes `.close_session.lock` between our\n"
    "         step 1 (create `.lifecycle.lock`) and step 2 (create\n"
    "         `.close_session.lock`), we roll back step 1 and\n"
    "         raise. Is the order correct, or should we acquire\n"
    "         legacy first so the more-contended file is taken\n"
    "         first?\n"
    "       - Release order: new first, then legacy. If we crash\n"
    "         between, the legacy file becomes the orphan that the\n"
    "         next acquirer's stale-check reaps. Does this match\n"
    "         the existing stale-reclaim semantics? (TTL is 10\n"
    "         minutes; dead-PID probe is immediate.)\n"
    "       - Symmetry: the tests `test_live_legacy_lock_blocks_\n"
    "         new_acquisition` and `test_dual_acquire_creates_both_\n"
    "         files` cover the live-blocker path and the dual-write\n"
    "         success path. Is there a third path that should be\n"
    "         tested — e.g., the legacy file being stale-but-the-\n"
    "         new-file-also-being-stale?\n\n"
    "   (b) MAJOR fix: `_resolve_chat_session_id()` now treats\n"
    "       `args.chat_session_id is None` as 'omitted; fall through\n"
    "       to env' and any other value (including '') as authoritative.\n"
    "       Empty string still collapses to `None` in the return value\n"
    "       so the state file never carries an empty-string identity.\n"
    "       The new test `test_explicit_empty_string_clears_env`\n"
    "       exercises this with `CHAT_SESSION_ID` set in the env.\n"
    "       Question: does the new docstring match what the code does\n"
    "       (especially the 'precedence' bullet list and the empty-\n"
    "       string collapse semantics)?\n\n"
    "   (c) MINOR fix: `close_lock.py` module docstring now documents\n"
    "       per-caller exit codes (start_session → 5, close_session →\n"
    "       3) instead of asserting a single code. Cite the line\n"
    "       range and confirm the surface is accurate.\n\n"
    "1. ai_router/tests/test_chatsessionid_writer.py — now 15 tests:\n"
    "   (a) test_fresh_check_out_writes_chat_session_id — writes\n"
    "       the explicit CLI value into the orchestrator block.\n"
    "   (b) test_fresh_check_out_writes_none_when_unsupplied —\n"
    "       strict-on-write contract: key present, value None.\n"
    "   (c) test_fresh_check_out_picks_up_env_var — $CHAT_SESSION_ID\n"
    "       fallback path; uses an `_isolate_env` autouse fixture\n"
    "       to strip ambient values.\n"
    "   (d) test_same_composite_reattach_is_benign — full composite\n"
    "       match preserves checkedOutAt + idempotent rc=0.\n"
    "   (e) test_different_chat_session_id_refuses — engine+provider\n"
    "       match but chatSessionId mismatch → EXIT_CHECKOUT_CONFLICT\n"
    "       (4); refusal names both chatSessionIds.\n"
    "   (f) test_refusal_message_for_legacy_state_calls_out_no_chat_id\n"
    "       — legacy block (no chatSessionId field) + engine+provider\n"
    "       mismatch → refusal message names the 'no chat session ID\n"
    "       recorded' state.\n"
    "   (g) test_force_override_rewrites_chat_session_id — --force\n"
    "       writes the new value + appends a writer-log line\n"
    "       containing both chatSessionIds.\n"
    "   (h) test_legacy_no_chat_session_id_tolerated_then_populated\n"
    "       — tolerant-on-read; first new write populates the field.\n"
    "   (i) test_lock_contention_returns_exit_5 — pre-acquires the\n"
    "       lock in the test thread, monkeypatches timeout to 0.5s,\n"
    "       asserts EXIT_LOCK_CONTENTION (5) and 'lifecycle lock\n"
    "       contention' in stderr.\n"
    "   (j) test_lock_acquired_when_no_peer_holds — clean acquire +\n"
    "       release on a no-peer set; asserts the lock file is\n"
    "       removed on exit.\n"
    "   (k) test_closeout_succeeded_payload_includes_orchestrator_\n"
    "       identity — drives a real start_session + close_session\n"
    "       (with stubbed gate predicates) and asserts the\n"
    "       closeout_succeeded event payload carries chatSessionId\n"
    "       + engine + provider + model.\n"
    "   (l) test_legacy_close_session_lock_swept_when_stale — writes\n"
    "       a stale .close_session.lock with a dead PID, asserts\n"
    "       start_session sweeps it on the new acquisition path.\n"
    "\n"
    "   Questions:\n"
    "   - Branch coverage: did this miss any branch of the H3\n"
    "     composite-identity logic? Specifically, the \"prior chat\n"
    "     session ID is None but caller's is not\" case (tolerant-\n"
    "     on-read for a Set 036+ writer that had no ID at write\n"
    "     time, vs. legacy block with field absent). Are both\n"
    "     branches exercised by tests (h) and (e) respectively?\n"
    "   - test_legacy_close_session_lock_swept_when_stale uses\n"
    "     PID 999_999. Could that PID happen to be live on a CI\n"
    "     host where the test runs? The existing\n"
    "     test_stale_lock_by_dead_pid_is_reclaimed in\n"
    "     test_close_lock.py uses the same idiom — is this an OK\n"
    "     pattern, or should we look at /proc / OpenProcess\n"
    "     before picking the number?\n"
    "   - The _fresh_set fixture now includes the\n"
    "     '## Session Set Configuration' heading so totalSessions=3\n"
    "     is picked up by the spec parser. Without the heading the\n"
    "     writer falls back to inferring total=1 from\n"
    "     session_number. Is the comment in the fixture clear\n"
    "     enough that a future contributor doesn't accidentally\n"
    "     strip it?\n\n"
    "2. ai_router/docs/close-out.md — three updates:\n"
    "   - Section 2 step 3: acquire lifecycle lock; both filenames\n"
    "     honored on read; start_session polls 30s, close_session\n"
    "     fails immediately on contention.\n"
    "   - 'Stale lock' troubleshooting paragraph: lifecycle.lock\n"
    "     primary, legacy filename mentioned for the migration\n"
    "     window.\n"
    "   - 'Cross-set parallelism' paragraph: per-set lifecycle\n"
    "     lock now serializes same-set lifecycle re-entry (start\n"
    "     + close).\n"
    "   Are the doc surfaces sufficient for a reader who has not\n"
    "   read the spec? Anything that should reference the Set 036\n"
    "   audit-locked proposal directly?\n\n"
    "3. ai_router/session_events.py — closeout_succeeded payload\n"
    "   docstring update: Q4 audit-trail extension noted with the\n"
    "   four field names and the legacy degradation behavior. Is\n"
    "   the language clear about when fields are 'omitted' vs.\n"
    "   'present with None value'?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references."
)


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 1 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="036-chatsessionid-and-watcher-scope-implementation",
        session_number=1,
    )
    dump_path = (
        REPO_ROOT / "scripts" / f"verify_session_036_1_result_{label.lower()}.json"
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


def _head(text: str, n_lines: int) -> str:
    return "\n".join(text.splitlines()[:n_lines])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", choices=["A", "B"], default="A")
    args = parser.parse_args()

    ar_dir = REPO_ROOT / "ai_router"
    close_lock_text = (ar_dir / "close_lock.py").read_text("utf-8")
    start_session_text = (ar_dir / "start_session.py").read_text("utf-8")
    # session_state.py is large; ship only the delta-relevant slice:
    # register_session_start + the orchestrator-block-build section.
    session_state_text = (ar_dir / "session_state.py").read_text("utf-8")
    close_session_text = (ar_dir / "close_session.py").read_text("utf-8")
    session_events_text = (ar_dir / "session_events.py").read_text("utf-8")

    test_text = (
        ar_dir / "tests" / "test_chatsessionid_writer.py"
    ).read_text("utf-8")
    close_out_doc = (ar_dir / "docs" / "close-out.md").read_text("utf-8")
    gate_checks_text = (ar_dir / "gate_checks.py").read_text("utf-8")

    rounds = {
        "A": (
            "Round A: lifecycle lock + start_session core deltas",
            (
                f"=== ai_router/close_lock.py "
                f"(full file — lifecycle lock rename + sweep + timeout) ===\n"
                f"{close_lock_text}\n\n"
                f"=== ai_router/start_session.py "
                f"(full file — --chat-session-id + EXIT_LOCK_CONTENTION + "
                f"lifecycle lock wrap + H3/H4 composite identity) ===\n"
                f"{start_session_text}\n"
            ),
            VERIFICATION_ASKS_A,
        ),
        "B": (
            "Round B: session_state + close_session + gate_checks + tests + docs",
            (
                f"=== ai_router/session_state.py "
                f"(register_session_start slice) ===\n"
                f"{_slice_session_state(session_state_text)}\n\n"
                f"=== ai_router/close_session.py "
                f"(closeout_succeeded payload extension) ===\n"
                f"{_slice_close_session(close_session_text)}\n\n"
                f"=== ai_router/gate_checks.py "
                f"(ignore patterns block) ===\n"
                f"{_slice_gate_checks(gate_checks_text)}\n\n"
                f"=== ai_router/tests/test_chatsessionid_writer.py ===\n"
                f"{test_text}\n\n"
                f"=== ai_router/docs/close-out.md "
                f"(updated paragraphs) ===\n"
                f"{_slice_close_out_doc(close_out_doc)}\n\n"
                f"=== ai_router/session_events.py "
                f"(EVENT_TYPES docstring) ===\n"
                f"{_slice_session_events_doc(session_events_text)}\n"
            ),
            VERIFICATION_ASKS_B,
        ),
    }

    label, bundle, asks = rounds[args.round]
    print(f"Running {label} ...")
    _run_round(args.round, bundle, asks)
    return 0


def _slice_session_state(text: str) -> str:
    """Show register_session_start through orchestrator block write."""
    lines = text.splitlines()
    # Find start of register_session_start and a sensible end.
    start = next(
        (i for i, l in enumerate(lines) if "def register_session_start(" in l),
        0,
    )
    # End at _propagate_total_sessions definition (after the function).
    end = next(
        (i for i, l in enumerate(lines)
         if i > start and "def _propagate_total_sessions" in l),
        start + 250,
    )
    return "\n".join(lines[start:end])


def _slice_close_session(text: str) -> str:
    """Show _peek_orchestrator_identity + the closeout_succeeded path."""
    lines = text.splitlines()
    start = next(
        (i for i, l in enumerate(lines)
         if "def _peek_orchestrator_identity" in l),
        0,
    )
    # Snap to a chunk that includes the closeout_succeeded emission
    # call in `run()`. _peek_orchestrator_identity → through outcome
    # block in run().
    end = next(
        (i for i, l in enumerate(lines)
         if i > start
         and "orchestrator_identity = _peek_orchestrator_identity" in l),
        start + 60,
    )
    head = "\n".join(lines[start:start + 50])
    # Then grab the closeout_succeeded emission block.
    succ_start = next(
        (i for i, l in enumerate(lines)
         if "Set 036 Session 1 (Q4): include the orchestrator" in l),
        end,
    )
    succ_end = next(
        (i for i, l in enumerate(lines)
         if i > succ_start and "# Flip session-state.json" in l),
        succ_start + 25,
    )
    succ_chunk = "\n".join(lines[succ_start:succ_end])
    snapshot_start = next(
        (i for i, l in enumerate(lines)
         if "Set 036 Session 1 (Q4): snapshot the orchestrator" in l),
        0,
    )
    snapshot_chunk = "\n".join(lines[snapshot_start:snapshot_start + 8])
    return (
        f"--- _peek_orchestrator_identity ---\n{head}\n\n"
        f"--- snapshot site in run() ---\n{snapshot_chunk}\n\n"
        f"--- closeout_succeeded emission ---\n{succ_chunk}"
    )


def _slice_gate_checks(text: str) -> str:
    lines = text.splitlines()
    start = next(
        (i for i, l in enumerate(lines)
         if "_WORKING_TREE_IGNORE_PATTERNS" in l),
        0,
    )
    end = next(
        (i for i, l in enumerate(lines)
         if i > start and l.strip() == ")"),
        start + 25,
    ) + 1
    return "\n".join(lines[start:end])


def _slice_close_out_doc(text: str) -> str:
    """Capture the three updated paragraphs."""
    lines = text.splitlines()
    out_chunks: list[str] = []
    markers = [
        ("Acquire lifecycle lock", 30),
        ("Stale lock", 12),
        ("Cross-set parallelism", 15),
    ]
    for marker, length in markers:
        idx = next(
            (i for i, l in enumerate(lines) if marker in l),
            None,
        )
        if idx is not None:
            out_chunks.append("\n".join(lines[idx:idx + length]))
    return "\n\n---\n\n".join(out_chunks)


def _slice_session_events_doc(text: str) -> str:
    lines = text.splitlines()
    start = next(
        (i for i, l in enumerate(lines)
         if "``closeout_succeeded`` — close-out completed" in l),
        0,
    )
    return "\n".join(lines[start:start + 12])


if __name__ == "__main__":
    raise SystemExit(main())

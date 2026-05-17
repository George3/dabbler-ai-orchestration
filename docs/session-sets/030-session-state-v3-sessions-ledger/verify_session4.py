"""Session 4 verification driver — Set 030.

Round A bundles the high-risk migrator surface:

  - ai_router/migrate_session_state.py — the inferential v2→v3 core
    (_resolve_total, _build_v3_sessions, _migrate_state_dict, the
    closed-signal force-promote rule, strict-int filtering of bool /
    float in v2 fields, dual-write derivation, atomic write).
  - The public entry point ``migrate_one_set`` (the helper Session 5's
    in-extension lazy migrator will also call).

Per memory ``feedback_split_large_verification_bundles``, the migrator
is sliced to keep the bundle under 700 LOC. CLI argparse / output
formatting / __all__ are excluded (lower risk; they don't affect the
correctness of migrated v3 state).

Per memory ``feedback_ai_router_route_result_handling``, the
RouteResult is dumped to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent


def read_lines(path, ranges):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel = path.relative_to(REPO_ROOT).as_posix()
    chunks = []
    for start, end in ranges:
        section = "\n".join(
            f"{i+1:>5}  {lines[i]}" for i in range(start - 1, min(end, len(lines)))
        )
        chunks.append(
            f"--- {rel} lines {start}-{min(end, len(lines))} ---\n{section}"
        )
    total_lines = sum(min(e, len(lines)) - s + 1 for s, e in ranges)
    return (
        f"=== FILE: {rel} ({total_lines} LOC across {len(ranges)} slice(s)) ===\n"
        + "\n\n".join(chunks)
    )


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


def run_round(label, system_summary, code_block, focus_prompt, out_path):
    print(f"\n{'='*60}\n[{label}] sending verification call...\n{'='*60}")
    result = ai_router.route(
        content=focus_prompt,
        task_type="session-verification",
        context=f"{system_summary}\n\n--- FILES ---\n{code_block}",
        session_set="030-session-state-v3-sessions-ledger",
        session_number=4,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


SYSTEM_SUMMARY = """
Set 030 Session 4 ships the bulk v2→v3 migrator
(`python -m ai_router.migrate_session_state`) and runs it in-place
against this repo's 29 v2 state files. Publishing to PyPI / Marketplace
moves to Session 5 (per spec D14 revision); Session 4 only builds the
release candidate (v0.4.0rc1 + v0.14.0-rc.1).

Per spec D5, the migrator emits the v3 dual-write shape: BOTH
`sessions[]` (the new canonical ledger) AND the legacy triple
(`currentSession` / `totalSessions` / `completedSessions`) derived from
sessions[]. Set 030 never drops legacy emission; that is a future set.

The migrator is INFERENTIAL, not strict. Unlike `progress.synthesize_v3_from_v2`
(which defaults to "not-started" and surfaces contradictions for the
read path), the migrator operates on already-existing v2 files where
the operator has already decided semantics. It uses these inference
rules:

1. **Closed signal force-promotes all.** When v2 input shows
   `status: complete` AND (`lifecycleState: closed` OR
   `currentSession >= totalSessions`), every session is set to
   `complete` — even if `completedSessions[]` is missing or empty.
   This is the key difference from synthesize_v3_from_v2: it heals
   sets 007/008/010/011/012/014/etc. which were closed without ever
   populating the completedSessions array (the array landed in Set 022).

2. **Otherwise trust the array.** When the closed signal is absent,
   `completedSessions[]` (filtered to strict positive ints in 1..total)
   is authoritative for which sessions are `complete`.

3. **Promote currentSession to in-progress** only when top-level
   status is `in-progress` AND currentSession is a strict positive
   int in [1, total] AND not already in completedSessions[].

4. **Strict-int filter:** bool/float/str values for currentSession or
   completedSessions[] entries are rejected at the boundary
   (`type(v) is int and v > 0`). A v2 file with currentSession=True or
   completedSessions=[1.0] does NOT silently escalate session 1.

5. **Top-level status canonicalized:** `done`/`completed` → `complete`
   on write (read path already tolerates).

6. **Lifecycle state resolution:** `status=complete` →
   `lifecycleState=closed`; `status=in-progress` + null lifecycle →
   `work_in_progress`; `status=cancelled` + null lifecycle → `closed`
   (the marker file is the operator-visible signal).

7. **Title resolution:** strategy=regex parses spec.md headings
   (`### Session K of N: <title>`); strategy=generic uses `Session N`
   labels. Missing/unreadable spec.md falls back to generic.

8. **Validation gate:** after computing sessions[], the migrator
   converts to SessionRecord[] and runs `validate_invariants` BEFORE
   any write. Any rule violation surfaces as ACTION_WOULD_VIOLATE
   (the on-disk file is left untouched even with --in-place).

Test coverage: 38 pytest cases covering idempotency (v3 inputs
skipped), all four lifecycle shapes (closed / in-flight /
between-sessions / not-started), cancelled sets, status aliases,
bool/float strict filtering, title resolution (regex/generic/missing
spec), malformed inputs (no state, bad JSON, top-level array),
dry-run vs in-place atomicity, AI-stub NotImplementedError,
unknown-strategy ValueError, discovery + filter, CLI exit codes +
JSON output + non-TTY interactive fallback.

Test results: pytest 568 passed + 1 skipped + 8 e2e deselected
(includes the 38 new test_migrate_session_state cases + 1 allowlist
update to test_no_legacy_field_reads.py adding migrate_session_state.py
to the carve-out list — the migrator IS the v2-compat path, so D13
allowlists it like progress.py and session_state.py). Mocha unit
376 passing + 2 failing (both pre-existing baseline failures
unrelated to v3, identical to Session 3's). Layer 3 Playwright 5/5
passing. tsc --noEmit clean.

In-repo migration applied: 29 v2 state files (001 through 029)
migrated in-place via `--strategy regex --in-place`. 030 itself
skipped (already v3). 0 malformed, 0 would-violate. The migration
is its own commit so it can be diffed and reverted independently.

D16 Lightweight-tier ergonomics dry-run: representative
dabbler-homehealthcare-accessdb fixture (001-forms-detail-uat,
4 sessions, closed) copied to C:/tmp/v3-ergonomics-dry-run, migrated
via --strategy regex --in-place; demo script walks the one-field-flip
transitions for not-started → in-progress → complete and confirms
each step round-trips through read_progress without violation.
Worked example saved to verification-output/lightweight-ergonomics-demo.txt.

Consumer dry-run doc: docs/migration-v3-dry-run.md.

RC artifacts built locally (not committed, not published):
- dist/dabbler_ai_router-0.4.0rc1-py3-none-any.whl
- tools/dabbler-ai-orchestration/dabbler-ai-orchestration-0.14.0-rc.1.vsix
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 4 bulk migrator correctness.

The bundle below contains the migrator's inferential core plus its
public entry points. Verify:

A. **Inferential closed-signal correctness (`_build_v3_sessions`,
   `_migrate_state_dict`).** The migrator force-promotes every
   session to `complete` when v2 input shows `status: complete` AND
   (`lifecycleState: closed` OR `currentSession >= totalSessions`).
   Verify:
   1. Are both branches of the disjunction tested? Specifically: a v2
      file with `status: complete + lifecycleState: closed +
      completedSessions: []` (the 007/008/010/011/012/014 shape) is
      correctly migrated to all-complete?
   2. A v2 file with `status: complete + lifecycleState: null +
      currentSession >= totalSessions` (the alternative closed
      signal) also gets all-complete?
   3. Does the lifecycle resolution then set `lifecycleState=closed`
      in the output even when the input had `null` (since `status:
      complete` should pair with `closed` per rule 8)?
   4. When closed_signal is true but completedSessions[] contains
      MORE numbers than the closed-signal forces (e.g., a stale
      currentSession=2 + completedSessions=[1,2,3] + totalSessions=3
      + status=complete), is the output still all-complete (no
      ambiguity)?

B. **`_strict_positive_int` boundary filter.** The function uses
   `type(v) is int and v > 0`. Confirm:
   1. `True` is rejected even though `isinstance(True, int)` is True
      and `True == 1` (Python's bool/int aliasing).
   2. `1.0` is rejected even though `1.0 == 1`.
   3. `"1"` is rejected.
   4. `0` and negative ints are rejected.
   5. `None` is rejected without raising.
   These checks gate currentSession promotion to in-progress AND
   completedSessions[] membership for the "complete" status. Identify
   any code path where a non-int-positive value could still leak
   through and escalate a session's status.

C. **Title resolution.** `_build_v3_sessions` uses spec_titles when
   `use_generic_titles=False` AND the number is in spec_titles. Else
   falls back to `Session N`. Verify:
   1. Strategy=regex with a complete spec.md → all titles from regex
      extraction.
   2. Strategy=regex with a partial spec.md (heading for sessions 1,
      2 but not 3) → 1 and 2 from regex, 3 falls back to `Session 3`.
   3. Strategy=generic → all titles `Session N` regardless of spec
      content.
   4. Strategy=regex with no spec.md → all titles `Session N`.

D. **Total-session resolution (`_resolve_total`).** Picks the max of
   totalSessions (if strict-positive), max(spec_titles.keys()),
   currentSession (if strict-positive), and the max of strict-int
   entries in completedSessions[]. Verify:
   1. A v2 file with totalSessions=3 but spec.md declaring 4 sessions
      → resolves to 4 (operators who edit spec.md upward should see
      the larger total surface in the migrated v3 ledger).
   2. A v2 file with totalSessions=null + completedSessions=[1, 2, 3]
      → resolves to 3.
   3. A v2 file with no signal anywhere → resolves to 0 → migration
      raises SessionStateInvariantError(rule=1) → caller wraps as
      ACTION_WOULD_VIOLATE.

E. **Cancelled-set handling.** `_resolve_lifecycle_state` for
   `status=cancelled` keeps any non-empty operator-written
   lifecycleState, defaulting to `closed`. Session-level status
   reflects ACTUAL completion (from completedSessions[]), not
   `cancelled` (since v3 doesn't have per-session cancellation —
   spec D12). Verify:
   1. A v2 file with status=cancelled + lifecycle=null +
      completedSessions=[1] (partial) → top status preserved
      `cancelled`, lifecycle becomes `closed`, sessions[0]=complete,
      sessions[1..]=not-started, validation passes (rule 7 does NOT
      fire for cancelled — that rule applies to status=complete
      only).
   2. A v2 file with status=cancelled + lifecycle="active" → operator
      value preserved as "active" (the function explicitly keeps
      non-empty operator-written values for cancelled). Confirm this
      is the intended behavior or flag if it should normalize.

F. **Dual-write parity (`_derive_legacy_triple`).** The legacy triple
   is computed from sessions[] AFTER inference. Verify:
   1. `current` = the in-progress session number, else None.
   2. `total` = len(sessions).
   3. `completed` = sorted ascending list of complete-status numbers.
   4. For a closed set, current=None (no in-progress), total=N,
      completed=[1..N].
   5. For an in-flight set with 1 complete + 1 in-progress + rest
      not-started, current=2, completed=[1], total=N.
   6. For a between-sessions set, current=None, completed=[...],
      total=N.

G. **Atomic write (`_atomic_write_json`).** Uses tempfile in the
   same directory + os.replace. Verify:
   1. A partial write (e.g., disk full mid-write) leaves the
      original file intact (os.replace is atomic on the same
      volume; tempfile in same directory guarantees same volume).
   2. The temp filename pattern (`.{basename}.tmp`) is unlikely to
      collide with operator-created files.
   3. The cleanup contract: on success, no temp file remains. On
      failure of tempfile creation, no partial state. Identify any
      crash window where a `.session-state.json.tmp` could be
      left behind (e.g., if json.dump raises mid-serialization).

H. **`migrate_one_set` contract.** The public entry point used by
   both the CLI and (Session 5) the in-extension lazy migrator.
   Verify:
   1. A missing state file → ACTION_SKIPPED_NO_STATE, never raises.
   2. Unparseable JSON → ACTION_SKIPPED_MALFORMED, never raises.
   3. Top-level JSON array (not object) → ACTION_SKIPPED_MALFORMED.
   4. A v3 file (schemaVersion=3 with sessions[] list) →
      ACTION_SKIPPED_V3, no write.
   5. strategy=`ai` raises NotImplementedError (Session 5 dependency
      stub).
   6. strategy=`interactive` resolves to `regex` when called as a
      library (the CLI's interactive flow handles per-set prompts
      upstream).
   7. Any unknown strategy raises ValueError.
   8. ACTION_WOULD_VIOLATE leaves the on-disk file untouched even
      when dry_run=False.

I. **Idempotency.** Running the migrator on a v3 file produces
   ACTION_SKIPPED_V3. Verify:
   1. Re-running the migrator after a successful in-place migration
      is a no-op (counts: 29 migrated → 0 migrated, 29 skipped_v3
      on the second pass).
   2. The schemaVersion check + sessions[] presence check together
      reject any partially-migrated shape from a future schema bump.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have
    notes.)
  - REJECTED: <bulleted list of must-fix issues with line numbers>.

Cite specific line numbers when flagging issues. Skip stylistic nits.
Focus on correctness: does the inferential logic produce v3 states
that satisfy the 8 invariants under every input shape v2 state files
take in the wild, AND does the validation gate correctly refuse to
write when inference produces an invalid shape?
""".strip()


def _files() -> str:
    migrator = read_lines(
        REPO_ROOT / "ai_router" / "migrate_session_state.py",
        # Skip module docstring (already in SYSTEM_SUMMARY) and CLI
        # argparse / output formatting (lower risk). Bundle the
        # inferential core + public entry points.
        [
            (104, 220),   # constants + MigrationResult + helpers (_strict_positive_int,
                          # _strip_legacy_completed, _resolve_total, _resolve_lifecycle_state)
            (220, 360),   # _build_v3_sessions + _derive_legacy_triple + _migrate_state_dict
            (360, 470),   # migrate_one_set (public entry) + _atomic_write_json + discover/migrate_all
        ],
    )
    return migrator


def main():
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session4.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    if sub == "round-a":
        code_block = _files()
        run_round(
            "Round A",
            SYSTEM_SUMMARY,
            code_block,
            FOCUS_PROMPT,
            out_dir / "round-a-session-4-result.json",
        )
    elif sub == "round-b":
        code_block = _files()
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated migrator.\n\n"
            "For each Round-A issue, confirm:\n"
            "  - The fix is present at the cited location.\n"
            "  - The fix doesn't introduce a new contradiction.\n"
            "  - The fix is consistent with spec D5 (dual-write — "
            "Set 030 does not drop legacy emission), D6 (fail loud, "
            "never silently recover), and the inferential rules in "
            "the module docstring.\n\n"
            "Format: VERIFIED if all issues addressed and no new ones "
            "found; REJECTED if any remain or new ones surfaced. Cite "
            "line numbers; skip stylistic nits."
        )
        run_round(
            "Round B",
            SYSTEM_SUMMARY
            + "\n\n--- Round B context ---\nRound A returned REJECTED "
            "with must-fix issues. The fixes are in place; Round B is "
            "the confirmation pass.",
            code_block,
            focus,
            out_dir / "round-b-session-4-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

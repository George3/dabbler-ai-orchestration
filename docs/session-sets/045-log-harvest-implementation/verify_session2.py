"""Session 2 verification driver — Set 045 / log-harvest implementation.

Bundles the S2 deliverables and asks a cross-provider verifier
(Gemini Pro) to confirm the joiner-spec design + the Python
skeleton match the joiner-location lock + correlation evidence
from S1.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
Per memory `feedback_session_verification_gpt54_429_pivot_to_gemini`:
go straight to gemini-pro to avoid the GPT-5.4 429 cascade that
hit S1 and Set 036.
Per memory `feedback_split_large_verification_bundles`: bundle
estimated <100KB; well within gemini-pro's context window.
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


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 045 (log-harvest implementation) ships the dual-primary
observability architecture locked by Set 044's consensus-audited
proposal: a Python launch wrapper + per-backend native-log parsers
+ a joiner that detects coordination conflicts and writer-bypass
writes.

Session 1 (CLOSED, VERIFIED by gemini-pro at $0.024) resolved four
open empirical questions: bypass-rate self-observation log clock-
started, deterministic wrapper-to-native-log correlation proven
1:1 on real on-disk Claude+Copilot logs at a 30s window, Claude
phrasing-trigger hypothesis matrix + four defensive template rules
authored, and joiner location LOCKED to Python at ai_router.joiner.

Session 2 (THIS verification) ships the joiner design + canonical
schema + Python skeleton + Layer-1 tests:

  - joiner-spec.md (this is the engineering-center-of-gravity doc
    per Set 044 Pass B consensus)
  - ai_router/joiner/ package (schema.py, parsers.py, conflicts.py,
    coverage.py, cli.py, __init__.py, __main__.py)
  - ai_router/tests/test_joiner_*.py (59 new tests covering each
    module; full pytest suite remains green at 752 passed, 1 skipped)

S3 will ship the dabbler-launch wrapper + Copilot parser hardening
that produces records the joiner consumes. S4 ships the Claude
parser hardening + narration template. S5 wires the Explorer to
the joiner CLI. S6 ships UAT + cross-tier docs + dual-registry
release.

Cumulative routed spend across Set 045 = $0.024 of $5.00 NTE
coming into THIS verification.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt was authored by an AI agent that may
have an opinion on the answer. Its framing may inadvertently
constrain you to in-scope refinements when the right answer is
to question the scope. The work being reviewed may be presented
as further along than it should be. Before answering as posed,
briefly check whether this is the right question. If a different
question would be more useful, answer that one too.

ROUND A — Session 2 deliverable verification for Set 045
(log-harvest implementation).

You are Gemini Pro, asked to verify that Session 2 of Set 045
ships a defensible joiner specification + canonical schema +
Python skeleton + Layer-1 test coverage that the S3–S5
implementation sessions can build on without re-litigating the
design.

Verification targets:

A. **joiner-spec.md — conflict-detection semantics (§3).**

   1. Three modes are specified: engine-mismatch (Mode A, high
      severity), bare-touch / stale-checkout-touch (Mode B,
      medium), writer-bypass (Mode C, high). Is the set
      *complete* given the Set 044 proposal §4.4 enumeration?
      Anything proposal §4.4 surfaces that S2 doesn't model?

   2. The engine-mismatch window is widened from S1's 30s
      correlation window to 5 minutes ("the conflict-detection
      window must be wider than the deterministic-binding
      window"). Is the reasoning sound? Are there edge cases
      where 5 minutes is too narrow (false-negative — a stray
      AI that started 10 minutes after the checkout would NOT
      be flagged)?

   3. Mode B's staleness threshold defaults to 2 hours,
      matching the existing CheckoutPollService 30-min default
      *poll timeout*. Is that the right baseline, or should
      staleness be tighter / looser? §3.2's false-positive
      mitigation requires the native session's cwd to be
      *strictly inside* the workspace boundary
      (`startswith(workspace + "/")`) — is that correct, or
      does it miss legitimate touches that root the cwd at the
      workspace itself (equal, not strict-inside)?

   4. Mode C's writer-bypass detector uses mtime + ±2s event-
      ledger correlation. §3.3's false-positive guard notes
      editor-save-without-changes can bump mtime. Is the
      mtime+event-correlation rule strong enough for S2, or
      does the missing content-hash check undercut the value?

   5. §3.4's resolution priorities table — does any cell name
      the wrong authority? E.g., should "what did Dabbler
      launch?" defer to the wrapper launch log OR to
      session-events.jsonl's `launch_started` event if the
      wrapper writes one in the same transaction?

B. **Canonical Harvest Record schema (§5).**

   1. The schema is derived FROM joiner needs per Pass B
      consensus. Is every field actually consumed by the
      joiner, or are there fields carried for "future use"
      that should be deferred?

   2. The schema replaces v0 (Set 044 §4.1 sketch) with
      tighter event_type enum + new binding_state field +
      tool_args_summary (redacted) instead of raw tool_args.
      §5.2 enumerates 5 specific revisions. Are these the
      right revisions? Anything v0 had that should have been
      KEPT in v1?

   3. §5.3 explicitly excludes per-turn message content,
      AI-CLI exit code, and per-turn effort. Are these the
      right exclusions, or do any of them belong in the
      schema for the S5 Explorer surface?

   4. The `binding_state` enum is `bound | unbound |
      ambiguous`. The Q2 evidence demonstrated 1:1 binding at
      30s on real data + ambiguity probe at 1h still 1:1.
      Should `ambiguous` be deferred until evidence surfaces
      it, or is reserving the enum value sound future-
      proofing?

C. **Python skeleton (ai_router/joiner/).**

   1. The module split is schema.py / parsers.py /
      conflicts.py / coverage.py / cli.py / __init__.py /
      __main__.py. Is this the right granularity for a
      ~1500-LOC package? Anything that should be split
      further or combined?

   2. parsers.py promotes the S1 spike scrapers
      (scan_claude_logs, scan_copilot_logs). The S1
      benchmark showed Python is 70× faster than the
      idiomatic TypeScript port on real workloads. Does the
      promoted code preserve the streaming I/O property
      (line-by-line read, no slurp), or does any hardening
      step regress it?

   3. The CLI accepts --conflicts, --coverage, --harvest
      modes (mutually exclusive). The S5 Explorer integration
      will shell out per refresh. Is the CLI surface
      ergonomic enough for the extension's
      SessionSetsProvider, or does it need additional flags
      (--since, --severity-min, --format)?

   4. The public API re-exports `scan_conflicts`, `harvest`,
      `coverage` from the package root. Are the import paths
      stable enough that S3+ implementation work won't
      churn them, or should anything be hidden until S5 ships?

D. **Layer-1 test coverage (ai_router/tests/test_joiner_*.py).**

   1. 59 tests across 5 files (schema, parsers, conflicts,
      coverage, cli). The full pytest suite remains green at
      752 passed (was 693 in S1 — 59 net added with zero
      regressions). Is the coverage breadth right?

   2. Each conflict mode has positive + negative + boundary
      cases. Is there a class of regression the tests would
      miss? (E.g., a Mode A engine that matches the state-
      engine after normalization but not before — currently
      tested in `test_same_engine_no_conflict` via
      "claude-code" → "claude".)

   3. The writer-bypass test uses os.utime to force a known
      mtime, then writes an events ledger entry at that
      timestamp ±some delta. Is that a robust mechanism
      across platforms (Windows + macOS + Linux for CI), or
      does it have a known portability issue (mtime precision
      on Windows is documented ~10ms granularity)?

E. **Cross-cutting calibration.**

   1. The S2 deliverables claim "the engineering center of
      gravity per Set 044 Pass B consensus" — does the actual
      content match that claim, or is the spec lighter than
      the framing suggests?

   2. §8 carves what S3, S4, S5 add vs. what S2 ships.
      Specifically, S2 ships the wrapper-launch SCAN code
      (parsers.scan_launch_log) but no wrapper writes the
      log yet (S3 owns that). Is that the right surgical
      slice, or is the wrapper-scan code premature?

   3. §9 records 4 deferred follow-ups (content-hash check,
      latency budget, bypass-rate feedback loop, Codex/Gemini
      shims). Is the deferral framing honest, or does any of
      these deserve to land in S2 rather than be punted?

   4. §7 privacy/redaction posture. Set 045 ships into
      consumer repos including a healthcare-accessdb
      (Lightweight tier). Are the redaction commitments
      strong enough for that consumer's compliance posture,
      or is more needed?

F. **Are these the right questions?**

   Per the bias-cautions preamble: if a different question
   would be more useful, answer that one too. Specific
   examples that may belong here:
     - Is the *staleness threshold* of 2 hours the right
       default given operator memory entries say "use the
       working CheckoutPollService 30-min default poll
       timeout"? (Specifically: §3.2 says "2h" but the
       CheckoutPollService default is 30min; is this a
       mis-citation?)
     - The S1 joiner-location-decision.md noted "the
       integration pattern: the extension's existing
       SessionSetsProvider polls session-state.json and
       re-renders. When it does, it shells out to python -m
       ai_router.joiner --conflicts --set-slug <slug>." Does
       the S2 CLI design align with that pattern, or has it
       drifted?
     - Should the joiner emit events to its own ledger (an
       `ai_router/router-joiner-runs.jsonl` or similar) for
       observability of the joiner itself, or is that
       premature optimization?

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(SET_DIR / "joiner-spec.md"),
        read_file(REPO_ROOT / "ai_router/joiner/__init__.py"),
        read_file(REPO_ROOT / "ai_router/joiner/schema.py"),
        read_file(REPO_ROOT / "ai_router/joiner/parsers.py"),
        read_file(REPO_ROOT / "ai_router/joiner/conflicts.py"),
        read_file(REPO_ROOT / "ai_router/joiner/coverage.py"),
        read_file(REPO_ROOT / "ai_router/joiner/cli.py"),
        read_file(REPO_ROOT / "ai_router/joiner/__main__.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_schema.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_parsers.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_conflicts.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_coverage.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_cli.py"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-002-route-result.json"

    print(f"\n{'='*60}\n[Round A] sending to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=FOCUS_PROMPT,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE START ---\n{bundle}\n--- BUNDLE END ---",
        session_set="045-log-harvest-implementation",
        session_number=2,
    )
    result_dict = dump_route_result_to_json(result)
    out_path.write_text(
        json.dumps(result_dict, default=str, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"Provider: {result_dict.get('provider')}")
    print(f"Model: {result_dict.get('model') or result_dict.get('model_name')}")
    print(
        "Tokens: "
        f"in={result_dict.get('input_tokens', '?')}, "
        f"out={result_dict.get('output_tokens', '?')}"
    )
    print(f"Cost: ${result_dict.get('cost_usd', result_dict.get('cost', '?'))}")
    print(f"Latency: {result_dict.get('latency_ms', '?')} ms")
    text = (
        result_dict.get("response")
        or result_dict.get("text")
        or result_dict.get("content")
    )
    if isinstance(text, str):
        print(f"\n--- VERIFIER OUTPUT ---\n{text}\n--- end ---")
        # Save the verdict alongside the result JSON for easy reading.
        verdict_path = out_dir / "session-002.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

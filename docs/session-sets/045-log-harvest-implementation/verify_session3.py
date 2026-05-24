"""Session 3 verification driver — Set 045 / log-harvest implementation.

Bundles the S3 deliverables and asks a cross-provider verifier
(Gemini Pro) to confirm the dabbler-launch wrapper + Copilot OTel
parser hardening + joiner harvest() wire-up match the S2 contract.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
Per memory `feedback_session_verification_gpt54_429_pivot_to_gemini`:
go straight to gemini-pro to avoid the GPT-5.4 429 cascade that hit
Set 036 + Set 045 S1.
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

Session 1 (CLOSED, VERIFIED, $0.024 routed) resolved four open
empirical questions: bypass-rate self-observation log started,
deterministic correlation proven 1:1 at 30s window, Claude
phrasing-trigger hypothesis matrix + four defensive template
rules authored, joiner location LOCKED to Python at
ai_router.joiner.

Session 2 (CLOSED, VERIFIED, $0.053 routed) shipped joiner-spec.md
(conflict-detection semantics + canonical Harvest Record schema +
positive join algorithm + redaction posture) + the ai_router/joiner/
Python skeleton (7 modules) + 59 Layer-1 unit tests. Cumulative
routed Set 045 coming into S3: $0.077 of $5 NTE budget.

Session 3 (THIS verification) ships the S2 contract's three
remaining producer-side gaps:

  - ai_router/dabbler_launch.py — headless-mode wrapper CLI that
    writes canonical Harvest Record §5 shape to
    ~/.dabbler/launch-log.jsonl. Records carry event_type="launch",
    source="wrapper", engine + provider + model + effort. raw_ref
    carries launch_id (uuid4). The wrapper appends BEFORE
    subprocess spawn so failed spawns still surface as unbound
    launches in the joiner output.

  - Hardened Copilot OTel parser (read_copilot_session_events in
    ai_router/joiner/parsers.py) — per-event HarvestRecord
    emission for session.start / session.end / turn.* / tool.* /
    usage. Sticky context (cwd, conv_id, model, provider)
    propagates from session.start through subsequent events.
    Tool args go through _summarize_tool_args (§7 redaction).

  - harvest() wire-up (ai_router/joiner/schema.py) — applies the
    §4 positive-case join algorithm with 30s bind_window default.
    Each launch yields bound / unbound / ambiguous records.
    Free-running natives (no launch claim) still emit
    session_start records.

LaunchRecord parser projection renamed target_backend → engine for
consistency with HarvestRecord §5; reader accepts both shapes.

S4 ships Claude parser hardening + narration template. S5 wires
Explorer to the joiner CLI. S6 ships UAT + cross-tier docs +
dual-registry release.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt was authored by an AI agent that may
have an opinion on the answer. Its framing may inadvertently
constrain you to in-scope refinements when the right answer is
to question the scope. The work being reviewed may be presented
as further along than it should be. Before answering as posed,
briefly check whether this is the right question. If a different
question would be more useful, answer that one too.

ROUND A — Session 3 deliverable verification for Set 045
(log-harvest implementation).

You are Gemini Pro, asked to verify that Session 3 of Set 045
ships a wrapper + Copilot parser + joiner wire-up that match the
S2 contract verbatim (no schema or §4 algorithm drift) and that
the test coverage is sufficient for S4 and S5 to build on
without re-litigating Producer-side correctness.

Verification targets:

A. **dabbler-launch wrapper (ai_router/dabbler_launch.py).**

   1. Per joiner-spec.md §5 producers MUST emit to the canonical
      Harvest Record shape verbatim. Does build_record() emit
      every required §5.1 field? Are any fields missing or
      misnamed? Are nullable fields (conv_id, binding_state,
      tool, tool_args_summary, tokens_in, tokens_out,
      bound_candidates) emitted as explicit null per §5.1, or
      omitted (which would make JSON consumers branch)?

   2. The wrapper appends the record BEFORE spawning the child
      subprocess so a failed spawn still surfaces as an unbound
      launch in the joiner. Is the ordering correct, or does
      the wrapper's append+spawn sequence have a race where a
      crash between append and spawn could orphan a launch_id?

   3. Headless-only per Set 044 commitment 4. subprocess.run is
      used with the default stdin/stdout/stderr inheritance.
      Are there Windows-specific gotchas (console handle
      inheritance, Ctrl-C signal propagation) that the wrapper
      needs to handle, or does inheritance "just work" for the
      AI-CLI subprocess use case?

   4. Engine validation accepts {claude, copilot, codex,
      gemini}. The S2 schema enum agrees. If a consumer wants
      to wrap a vendor variant (e.g. "claude-code" vs
      "claude"), the wrapper rejects. Is that the right
      strictness, or should normalize_engine() be applied
      before validation?

   5. --dry-run is supported for record-only invocations.
      Is the flag's semantics tight enough (write the
      record + return 0; no subprocess spawn), or could a
      caller misuse it?

B. **Copilot OTel parser hardening
   (read_copilot_session_events in parsers.py).**

   1. Event type mapping is:
      session.start → session_start, session.end → session_end,
      turn.start / turn.end → turn, tool.call / tool.invoke →
      tool_call, usage → usage. Unknown types are skipped.
      Is this the right mapping? Is collapsing turn.start +
      turn.end into a single "turn" event lossy in a way that
      breaks downstream (e.g., S5 Explorer wants to render
      turn duration)?

   2. Sticky context (cwd, conv_id, model, provider)
      propagates from session.start through subsequent events.
      Is the stickiness rule sound, or does it have a failure
      mode (e.g., a mid-session re-checkout that changes
      provider would silently be misattributed)?

   3. §7 redaction: _summarize_tool_args reduces raw tool args
      to {file, lines, arg_count}. Are the heuristic keys
      (file/path/filename, line_count/lines/count, args)
      complete enough to cover the real Copilot OTel shape, or
      will real tool calls bypass the summary and leak raw
      content via arg_keys fallback?

   4. The function returns Iterable[HarvestRecord], not a
      bounded list. Is the streaming-generator contract honored
      end-to-end, or does a hardening step buffer everything?

   5. The original _read_copilot_events (session-level
      NativeSession projection) is preserved and unchanged.
      Is that the right split (per-event emission as a NEW
      function, not a replacement of the session-level one),
      or should the session-level scrape be migrated too?

C. **harvest() wire-up (ai_router/joiner/schema.py).**

   1. The join algorithm matches joiner-spec.md §4. For each
      launch, candidates = native sessions where
      engine matches + cwd_canonical matches + |first_event_ts
      − launch_ts| ≤ bind_window. 0 candidates → unbound;
      1 → bound; >1 → ambiguous. Is the candidate predicate
      exactly the spec's, or are there subtle differences (e.g.,
      the spec uses normalize_engine but the implementation
      uses raw equality)?

   2. After binding, the launch's bound conv_id is recorded
      in bound_native_ids. But the native session_start record
      is still emitted alongside the launch. Is that the right
      shape (launch + bound native both visible), or should the
      bound native be suppressed since the launch already
      carries the conv_id?

   3. The free-running natives (no launch) emission preserves
      the S2 behavior (session_start with no binding_state).
      Per joiner-spec.md §4 these are "free-running" sessions
      bypass-channel observability. Is the emission correct?

   4. Filters (workspace_cwd, since) apply to BOTH launches
      and natives. The implementation filters launches by
      launch_ts and natives by first_event_ts. Is that
      consistent (a launch that occurs before `since` but
      binds to a native after `since` — what happens)?

D. **Test coverage.**

   1. 18 new tests (3 Copilot OTel + 3 launch-log shape +
      9 wrapper + 4 join e2e). Layer-1 + Layer-2. Are the
      conflict modes from §4 (bound, unbound, ambiguous) +
      free-running case each covered? Anything in the Set 044
      proposal §4 or joiner-spec.md §4/§5 that the tests miss?

   2. The wrapper L1 tests use spawn=False / --dry-run to
      avoid invoking a real AI CLI. Is that the right
      compromise (testing the writer side only), or does the
      missing subprocess-spawn test mean a Windows-only or
      env-pollution regression could ship undetected? (Memory
      `project_electron_launch_env_pollution` is a related
      cautionary tale.)

   3. The Layer-2 e2e test (test_dabbler_launch_join_e2e.py)
      synthesizes Claude JSONL events at specific time offsets
      from a wrapper launch and asserts the joiner emits the
      right binding_state. Is the e2e coverage complete enough
      for S3 close-out, or does S5 Explorer integration need
      additional fixtures that S3 should pre-write?

E. **Backward compatibility (LaunchRecord field rename).**

   1. The LaunchRecord parser projection's target_backend
      field was renamed to engine. scan_launch_log accepts
      both v0 stub shape (target_backend / launch_ts) and
      canonical shape (engine / ts) on disk. The wrapper
      writes the canonical shape. Is the dual-acceptance
      reader the right backward-compat posture, or should
      the v0 shape be rejected outright (no live data in the
      v0 shape exists; S3 is the first writer)?

   2. The test_scan_launch_log_v0_stub_field_names_backward_compat
      test pins the v0 shape acceptance. Is that helpful (a
      safety net for any prior test fixture or operator-typed
      log) or a tech-debt magnet (a shape that should never
      have been written should not become a contract)?

F. **Cross-cutting / re-question.**

   Per the bias-cautions preamble: if a different question
   would be more useful, answer that one too. Specifically:

     - The wrapper writes records to ~/.dabbler/launch-log.jsonl.
       The file grows unbounded. Should a log-rotation hook be
       part of S3, or is unbounded growth tolerable for the
       set's expected scale (≤ a few launches per day per
       operator)?

     - The Copilot OTel parser maps tool.call AND tool.invoke
       to tool_call. Are these actually equivalent in real
       Copilot OTel, or does the conflation paper over a
       semantic difference (e.g., invoke = sync, call = async)?

     - Set 044 commitment 4 is "headless mode first; interactive
       TTY-passthrough deferred". The wrapper has no TTY mode
       at all (not even stubbed). Is the absence of any TTY
       stub correct, or should there be a placeholder for the
       follow-on?

     - The launch_id is a uuid4 in raw_ref. The joiner does
       not consume launch_id today (binding is by engine + cwd
       + time-window). Is launch_id worth carrying at all, or
       is it dead weight until a future spec needs it?

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(SET_DIR / "joiner-spec.md"),
        read_file(REPO_ROOT / "ai_router/dabbler_launch.py"),
        read_file(REPO_ROOT / "ai_router/joiner/__init__.py"),
        read_file(REPO_ROOT / "ai_router/joiner/schema.py"),
        read_file(REPO_ROOT / "ai_router/joiner/parsers.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_dabbler_launch.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_dabbler_launch_join_e2e.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_parsers.py"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-003-route-result.json"

    print(f"\n{'='*60}\n[Round A] sending to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=FOCUS_PROMPT,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE START ---\n{bundle}\n--- BUNDLE END ---",
        session_set="045-log-harvest-implementation",
        session_number=3,
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
        verdict_path = out_dir / "session-003.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

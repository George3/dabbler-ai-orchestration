"""Round B verification — Set 045 / S3 — narrow re-check on Round A fixes.

Round A returned REJECTED on two must-fix issues:

  1. harvest() candidate predicate used raw engine equality
     instead of normalize_engine; vendor variants
     ("claude-code" vs. "claude") would miss the join.

  2. harvest() emitted only session_start for bound natives
     instead of the full per-event stream per joiner-spec.md §4
     (HarvestRecord.from_native(launch, native_evt)). The bound
     native was also being re-emitted in the free-running loop,
     causing duplicate session_start records.

Round B bundles ONLY the changed files + the two new test
classes that pin the fixes, plus joiner-spec.md §4 for the spec
contract. The verifier is asked to confirm (a) the must-fix
items are addressed correctly and (b) the fixes don't introduce
new regressions.
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
Round B for Set 045 Session 3. The S3 deliverables (wrapper +
Copilot OTel hardening + harvest() wire-up + Layer-1 / Layer-2
tests) were reviewed in Round A by Gemini Pro. Round A returned
REJECTED on two specific must-fix issues:

  Issue 1: harvest() candidate predicate used raw engine equality
  (`ns.engine == launch.engine`) instead of normalize_engine, so
  vendor variants ("claude-code" on disk vs. "claude" in the
  launch record) would silently fail to bind.

  Issue 2: When a launch was bound to a native session, harvest()
  emitted only a single session_start record for that native
  (the spec §4 mandates the full per-event stream with launch
  context merged: set_slug + session_number + provider/model/
  effort threading). Bound natives were ALSO re-emitted in the
  free-running loop, producing a duplicate session_start.

Fix applied:

  - harvest()'s candidate predicate now uses
    `normalize_engine(ns.engine) == normalize_engine(launch.engine)`.

  - When `binding_state == "bound"`, harvest() calls
    `_native_events_for(bound_native)`. For Copilot, this
    delegates to `read_copilot_session_events()` (the S3
    hardened per-event parser) and yields a HarvestRecord per
    event. For Claude (per-event parser is the S4 deliverable
    per joiner-spec.md §8.1), it falls back to a single
    session_start projection.

  - Each native event is passed through `_merge_launch_context()`,
    which threads `set_slug`, `session_number`, and (when the
    native event doesn't have its own values) provider / model /
    effort onto the event. Existing native-event values win.

  - The free-running emission loop now skips natives that were
    bound to a launch (via a `bound_native_ids` set), so the
    session_start is no longer duplicated.

Three new tests pin the fixes:

  - test_launch_engine_claude_binds_to_native_engine_claude_code:
    monkey-patches scan_claude_logs to emit engine="claude-code",
    then asserts that a launch with engine="claude" still binds.

  - test_bound_copilot_emits_full_event_stream_with_launch_context:
    runs a wrapper launch and a synthetic Copilot session
    (session.start + tool.call + usage), asserts that the
    Copilot per-event stream is emitted with set_slug merged
    from the launch.

  - test_bound_native_is_not_re_emitted_in_freerunning_loop:
    asserts exactly one claude-native record per bound conv_id
    (no duplicate from the free-running loop).

Full pytest suite remains green at 773 passed, 1 skipped (was
770 before Round A fixes; +3 net tests, zero regressions).
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt asks you to re-verify a fix to issues
YOU flagged in Round A. The author has an obvious motivation to
declare the fixes complete. Read with extra scrutiny: did the
fix address the root cause, or did it just paper over the
symptom enough to pass the new tests? If the fix is correct,
say VERIFIED. If not, say REJECTED with specifics.

ROUND B — Narrow re-check of two must-fix issues from Round A.

Verification targets:

A. **Engine normalization fix (Issue 1).**

   1. Does the new candidate predicate in harvest() correctly
      apply normalize_engine to both sides of the comparison?

   2. Is normalize_engine the right canonicalization for this
      use case? (It strips ``-code`` and ``-cli`` suffixes and
      lowercases.) Could a real vendor variant slip through?
      E.g., "anthropic-claude" or "github-copilot" would NOT
      be normalized to the base name by the current
      implementation.

   3. Does the test test_launch_engine_claude_binds_to_native_engine_claude_code
      actually exercise the fix, or is it asserting a tautology?

B. **Bound-native event stream fix (Issue 2).**

   1. Does _native_events_for correctly dispatch by engine?
      Copilot → read_copilot_session_events (per-event); Claude
      → session_start fallback (per-event parser is S4 work).
      Is the engine-aware dispatch sound, or does it leave a
      gap (e.g., what happens for engine="codex" or
      engine="gemini")?

   2. Does _merge_launch_context correctly thread launch
      context (set_slug, session_number, effort, provider,
      model) onto the native event WITHOUT clobbering
      pre-existing native values? (The spec §4 implies the
      native event's own values win — a marker event might
      already carry its own set_slug.)

   3. Are the bound natives correctly suppressed from the
      free-running emission loop? The bound_native_ids set is
      keyed by (engine, conv_id). Is that the right key, or
      could a legitimate distinct session collide on
      conv_id-only (probably not — conv_ids are uuid-shaped —
      but worth confirming)?

   4. The S3 Claude branch falls back to a single session_start
      record because the per-event parser is S4 work. Is this
      a clean deferral (the operator gets per-event for
      Copilot today, session-only for Claude until S4 ships),
      or does it create a confusing asymmetry the Explorer
      will need to special-case?

C. **No new regressions.**

   1. The free-running native emission loop now has a new
      branch (skip if (engine, conv_id) in bound_native_ids).
      Could that branch incorrectly skip a session that should
      have been emitted free-running? (E.g., two launches
      bind to the same native — impossible since binding adds
      to bound_native_ids; but a malformed scenario?)

   2. The filter logic (workspace_cwd, since) interacts with
      the bound-native suppression. If a bound native fails
      the workspace_cwd filter but was added to
      bound_native_ids in an earlier iteration, the
      free-running loop would still skip it. Is that a
      problem in practice?

   3. The tests use monkey-patching to inject vendor variants
      (test_launch_engine_claude_binds_to_native_engine_claude_code
      replaces scan_claude_logs). Is the monkey-patch safe (no
      cross-test contamination from a `try/finally` block)?

D. **Verdict-shape question.**

   Round A REJECTED. Round B is asked to confirm whether the
   fixes are complete (VERIFIED) or whether new issues
   surfaced (REJECTED with new must-fix list). Please be
   strict: if the fix addresses the symptoms but not the root
   cause, or if a new must-fix issue surfaced during the
   change, return REJECTED.

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(SET_DIR / "joiner-spec.md"),
        read_file(REPO_ROOT / "ai_router/joiner/schema.py"),
        read_file(REPO_ROOT / "ai_router/joiner/parsers.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_dabbler_launch_join_e2e.py"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-003-round-b-route-result.json"

    print(f"\n{'='*60}\n[Round B] sending to gemini-pro...\n{'='*60}")
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
    text = (
        result_dict.get("response")
        or result_dict.get("text")
        or result_dict.get("content")
    )
    if isinstance(text, str):
        print(f"\n--- VERIFIER OUTPUT (ROUND B) ---\n{text}\n--- end ---")
        verdict_path = out_dir / "session-003-round-b.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

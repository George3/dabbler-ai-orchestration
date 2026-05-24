"""Round C verification — Set 045 / S3 — narrow re-check on Round B fixes.

Round B returned REJECTED on three issues:

  Issue 1: Two launches could both claim one native, duplicating the
  native's event stream and corrupting bypass-rate downstream.

  Issue 2: workspace_cwd / since filters were applied AFTER binding;
  a filtered-out launch could consume a native that should have
  appeared in the free-running loop.

  Issue 3: normalize_engine only handles ``-code`` / ``-cli`` suffixes;
  variants like ``anthropic-claude`` would miss the join.

Fixes applied:

  - Issue 1: candidates filter now excludes natives already in
    bound_native_ids; single-bind invariant enforced (1:1 binding).

  - Issue 2: cwd_filter and since filters moved to the TOP of the
    per-launch loop, BEFORE candidate matching. A filtered launch
    cannot bind to a native.

  - Issue 3: documented as a deferred follow-up in joiner-spec.md
    §9 row 5. The §3.1 contract is unchanged ("drop -code, -cli
    suffixes"); broadening it is a spec-level decision that
    requires its own audit pass, not an in-flight S3 widening.

Round C is asked to confirm Issues 1 and 2 are addressed correctly
and that the §9 deferral of Issue 3 is honest framing rather than
out-of-scope hiding.
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
Round C for Set 045 Session 3. Round B (this verifier's prior
pass) returned REJECTED on three issues — see SCRIPT DOCSTRING
for the precise framing. The fixes are now in place:

  Fix 1 (single-bind invariant). The harvest() candidate
  comprehension now excludes any native already in
  bound_native_ids. The first launch that matches a native
  claims it; subsequent launches see that native as already
  consumed.

  Fix 2 (filter ordering). The cwd_filter / since filters are
  applied BEFORE candidate matching. A filtered-out launch
  short-circuits with `continue` and never reaches the
  candidates list.

  Deferral 3 (normalize_engine breadth). A new row 5 added to
  joiner-spec.md §9 acknowledges that vendor variants outside
  the ``-code`` / ``-cli`` suffix pattern (e.g. ``anthropic-
  claude``) would miss the join. The §3.1 contract is the
  documented scope; expanding it requires a spec audit, not an
  in-flight S3 widening. The deferral cites Round-B
  verification as the source.

New tests:

  - test_two_launches_dont_both_claim_one_native: emits two
    launches in overlapping windows, one native in their join
    range. Asserts exactly one launch is bound, the other is
    unbound, and the native appears exactly once in the
    output.

  - test_filtered_launch_does_not_consume_native: launch in
    workspace A, native in workspace B, harvest filtered to
    workspace B. Asserts the launch is filtered out and the
    native still appears as free-running.

Full pytest suite: 775 passed, 1 skipped (was 773 entering
Round B; +2 net tests, zero regressions).
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt asks you to re-verify fixes you
flagged in Round B. The author has motivation to declare them
complete. Read with extra scrutiny.

ROUND C — Narrow re-check of three Round-B issues.

A. **Fix 1 — single-bind invariant.**

   1. The candidate comprehension now excludes
      ``(ns.engine, ns.conv_id) in bound_native_ids``. Does
      this correctly enforce 1:1 binding (first-launch-wins),
      or is there a corner case (e.g. two launches with
      identical launch_ts) where the ordering is
      nondeterministic?

   2. test_two_launches_dont_both_claim_one_native confirms
      the bound/unbound split. Does it actually exercise the
      fix, or could the test have passed by coincidence
      (e.g. ordering of launches in the launch log happens to
      match the test's assumption)?

B. **Fix 2 — filter ordering.**

   1. The cwd_filter / since filters are now applied at the
      top of the per-launch loop, BEFORE candidate matching.
      A filtered launch hits ``continue`` and never reaches
      bound_native_ids. Is the ordering correct, or is there
      a remaining path where a filter applied later could
      still mark a native as bound?

   2. test_filtered_launch_does_not_consume_native asserts
      the native appears free-running when the launch is
      filtered out. Is that the right assertion (the native
      should NOT be suppressed) — or should the test also
      assert no launches appear in the output?

C. **Deferral 3 — normalize_engine breadth.**

   The joiner-spec.md §9 follow-ups table grew a row 5
   acknowledging that ``normalize_engine`` only handles the
   ``-code`` / ``-cli`` suffix pattern documented in §3.1.
   Vendor variants outside that pattern (``anthropic-
   claude``, ``github-copilot``) would miss the join.

   1. Is the deferral framing honest, or does it hide a real
      blocker for S5 (the Explorer integration session)? Are
      there real-world variants the operator would encounter
      that the current scope misses?

   2. The §9 row's "Carry-forward" says "Follow-on once a
      real-world variant breaks a join — speculative variants
      don't justify expanding the §3.1 contract today."
      Is this the right posture, or should the alias-map
      land in S3 to avoid a discovery-cost-during-S5 hit?

D. **No new regressions.**

   1. The Round-B fixes touched the harvest() function. Did
      the changes introduce any new must-fix issues
      (algorithm drift, ordering bug, broken filter
      interaction)? Re-check the harvest() body holistically.

   2. The new candidate predicate uses a 4-condition AND. Is
      the order of conditions efficient (fast checks first)
      and correct, or is there a short-circuit-evaluation
      issue?

E. **Verdict shape.**

   Round B raised THREE issues. Round C should confirm
   Issues 1 and 2 are fixed and Issue 3's deferral is
   acceptable. If any of those judgments is wrong, REJECT
   with the specific issue. If new issues surface during
   the re-check, REJECT with those — but please distinguish
   "regression introduced by the Round B fix" from "issue
   that existed before but wasn't flagged in A or B."

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(SET_DIR / "joiner-spec.md"),
        read_file(REPO_ROOT / "ai_router/joiner/schema.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_dabbler_launch_join_e2e.py"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-003-round-c-route-result.json"

    print(f"\n{'='*60}\n[Round C] sending to gemini-pro...\n{'='*60}")
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
        print(f"\n--- VERIFIER OUTPUT (ROUND C) ---\n{text}\n--- end ---")
        verdict_path = out_dir / "session-003-round-c.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

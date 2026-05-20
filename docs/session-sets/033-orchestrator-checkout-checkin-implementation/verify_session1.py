"""Session 1 verification driver — Set 033 (implementation cycle).

Round A bundles the artifacts produced by Session 1:

  - ai_router/start_session.py — H3+H4 conflict gate, --force flag,
    writer-log audit append.
  - ai_router/session_state.py (register_session_start function only)
    — same-holder re-attach preservation of checkedOutAt; fresh /
    force-override rewrite logic.
  - ai_router/tests/test_checkout_writer.py — the 7 unit tests
    covering the six branches spec Step 6 enumerates.
  - docs/session-state-schema.md (Check-out / check-in section +
    worked examples) — schema delta + invariant codification.

Ground truth bundled alongside:
  - The 6 locked verdicts (§9 of proposal-addendum.md) — the audit
    outcome the implementation must trace to.
  - Set 033 spec.md Session 1 — the contract this session ships.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
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
PROPOSAL_DIR = (
    REPO_ROOT / "docs" / "proposals" / "2026-05-19-orchestrator-tracking-architecture"
)


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def read_section(
    path: Path, start_marker: str, end_marker: str | None = None
) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        return f"=== FILE: {rel} (SECTION MISSING: {start_marker!r}) ==="
    if end_marker is None:
        section = text[start:]
    else:
        end = text.find(end_marker, start + len(start_marker))
        section = text[start:end] if end > 0 else text[start:]
    return f"=== FILE: {rel} (from {start_marker!r}) ===\n{section}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 033 implements the orchestrator check-out / check-in migration
from the six verdicts the Set 032 audit locked. Session 1 ships the
writer side:

  - Schema delta on session-state.json: under `orchestrator`, two
    new nested ISO timestamp fields `checkedOutAt` + `lastActivityAt`.
    The block is null when top-level status != "in-progress" (the
    OQ1 invariant). The block is the canonical check-out record
    (per H2; the per-set `.dabbler/orchestrator.json` marker is
    retired in Session 2).
  - register_session_start(): same-holder re-attach (engine+provider
    composite, per H4) preserves checkedOutAt and bumps
    lastActivityAt; fresh check-out OR force-override handoff sets
    both to `now`.
  - start_session CLI: H3 hard-coordination gate. When the existing
    orchestrator block names a different (engine, provider) than
    the caller, REFUSE unless --force is set. Refusal exit code 4
    (new). Refusal error must name (a) the holder identity AND
    (b) the two release paths (--force and "Release Check-Out"
    Command Palette action).
  - --force flag: appends a force-override entry to
    ~/.dabbler/orchestrator-writer.log (best-effort; log failure
    does not block the override) and proceeds.
  - 7 unit tests covering the six branches enumerated in the spec.

Sessions 2-6 are out of scope for THIS verification. The bundle
includes only Session 1 deliverables.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 1 implementation faithfulness, contract coverage,
and unit-test adequacy.

You are Gemini Pro, asked to verify that Session 1 of Set 033 ships
the writer side of the check-out / check-in migration consistent
with the six locked verdicts.

Verify:

A. **Verdict implementation in Session 1.** For each verdict
   relevant to Session 1 (H1 writer authority, H3 hard
   coordination, H4 identity predicate, OQ1 field merge),
   check that the bundled code implements it correctly.

   1. H4 — identity is the `engine + provider` composite.
      Confirm:
      - register_session_start's same-holder predicate compares
        engine AND provider (not model, not effort).
      - The CLI's H3 gate uses the same predicate.
      - Tests cover "model+effort change does NOT reset
        checkedOutAt" (model is mutable in place).
      - Tests cover same-holder reattach AND different-holder
        refusal.

   2. H3 — hard coordination + named release paths.
      Confirm:
      - CLI refuses different-holder writes with a non-zero exit
        and does NOT mutate state.
      - The refusal MESSAGE contains BOTH the current holder
        identity (engine + provider, both visible) AND the literal
        strings `--force` AND `Release Check-Out`.
      - --force overrides the H3 refusal but NOT the other
        boundary checks (in-flight, closed-session re-open,
        skip-ahead).
      - The H3 check runs AFTER the existing boundary checks, so
        the more-specific "still in flight" / "already closed" /
        "skip-ahead" errors surface first.

   3. OQ1 — field merge with checkedOutAt + lastActivityAt.
      Confirm:
      - Fresh check-out: checkedOutAt == lastActivityAt == now.
      - Same-holder re-attach: checkedOutAt preserved,
        lastActivityAt bumped to now.
      - Force-override handoff: checkedOutAt rewritten to now
        (new authority), lastActivityAt mirrors it.
      - Tolerated read: prior orchestrator block without
        checkedOutAt is read without error; next same-holder
        write populates the field.

   4. H1 — writer authority. THIS session's part: the writer is
      authoritative; hooks (Sessions 2-3) will become invokers.
      Confirm Session 1's writer is self-contained — it does not
      delegate the schema invariants to hook callers.

B. **Unit-test coverage of the six branches spec Step 6 lists.**
   The spec enumerates: (a) fresh = (checkedOutAt, lastActivityAt);
   (b) same-holder reattach bumps only lastActivityAt; (c)
   different-holder refusal returns non-zero + no mutation; (d)
   refusal message contains both the holder identity AND both
   release paths; (e) --force writes through + appends to writer
   log; (f) tolerated read of an in-flight set with no
   checkedOutAt.

   For each branch, point to the test function that covers it.
   Flag any branch not covered or weakly covered.

C. **Schema-doc consistency.** docs/session-state-schema.md was
   updated with a Check-out / check-in section and worked-example
   adjustments. Verify:
   - The +2 nested fields are documented under `orchestrator`.
   - The H4 identity rule is stated (engine + provider, NOT
     including model).
   - The H3 refusal contract is documented (holder + two release
     paths).
   - The block-null-when-not-in-progress invariant is stated.
   - The migration tolerance for pre-Set-033 in-flight files is
     documented.

D. **Boundary refusal ordering.** Confirm the CLI's check order is:
   (1) directory exists → (2) session-number sane → (3) in-flight
   refusal → (4) closed-session re-open refusal → (5) skip-ahead
   refusal → (6) NEW H3 check-out conflict → (7) writer call.

   Flag any sequencing that would surface H3 conflict for a case
   the existing boundary checks should catch first.

E. **What's missing or risky.** Any edge case the implementation
   omits that would bite a real run?
   - Empty/null provider on the caller AND empty/null provider on
     the prior block — does the equality still work? (Both None →
     should equal True.)
   - Writer log directory missing or unwritable — does the
     override still proceed?
   - register_session_start called with no prior state file at
     all (a totally fresh set) — does the H3 check no-op
     correctly? (No prior block ⇒ no conflict ⇒ proceed.)
   - Force-override + same-holder (force on an existing
     same-engine call) — does it still preserve checkedOutAt,
     OR does it rewrite it because of the force flag?
     (Implementation-defined; verify the current behavior is
     sensible. Reading the CLI: force only matters when
     same_holder is False, so the writer's same-holder branch
     still runs ⇒ checkedOutAt preserved. Confirm this is
     what the code does.)

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits. Session 1 is the load-bearing writer
foundation — Sessions 2-6 all depend on its contract — so a
must-fix here will block downstream work.
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverables
        read_file(REPO_ROOT / "ai_router" / "start_session.py"),
        read_section(
            REPO_ROOT / "ai_router" / "session_state.py",
            "def register_session_start(",
            "def _propagate_total_sessions(",
        ),
        read_file(SET_DIR.parent.parent.parent / "ai_router" / "tests" / "test_checkout_writer.py"),
        # Schema delta
        read_section(
            REPO_ROOT / "docs" / "session-state-schema.md",
            "### Check-out / check-in (Set 033)",
            "### Dual-write legacy fields",
        ),
        # Ground truth: the 6 locked verdicts
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # Ground truth: Session 1 spec
        read_section(
            SET_DIR / "spec.md",
            "## Session 1 of 6:",
            "## Session 2 of 6:",
        ),
    ]
    return "\n\n".join(parts)


def run_round(label: str, code_block: str, focus_prompt: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{label}] sending verification call to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=focus_prompt,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE ---\n{code_block}",
        session_set="033-orchestrator-checkout-checkin-implementation",
        session_number=1,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, "
        f"out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


def main() -> None:
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session1.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-1-result.json",
        )
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated code.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round(
            "Round B",
            bundle,
            focus,
            out_dir / "round-b-session-1-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

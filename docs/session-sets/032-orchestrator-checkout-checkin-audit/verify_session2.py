"""Session 2 verification driver — Set 032 (audit cycle).

Round A bundles the documentation artifacts produced by Session 2:
the drafted Set 033 spec.md (primary deliverable), the spec
cross-review verdict from Gemini Pro (ground truth for must-fix
application), the audit-input README updates, the Set 032 change-
log, and proposal-addendum §9 (the 6 locked verdicts that drive
the spec — ground truth for traceability check).

This is a DOC-ONLY session. Verification asks:

  1. Does the Set 033 spec faithfully translate ALL 6 locked
     verdicts (H1, H2, H3, H4, OQ1, OQ2) into concrete per-session
     steps?
  2. Were the two cross-review suggestions actually applied to the
     spec (S6 idempotence + R7 performance risk)?
  3. Is per-session sequencing internally consistent (S2 depends
     on S1's writer, S4 depends on S1-S3's visible behaviors,
     etc.)?
  4. Are the README + change-log honest about what shipped?

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
SET_033_DIR = (
    REPO_ROOT
    / "docs"
    / "session-sets"
    / "033-orchestrator-checkout-checkin-implementation"
)


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def read_section(path: Path, start_marker: str, end_marker: str | None = None) -> str:
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
Set 032 is a 2-session AUDIT cycle for the orchestrator check-out /
check-in migration. Session 1 (CLOSED 2026-05-19) routed an audit
packet through Gemini Pro + GPT-5.4 and locked six verdicts:

  H1 — Router-only writes; hooks become invokers.
  H2 — session-state.json canonical; .dabbler/orchestrator.json
       RETIRED.
  H3 — Hard coordination at write time + explicit operator override
       safety valve (--force, Release Check-Out command). Refusal
       error MUST name the holder AND the two release paths.
  H4 — Holder identity = engine + provider composite (model + effort
       are mutable holder-state).
  OQ1 — Merge into existing orchestrator block; +2 fields
       (checkedOutAt, lastActivityAt).
  OQ2 — work_checked_out / work_checked_in are ALIASES for
       work_started / closeout_succeeded; no ledger schema change.

Session 2 (THIS session) drafted the Set 033 implementation spec.md
from those verdicts, cross-reviewed it via Gemini Pro
(approve-with-suggestions; two suggestions applied: S6 idempotence
+ R7 performance risk), updated the audit-input README to flip from
"audit resolved" to "audit-then-spec cycle complete", and authored
the Set 032 change-log.

Deliverables for verification:
  - docs/session-sets/033-orchestrator-checkout-checkin-implementation/spec.md
    (replaces the placeholder; the primary deliverable)
  - docs/session-sets/033-orchestrator-checkout-checkin-implementation/session-state.json
    (title alignment)
  - docs/proposals/2026-05-19-orchestrator-tracking-architecture/README.md
    (status-header + table flips)
  - docs/session-sets/032-orchestrator-checkout-checkin-audit/change-log.md
    (Set 032 final-session aggregation)

Ground truth files:
  - docs/proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md
    §9 (the 6 locked verdicts)
  - docs/session-sets/032-orchestrator-checkout-checkin-audit/spec-review-gemini-pro.txt
    (Gemini's approve-with-suggestions verdict on the drafted spec)
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 2 documentation faithfulness, traceability, and
sequencing consistency.

You are Gemini Pro, asked to verify Session 2's primary deliverable
(the Set 033 implementation spec.md) plus the supporting artifacts.

Verify:

A. **Verdict traceability into the Set 033 spec.** For each of H1,
   H2, H3, H4, OQ1, OQ2, check:
   1. Is the verdict implemented in at least one concrete per-session
      step in the spec? Flag any verdict without a clear landing
      point.
   2. Does the spec correctly preserve nuance from the addendum §9
      verdict? Specifically:
      - H1: hooks INVOKE the writer; do not write directly. Failure
        surfaces as toast, not silent retry. (Captured in S3?)
      - H3: refusal error MUST name both (a) the holder identity AND
        (b) the two release paths (--force, Release Check-Out).
        (Captured in S1's writer logic AND S4's Playwright assertion?)
      - H4: identity is `engine + provider` composite; `model` and
        `effort` are mutable. (Captured in S1's equality predicate
        AND S5's polling identity check?)
      - OQ1: `lastActivityAt` bumped on same-orchestrator re-attach
        + effort-change. `orchestrator` is null when status !=
        in-progress. (Captured in S1?)
      - OQ2: ALIASES only; no ledger schema change. (Captured in S6
        as doc-only updates?)

B. **Two cross-review suggestions applied.** The Gemini Pro spec
   cross-review verdict (spec-review-gemini-pro.txt) called out
   two non-blocking suggestions:
   1. S6 Step 1: invoking close_session on a set whose orchestrator
      block is already null is a successful no-op.
   2. Risks: add R7 for listInProgressSets() performance in repos
      with many session sets, with a benchmark note.
   Verify BOTH are present in the spec. Flag if either is missing
   or the wording weakens the original suggestion.

C. **Per-session sequencing consistency.** The spec's per-session
   split is S1 writer → S2 reader → S3 UI → S4 tests → S5 queueing
   → S6 close-out + docs + release. Cross-check:
   1. Does each session's "Touches" list include only files that
      are realistic to modify given the steps?
   2. Does S2 depend only on S1-completed behavior? (S2's
      listInProgressSets refactor depends on the canonical
      session-state.json authority that S1 establishes.)
   3. Does S3 depend on S2's reader refactor being landed? (S3's
      Command Palette "Release Check-Out" + hook refactor presume
      the reader already consumes the canonical authority.)
   4. Does S4 cover the visible behaviors S1-S3 produced?
      Specifically: multi-set rendering (from S2), refusal error
      content per H3 (from S1), force-override behavior + writer
      log (from S1), Release Check-Out command (from S3), same-
      orchestrator re-attach (from S1).
   5. Does S5's queueing logic depend on S1's structured refusal
      error contract AND S3's hook refactor?
   6. Does S6 close out everything (cross-tier check-in, all three
      canonical doc updates, cross-repo notification, PyPI +
      Marketplace release)?

D. **Honesty in the supporting artifacts.**
   1. The audit-input README's status header now reads
      "audit-then-spec cycle complete" (or similar). Does it
      accurately describe Session 2's outcome (spec authored +
      cross-reviewed) rather than implying Set 033 has started?
   2. The change-log.md correctly captures Session 1 + Session 2's
      work, including the H4 mid-audit surfacing and the Gemini
      approve-with-suggestions verdict. Any overclaim or omission?
   3. The Set 033 session-state.json titles match the authored
      spec's per-session goals (no leftover "(placeholder)" text)?

E. **What's missing.** Is there any verdict-implied behavior, edge
   case, or cross-tier consideration the spec omits that would
   bite Set 033's implementer? Examples to consider:
   - Migration of existing in-flight session-state.json files that
     pre-date the +2 nested fields.
   - Behavior when the same orchestrator calls start_session twice
     for the same session number (idempotence on the writer side,
     not just close-out).
   - The relationship between Set 033's S2 marker deletion and
     consumer-repo session sets that still have .dabbler/orchestrator.json
     files (handled in S6's cross-repo notification, or earlier?).

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases when flagging issues; skip stylistic
nits. Focus on: does the spec faithfully translate the 6 verdicts
into an implementable plan, with the cross-review suggestions
applied, and are the README + change-log honest about what shipped?
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverable
        read_file(SET_033_DIR / "spec.md"),
        # Title alignment
        read_file(SET_033_DIR / "session-state.json"),
        # Audit-input README updates
        read_file(PROPOSAL_DIR / "README.md"),
        # Final-session change-log
        read_file(SET_DIR / "change-log.md"),
        # Ground truth: 6 locked verdicts
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # Ground truth: spec cross-review verdict
        read_file(SET_DIR / "spec-review-gemini-pro.txt"),
    ]
    return "\n\n".join(parts)


def run_round(label: str, code_block: str, focus_prompt: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{label}] sending verification call to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=focus_prompt,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE ---\n{code_block}",
        session_set="032-orchestrator-checkout-checkin-audit",
        session_number=2,
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


def main() -> None:
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session2.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round("Round A", bundle, FOCUS_PROMPT, out_dir / "round-a-session-2-result.json")
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated documentation.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round("Round B", bundle, focus, out_dir / "round-b-session-2-result.json")
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

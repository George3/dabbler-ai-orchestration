"""Session 1 verification driver — Set 032 (audit cycle).

Round A bundles the documentation artifacts that capture the locked
verdicts: the audit-resolution-request.md packet, the H4 follow-up
packet, the new addendum §9 "Audit resolution" section, and the
README "Audit resolution — Set 032 Session 1" section.

This is a DOC-ONLY session. Verification asks: do the four
artifacts faithfully and internally-consistently capture the six
locked verdicts (H1, H2, H3, H4, OQ1, OQ2)? Are there contradictions
between the addendum and the README? Did anything in the engine
responses get lost in synthesis?

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


def read_section(path: Path, start_marker: str, end_marker: str | None = None) -> str:
    """Read a labeled section from a Markdown file (start_marker to
    end_marker exclusive; end_marker=None reads to EOF)."""
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
Set 032 Session 1 is the audit-resolution leg of the audit-then-spec
cycle for the orchestrator check-out / check-in migration. The
pre-audit (Set 029 Session 6) produced three GPT-5.4 round-2 Highs
(H1, H2, H3) and two open questions (OQ1, OQ2). Session 1 routed an
audit-resolution packet through Gemini Pro + GPT-5.4 (manual paste
fallback for GPT due to 429, matching the pre-audit pattern). Both
engines confirmed all five originals. GPT-5.4 raised a sixth item
H4 (holder identity key) which Gemini Pro refined; operator
adjudicated 2026-05-19 to lock H4 = `engine + provider` composite.

The six locked verdicts driving Set 033's implementation spec:

  H1 — Router-only writes; hooks become invokers.
  H2 — session-state.json canonical; .dabbler/orchestrator.json
       RETIRED.
  H3 — Hard coordination at write time + explicit operator override
       safety valve (--force, Release Check-Out command, conflict
       prompt).
  H4 — Holder identity = engine + provider composite (model + effort
       are mutable holder-state).
  OQ1 — Merge into existing orchestrator block; +2 fields
       (checkedOutAt, lastActivityAt).
  OQ2 — work_checked_out / work_checked_in are ALIASES for
       work_started / closeout_succeeded; no ledger schema change.

Deliverables for verification:
  - audit-resolution-request.md (the 5-item packet sent to both
    engines)
  - audit-resolution-h4-request.md (the H4 follow-up packet sent to
    Gemini)
  - proposal-addendum.md §9 (new "Audit resolution" section)
  - README.md "Audit resolution — Set 032 Session 1" section

The engine responses live at:
  - audit-resolution-gemini-pro.txt (5/5 confirmed)
  - audit-resolution-gpt-5-4.txt (5/5 confirmed + H4 raised)
  - audit-resolution-h4-gemini-pro.txt (H4 refined to engine +
    provider)
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 1 documentation faithfulness + internal
consistency.

You are Gemini Pro, asked to verify that the four documentation
artifacts in the bundle below faithfully and consistently capture
the six locked verdicts (H1, H2, H3, H4, OQ1, OQ2). The engine
responses (yours + GPT-5.4's) are appended at the bottom of the
bundle as ground truth — what's documented in the addendum and
README must match what you and GPT actually said.

Verify:

A. **Faithful capture of each locked verdict.** For each of H1, H2,
   H3, H4, OQ1, OQ2, check:
   1. Does the addendum §9 verdict match the substance of what BOTH
      engines actually said in the response files? Flag any case
      where the addendum overstates consensus (e.g., claims "both
      engines confirmed" when one only permitted).
   2. Does the README "Audit resolution" section match the
      addendum §9? Any wording drift that could read as a
      different verdict?
   3. For H4 specifically: does the addendum correctly note that
      GPT-5.4 PERMITTED any stable subset (didn't pick) and Gemini
      Pro REFINED to engine + provider, with the operator
      adjudicating the composite?

B. **Internal consistency.** Cross-check:
   1. H1 says hooks become invokers, never peer writers. Does the
      addendum (or README) anywhere else imply hooks write the
      lifecycle field directly?
   2. H2 says the .dabbler/orchestrator.json marker file is
      RETIRED. Does the addendum or README anywhere imply it
      remains as derived UI cache or another role? (It shouldn't —
      the cache option was explicitly rejected.)
   3. H3 says HARD coordination at write time. Does any later
      sentence call check-out "purely advisory" or imply
      writes succeed unconditionally? (Earlier sections of the
      addendum DID say "purely advisory" — those should be marked
      retracted.)
   4. H4's `engine + provider` rule. Does the addendum / README
      anywhere else say identity is `engine`-only or include
      `model` / `effort` in the identity comparison?
   5. OQ1's merge into existing orchestrator block. Any mention
      anywhere of separate `checkedOut` / `checkedOutBy` top-level
      fields (rejected design)?
   6. OQ2's aliases-only verdict. Any sentence that implies new
      ledger event types or a schema change to
      session-events.jsonl?

C. **Edge cases the audit packet acknowledged.** The audit-
   resolution-request.md and the H4 follow-up acknowledged some
   edge cases:
   1. H1: non-blocking hook invocation; failure surfaces as
      user-visible toast, not silent retry. Captured in addendum
      §9?
   2. H3: refusal returns a clear error naming (a) the current
      holder and (b) the two release paths (--force or Release
      Check-Out). Captured?
   3. H4: future-collision case (e.g., two distinct
      claude-via-X providers both having `engine: claude`). The
      packet noted the rule extends to `engine + provider` if/when
      that lands. With the composite verdict locked, this
      automatically covers the case — but is the addendum's
      framing accurate?
   4. OQ1: `lastActivityAt` is bumped on same-orchestrator
      re-attach AND on `/think*` effort-change events. Captured?

D. **What's missing.** Does the documentation omit anything from
   the engine responses that would be load-bearing for Set 033's
   spec author?
   - GPT-5.4's H4 caveat ("Set 033 must define holder comparison
     explicitly once mutable fields continue to live in this
     block") — is the addendum's H4 verdict explicit enough that
     a downstream spec author can implement this correctly?
   - GPT-5.4's H1 nuance: "Non-blocking invocation is fine; silent
     retry or write-behind logic is not." — captured?
   - Either engine's overall recommendation paragraphs — anything
     load-bearing that didn't make it into the synthesis?

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have
    notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases when flagging issues; skip stylistic
nits. Focus on: does what's documented match what was decided,
without overstating consensus and without losing the engines'
nuance.
""".strip()


def _bundle() -> str:
    parts = [
        # The packets sent to the engines
        read_file(PROPOSAL_DIR / "audit-resolution-request.md"),
        read_file(PROPOSAL_DIR / "audit-resolution-h4-request.md"),
        # The new "resolved" framing in addendum
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # The README's new resolved section
        read_section(
            PROPOSAL_DIR / "README.md",
            "## Audit resolution — Set 032 Session 1 (2026-05-19)",
            "## Cost record",
        ),
        # Ground truth: engine responses
        read_file(PROPOSAL_DIR / "audit-resolution-gemini-pro.txt"),
        read_file(PROPOSAL_DIR / "audit-resolution-gpt-5-4.txt"),
        read_file(PROPOSAL_DIR / "audit-resolution-h4-gemini-pro.txt"),
    ]
    return "\n\n".join(parts)


def run_round(label: str, code_block: str, focus_prompt: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{label}] sending verification call to gemini-pro...\n{'='*60}")
    # Force gemini-pro per Set 032 spec routing notes; route() picks
    # gpt-5-4 from this bundle's complexity score and that provider
    # has been 429ing for the audit packet today.
    result = ai_router.query(
        model="gemini-pro",
        content=focus_prompt,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE ---\n{code_block}",
        session_set="032-orchestrator-checkout-checkin-audit",
        session_number=1,
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
        print("Usage: python verify_session1.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round("Round A", bundle, FOCUS_PROMPT, out_dir / "round-a-session-1-result.json")
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated documentation.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round("Round B", bundle, focus, out_dir / "round-b-session-1-result.json")
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

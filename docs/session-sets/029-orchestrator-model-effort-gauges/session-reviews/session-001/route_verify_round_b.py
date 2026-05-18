"""Round B verification — Set 029 Session 1.

Round A (route_verify.py / verify-result.json) returned REJECTED
with a punch list of Bucket 1 doc-accuracy drift + Bucket 2 design
refinements. The Bucket 2 items were routed through a cross-engine
consensus call (route_consensus.py) and both gpt-5-4 + gemini-pro
accepted the proposed direction (gpt-5-4 added five tightening
modifications, all absorbed). Bucket 1 fixes were applied directly.

Round B sends the SAME bundle as Round A back to gpt-5-4 and asks:
for each Round-A must-fix item, is it addressed in the updated
docs? Are any new issues surfaced? Per memory
feedback_verifier_spiral_recruit_codex, if Round B raises NEW
issues vs. confirming prior fixes, stop and escalate.

Per memory feedback_ai_router_route_result_handling, the RouteResult
is dumped to JSON before any field access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


ROUND_B_PROMPT_HEADER = """\
# Round B verification — Set 029 Session 1 (orchestrator model & effort indicator gauges)

## Context

Round A (your previous verification call on this synthesis) returned
**REJECTED** with concrete must-fix items spanning two buckets:

**Bucket 1 — doc-accuracy drift fixes (no design judgment):**

1. Audit-summary "Both reviewers agreed" wording for Q1 and
   "accepts fallback dominance" for Q2/Q3/Q4 overstated Gemini's
   participation. Should reword as GPT-explicit / Gemini-silent.
2. Audit-summary schema bullet referred to `model.signalKind` but
   no `model` object exists in v2 — top-level `signalKind` applies
   to the model signal.
3. Spec R2 still talked about Stop-hook payload drift even though
   Stop was rejected. Should reference SessionStart / UserPromptSubmit.
4. Spec routing notes + total cost still assumed router-based S1
   audit. Reality is $0.00 manual paste-and-collect; waiver should
   be durably documented in spec.md.
5. Audit-summary single-quickpick vs spec multi-step quickpick
   inconsistency. Pick one and align both docs.

**Bucket 2 — design refinements (each routed through cross-engine
consensus call, both engines accepted the direction):**

1. Multi-writer precedence policy (Q7 #1 — only true architectural
   gap). Policy: `current` > `manual` > `last-observed` >
   `configured-default`; writers read-check-rewrite with re-read
   immediately before atomic rename to close the TOCTOU race.
   Manual-override has force-override escape hatch.
2. `configured-default` vs stale visual collision. Stripes now
   stale-only; `configured-default` uses dashed rim + "DEFAULT"
   pill badge.
3. `last-observed` strengthened: hollow rim + filled needle +
   clock-icon overlay + time-elapsed sublabel.
4. Windows retry ceiling bumped from 3 attempts / 600ms to 5
   attempts (initial + 4 retries) / 50/200/600/1200ms / ~2050ms.
5. Initial-size limitation documented explicitly (container height
   cannot be guaranteed; drag divider to reset; content scrollable
   if compressed).
6. `confidence` field operationalized: Claude hook helper emits
   `confidence: "low"` + `model: "unknown"` on missing/null/
   unparseable payload; tooltip surfaces the reason.
7. `/clear`-vs-`SessionStart` dual-condition verification added to
   Session 2 step 5; **R7** added to Risks; clobber gated on BOTH
   `/clear` firing SessionStart AND resetting effort semantically.

## What you're being asked in Round B

For each Round-A must-fix item above, verify the fix is present in
the updated artifacts inlined below. Specifically:

- **Bucket 1 #1:** check `audit-summary.md` convergence table +
  Q1 reasoning + post-audit-verification note.
- **Bucket 1 #2:** check `audit-summary.md` "Changes from the
  original proposal" bullets.
- **Bucket 1 #3:** check `spec.md` R2.
- **Bucket 1 #4:** check `spec.md` "Routing notes" + "Total
  estimated cost" + Session 1 step 2 (waiver).
- **Bucket 1 #5:** check `audit-summary.md` "Manual-override
  quickpick UX" + `spec.md` Session 3 step 4.
- **Bucket 2 #1:** check `audit-summary.md` "Multi-writer
  precedence" + `spec.md` R4 + Session 2 step 5 + Session 3 step 1
  (Codex writer reuse note).
- **Bucket 2 #2:** check `audit-summary.md` "Visual treatment by
  signalKind" + `spec.md` Session 2 step 2 + Session 3 step 6
  (Playwright reflects no-stripes-for-configured-default).
- **Bucket 2 #3:** check `audit-summary.md` visual matrix + Q1
  reasoning + `spec.md` D6 footnote + Session 2 step 2.
- **Bucket 2 #4:** check `audit-summary.md` S5 mitigation +
  `spec.md` R5 + Session 2 step 5.
- **Bucket 2 #5:** check `audit-summary.md` S3 mitigation + `spec.md`
  Session 2 step 9 CHANGELOG bullets.
- **Bucket 2 #6:** check `audit-summary.md` "Changes from the
  original proposal" confidence bullet + `spec.md` Session 2 step 5.
- **Bucket 2 #7:** check `spec.md` D6 footnote + Session 2 step 5
  pre-implementation verification + R7.

Format response as:

```
B1-1: ADDRESSED | PARTIAL (…) | NOT ADDRESSED (…)
B1-2: …
…
B2-7: …
```

Then a final verdict line:

```
VERDICT: VERIFIED | REJECTED (<bulleted new issues>)
```

VERIFIED if all 12 items are addressed and no NEW must-fix issues
surface. REJECTED if any item remains or new issues appear. Cite
specific line numbers for any remaining issue; skip stylistic nits.
"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dump(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    return {
        "content": getattr(result, "content", None),
        "model_name": getattr(result, "model_name", None),
        "input_tokens": getattr(result, "input_tokens", None),
        "output_tokens": getattr(result, "output_tokens", None),
        "cost_usd": getattr(result, "cost_usd", None),
        "total_cost_usd": getattr(result, "total_cost_usd", None),
        "elapsed_seconds": getattr(result, "elapsed_seconds", None),
    }


def main() -> int:
    audit_summary = _read(
        REPO_ROOT
        / "docs"
        / "proposals"
        / "2026-05-17-model-effort-gauges-design-audit"
        / "audit-summary.md"
    )
    spec_text = _read(
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )

    full_content = (
        ROUND_B_PROMPT_HEADER
        + "\n\n---\n\n## Doc 1: audit-summary.md (updated)\n\n"
        + audit_summary
        + "\n\n---\n\n## Doc 2: spec.md (updated)\n\n"
        + spec_text
    )

    rendered_path = HERE / "prompt-round-b.rendered.md"
    rendered_path.write_text(full_content, encoding="utf-8")
    print(f"rendered prompt size: {len(full_content):,} chars")

    result = ai_router.query(
        model="gpt-5-4",
        content=full_content,
        task_type="session-verification",
        session_set=str(
            REPO_ROOT
            / "docs"
            / "session-sets"
            / "029-orchestrator-model-effort-gauges"
        ),
        session_number=1,
    )
    dumped = _dump(result)
    out_path = HERE / "verify-result-round-b.json"
    out_path.write_text(
        json.dumps(dumped, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    cost = dumped.get("total_cost_usd") or dumped.get("cost_usd")
    print(f"verifier model: {dumped.get('model_name')}")
    print(f"cost: ${cost}")
    print(f"input tokens:  {dumped.get('input_tokens')}")
    print(f"output tokens: {dumped.get('output_tokens')}")
    print(f"dumped to: {out_path}")
    text = dumped.get("content") or dumped.get("response") or dumped.get("text")
    if isinstance(text, str):
        print(f"\n--- ROUND B OUTPUT ---\n{text}\n--- end ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())

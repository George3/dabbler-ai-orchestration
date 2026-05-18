"""Round C verification — Set 029 Session 1.

Round B confirmed all 12 Round-A must-fix items addressed, then
raised ONE new issue: spec.md "Goal state" section (lines ~67-92)
still contained pre-audit wording (1h stale threshold, install CTA
on stale, Claude=Stop hook). The Goal-state region was not in
Round A's verification bundle, so this drift was uncovered for the
first time in Round B.

Round C re-bundles the full spec.md (so the Goal state IS included)
and asks: is the Round-B new issue addressed, and is any further
pre-audit drift visible anywhere else in the doc? Per memory
feedback_verifier_spiral_recruit_codex, if Round C raises another
NEW issue beyond the Round-B Goal-state fix, that's a spiral signal
and the right move is to escalate to an external assistant rather
than route a Round D.

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


ROUND_C_PROMPT_HEADER = """\
# Round C verification — Set 029 Session 1

## What changed since Round B

Round B returned VERDICT: REJECTED with one specific new issue
beyond the 12 Round-A must-fixes (which were all marked ADDRESSED):

> `spec.md` Goal state still contains pre-audit behavior that
> contradicts the locked design: it says stale is `>1h` and shows
> the install CTA when stale, and it still says Claude uses a `Stop`
> hook installer (`spec.md:85-92`). This conflicts with the updated
> Q5/Q6/D8 decisions (8h stale threshold, stale ≠ no-signal CTA,
> Claude uses `SessionStart`, Gemini/Copilot are manual-only, Codex
> is watcher-based).

The fix has been applied to `spec.md` "Goal state" section:
- Stale threshold changed from `>1h` to `>stalenessMaxSec` (default
  8h) per Q6.
- "No signal — install hook" CTA now fires only on **missing**
  marker file, not on stale; stale gets the diagonal-stripe overlay
  per audit-locked Q6.
- Installer description rewritten per D8: Claude=SessionStart;
  Codex=auto via config.toml watcher (no installer); Gemini/Copilot=
  manual-only command surfacing manual-override quickpick; universal
  manual-override quickpick as fallback.

## Round C ask

The full updated `spec.md` is inlined below. Specifically answer:

1. Is the Round-B Goal-state issue ADDRESSED in the updated spec.md?
2. Does any OTHER section of spec.md still contain pre-audit drift
   (any other reference to "Stop hook" outside of the audit
   acknowledgment of why Stop was rejected; any other 1h stale
   threshold; any other place where stale and missing are conflated;
   any contradiction with the locked D1-D10 + Q1-Q6 decisions)?

Be precise — cite line numbers for anything still drifted. Skip
stylistic nits.

Format response as:

```
Round-B-Goal-state: ADDRESSED | PARTIAL (…) | NOT ADDRESSED (…)
Additional-drift: NONE | <bulleted list with line numbers>
VERDICT: VERIFIED | REJECTED (<smallest concrete change to get to VERIFIED>)
```
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
    spec_text = _read(
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "029-orchestrator-model-effort-gauges"
        / "spec.md"
    )
    full_content = (
        ROUND_C_PROMPT_HEADER
        + "\n\n---\n\n## Doc: spec.md (post-Round-B fix)\n\n"
        + spec_text
    )

    rendered_path = HERE / "prompt-round-c.rendered.md"
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
    out_path = HERE / "verify-result-round-c.json"
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
        try:
            print(f"\n--- ROUND C OUTPUT ---\n{text}\n--- end ---")
        except UnicodeEncodeError:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(f"\n--- ROUND C OUTPUT ---\n{text}\n--- end ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())

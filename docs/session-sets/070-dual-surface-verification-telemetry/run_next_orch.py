"""Set 070 S2 -- route the next-orchestrator recommendation for Session 3 (L-064-6:
never self-opine on model choice; produce it via routed analysis)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

PROMPT = """\
You are recommending the orchestrator (engine / provider / model / effort) for
Session 3 of 3 of Set 070 (dual-surface verification + push fair-shake telemetry)
in the dabbler-ai-orchestration repo. Give a single concrete recommendation with a
short reason. Be objective about cost vs capability; do not default to any provider.

CONTEXT:
- Sessions 1-2 are CLOSED + VERIFIED. S1 shipped the steelman-push upgrade
  (verification.md devil's-advocate framing), the start_session contractGate-seed
  fix, and the dual-surface two-arm runner (ai_router/dual_surface_verify.py). S2
  shipped the provenance merge (merge_findings: stable-defectKey only, never
  free-text), the comparison artifact + pure-Python validator + JSON Schema
  (docs/dual-surface-comparison.schema.json, L-066-1 parity), the fair-shake
  scoring (score_comparison + score_against_benchmark over the Set 069
  replacement_gate benchmark, underpowered->inconclusive, never-pool-sampled-with-
  opt-in), and the dualSurfaceMode verificationMode-pattern option + CLI.
- Session 3 (FINAL) scope: (a) update docs/verification-surface-strategy.md (the
  mode + steelman-push are now BUILT; record the first benchmark telemetry
  datapoint and whether it is powered enough) + ai_router/docs/pull-verifier.md;
  promote a lesson if warranted; (b) finalize tests; BUMP ai_router (minor) and ship
  the PyPI release per the publish runbook (green-Test-on-the-tagged-SHA; verify
  tag commit == fixed SHA -- the Set 068 lesson; operator pushes/approves the tag);
  record the publish run id; (c) change-log.md; (d) route the next-session-set
  recommendation; (e) DOGFOOD the new dual-surface mode over THIS set's own diff and
  record the provenance-tagged comparison; pathAwareCritique:required +
  contractGate:advisory close-out gates; close_session.
- S3 is a DOCS + RELEASE + DOGFOOD session: prose synthesis (cross-referenced doc
  consistency, L-065-1), a real PyPI publish (the riskiest, operator-gated step),
  and running the actual dual-surface mode over the set's own committed diff. It is
  less novel-code than S1/S2 but the release + the live dogfood carry real
  irreversibility (a bad publish is hard to undo) and need careful prose accuracy.
- Available engines: claude (anthropic: opus-4-8, sonnet-4-6, haiku), codex
  (openai: gpt-5-4), gemini (google: gemini-pro). The orchestrator for S1/S2 was
  claude/anthropic/opus-4-8 high.

Return: engine, provider, model, effort (low/medium/high), and a 2-4 sentence
reason. Consider that the verifier across this set has been gpt-5-4, so the
orchestrator should differ from the verifier where a cross-perspective helps.
"""


def main():
    r = route(PROMPT, task_type="analysis", session_set=str(HERE), session_number=2)
    out = HERE / "s2-next-orchestrator.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

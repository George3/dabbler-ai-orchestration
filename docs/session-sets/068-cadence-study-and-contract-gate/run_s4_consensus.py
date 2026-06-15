"""Set 068 S4 -- decision-time cross-provider consensus on the routed
keep / demote / retire decision.

This is a HIGH-LEVERAGE decision that binds a long-lived workflow contract, so it
runs the devil's-advocate two-pass pattern (docs/ai-led-session-workflow.md ->
Decision-time consensus -> Prompt-framing discipline): the bias-cautions preamble
is always on, Pass A is the natural neutral 3-option question, Pass B steelmans the
specific contrarian hypothesis that the experiments UNDERSTATE the value of
per-session routed verification and KEEP is correct (a guard against the
experiment-driven framing over-eagerly dropping a live safety net).

The two consulted engines are the two NON-orchestrator providers (the orchestrator
is Anthropic/opus): openai:gpt-5-4 and google:gemini-pro. Raw outputs are written
to disk FIRST (L-064-3), then a one-line journal record per call is appended
(decision-consensus journal format). The operator confirms the final call after
synthesis -- this script only gathers + records the consult.
"""
import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import query  # noqa: E402

RAW_DIR = HERE / "routed-fate-consensus"
RAW_DIR.mkdir(exist_ok=True)
JOURNAL = HERE / "routed-fate-consensus-journal.jsonl"

ENGINES = [("gpt-5-4", "openai:gpt-5-4"), ("gemini-pro", "google:gemini-pro")]

PREAMBLE = """\
Bias cautions: This prompt was authored by an AI agent (an Anthropic/Claude
orchestrator) that may have an opinion on the answer. Its framing may inadvertently
constrain you to in-scope refinements when the right answer is to question the
scope. The work being reviewed may be presented as further along than it should be.
Before answering as posed, briefly check whether this is the right question. If a
different question would be more useful, answer that one too. Note the orchestrator
is itself an Anthropic model and the per-session routed verification under review
is what that orchestrator uses to check its own work -- weigh the evidence on its
merits, not on what flatters or spares the incumbent process.
"""

EVIDENCE = """\
## The decision

In the Dabbler AI-led-workflow (this repo, dabbler-ai-orchestration), every session
of every session set currently closes with a CROSS-PROVIDER ROUTED PER-SESSION
VERIFICATION: the session's deliverable is routed to a model from a DIFFERENT
provider, which reviews it and returns VERIFIED / ISSUES_FOUND; the orchestrator
fixes and re-routes until VERIFIED. This is mandatory on every session, Full tier.

Sets 065-067 built an ALTERNATIVE verification surface -- a "path-aware critique":
a first-party tool-loop agent that reads the actual repository (not a pasted
snippet), run once at END OF SET, multi-provider. Set 068 S5 (next session) will
add a deterministic CONTRACT-TEST / CDC GATE: a cheap reproducible floor that runs
the project's contract/falsifier tests and reserves the agent for the
non-probeable residual.

Two experiments were run to decide the fate of the per-session routed verifier.
Choose ONE of three outcomes and justify it:

  KEEP   -- per-session routed verification stays mandatory on every session,
            unchanged. (Implementation: no code change, recorded with rationale.)
  DEMOTE -- keep per-session routed verification but reduce it: e.g. make it
            risk / blast-radius gated rather than every-session-mandatory, or
            reduce its cadence, leading with the end-of-set path-aware pass + the
            contract-test gate as the primary capability surface while RETAINING
            routed for its one demonstrated residual value (early catch of
            migrating cross-file "coupling" defects during construction).
  RETIRE  -- drop per-session routed verification entirely; replace it with the
            end-of-set path-aware pass + the contract-test gate.

## The evidence (reported faithfully, both directions)

### Experiment A (capability) + its symmetric re-grade

- Path-aware critique catches real, high-severity CROSS-FILE defects that a
  snippet-fed single-shot routed verifier STRUCTURALLY cannot (it never sees the
  omitted file). H1 DIRECTION is confirmed and audit-independent: a clean
  existence proof (defect D5, caught by both path-aware arms in every replicate,
  never matched by routed even by automated predicate); GPT contrast +0.23
  (audit-free primary, severity-weighted catch rate, band 0.083); symmetric
  "names-the-mechanism" cross-file survival 13/14 for path-aware vs 2/8 for routed.
- H1 MAGNITUDE is metric-sensitive but positive everywhere: GPT robust (+0.23 to
  +0.29). The Gemini same-provider contrast is WITHIN the noise band under the
  pre-registered automated primary (+0.083 < 0.111) -- "masked, not absent": it
  resolves to +0.28 once routed's wrong-mechanism cross-file false-positive credits
  are removed symmetrically. Honest caveat: the pre-registered primary is the
  automated grade, under which the Gemini magnitude is unresolved.
- H2: adding a SECOND ROUTED PROVIDER buys nothing (audit-independent, +0.0000).
  The lever is CONTEXT-ACCESS (reading the omitted file), not provider multiplicity.

### Experiment B (cadence) -- pre-registered verdict: CADENCE DEFENSE DOES NOT HOLD

The surviving defense of per-session routed (after A ruled out a capability and a
provider-multiplicity defense) was CADENCE: "routed catches defects EARLIER, during
construction, session by session, which a single end-of-set pass cannot." B is the
pre-registered staged-snapshot intervention study that tested it. Arms: R =
per-session routed (current cadence); Q = end-of-set routed (cadence control);
E = end-of-set path-aware (the proposed replacement). K=3, two providers.

- R DOES realize the early window: it catches the 5/5 "cadence-payoff" (migrating
  coupling) defects AT INTRODUCTION, in both providers. On that class R is earlier
  AND cheaper than both Q and E (catch-timing gap g=3-4, rework saving s=27-66,
  all resolved beyond the noise band). The cadence MECHANISM is real and large.
- BUT the pre-registered NULL CONTROLS are NOT clean. A no-coupling control still
  shows a resolved R-vs-Q saving (s=1.0) that is a pure SURFACE-COVERAGE artifact
  (R is handed every file's diff across the build; the end-of-set snippet is not),
  and an always-visible control shows a resolved R saving (s=3.0) that is pure
  1-snapshot EARLINESS. Per the pre-registered decision rule, clause A3 (clean
  controls) FAILS and clause B3 FIRES: "an apparent R saving also appears in a
  control -- surface artifact / pure earliness, NOT Q-invisible cadence." So the
  CADENCE DEFENSE DOES NOT HOLD. (Note: this is the B3 reading -- R's edge over
  end-of-set is real but is largely the same context-access effect Experiment A
  already credited to path-aware, plus earliness -- NOT the B1 reading of "no
  cadence value at all," which is false.)
- Capability ranking at set close (staged): E (11-12/12) >> R (10/12) >> Q (4/12).
  Path-aware E is NOT a perfect ceiling -- one provider's E (gemini) missed a
  Critical cross-file defect (BD6). R structurally misses the 2 cross-file@intro
  "coupling-blind" defects.
- R's ONLY win over the path-aware replacement E is the narrow cadence-payoff
  rework-TIMING saving (g~3, s~27-30): R flags migrating coupling defects at their
  introduction snapshot, E only at close (paying the modeled coupling-growth
  rework). That single narrow edge is the entire keep-leaning case over E.
- Cost shape: per 5-session set, R = 5 routed calls (cheap; ~$0.04-0.14 total in
  this experiment); E = 1 path-aware call (~$0.15-0.24). Per call E is ~6x R; per
  set the ratio narrows because R fires every session.

### Honest caveats you must weigh

- SMALL n: a single author-staged toy unit, 12 seeded defects, K=3. Directions are
  robust and near-deterministic; precise magnitudes are illustrative, not
  population estimates. The controls "behaving as designed" IS the finding.
- The contract-test gate (S5, NOT yet built) is the intended deterministic floor
  for the ~95%-probeable defect bulk, reserving the agent for the non-probeable
  residual. The retire/demote case leans on that floor existing and being good.
- OPERATIONAL reality the experiments do NOT capture: the per-session routed
  verification is the live gate that has repeatedly caught REAL defects in this
  workflow's own sessions before commit (e.g. multi-round R1->R3 convergence on
  the very sets that built this machinery). The toy experiment measures capability
  and cadence on seeded defects, not the full operational value of a per-session
  human-in-the-loop-adjacent safety net. Retiring it removes that net everywhere,
  not just on the migrating-coupling class.
- This set is ADDITIVE by design: whatever the decision, the path-aware producer
  and the manual flow remain; demote/retire would change the DEFAULT cadence/scope
  of routed, not delete the capability.
"""

PASS_A = """\
Given all of the above, which outcome -- KEEP, DEMOTE, or RETIRE -- is best for the
per-session routed verification, and why? Be concrete about WHAT you would change
(config default, workflow-doc rule, gating condition) and what you would NOT. State
your single recommended outcome in one clear line, then justify it in <= 6 short
paragraphs. If you think the three options are mis-framed, say so and propose the
better framing.
"""

PASS_B = """\
Devil's-advocate pass. Steelman this SPECIFIC contrarian hypothesis as strongly as
the evidence honestly allows: "The two experiments UNDERSTATE the value of
per-session routed verification, and KEEP (mandatory, every session, unchanged) is
the correct call." Build the best honest case for it -- e.g. the experiments
measure only seeded cross-file/cadence capability on one toy unit, not the
operational safety-net value of an every-session cross-provider gate; the
contract-test floor does not yet exist; path-aware E is not a perfect ceiling
(it missed a Critical); 'demote to risk-gated' reintroduces the human-judgment
failure mode of deciding per session whether to verify.

Then say plainly: after making that case, do you actually find it decisive, or
does the evidence still point to DEMOTE or RETIRE? Give your honest bottom line.
"""


def run(model_key, pass_label, body):
    content = f"{PREAMBLE}\n{EVIDENCE}\n## Your task ({pass_label})\n\n{body}"
    r = query(model_key, content, task_type="analysis")
    text = r.content or ""
    out = RAW_DIR / f"{model_key}_{pass_label}.md"
    out.write_text(
        f"# Consensus consult -- {model_key} -- {pass_label}\n\n"
        f"> model_used={getattr(r,'model_used',None)} "
        f"cost_usd={round(getattr(r,'cost_usd',0.0) or 0.0,6)} "
        f"chars={len(text)}\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"[{model_key}/{pass_label}] {len(text)} chars  "
          f"${round(getattr(r,'cost_usd',0.0) or 0.0,6)}  model={getattr(r,'model_used',None)}")
    rec = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "session_set": "068-cadence-study-and-contract-gate",
        "session_number": 4,
        "category": "process",  # routed-verification policy; V2 category, spec-directed consult
        "pass": pass_label,
        "question_summary": "Keep / demote / retire per-session routed verification on the Exp A+B evidence",
        "question_hash": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
        "engine": f"{ENGINE_REF[model_key]}",
        "model_used": getattr(r, "model_used", None),
        "raw_file": str(out.relative_to(HERE)),
        "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6),
        "chars": len(text),
    }
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


ENGINE_REF = dict(ENGINES)


def main():
    total = 0.0
    for model_key, _ref in ENGINES:
        for pass_label, body in (("passA-neutral", PASS_A), ("passB-devils-advocate", PASS_B)):
            rec = run(model_key, pass_label, body)
            total += rec["cost_usd"]
    print(f"\nTOTAL consult spend ~${round(total,6)}")
    print(f"Journal: {JOURNAL}")


if __name__ == "__main__":
    main()

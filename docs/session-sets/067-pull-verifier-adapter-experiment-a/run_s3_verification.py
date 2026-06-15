"""Set 067 S3 cross-provider verification of the EXPERIMENT A ANALYSIS.

Per spec S3 Step 6: the routed verifier checks the INFERENCE (does the verdict
follow from the data and respect the pre-registered criteria?), NOT the wet-lab
run. Independent verifier: gpt-5.4 (openai) - cross-provider for the Claude
orchestrator. Persists raw output BEFORE printing (L-064-3).

Usage:
  .venv/Scripts/python.exe docs/session-sets/067-.../run_s3_verification.py [--round N]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

EA = HERE / "experiment-a"
prereg = (HERE / "experiment-a-preregistration.md").read_text(encoding="utf-8")
results = (HERE / "experiment-a-results.md").read_text(encoding="utf-8")
data = (EA / "experiment-a-data.json").read_text(encoding="utf-8")
audit = (EA / "audit.json").read_text(encoding="utf-8")
catalogue = (EA / "catalogue.json").read_text(encoding="utf-8")

# Two disputed raw cells so the verifier can spot-check the audit against truth.
raw_a1_t3 = (EA / "raw" / "tree3_aggregator" / "A1_k1.json").read_text(encoding="utf-8")
raw_a2_t2 = (EA / "raw" / "tree2_registry" / "A2_k2.json").read_text(encoding="utf-8")

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; they are the agreed
baseline / by-design scope for this session):

THIS IS A RESEARCH/EXPERIMENT SESSION. Set 067 Session 3 of 4 runs Experiment A
(a controlled capability study). It ships NO production code and NO release this
session (the PyPI bump is Session 4). The deliverable under review is the
ANALYSIS: experiment-a-results.md and its verdict, judged against the
PRE-REGISTERED criteria (experiment-a-preregistration.md, written before any
data). The adapter itself (ai_router/pull_verifier.py) was already cross-provider
VERIFIED in S1+S2 - do NOT re-review the adapter code.

YOUR JOB: verify the INFERENCE, not the wet-lab run. Does the capability verdict
follow from the data? Are the pre-registered criteria honestly applied? Is the
manual audit (the single largest subjectivity) defensible against the raw text?
Is the honesty about limitations adequate, or is anything over-claimed?

BY-DESIGN (not defects): seeded (not natural) defects; n=5 trees x K=3 (resolves
large effects only, stated); a deterministic predicate grade + a pre-registered
manual audit of routed x cross-file catches; in-snippet defects showing NO
context gap (that is the built-in control). Experiment B (cadence), the
keep/demote/retire decision, and the contract-test gate are deliberately Set 068.
"""

SYSTEM_PROMPT = (
    "You are a senior empirical-methods reviewer giving an independent "
    "cross-provider verification of a completed capability experiment's ANALYSIS "
    "(Set 067 Session 3, Experiment A). You did not run it. Be rigorous about "
    "causal inference, pre-registration discipline, grading validity, and "
    "over-claiming. Distinguish a real inferential defect from a presentation "
    "nit. End with a JSON verdict block: {\"verdict\":\"VERIFIED\"|\"ISSUES_FOUND\","
    "\"issues\":[{\"severity\":\"Critical|Major|Minor\",\"claim\":\"<what>\","
    "\"problem\":\"<why>\",\"fix\":\"<how>\"}]}."
)

FOCUS = """\
FOCUS your review on:
1. CRITERIA DISCIPLINE: Are the verdicts (H1 CONFIRMED, H2 context-access, H3
   routed-capability RULED OUT, H4 falsifier 0.95) the ones the pre-registration
   actually committed to, or were thresholds/comparisons moved after seeing data?
2. H1 SOUNDNESS: Does +0.306 / +0.361 weighted gap, concentrated entirely in the
   cross-file subclass with 2 Criticals path-aware-only, support "context-access
   confirmed"? Is the noise-band comparison valid? Is the in-snippet control
   (all arms 13/13) correctly used as the negative control?
3. THE AUDIT (most important): the analysis admits the headline H1 result for
   B2-A2 depends on the manual audit removing routed's cross-file "catches". Check
   the audit rule and the two committed raw samples (A1 tree3 = a REJECTED D9 +
   a KEPT D10; A2 tree2 = a REJECTED D6). Are the reject/keep calls defensible
   against the raw text, or did the author bias the grade to manufacture the gap?
4. H3 / H2 LOGIC: Is "routed-pair minus path-aware-pair = empty" correctly read
   as ruling out routed CAPABILITY but NOT cadence? Is the "second routed
   validator adds nothing" claim (routed-pair == best-single-routed) sound?
5. OVER-CLAIM CHECK: Does the write-up over-generalize from a 5-tree mock-repo?
   Are the limitations (author-seeded, small n, audit dependence, falsifier
   pre-authoring caveat) adequate and honestly placed, or buried?
6. INTERNAL CONSISTENCY: do the matrix, the per-arm rates, the derived pairs, and
   the prose agree? Any number in the prose not supported by experiment-a-data.json?
"""

USER = f"""{CONVENTIONS}

{FOCUS}

=== PRE-REGISTRATION (written before any data) ===
{prereg}

=== ANALYSIS UNDER REVIEW: experiment-a-results.md ===
{results}

=== MACHINE METRICS: experiment-a-data.json ===
{data}

=== AUDIT DECISIONS (with quotes): audit.json ===
{audit}

=== CATALOGUE (defect labels + predicates): catalogue.json ===
{catalogue}

=== RAW SAMPLE 1: routed GPT on tree3 (A1_k1) -- basis for REJECT D9, KEEP D10 ===
{raw_a1_t3}

=== RAW SAMPLE 2: routed Gemini on tree2 (A2_k2) -- basis for REJECT D6 ===
{raw_a2_t2}

Review per the FOCUS list. Return your findings then the JSON verdict block."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()

    cfg = yaml.safe_load(
        (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
    )
    pcfg = cfg["providers"]["openai"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4")
    result = providers.call_model(
        provider_name="openai",
        model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT,
        user_message=USER,
        max_tokens=28000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    suffix = "" if args.round == 1 else f"-round-{args.round}"
    out = HERE / f"s3-verification{suffix}.md"
    out.write_text(
        f"# Set 067 S3 -- Cross-provider verification of the Experiment A analysis "
        f"(gpt-5.4), Round {args.round}\n\n"
        "> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude\n"
        f"> orchestrator. Checks the INFERENCE, not the wet-lab run.\n\n{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1e6 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1e6 * result.output_tokens
    print(f"Wrote {out.name} ({len(result.content)} chars)")
    print(json.dumps({
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cost_usd": round(in_cost + out_cost, 6), "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()

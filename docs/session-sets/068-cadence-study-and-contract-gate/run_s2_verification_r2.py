"""Set 068 S2 cross-provider verification -- ROUND 2.

Round 1 (gpt-5.4) returned ISSUES_FOUND: 1 Minor (re-grade 'conservative floor'
overclaim) + 2 Major (Experiment B prereg: union-over-K primary not stability-
binding; missing vis_at_close_for_Q to operationalize the migration mechanism).
All three were addressed. This round re-sends the UPDATED deliverables + the R1
findings verbatim and asks gpt-5.4 to confirm resolution and flag any new issue.
Same provider (gpt-5.4) for continuity; provider pinned via call_model (no router
escalation). Persists raw output BEFORE printing (L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

RG = HERE / "experiment-a-regrade"
regrade_md = (HERE / "experiment-a-regrade.md").read_text(encoding="utf-8")
regrade_data = (RG / "experiment-a-regrade-data.json").read_text(encoding="utf-8")
prereg_b = (HERE / "experiment-b-preregistration.md").read_text(encoding="utf-8")
skeleton = (HERE / "experiment-b" / "harness-skeleton.md").read_text(encoding="utf-8")
r1 = (HERE / "s2-verification.md").read_text(encoding="utf-8")

CHANGES = """\
WHAT CHANGED SINCE ROUND 1 (address each R1 finding):

FINDING 1 (Minor -- 'conservative floor' overclaim, experiment-a-regrade.md S3/S5):
  FIXED by COMPUTING the audited replicate-level means rather than hand-waving.
  regrade.py now applies BOTH mechanism audits PER REPLICATE and reports
  replicate_mean_sym_audited + noise_band_sym_audited per arm (see DELIVERABLE 2,
  per_arm.*). The 'conservative floor' wording is removed. New measured numbers:
  - per-arm sym-audited replicate mean: A1 0.639, A2 0.583, B1 0.926, B2 0.861.
  - GPT B1-A1 sym-audited replicate-mean gap = +0.2870 (band 0.0555) EXCEEDS.
  - Gemini B2-A2 sym-audited replicate-mean gap = +0.2778 (band 0.0556) EXCEEDS.
  The doc now states the Gemini effect was MASKED by routed's wrong-mechanism
  cross-file credit (not absent): within-band under the pre-registered automated
  primary, +0.28 under the symmetric mechanism-audited replicate-mean -- with an
  explicit caveat that the automated grade is the pre-registered PRIMARY and the
  mechanism-audited metric is author-applied audit (so it carries the audit caveat).

FINDING 2 (Major -- Exp B primary not stability-binding; band formula imprecise):
  FIXED in experiment-b-preregistration.md S6/S7/S8 + harness-skeleton.md.
  - PRIMARY is now PER-REPEAT first-catch c_k(arm,defect) (n+1 if uncaught in k),
    aggregated across K as mean AND median; union-over-K + reliable-across-K are
    DEMOTED to secondary/descriptive only.
  - A BINDING stability gate: 'realized-early-catch' = caught at c_k <= t0+1 in a
    MAJORITY of repeats (>= ceil(2K/3) = 2/3). The S8 decision rule's HOLDS clause
    now REQUIRES this majority gate; a single lucky repeat cannot set the verdict.
  - The noise band now has a PINNED per-metric formula (S6): per-repeat class
    catch-timing gap g_k and per-repeat class cost cost_k, band = max-min over the
    K per-repeat values, contrast band = max(bandB, bandA).

FINDING 3 (Major -- migration mechanism not operationalized; Q could still see
  the defect, so a null R-vs-Q would be a seed artifact):
  FIXED by adding a THIRD pre-registered axis and pinning Q's surface.
  - S3a pins R's per-session surface (S(i)\\S(i-1)) and Q's end-of-set surface (the
    final session diff + headline changed file by the Exp A snippet rule, OMITTING
    earlier-untouched files; no probing), committed per-unit in the catalogue
    (Q_surface_files) BEFORE runs.
  - New axis vis_at_close_for_Q. Cadence-payoff is REDEFINED as
    d>0 AND in-snippet@intro AND CROSS-FILE@close_for_Q (recognizable early by R,
    INVISIBLE to end-of-set Q). Added an 'always-visible' control
    (in-snippet@intro AND in-snippet@close_for_Q) to isolate that R's edge needs
    Q-invisibility, not mere earliness. Minimum counts asserted before the sweep
    (>=3 cadence-payoff, >=2 each control). The S8 null checks now include the
    always-visible control too.

CONVENTIONS (unchanged from R1): no production code, no release this session; the
re-grade re-analyses committed Set 067 data (no new collection); cost_model.py
self-tests PASS; the full ai_router suite is GREEN (1548 passed, 1 skipped).
"""

SYSTEM_PROMPT = (
    "You are the same senior research-methodology + software-verification reviewer "
    "doing ROUND 2 of an independent cross-provider verification (Set 068, Session "
    "2). You raised 1 Minor + 2 Major in Round 1. Confirm whether each is resolved "
    "by the updated deliverables, and flag any NEW defect the changes introduce. Be "
    "concrete: cite the claim/number/section. Do not re-litigate the agreed "
    "conventions. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[{"severity":"Critical|Major|'
    'Minor","claim":"<what>","problem":"<why>","fix":"<how>"}]}. Return VERIFIED '
    "only if no Critical/Major remains."
)

USER = f"""{CHANGES}

=== ROUND 1 VERDICT (your prior findings, verbatim) ===
{r1}

=== UPDATED DELIVERABLE 1: experiment-a-regrade.md (full) ===
{regrade_md}

=== UPDATED DELIVERABLE 2: experiment-a-regrade-data.json (now incl. sym-audited replicate means) ===
{regrade_data}

=== UPDATED DELIVERABLE 3: experiment-b-preregistration.md (full) ===
{prereg_b}

=== UPDATED DELIVERABLE 4: experiment-b/harness-skeleton.md (full) ===
{skeleton}

Confirm resolution of the 3 findings (or not), flag any new issue, then the JSON verdict block."""


def main():
    cfg = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))
    pcfg = cfg["providers"]["openai"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4")
    result = providers.call_model(
        provider_name="openai", model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT, user_message=USER,
        max_tokens=28000, config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s2-verification-round-2.md"
    out.write_text(
        "# Set 068 S2 -- Cross-provider verification ROUND 2 (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai). Re-check of the 3 Round-1 findings\n"
        "> (1 Minor + 2 Major) after remediation.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(json.dumps({
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cost_usd": round(in_cost + out_cost, 6), "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()

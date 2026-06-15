"""Set 068 S2 cross-provider verification -- ROUND 3.

Round 2 cleared R1-Finding-1 (RESOLVED) and confirmed the structural fixes for
the two Majors, but flagged two precise residual inconsistencies:
  (2) median made decision-binding in S8 without a pinned median-band, and the
      contrast-level g_k band rule conflicted with a max(band_armB,band_armA) rule;
  (3) Q's surface contradictory -- S3 table + harness runner still said
      aggregate_diff(S_n) while S3a + schema used the narrower Q_surface_files.
Both were fixed. This round re-sends the touched sections + the R2 verdict and
asks gpt-5.4 to confirm. Provider pinned (gpt-5.4); persists raw BEFORE print
(L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

prereg_b = (HERE / "experiment-b-preregistration.md").read_text(encoding="utf-8")
skeleton = (HERE / "experiment-b" / "harness-skeleton.md").read_text(encoding="utf-8")
r2 = (HERE / "s2-verification-round-2.md").read_text(encoding="utf-8")

CHANGES = """\
WHAT CHANGED SINCE ROUND 2 (only the two residual Majors; Finding 1 was RESOLVED
in R2 and is untouched; the re-grade docs are unchanged):

RESIDUAL of FINDING 2 (band/median spec): FIXED in experiment-b-preregistration.md
  §6 + §8 (+ harness-skeleton.md decision wiring).
  - §6 now pins ONE rule: every decisive quantity is a per-repeat CONTRAST value
    X_k (already B-minus-A); its band is its OWN across-K range
    band = max_k X_k - min_k X_k; the decision statistic is mean_k X_k; resolved
    iff |mean_k X_k| > band. The earlier max(band_armB, band_armA) rule is REMOVED
    (there are no arm-level bands in the decision now).
  - The MEDIAN is explicitly NOT a separate threshold: it is reported as a
    sign-agreement robustness check; a mean/median sign disagreement -> unresolved.
  - The two decisive contrasts are named: catch-timing gap g_k and rework-cost
    saving s_k, both per-repeat, both judged by the single §6 rule.
  - §8 HOLDS clause 2 now reads '|mean_k g_k| > band ... mean_k s_k > band' with
    'median agreeing in sign'; the DOES-NOT-HOLD clause uses 'mean_k within band
    (or mean/median sign disagreement)'. No median-band is left undefined.

RESIDUAL of FINDING 3 (Q surface contradiction): FIXED -- Q is now the narrower
  snippet EVERYWHERE.
  - §3 arms table: Arm Q = route() over Q's end-of-set surface (Q_surface_files,
    §3a), once -- no longer 'aggregate diff'.
  - §3a: states the surface IS the catalogue's Q_surface_files and 'Arm Q is run
    on precisely that bundle -- never on the whole aggregate diff', checked against
    the same Q_surface_files so classification and the run cannot drift.
  - harness-skeleton.md runner: Arm Q context = Q_surface_files (NOT
    aggregate_diff(S_n)); the renamed session_diff(S_i) for R.

CONVENTIONS (unchanged): no production code, no release this session; cost_model.py
self-tests PASS; full ai_router suite GREEN (1548 passed, 1 skipped).
"""

SYSTEM_PROMPT = (
    "You are the same reviewer doing ROUND 3 of an independent cross-provider "
    "verification (Set 068, Session 2). Two Major residuals remained after Round 2 "
    "(decisive-statistic/band specification; Q-surface contradiction). Confirm "
    "whether each is now fully resolved and flag any NEW inconsistency the edits "
    "introduce. Be concrete; cite section/line. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]}. Return VERIFIED only if '
    "no Critical/Major remains."
)

USER = f"""{CHANGES}

=== ROUND 2 VERDICT (verbatim) ===
{r2}

=== UPDATED DELIVERABLE: experiment-b-preregistration.md (full) ===
{prereg_b}

=== UPDATED DELIVERABLE: experiment-b/harness-skeleton.md (full) ===
{skeleton}

Confirm resolution of the two residual Majors, flag any new issue, then the JSON verdict block."""


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
    out = HERE / "s2-verification-round-3.md"
    out.write_text(
        "# Set 068 S2 -- Cross-provider verification ROUND 3 (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai). Re-check of the two residual\n"
        "> Major findings (decisive-statistic/band spec; Q-surface contradiction).\n\n"
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

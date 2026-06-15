"""Set 068 S3 cross-provider verification - ROUND 2 (focused re-verify).

R1 (gpt-5.4) returned ISSUES_FOUND: 1 Major (results.md overstated arm E,
esp. Gemini) + 3 Minor (grade.py 'evidence file' wording; mean/median
sign-agreement not folded into `resolved`; run_test live-use not cited to a raw
trace). All four were addressed. This round shows the SAME verifier the corrected
artifacts + the exact fixes and asks whether each R1 issue is resolved and whether
any NEW issue was introduced. Persists raw output BEFORE printing (L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

EB = HERE / "experiment-b"
results = (HERE / "experiment-b-results.md").read_text(encoding="utf-8")
data = (EB / "experiment-b-data.json").read_text(encoding="utf-8")
grade = (EB / "grade.py").read_text(encoding="utf-8")

CONVENTIONS = """\
ROUND 2 - FOCUSED RE-VERIFY. You (gpt-5.4) reviewed Set 068 S3 in Round 1 and
returned ISSUES_FOUND with 1 Major + 3 Minor. All four were addressed; confirm
resolution and flag any NEW defect introduced by the edits. Do NOT re-open the
agreed baseline (no production code / no release this session; suite green 1548/1;
the decision rule is the FIXED, S2-verified pre-registration). The verdict branch
(DOES NOT HOLD via B3) was confirmed correct in R1 and is unchanged.

THE FOUR R1 FINDINGS AND THE FIXES APPLIED:

[MAJOR] R1: experiment-b-results.md overstated arm E, esp. Gemini -- said 'E gemini
11/12 (1 minor)' when the miss is BD6 (Critical), and claimed E catches 'the two
coupling-blind defects R misses' when E_google catches only BD7.
FIX: results.md Sec 2 table now lists 'E gemini 11/12 | BD6 (Critical coupling-
blind)' and 'E gpt 12/12'; the reading + Sec 5 + Sec 6 + the Sec 0 TL;DR now state
per-provider: E gpt catches both coupling-blind defects R misses (12/12); E gemini
catches one (BD7), missing the Critical BD6 (11/12); 'path-aware is not a perfect
ceiling'. Verify experiment-b-data.json: E_google majority-misses == ['BD6'] (BD6
severity Critical); E_openai majority-misses == [].

[MINOR] R1: grade.py docstring said catches gate on the 'EVIDENCE FILE'.
FIX: docstring now says the gate is on the DEFECT'S OWN file (not the upstream
evidence file), and that cross-file@intro is adjudicated EMPIRICALLY + by the
symmetric audit, not by the surface gate. (No behavior change; wording now matches
_in_surface, which checks defect['file'].)

[MINOR] R1: grade.py::_band_stats set `resolved = abs(mean) > band` without folding
in mean/median sign-agreement (prereg Sec 6/8 says a sign disagreement is unresolved).
FIX: `resolved = (abs(mean) > band) and sign_agree`. Re-graded: NO decisive cell
flipped (all decisive cells have sign_agree True). Confirm the decisive contrasts
in experiment-b-data.json are unchanged (R-vs-Q cadence-payoff s=66 resolved;
R-vs-E cadence-payoff s=27/30 resolved; no-coupling s=1.0 resolved; always-visible
s=3.0 resolved -> A3 still fails, B3 still fires).

[MINOR] R1: the run_test live-use claim was not cited to a raw trace.
FIX: results.md Sec 1 now cites experiment-b/raw/numkit/E_google_S5_k1.json
(trace.tool_calls includes a run_test entry at turn:8, raw:true, error:false).

Confirm each of the four is resolved by the supplied corrected artifacts, and
check the edits introduced no NEW inconsistency (esp. that the per-provider E
numbers are internally consistent across Sec 0/2/5/6 and match the data).
"""

SYSTEM_PROMPT = (
    "You are the same independent cross-provider verifier (gpt-5.4) doing a focused "
    "round-2 re-verify of Set 068 S3. Confirm the four R1 findings are resolved and "
    "flag any NEW defect the edits introduced. Be concise. End with a JSON verdict "
    'block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]} -- VERIFIED if the '
    "four are resolved and nothing new is broken."
)

USER = f"""{CONVENTIONS}

=== CORRECTED DELIVERABLE: experiment-b-results.md (full, post-fix) ===
{results}

=== experiment-b/grade.py (post-fix: docstring + _band_stats) ===
{grade}

=== experiment-b/experiment-b-data.json (re-graded after the _band_stats fix) ===
{data}

Confirm resolution of the four R1 findings and report any NEW issue. Then the JSON verdict block."""


def main():
    cfg = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))
    pcfg = cfg["providers"]["openai"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4")
    result = providers.call_model(
        provider_name="openai", model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT, user_message=USER,
        max_tokens=20000, config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s3-verification-round-2.md"
    out.write_text(
        "# Set 068 S3 -- Cross-provider verification ROUND 2 (gpt-5.4)\n\n"
        "> Focused re-verify of the four R1 findings (1 Major arm-E overstatement +\n"
        "> 3 Minor: grader wording, sign-agreement fold-in, run_test citation).\n\n"
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

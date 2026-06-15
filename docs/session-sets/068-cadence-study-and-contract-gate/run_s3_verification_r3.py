"""Set 068 S3 cross-provider verification - ROUND 3 (final, wording-only confirm).

R2 confirmed all four R1 findings resolved and raised ONE new trivial nit: the
`_in_surface` function docstring in grade.py still said 'evidence file' while the
module docstring had been corrected to 'defect's own file'. That one-line wording
mismatch is now fixed. This round confirms it and the absence of any other
regression. No behavior, no numbers, no verdict changed. Persists raw first.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

grade = (HERE / "experiment-b" / "grade.py").read_text(encoding="utf-8")
# Just the relevant region for a focused confirm.
region = "\n".join(grade.splitlines()[150:175])

SYSTEM_PROMPT = (
    "You are the same gpt-5.4 verifier doing a final wording-only confirm of Set "
    "068 S3. R2 raised exactly one trivial nit: grade.py::_in_surface's docstring "
    "said 'evidence file' while the module docstring correctly said 'defect's own "
    "file'. Confirm it is now consistent. Reply briefly and end with the JSON "
    'verdict block {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]}.'
)
USER = (
    "The ONLY change since R2 is the _in_surface docstring. It now reads (with the "
    "module docstring's gating note unchanged):\n\n"
    f"```python\n{region}\n```\n\n"
    "The module-level grading-discipline docstring already states the gate is on "
    "the DEFECT'S OWN file (not the upstream evidence file) and that cross-file "
    "strictness is enforced empirically + by the symmetric audit. Behavior is "
    "unchanged; re-grade is clean; all decisive contrasts unchanged (A3 fails, B3 "
    "fires). Confirm the wording nit is resolved and nothing else regressed."
)


def main():
    cfg = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))
    pcfg = cfg["providers"]["openai"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4")
    result = providers.call_model(
        provider_name="openai", model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT, user_message=USER,
        max_tokens=6000, config=pcfg,
        generation_params={"reasoning_effort": "medium"},
    )
    out = HERE / "s3-verification-round-3.md"
    out.write_text(
        "# Set 068 S3 -- Cross-provider verification ROUND 3 (gpt-5.4, final)\n\n"
        "> Wording-only confirm of the single R2 nit (_in_surface docstring).\n\n"
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

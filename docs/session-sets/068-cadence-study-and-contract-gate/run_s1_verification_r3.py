"""Set 068 S1 cross-provider verification - ROUND 3 (confirm R2 fixes).

Feeds gpt-5.4 its Round 2 findings + the targeted remediation and asks for a
per-issue RESOLVED/NOT and a final verdict. Persists raw output first (L-064-3).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

r2 = (HERE / "s1-verification-round-2.md").read_text(encoding="utf-8")
cage = (REPO / "ai_router" / "run_test_sandbox.py").read_text(encoding="utf-8")

REMEDIATION = """\
ROUND 3 REMEDIATION (targeted at your three Round 2 issues):

R2 Critical (stale absolute language in the module): FIXED. The module-summary
item 2 and the run_test_in_cage() docstring no longer say "write-confined" /
"never mutated"; both now describe disposable-CWD isolation of a TRUSTED command
and point to the "Scope of the isolation" note, which enumerates the non-confined
vectors. A grep confirms NO residual "write-confined"/"never mutated"/"is never
the cwd" in run_test_sandbox.py or pull_verifier.py (the _dispatch_run_test
docstring's "write-confinement" was also changed to "disposable-CWD isolation").

R2 Major (prune not guaranteed): FIXED. _teardown() now calls
`git worktree prune --expire now` (forces immediate expiry of stale entries; it
only ever prunes worktrees whose directory is ALREADY gone, so a live worktree is
untouched), THEN verifies via _worktree_registered.

R2 new Minor (leak render dropped raw output): FIXED. render() now PREFIXES the
`ERROR: ... teardown did NOT complete ...` line but STILL appends the raw exit
code + captured output block, so the unsafe-leak path stays diagnosable AND is
flagged as an error. Tests assert both the ERROR prefix and the preserved
`exit_code=...` / output on the leak path.

SUITE: full ai_router pytest suite green (1548 + 1 new = 1549).
"""

SYSTEM_PROMPT = (
    "You are the same reviewer doing a Round 3 confirmation of Set 068 S1. For "
    "each of your three Round 2 issues, state RESOLVED or NOT RESOLVED in one "
    "sentence grounded in the updated module. Flag any new regression. End with a "
    'JSON verdict block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]}.'
)

USER = f"""{REMEDIATION}

=== YOUR ROUND 2 REVIEW (verbatim) ===
{r2}

=== UPDATED: ai_router/run_test_sandbox.py (full) ===
{cage}

Confirm each Round 2 issue is resolved (or not), flag any regression, then the
JSON verdict block."""


def main():
    cfg = yaml.safe_load(
        (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
    )
    pcfg = cfg["providers"]["openai"]
    model = next(
        m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4"
    )
    result = providers.call_model(
        provider_name="openai",
        model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT,
        user_message=USER,
        max_tokens=16000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s1-verification-round-3.md"
    out.write_text(
        "# Set 068 S1 -- Cross-provider verification ROUND 3 (gpt-5.4)\n\n"
        "> Confirmation of the R2 Critical/Major/Minor fixes.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(json.dumps({
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(in_cost + out_cost, 6),
        "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()

"""Set 068 S1 cross-provider verification - ROUND 2 (remediation re-verify).

Feeds gpt-5.4 its own Round 1 findings + the remediation (updated cage, worker,
contract, and the new tests) and asks whether each R1 issue is resolved. Persists
raw output BEFORE printing (L-064-3).
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

r1 = (HERE / "s1-verification.md").read_text(encoding="utf-8")
cage = (REPO / "ai_router" / "run_test_sandbox.py").read_text(encoding="utf-8")
worker = (REPO / "ai_router" / "regex_worker.py").read_text(encoding="utf-8")
contract = (HERE / "run-test-contract.md").read_text(encoding="utf-8")
diff = subprocess.run(
    ["git", "-C", str(REPO), "diff", "--",
     "ai_router/tests/test_run_test_sandbox.py", "ai_router/pull_verifier.py"],
    capture_output=True, text=True, check=True,
).stdout

REMEDIATION = """\
REMEDIATION SUMMARY (what changed since Round 1):

R1 Critical (write-confinement overclaim): NOT building an OS sandbox - it is an
explicit non-goal for this bounded verification cage (the cage runs the project's
OWN trusted test command on its OWN pinned snapshots; Experiment B's threat model
is accidental/incidental writes by a trusted command, not a malicious payload).
The claim was RE-SCOPED to be precise and honest (L-064-8): the module docstring,
the contract sec 1(2)/1(3), and the run_test tool-schema description now state the
guarantee is DISPOSABLE-CWD isolation of the trusted command's ordinary
working-directory writes, and explicitly enumerate what it does NOT confine
(absolute-path writes, committed symlinks, `git worktree list` main-worktree
discovery, detached children) and that confining untrusted code is a non-goal.

R1 Major 2a (prune ordering leak): _teardown now runs `worktree remove --force`
-> `shutil.rmtree(parent)` -> `git worktree prune` (prune AFTER the dir is gone,
so a failed remove is still deregistered), then verifies via _worktree_registered
(parses `git worktree list --porcelain`); a surviving registration -> removed=False.

R1 Major 2b (leak not surfaced): RunTestResult.render() now returns a leading
`ERROR: run_test cage: ... teardown did NOT complete ...` when ran=True and
worktree_removed=False, so _dispatch_run_test's `content.startswith("ERROR: ")`
flags it as an error probe. New tests: test_teardown_leak_is_reported_and_surfaced,
test_render_surfaces_leak_without_cage_error.

R1 Minor 3 (corrupted partial regex line): isolated_regex_search now takes the
text BEFORE the elision marker and drops the final (partial) line, instead of the
old lines[:-1] that only dropped the marker's trailing empty string. New test:
test_elided_output_drops_partial_match_line.

ALSO FIXED (found while writing the Minor-3 test): the regex worker wrote its
match lines via text-mode stdout, so Windows translated the "\\n" separators to
"\\r\\n", leaving a stray "\\r" on every multi-line grep result. The worker now
writes via sys.stdout.buffer (bare "\\n"). New regression test:
test_multi_match_lines_are_clean_no_carriage_return.

SUITE: full ai_router pytest suite green (1544 + 4 new remediation tests = 1548).
"""

SYSTEM_PROMPT = (
    "You are the same independent cross-provider reviewer, now doing a Round 2 "
    "remediation re-verification of Set 068 Session 1. For EACH of your Round 1 "
    "issues (Critical, Major, Minor), state RESOLVED or NOT RESOLVED with a one- "
    "to-two-sentence justification grounded in the updated code/contract. For the "
    "Critical, judge whether the RE-SCOPED claim is now accurate and internally "
    "consistent (a precise, honestly-bounded claim is an acceptable resolution; "
    "an OS sandbox was not required). Flag any NEW issue the remediation "
    "introduced. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]}.'
)

USER = f"""{REMEDIATION}

=== YOUR ROUND 1 REVIEW (verbatim) ===
{r1}

=== UPDATED: ai_router/run_test_sandbox.py (full) ===
{cage}

=== UPDATED: ai_router/regex_worker.py (full) ===
{worker}

=== UPDATED: run-test-contract.md (full) ===
{contract}

=== DIFF: tests + pull_verifier schema description ===
{diff}

Confirm each Round 1 issue is resolved (or not), flag any regression, then the
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
        max_tokens=20000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s1-verification-round-2.md"
    out.write_text(
        "# Set 068 S1 -- Cross-provider verification ROUND 2 (gpt-5.4)\n\n"
        "> Remediation re-verify of the R1 Critical/Major/Minor findings.\n\n"
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

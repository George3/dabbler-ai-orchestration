"""Set 068 S1 cross-provider session-verification.

Independent verifier: gpt-5.4 (openai) -- cross-provider for the Claude
orchestrator. Reviews the S1 run_test execution cage (run_test_sandbox.py +
regex_worker.py), its wiring into the Set 067 pull-verifier adapter
(pull_verifier.py), and the relocated grep ReDoS isolation, plus the tests that
pin those invariants. Persists raw output BEFORE printing (L-064-3).

Usage:
    .venv/Scripts/python.exe docs/session-sets/068-.../run_s1_verification.py
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

contract = (HERE / "run-test-contract.md").read_text(encoding="utf-8")
cage = (REPO / "ai_router" / "run_test_sandbox.py").read_text(encoding="utf-8")
worker = (REPO / "ai_router" / "regex_worker.py").read_text(encoding="utf-8")
cage_tests = (
    REPO / "ai_router" / "tests" / "test_run_test_sandbox.py"
).read_text(encoding="utf-8")

# Tracked-file changes (pull_verifier wiring, config, exports, new wiring tests).
# New files are included in full above (L-064-9: diff omits untracked files).
diff = subprocess.run(
    ["git", "-C", str(REPO), "diff", "--",
     "ai_router/pull_verifier.py", "ai_router/router-config.yaml",
     "ai_router/__init__.py", "ai_router/tests/test_pull_verifier.py"],
    capture_output=True, text=True, check=True,
).stdout

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; they are the agreed
baseline, in-scope-by-design, or explicit later-session scope):

SUITE BASELINE: the full ai_router pytest suite is GREEN at session close
(1519 pre-existing passing + 25 new = 1544 passing, 1 pre-existing skip). No
pre-existing failures are introduced. Assume green; do not ask for counts.

RELEASE CONTRACT: Session 1 of 6 ships NO release. The PyPI ai_router bump ships
in Session 6. S1 only adds the cage library module + the regex worker + tests +
the pinned contract, wires run_test into the Set 067 adapter, relocates the grep
ReDoS defense, and exports the new surface from ai_router/__init__.py.

BY-DESIGN SCOPE (Set 068 S1 only -- the rest is later sessions):
- run_test is OFFERED to the agentic loop ONLY when a RunTestConfig is passed to
  pull_route(). Absent that, the offered tools are byte-for-byte the Set 067
  read-only set; the default loop is unchanged. This is intentional (additive),
  not a gap.
- NO live/metered API call is made in the unit tests by design: a FakeBinding
  drives the loop; the cage runs LOCAL git + subprocess (the venv python). The
  live, metered end-to-end use of run_test inside a build+test-per-snapshot loop
  is Experiment B (Session 3). S1 ships the cage + wiring + dispatch seam only.
- re2 is NOT installed in this venv, so the live ReDoS path is the subprocess +
  hard-timeout fallback; the re2 inline fast path is a best-effort optimization
  for hosts that have it. Both are in scope; only one runs here.
- The router-config run_test caps block is consumed by run_test_caps_from_config
  (a shipped, tested reader); the S3 cadence harness will use it to build the
  live cage's bounds. A caps reader without a live metered caller this session is
  intended, not dead config.

FOCUS your review on:
1. CRASH-SAFE TEARDOWN: does run_test_in_cage ALWAYS tear the disposable worktree
   down -- on success, on a failed command, on a timeout-kill, AND on any
   exception in create/run? Is the dataclasses.replace-after-finally pattern
   sound (no path that returns before teardown, no swallowed exception that
   leaks a worktree)? Can a worktree ever leak registered with git?
2. WRITE-CONFINEMENT / DETERMINISTIC SERVANT EXTENDED TO EXECUTION: is the claim
   "the real tree is never mutated" actually true? The defense is (a) cwd = a
   disposable detached worktree + (b) a bounded, operator-authored command
   surface the model cannot author. Is that airtight, or can the model reach an
   arbitrary write (e.g. via the run_test `name` input, an absolute path, a
   shell string)? Is run_test correctly kept OUT of the byte-equality guard
   (execution is non-re-derivable) WITHOUT opening a hole in the read-only
   probes' guard?
3. TIMEOUT-KILL: does run_subprocess_capped actually KILL an overrunning process
   (and its children) and report timed_out / exit_code=None? Is the process-tree
   kill correct on both Windows (taskkill /T) and POSIX (killpg)? Any way the
   wall-clock cap is defeated (e.g. a child outliving the parent)?
4. OUTPUT CAP: is output truly bounded (temp-file capture + capped head read), so
   a flooding command cannot blow memory before the timeout? Is the elision raw
   (a head slice + marker), never paraphrased?
5. ReDoS ISOLATION: does isolated_regex_search actually BOUND a catastrophic
   pattern that DEFEATS the cheap heuristic (e.g. (a|a)*c), by killing the
   subprocess at the timeout? Is the heuristic correctly demoted to a pre-filter
   only? Is the worker's output handling correct (elision drop of a partial
   trailing line; no corrupted match line)? Any way a pattern still hangs the
   orchestrator process?
6. WIRING CORRECTNESS: is the Set 067 read-only loop genuinely unchanged when no
   RunTestConfig is given (tool set, dispatch, guard)? Is run_test counted as a
   real probe (so a verdict informed by it is NOT zero_tool_calls)? Does the
   dual import (relative / bare) match the package's convention and not create a
   cycle (pull_verifier -> run_test_sandbox only)?
7. TEST QUALITY: do the new tests actually PIN invariants 1-6 (teardown on
   exception, timeout-kill, output cap, write cannot escape, raw exit+output,
   catastrophic regex bounded), or are any vacuous / tautological? Anything an
   invariant claims that no test covers?
"""

BIAS_CAUTIONS = (
    "Bias cautions: this code was authored by an AI agent (Claude Opus 4.8) that "
    "maintains the workflow under study and has a stake in shipping the cage. Its "
    "self-review may miss a hole in the very safety property it is proud of. Be "
    "adversarial about crash-safe teardown and write-confinement in particular. "
    "If the right question to ask differs from the one posed, answer that too."
)

SYSTEM_PROMPT = (
    "You are a senior software-verification reviewer giving an independent "
    "cross-provider verification of a completed implementation session (Set 068, "
    "Session 1: the disposable-worktree run_test execution cage + relocated grep "
    "ReDoS isolation). You did not author it. Be rigorous and concrete: cite the "
    "specific function / line / claim. Distinguish a real correctness or safety "
    "defect from a style nit. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[{"severity":'
    '"Critical|Major|Minor","claim":"<what>","problem":"<why>","fix":"<how>"}]}.'
)

USER = f"""{BIAS_CAUTIONS}

{CONVENTIONS}

=== DELIVERABLE 1: run-test-contract.md (the pinned S1 design contract) ===
{contract}

=== DELIVERABLE 2: ai_router/run_test_sandbox.py (the cage, NEW FILE, full) ===
{cage}

=== DELIVERABLE 3: ai_router/regex_worker.py (the isolated regex worker, NEW FILE, full) ===
{worker}

=== DELIVERABLE 4: ai_router/tests/test_run_test_sandbox.py (cage tests, NEW FILE, full) ===
{cage_tests}

=== DELIVERABLE 5: git diff of changed TRACKED files (pull_verifier wiring, config, exports, new wiring tests) ===
{diff}

Review per the FOCUS list. Return your findings then the JSON verdict block."""


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
        max_tokens=28000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s1-verification.md"
    out.write_text(
        "# Set 068 S1 -- Cross-provider verification (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude\n"
        "> orchestrator. Round 1.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(
        json.dumps(
            {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": round(in_cost + out_cost, 6),
                "stop_reason": result.stop_reason,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""Set 068 S5 cross-provider verification driver (route -> gpt-5-4).

Builds the verification prompt with the up-front conventions block (L-064-10
promoted), embeds the full new module + the close_session wiring diff + schemas +
design doc, routes a single-shot analysis verification to a NON-Anthropic
provider (the orchestrator is opus), and writes the raw output to disk FIRST
(L-064-3) before printing.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ai_router import route

SET = Path("docs/session-sets/068-cadence-study-and-contract-gate")
ROOT = Path(".")


def _read(p):
    return Path(p).read_text(encoding="utf-8")


def main(out_name="s5-verification.md", model="gpt-5-4"):
    contract_gate = _read("ai_router/contract_gate.py")
    close_diff = _read(SET / "cs.diff")
    manifest_schema = _read("docs/contract-manifest.schema.json")
    floor_schema = _read("docs/contract-floor-result.schema.json")
    design = _read(SET / "contract-gate-design.md")
    gate_doc = _read("docs/contract-gate.md")
    cfg_anchor = ""
    cfg = _read("ai_router/router-config.yaml").splitlines()
    for i, ln in enumerate(cfg):
        if "Contract-test / CDC gate (Set 068 S5)" in ln:
            cfg_anchor = "\n".join(cfg[i - 1:i + 14])
            break

    prompt = f"""You are the cross-provider session verifier for Set 068 Session 5
of the dabbler-ai-orchestration repo. You are a DIFFERENT provider than the
orchestrator (Claude Opus 4.8), which is the whole point of this review.

================ CONVENTIONS / BASELINE (read first) ================
- Suite baseline: BEFORE this session the Python suite was 1548 passing / 1
  skipped. AFTER this session it is 1632 passing / 1 skipped (this session adds
  84 tests across test_contract_gate.py, test_contract_gate_close.py,
  test_contract_gate_schema.py). The 1 skip is pre-existing and unrelated.
- Release contract: NO release this session. Set 068 ships its PyPI ai_router
  release in S6 (synthesis + release + dogfood + close). This session ships code
  only; do NOT flag "no version bump / no release" as a defect.
- Scope by design: this is S5 of a 6-session set. IN scope: build + wire + test
  the contract-test / CDC gate. OUT of scope (deferred to S6): wiring the
  blast-radius gating predicate that flips per-session routed verification to
  gated, the verification-surface synthesis doc, and any Explorer/extension UI.
  Do NOT flag these deferrals as defects; they are the S4 decision's explicit
  sequencing (routed-fate-decision.md transition guard).
- ASCII-only CLI/terminal output is a project convention (cp1252 Windows).
- The gate deliberately MIRRORS the Set 066 path-aware-critique gate (an existing,
  reviewed pattern): a per-set policy attribute recorded once at set start +
  immutable, a produce-then-validate split, posture-aware close-out wiring
  (required hard-TTY/soft-headless, advisory always-soft, none skip), fail-open.
  Divergence from that established pattern is what to scrutinize, not the pattern.

================ WHAT THIS SESSION BUILT ================
The contract-test / CDC gate: the deterministic verification FLOOR. A per-set,
opt-in `contractGate` (none|advisory|required) whose close-out gate confirms a
set's contract/falsifier tests ran and PASSED in the Set 068 S1 disposable
run_test cage and cover every PROBEABLE defect class, reserving the path-aware
critique agent for the NON-probeable residual (Experiment A H4: ~95% of seeded
defects are deterministically falsifiable). It is the replacement floor the S4
routed keep/demote/retire DEMOTE decision's transition guard waits on.

Design intent + the produce->validate rationale:
--- contract-gate-design.md ---
{design}

Canonical doc:
--- docs/contract-gate.md ---
{gate_doc}

================ THE NEW MODULE (review in full) ================
--- ai_router/contract_gate.py ---
{contract_gate}

================ CLOSE_SESSION WIRING (unified diff) ================
{close_diff}

================ ROUTER-CONFIG COMMENT ANCHOR ================
{cfg_anchor}

================ THE TWO JSON SCHEMAS (structural contract) ================
--- docs/contract-manifest.schema.json ---
{manifest_schema}

--- docs/contract-floor-result.schema.json ---
{floor_schema}

================ TESTS (summary; 84 new, all pass) ================
- test_contract_gate.py: policy attribute (default/record/immutable/seed/
  unreadable), manifest validator (valid + ~12 malformations incl. L-066-1
  schemaVersion int-not-bool/float, duplicate ids, non-bool probeable, bad
  coveredBy, uncovered-probeable-flagged), floor-result validator (passing/
  failing/timeout/leak/passed-mismatch/type guards), the PRODUCER driving the
  real S1 cage against a throwaway git repo (passing/failing/not-a-repo/no-
  manifest), the close-out validator (none no-op, happy path, identity
  mismatches, uncovered-probeable fail, missing/mismatched/non-passing floor,
  residual reporting), and the CLI.
- test_contract_gate_close.py: the close_session integration (none/advisory/
  required posture, set-terminal scoping, corrupt-activity-log warning),
  mirroring test_path_aware_critique_close_gate.py.
- test_contract_gate_schema.py: JSON Schema <-> pure-Python validator parity for
  BOTH artifacts (L-066-1), incl. the documented Python-only semantic rules
  (uncovered-probeable, passed-must-agree).

================ YOUR TASK ================
Review for CORRECTNESS, COMPLETENESS, and FALSE POSITIVES. Focus on:
1. Coverage-rule soundness: does the gate genuinely guarantee the floor carries
   every probeable defect class, and correctly treat the non-probeable residual
   as agent-reserved (not a failure)?
2. The floor pass criterion (ran AND exitCode==0 AND not timedOut AND
   worktreeRemoved) and the producer's `passed` write agreeing with the
   validator's derived criterion (the passed-mismatch rejection).
3. Identity checks (manifest + floor result must match THIS set; floor command
   must match the manifest) -- can a stale/copied/mismatched artifact satisfy a
   required gate?
4. The close_session wiring: set-terminal scoping, posture (required hard-TTY/
   soft-headless, advisory soft, none skip), fail-open ("any internal error
   never wedges close-out"), and the corrupt-activity-log loud-warning.
5. L-066-1 validator/schema parity: are there schema-constrained fields (required
   OR optional) the pure-Python validator fails to type-check, or int/bool/float
   confusions?
6. Any way the producer's S1-cage use could mutate the real tree, leak a
   worktree without detection, or mis-record a result.

Output a clear verdict line: exactly `VERIFIED` if you find no
Critical/Major issues, or `ISSUES_FOUND` with each issue labelled
Critical/Major/Minor, a file:concept location, and a concrete fix. Be specific;
do not invent issues to appear thorough (false positives are themselves a defect
this review must avoid)."""

    out_path = SET / out_name
    r = route(prompt, task_type="session-verification", complexity_hint=70,
              session_set=str(SET), session_number=5)
    out_path.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out_path} ({len(r.content)} chars)")
    print("model_used:", getattr(r, "model_used", None),
          "cost_usd:", round(getattr(r, "cost_usd", 0.0) or 0.0, 6))


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)

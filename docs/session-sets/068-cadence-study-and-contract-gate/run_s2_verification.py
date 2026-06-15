"""Set 068 S2 cross-provider session-verification.

Independent verifier: gpt-5.4 (openai) -- cross-provider for the Claude
orchestrator. S2 ships NO production code and NO release: it is (1) a SYMMETRIC
RE-GRADE of Experiment A (an inference over committed Set 067 data) and (2) a
PRE-REGISTRATION + cost model + harness skeleton for Experiment B (an
experimental design). So the verification target is the soundness of the
INFERENCE and the DESIGN, not code correctness. Persists raw output BEFORE
printing (L-064-3).
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
S067 = REPO / "docs" / "session-sets" / "067-pull-verifier-adapter-experiment-a"

regrade_md = (HERE / "experiment-a-regrade.md").read_text(encoding="utf-8")
audit_sym = (RG / "audit-symmetric.json").read_text(encoding="utf-8")
regrade_data = (RG / "experiment-a-regrade-data.json").read_text(encoding="utf-8")
evidence = (RG / "pathaware-crossfile-evidence.md").read_text(encoding="utf-8")
prereg_b = (HERE / "experiment-b-preregistration.md").read_text(encoding="utf-8")
cost_model = (HERE / "experiment-b" / "cost_model.py").read_text(encoding="utf-8")
skeleton = (HERE / "experiment-b" / "harness-skeleton.md").read_text(encoding="utf-8")
routed_audit = (S067 / "experiment-a" / "audit.json").read_text(encoding="utf-8")

# The 067 erratum (results section 8) is the question S2 answers; include it.
results_067 = (S067 / "experiment-a-results.md").read_text(encoding="utf-8")
erratum = results_067[results_067.index("## 8. Erratum"):]

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; they are the agreed
baseline / by-design scope for this session):

NO CODE, NO RELEASE THIS SESSION. Set 068 Session 2 of 6 ships NO production
code and NO PyPI release. It produces two analysis/design deliverables only:
(1) experiment-a-regrade.md -- a symmetric re-grade of the Set 067 Experiment A
data; (2) experiment-b-preregistration.md + experiment-b/{cost_model.py,
harness-skeleton.md} -- a pre-registration + the pre-committed cost model + the
harness skeleton. The Experiment B RUN is Session 3; the run_test cage + the
contract gate + the keep/demote/retire decision are S1/S4/S5; the release is S6.

SUITE BASELINE: full ai_router pytest suite GREEN (1548 passed, 1 skipped),
UNCHANGED from the S1 close -- nothing in ai_router/ changed this session
(testpaths=ai_router/tests; the docs/ experiment scripts are not collected).
cost_model.py ships with invariant self-tests that PASS. Assume green.

NO NEW DATA: the re-grade RE-ANALYSES the committed Set 067 raw outputs
(../067-.../experiment-a/raw/), it does not re-collect. regrade.py is
deterministic, no API. The small-n caveats from Experiment A persist by design;
the re-grade resolves the GRADING-SYMMETRY confound, not the sample-size one.

DELEGATION/AUTHORSHIP: this work was authored by the Claude Opus 4.8 orchestrator,
which (a) maintains the workflow under study, (b) is itself an Anthropic model
grading an experiment that bears on path-aware critique (which can use an
Anthropic provider) and on routed verification. That is a real conflict of
interest. The defense is that grading is mechanical (deterministic predicates +
a quoted-mechanism audit) and cross-provider-checked by YOU. Be adversarial about
any place the inference could be self-serving.

FOCUS your review on:

A. SYMMETRIC-AUDIT SOUNDNESS (the core of deliverable 1).
   A1. Is the ONE path-aware rejection B1:D12 correct? The claim: B1's tree3
       findings (k1-k3) name count_statements(D11), all_refs-drops-the-call/return
       category(D9), and build_index str(ref)(D10) -- but NEVER the seeded D12
       mechanism (collect_call_refs capturing only a single bare identifier via
       isidentifier()); the D12 predicate fired only on tokens carried by the D9
       finding. Check this against the evidence dump (DELIVERABLE 4). Is removing
       it right, and is B2:D12 correctly KEPT (B2 k2 names isidentifier)?
   A2. Are the 13 KEEPS defensible -- does each named path-aware cross-file catch
       actually name the seeded mechanism (not a token artifact)? Sample at least
       D5, D6 (esp. B2:D6, which is credited via k3's Low finding -- is that a
       legitimate union-level catch, or audit-generous?), and D9.
   A3. Is the standard applied SYMMETRICALLY -- the SAME 'names the mechanism'
       rule to both arms? The routed audit (DELIVERABLE 7) KEPT A1:D6/A1:D10 and
       REJECTED 6 routed cells. Does the re-grade's treatment of path-aware match
       that standard, neither stricter nor laxer? Is there any path-aware catch
       that SHOULD have been rejected under the routed standard but was kept (or
       vice versa)?

B. RE-GRADE INFERENCE (deliverable 1, Sections 3-5).
   B1. The pre-registered AUTOMATED PRIMARY is the per-replicate weighted mean +-
       across-K noise band (NOT the union). Under it: GPT B1-A1 = +0.2315 >
       band 0.0834 (EXCEEDS); Gemini B2-A2 = +0.0833 < band 0.111 (INSIDE).
       Do these follow from the data (DELIVERABLE 3)? Is calling the union the
       'audit-dependent secondary' view correct?
   B2. Is the 'automated primary is a conservative floor for GPT' argument valid
       (it still credits A1 with mechanism-wrong cross-file matches, so the true
       gap is >= +0.23)?
   B3. The erratum-CORRECTION: the re-grade says only D5 is a FULLY
       audit-INDEPENDENT existence proof, while D9 is audit-CONDITIONAL because
       routed's automated predicate DID match D9 (on a docstring 'subset' nitpick)
       and only the audit removes it. Verify D5 vs D9 in DELIVERABLE 3
       (existence_proofs) and the raw reasoning. Is this correction right, and is
       it fair to say it TIGHTENS rather than overturns the erratum?
   B4. H2 split: is 'a second routed provider adds nothing' genuinely
       audit-INDEPENDENT (A1_auto == A2_auto), and is the +0.31 'context is the
       bigger lever' magnitude correctly DOWNGRADED to exploratory? Any residual
       overclaim in the headline (Section 1)?

C. EXPERIMENT B DESIGN VALIDITY (deliverable 5 + cost model + skeleton).
   C1. Is the cadence mechanism coherent -- the claim that a coupling defect is
       in-snippet@introduction and MIGRATES to cross-file@close, giving
       per-session routed its one strong-window shot? Is this a sound, testable
       hypothesis or a rationalization?
   C2. Does the R-vs-Q control ACTUALLY isolate cadence from context (same routed
       surface, differ only in WHEN)? Is the R-vs-E confound (cadence x context)
       handled honestly?
   C3. Is the decision rule (Section 8) genuinely PRE-COMMITTED and FALSIFIABLE --
       can it return 'cadence HOLDS / keep routed'? Or is it rigged toward
       'retire'? Are the controls real nulls (no-coupling d=0 cannot show benefit
       by the cost model; coupling-blind tests the hollow-defense mode)?
   C4. Is the pre-registered cost_model.py HONEST -- deterministic, only-empirical-
       -input-is-catch-timing, can't be tuned post hoc? Are its invariants
       (d=0 cost timing-invariant; d>0 monotone; never-caught > caught-at-end) the
       right ones, and do they actually hold? Any way the constants
       (BASE_FIX/COUPLING_PENALTY/ESCAPE_PENALTY) bias the verdict?
   C5. Any threat to validity MISSING from Section 9 that could invalidate the S3
       result? Is the pilot gate (Section 10) sufficient?

D. INTERNAL CONSISTENCY. Do the numbers quoted in experiment-a-regrade.md match
   experiment-a-regrade-data.json exactly? Any arithmetic / citation error? Any
   claim in either doc unsupported by its evidence?
"""

SYSTEM_PROMPT = (
    "You are a senior research-methodology + software-verification reviewer "
    "giving an independent cross-provider verification of a completed analysis/"
    "design session (Set 068, Session 2: a symmetric re-grade of an experiment "
    "and the pre-registration of a follow-on experiment). You did not author it. "
    "Be rigorous and concrete: cite the specific claim / number / section / file. "
    "Judge statistical-inference honesty and experimental-design validity, not "
    "code style. Distinguish a real inference/design defect from a nit. End with a "
    'JSON verdict block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":'
    '[{"severity":"Critical|Major|Minor","claim":"<what>","problem":"<why>",'
    '"fix":"<how>"}]}.'
)

USER = f"""{CONVENTIONS}

=== DELIVERABLE 1: experiment-a-regrade.md (the symmetric re-grade conclusion) ===
{regrade_md}

=== DELIVERABLE 2: experiment-a-regrade/audit-symmetric.json (the symmetric overrides + per-cell quotes) ===
{audit_sym}

=== DELIVERABLE 3: experiment-a-regrade/experiment-a-regrade-data.json (machine output of regrade.py) ===
{regrade_data}

=== DELIVERABLE 4: experiment-a-regrade/pathaware-crossfile-evidence.md (raw path-aware cross-file catch text) ===
{evidence}

=== DELIVERABLE 5: experiment-b-preregistration.md (the Experiment B pre-registration) ===
{prereg_b}

=== DELIVERABLE 6: experiment-b/cost_model.py (the PRE-REGISTERED rework cost model + self-tests) ===
{cost_model}

=== DELIVERABLE 7 (CONTEXT): ../067-.../experiment-a/audit.json (the ORIGINAL one-directional routed audit -- the symmetry baseline) ===
{routed_audit}

=== CONTEXT: Experiment A results section 8 erratum (the question S2 answers) ===
{erratum}

=== DELIVERABLE 8: experiment-b/harness-skeleton.md (the S3 harness interface) ===
{skeleton}

Review per the FOCUS list (A-D). Return your findings then the JSON verdict block."""


def main():
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
    out = HERE / "s2-verification.md"
    out.write_text(
        "# Set 068 S2 -- Cross-provider verification (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude\n"
        "> orchestrator. Round 1. Target: the symmetric re-grade inference + the\n"
        "> Experiment B pre-registration/design (no production code this session).\n\n"
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

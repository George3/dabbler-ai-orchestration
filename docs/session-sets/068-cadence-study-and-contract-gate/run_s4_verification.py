"""Set 068 S4 -- cross-provider session verification of the routed keep/demote/retire
decision + its implementation. Saves raw verifier output to s4-verification.md (L-064-3)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402


def rd(p):
    return Path(p).read_text(encoding="utf-8")


DECISION = rd(HERE / "routed-fate-decision.md")
CONSULTS = "\n\n".join(
    f"===== CONSULT: {f.name} =====\n" + rd(f)
    for f in sorted((HERE / "routed-fate-consensus").glob("*.md"))
)
WORKFLOW_POLICY = rd(REPO / "docs/ai-led-session-workflow.md")
# extract just the two changed regions to keep the prompt focused
import re  # noqa: E402
m1 = re.search(r"### Verification-surface policy.*?(?=### Significance flagging)", WORKFLOW_POLICY, re.S)
m2 = re.search(r"### Step 6: End-of-Session Verification.*?dispatches to a different AI provider for independent review\..*?run this step exactly as written\.", WORKFLOW_POLICY, re.S)
WORKFLOW_EXCERPT = (m1.group(0) if m1 else "(policy subsection NOT FOUND)") + "\n\n---\n\n" + (m2.group(0) if m2 else "(Step 6 pointer NOT FOUND)")
CONFIG_EXCERPT = "\n".join(rd(REPO / "ai_router/router-config.yaml").splitlines()[534:560])

PROMPT = f"""\
You are the cross-provider session verifier for Session 4 of Set 068
(dabbler-ai-orchestration). Return the structured JSON verdict
({{"verdict": "VERIFIED" | "ISSUES_FOUND", "issues": [...]}}). Judge ONLY this
session's deliverable; do not re-litigate the experiments themselves.

## Conventions / baseline (read first)

- **Suite baseline:** `python -m pytest` = **1548 passed, 1 skipped** (unchanged
  from S1-S3). This session changed **no production code logic** — the only
  `ai_router/` change is a **comment-only anchor** in `router-config.yaml`; the
  rest is a decision record + workflow-doc prose. Do not ask for new tests: there
  is no new behavior to test (the transition guard means behavior is deliberately
  unchanged this session).
- **Release contract:** NO release this session. The PyPI `ai_router` release is
  Set 068 S6. No version bump here.
- **By-design scope:** S4 is a DECISION + a small doc/config implementation. The
  spec says the implementation "may be 'no code change'". The operator-confirmed
  decision is DEMOTE *with a transition guard*: the cut-over to gated routed
  verification does NOT take effect until the S5 contract-test gate is live, so
  S4 deliberately does NOT flip any behavioral flag and per-session routed
  verification REMAINS mandatory (including for S4's own close-out). Verifying
  "why didn't you change the config behavior?" is NOT a defect — that is the
  decision.

## What S4 was required to do (spec)

1. Read `experiment-a-regrade.md` + `experiment-b-results.md`.
2. ROUTE the keep/demote/retire decision through cross-provider consensus
   (decision-time consensus), record the journal; the OPERATOR confirms.
3. IMPLEMENT the chosen outcome (router-config.yaml / workflow-doc / close-out
   change the decision implies — may be "no code change"). Routed-verification
   status changes ONLY here and ONLY on the Experiment B evidence.
4. (this verification.)

## Evidence the decision must faithfully rest on

- Experiment A (+ symmetric re-grade): capability case for routed-as-default ruled
  out; lever is repository CONTEXT-ACCESS (path-aware provides it; snippet-fed
  routed cannot); a second routed provider buys nothing (H2).
- Experiment B: pre-registered verdict CADENCE DEFENSE DOES NOT HOLD **via clause
  B3** (R's edge over end-of-set is largely surface-coverage artifact + pure
  earliness, NOT Q-invisible cadence) — explicitly NOT the B1 "no cadence value"
  reading (B1 is false; the cadence mechanism IS real). R's one genuine residual:
  catches migrating cross-file coupling defects at introduction (5/5 early window).
  Capability at close: E (11-12/12) >> R (10/12) >> Q (4/12); path-aware E is NOT a
  perfect ceiling (one provider's E missed Critical BD6).

## Check for

- **Faithfulness:** does the decision record represent the evidence correctly —
  the B3 (not B1) verdict, "mechanism real but confounded", demote not retire,
  the narrow R-vs-E residual, E-not-a-perfect-ceiling? Any overclaim/underclaim?
- **Consensus integrity:** was the decision actually routed to TWO non-orchestrator
  providers with a devil's-advocate (steelman-KEEP) pass, and does the record
  match what the four consult outputs actually concluded? (Raw consults included.)
- **Coherence of the transition guard:** is "DEMOTE now, but stay mandatory until
  S5 gate is live" internally consistent across the decision record, the workflow
  policy subsection, the Step 6 note, and the config comment? Any place that
  implies routed is ALREADY gated/skipped (which would be wrong) ?
- **Internal consistency / stale echoes** across the four edited surfaces (L-065-1).
- **Scope discipline:** anything implemented that the decision did NOT authorize
  (e.g. a real behavioral flag flip), or any required element missing.

===== DELIVERABLE 1: routed-fate-decision.md =====
{DECISION}

===== DELIVERABLE 2: docs/ai-led-session-workflow.md (changed regions) =====
{WORKFLOW_EXCERPT}

===== DELIVERABLE 3: ai_router/router-config.yaml (verification: block header) =====
{CONFIG_EXCERPT}

===== SUPPORTING: the four raw consensus consults =====
{CONSULTS}
"""


def main():
    r = route(PROMPT, task_type="session-verification", complexity_hint=70,
              session_set=str(HERE), session_number=4)
    out = HERE / "s4-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print("model_used:", getattr(r, "model_used", None),
          "cost_usd:", round(getattr(r, "cost_usd", 0.0) or 0.0, 6))


if __name__ == "__main__":
    main()

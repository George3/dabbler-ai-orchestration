"""Set 046 Session 1 audit-pass cross-provider consensus driver.

Runs two-pass devil's-advocate verification on
[proposal.md](proposal.md):

  Pass A — straight cross-provider read (route + verify): "is this
           audit proposal sound?"
  Pass B — devil's-advocate framing (route + verify): the 5 biases
           in proposal §7 + 4 open questions in §8 are explicitly
           called out as the pressure test.

Outputs four files alongside proposal.md (pass_a_primary.md,
pass_a_verify.md, pass_b_primary.md, pass_b_verify.md) and a
cost_summary.json so the running spend is observable.

Per `feedback_split_large_verification_bundles` the proposal is
~300 LOC of markdown — safely under the 700-LOC bundle-split
threshold, so a single-shot route per pass is fine.

Per `feedback_ai_router_route_result_handling` the RouteResult is
dumped to JSON before any attribute access (lesson learned the
hard way).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402
PROPOSAL_PATH = HERE / "proposal.md"
SESSION_SET = "046-explorer-enrichment-from-harvest-records"
SESSION_NUMBER = 1


def _dump(label: str, obj) -> None:
    """Dump any ai_router result object to JSON for inspection."""
    try:
        as_dict = {
            k: getattr(obj, k)
            for k in dir(obj)
            if not k.startswith("_") and not callable(getattr(obj, k))
        }
        print(f"\n=== {label} (fields) ===")
        for k, v in as_dict.items():
            preview = str(v)[:200]
            print(f"  {k}: {preview}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (dump failed: {exc})")


def _write_response(out_path: Path, label: str, result, verifier=False) -> None:
    """Persist the model's text response to disk for audit-trail purposes."""
    # RouteResult uses `content`; VerificationResult uses `raw_response`
    text = (
        getattr(result, "raw_response", None)
        or getattr(result, "content", None)
        or getattr(result, "response", None)
        or getattr(result, "text", None)
        or getattr(result, "output", None)
        or ""
    )
    model = (
        getattr(result, "model_name", None)
        or getattr(result, "verifier_model", None)
        or getattr(result, "model", "unknown")
    )
    provider = (
        getattr(result, "verifier_provider", None)
        or getattr(result, "generator_provider", None)
        or getattr(result, "provider", "unknown")
    )
    cost = (
        getattr(result, "total_cost_usd", None)
        or getattr(result, "verifier_cost_usd", None)
        or getattr(result, "cost_usd", None)
        or getattr(result, "cost", None)
    )
    tokens_in = (
        getattr(result, "input_tokens", None)
        or getattr(result, "verifier_input_tokens", None)
    )
    tokens_out = (
        getattr(result, "output_tokens", None)
        or getattr(result, "verifier_output_tokens", None)
    )
    verdict = getattr(result, "verdict", None)
    header = [
        f"# {label}",
        "",
        f"- **Provider:** {provider}",
        f"- **Model:** {model}",
        f"- **Cost:** {cost}",
        f"- **Tokens (in/out):** {tokens_in}/{tokens_out}",
    ]
    if verifier:
        header.append(f"- **Verdict:** {verdict}")
    header.extend(["", "---", "", str(text)])
    out_path.write_text("\n".join(header), encoding="utf-8")
    print(f"  -> wrote {out_path.name} ({len(str(text))} chars)")


def run_pass(label: str, prompt: str, output_prefix: str) -> dict:
    """Route + verify a single pass; persist both responses; return cost dict."""
    print(f"\n========== {label}: ROUTE ==========")
    route_result = ai_router.route(
        content=prompt,
        task_type="analysis",
        context=(
            "This is a session-set scope-lock audit proposal. The author is "
            "Claude Opus 4.7. The audit needs a cross-provider read before "
            "the spec.md is rewritten to lock scope. Apply the bias-cautions "
            "framework where relevant."
        ),
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _dump(f"{label} route_result", route_result)
    _write_response(HERE / f"{output_prefix}_primary.md", f"{label} — Primary read", route_result)

    print(f"\n========== {label}: VERIFY ==========")
    verify_result = ai_router.verify(
        route_result=route_result,
        original_task=prompt,
        task_type="analysis",
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _dump(f"{label} verify_result", verify_result)
    _write_response(
        HERE / f"{output_prefix}_verify.md",
        f"{label} — Cross-provider verification",
        verify_result,
        verifier=True,
    )

    return {
        "label": label,
        "primary_model": getattr(route_result, "model_name", "unknown"),
        "primary_provider": getattr(route_result, "model_id", "unknown"),
        "primary_cost": getattr(route_result, "total_cost_usd", None),
        "verify_model": getattr(verify_result, "verifier_model", "unknown"),
        "verify_provider": getattr(verify_result, "verifier_provider", "unknown"),
        "verify_cost": getattr(verify_result, "verifier_cost_usd", None),
        "verify_verdict": getattr(verify_result, "verdict", None),
    }


def main() -> int:
    proposal_text = PROPOSAL_PATH.read_text(encoding="utf-8")
    print(f"Proposal loaded: {len(proposal_text)} chars, "
          f"{len(proposal_text.splitlines())} lines")

    pass_a_prompt = (
        "# Audit task: cross-provider read of Set 046 scope-lock proposal\n\n"
        "Below is a Pass A audit proposal for Session Set 046 (Explorer\n"
        "Enrichment from Harvest Records). The proposal scope-locks a\n"
        "stub-mode session set. Please read it as an independent reviewer\n"
        "and report:\n\n"
        "1. **Soundness of the candidate dispositions (§3).** Are the\n"
        "   six dispositions correctly classified as IN SCOPE / DEFER /\n"
        "   ALREADY SHIPPED? Flag any that are misclassified.\n"
        "2. **Soundness of the parked architectural question handling (§4).**\n"
        "   Is the v4-schema-deferral-to-its-own-set right? Is the\n"
        "   blocked-on-prereqs lifecycle bundling correct?\n"
        "3. **Session breakdown (§6).** Is the 6-session arc balanced?\n"
        "   Is any session over- or under-scoped?\n"
        "4. **Operator-locked deliverables (a/b/c).** Are they correctly\n"
        "   mapped onto the proposed sessions?\n"
        "5. **Any missing leverage point** the audit failed to surface.\n\n"
        "Return a verdict (ENDORSE / ENDORSE WITH REVISIONS / REJECT) at\n"
        "the top of your response, then itemize specific concerns.\n\n"
        "---\n\n"
        + proposal_text
    )

    pass_b_prompt = (
        "# Devil's-advocate audit task: pressure-test the Set 046 scope-lock proposal\n\n"
        "Below is a Pass A audit proposal for Session Set 046. Pass A has\n"
        "already been read by an independent provider. This is Pass B: a\n"
        "**devil's-advocate** pass.\n\n"
        "The proposal author (Claude Opus 4.7) flagged five specific biases\n"
        "in §7 and four open questions in §8. Your job is to specifically\n"
        "**invert** each bias-cautioned choice and argue why the inverted\n"
        "choice may be correct. Then opine on whether the proposal's choice\n"
        "or its inversion should win.\n\n"
        "The five biases to pressure-test (verbatim from §7):\n\n"
        "1. **Bias 1** — overweighting canonical state (`orchestrator` block)\n"
        "   over observed evidence (Harvest Records) for deliverable (b).\n"
        "2. **Bias 2** — overweighting router-ledger over harvest cost for §3.2.\n"
        "3. **Bias 3** — defer-bias on §3 / §4 (writer-bypass + multi-AI conflict\n"
        "   refinements).\n"
        "4. **Bias 4** — under-scoping the migrator by bundling it with §3.5\n"
        "   in Session 5.\n"
        "5. **Bias 5** — under-resourcing the README screenshot by parking it\n"
        "   on Session 6.\n\n"
        "For each: state the inverted position, give the strongest argument\n"
        "for the inversion, then state whether you'd flip the proposal's\n"
        "choice or stand by it. End with a single bottom-line verdict:\n"
        "ENDORSE PROPOSAL AS-IS / ENDORSE WITH SPECIFIC BIAS FLIPS / REJECT.\n\n"
        "Also opine on the four open questions in §8.\n\n"
        "---\n\n"
        + proposal_text
    )

    pass_a_summary = run_pass("PASS A", pass_a_prompt, "pass_a")
    pass_b_summary = run_pass("PASS B (devil's-advocate)", pass_b_prompt, "pass_b")

    summary = {
        "session_set": SESSION_SET,
        "session_number": SESSION_NUMBER,
        "passes": [pass_a_summary, pass_b_summary],
    }
    (HERE / "cost_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print("\n========== SUMMARY ==========")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

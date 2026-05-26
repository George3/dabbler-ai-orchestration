"""Set 048 Session 1 audit-pass cross-provider consensus driver.

Runs two-pass devil's-advocate verification on
[proposal.md](proposal.md):

  Pass A - straight cross-provider read (route + verify): "are the
           dispositions under the carry-forward locks sound?"
  Pass B - devil's-advocate framing (route + verify): the 8 biases
           in proposal section 10 + 5 open questions in section 11
           are explicitly called out as the pressure test.

Outputs four files alongside proposal.md (pass_a_primary.md,
pass_a_verify.md, pass_b_primary.md, pass_b_verify.md) and a
cost_summary.json so the running spend is observable.

Per feedback_split_large_verification_bundles the proposal is ~480
lines of markdown - safely under the 700-LOC bundle-split threshold,
so a single-shot route per pass is fine.

Per feedback_ai_router_route_result_handling the RouteResult is
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
SESSION_SET = "048-lightweight-tier-parity"
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
            "This is a session-set scope-lock audit proposal for Set 048 "
            "(Lightweight-Tier Parity). The author is Claude Opus 4.7. "
            "Set 047 closed yesterday and locked the v4 schema + four "
            "operator premises P1-P4 that carry forward to Set 048. The "
            "operator also locked four additional directives L1-L4 (path-"
            "reference prompts; hierarchical context menu; remove Open AI "
            "Assignment; close-on-blur). The audit needs a cross-provider "
            "read before spec.md is rewritten to lock implementation scope. "
            "Apply the bias-cautions framework where relevant."
        ),
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _dump(f"{label} route_result", route_result)
    _write_response(HERE / f"{output_prefix}_primary.md", f"{label} - Primary read", route_result)

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
        f"{label} - Cross-provider verification",
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
        "# Audit task: cross-provider read of Set 048 scope-lock proposal\n\n"
        "Below is a Pass A audit proposal for Session Set 048 (Lightweight-\n"
        "Tier Parity). The proposal scope-locks a stub-mode session set\n"
        "under carry-forward locks from Set 047's audit (premises P1-P4,\n"
        "decisions D1-D5) and four new operator-locked additions L1-L4.\n"
        "Please read it as an independent reviewer and report:\n\n"
        "1. **Soundness of the `--no-router` mode design (Group A,\n"
        "   sections A1-A4).** Are the activation-mechanism choice (CLI >\n"
        "   env > spec tier), lazy imports, verification short-circuit,\n"
        "   and backcompat scope sound? Flag any that are mis-scoped.\n"
        "2. **Soundness of the copyable-prompt design (Group B, sections\n"
        "   B1-B3).** The operator's L1 path-reference format is locked,\n"
        "   but the per-command details, enablement rules, and clipboard\n"
        "   mechanism are open. Are the choices sound? Flag misses.\n"
        "3. **Soundness of the context-menu IA refresh (Group C, sections\n"
        "   C1-C4).** L2/L3/L4 are locked premises but the rendering-\n"
        "   approach decision (cursor-anchor + HTML submenu vs QuickPick)\n"
        "   and the close-on-blur + close-button choice are NOT pre-locked.\n"
        "4. **Soundness of the doc-revision and migrator scope (Group D\n"
        "   + E5 + E8).** Are §D1-D4 and §E5/E8 appropriately scoped?\n"
        "5. **Session breakdown (section 9).** Is the 6-session arc\n"
        "   balanced? Should Sessions 3+4 (copyable prompts + context-\n"
        "   menu) merge? Should the bundled Set-047-plus-Set-048 publish\n"
        "   in Session 6 be split into independent ship moments?\n"
        "6. **Any missing audit topic** the proposal failed to surface.\n"
        "   Pay particular attention to: receiving-agent capability\n"
        "   variation under L1 (Copilot Chat vs Claude Code vs Codex);\n"
        "   accessibility implications of HTML submenus; the suggested-\n"
        "   state tri-state generality (Full tier too, or Lightweight only).\n\n"
        "Return a verdict (ENDORSE / ENDORSE WITH REVISIONS / REJECT) at\n"
        "the top of your response, then itemize specific concerns.\n\n"
        "---\n\n"
        + proposal_text
    )

    pass_b_prompt = (
        "# Devil's-advocate audit task: pressure-test the Set 048 scope-lock proposal\n\n"
        "Below is a Pass A audit proposal for Session Set 048. Pass A has\n"
        "already been read by an independent provider. This is Pass B: a\n"
        "**devil's-advocate** pass.\n\n"
        "The proposal author (Claude Opus 4.7) flagged eight specific\n"
        "biases in section 10 and five open questions in section 11. Your\n"
        "job is to specifically **invert** each bias-cautioned choice and\n"
        "argue why the inverted choice may be correct. Then opine on\n"
        "whether the proposal's choice or its inversion should win.\n\n"
        "The eight biases to pressure-test (verbatim from section 10):\n\n"
        "1. **Bias 1** - Drafter biases toward explicit-and-multiple over\n"
        "   minimal-and-implicit (§A1 three-knob activation).\n"
        "2. **Bias 2** - Drafter biases toward path-reference design after\n"
        "   L1 lock (§B1 — but receiving-agent capability varies).\n"
        "3. **Bias 3** - Drafter biases toward cursor-anchor preservation\n"
        "   in §C1 (HTML submenu vs QuickPick).\n"
        "4. **Bias 4** - Drafter biases toward triple-redundancy for the\n"
        "   suggested-state reminder (§E4).\n"
        "5. **Bias 5** - Drafter biases toward warnings over gates (§D2).\n"
        "6. **Bias 6** - Drafter biases toward repo-level review-criteria\n"
        "   storage (§E10).\n"
        "7. **Bias 7** - Drafter biases toward separating B2 and B7 into\n"
        "   different sessions (§9 sessions 3 and 4).\n"
        "8. **Bias 8** - Drafter biases toward bundling Set 047's HELD\n"
        "   publishes with Set 048's release (§9 session 6).\n\n"
        "For each: state the inverted position, give the strongest argument\n"
        "for the inversion, then state whether you'd flip the proposal's\n"
        "choice or stand by it. End with a single bottom-line verdict:\n"
        "ENDORSE PROPOSAL AS-IS / ENDORSE WITH SPECIFIC BIAS FLIPS / REJECT.\n\n"
        "Also opine on the five open questions in section 11.\n\n"
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

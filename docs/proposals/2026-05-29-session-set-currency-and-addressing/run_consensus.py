"""Set 050 S1 cross-provider consensus runner (devil's-advocate two-pass).

Calls gemini-pro and gpt-5-4 DIRECTLY via providers.call_model — NOT route()
— so there is no RouteResult.provider attribute access (the recurring trap).
Falls back gpt-5-4 -> gpt-5-4-mini on failure. Prints per-call cost so the
$10 NTE is respected and reportable.
"""
import sys
from pathlib import Path

from ai_router.config import load_config
from ai_router.providers import call_model

HERE = Path(__file__).parent
PROPOSAL = (HERE / "proposal.md").read_text(encoding="utf-8")

cfg = load_config()
MODELS = cfg["models"]


def cost(model_key, in_tok, out_tok):
    m = MODELS[model_key]
    return (in_tok / 1_000_000) * m["input_cost_per_1m"] + (
        out_tok / 1_000_000
    ) * m["output_cost_per_1m"]


def call(model_key, system_prompt, user_msg, max_tokens=8000):
    m = MODELS[model_key]
    gp = dict(m.get("generation_params") or {})
    res = call_model(
        provider_name=m["provider"],
        model_id=m["model_id"],
        system_prompt=system_prompt,
        user_message=user_msg,
        max_tokens=max_tokens,
        config=cfg["providers"][m["provider"]],
        generation_params=gp,
    )
    c = cost(model_key, res.input_tokens, res.output_tokens)
    return res, c


SYSTEM = (
    "You are a senior software architect reviewing a design proposal for "
    "'dabbler-ai-orchestration', a Python (ai_router) + TypeScript (VS Code "
    "extension) monorepo that is the canonical source of shared AI-orchestration "
    "infrastructure for several consumer repos. Session sets live in "
    "docs/session-sets/<slug>/ each with a spec.md and a session-state.json "
    "(schema versions v1..v4; a normalize_to_v4_shape reader shim consumes all "
    "of them). Migrators migrate_v3_to_v4 and migrate_lightweight_to_canonical_v4 "
    "already exist. Be concrete, terse, and decisive. You are NOT here to be "
    "agreeable; surface real risks."
)

PASS_A = """Below is a design proposal with the author's recommended disposition
for eleven open questions (Q1-Q11). For EACH question give exactly:

Qn: AGREE | AGREE-WITH-MODIFICATION | DISAGREE
  - one or two sentences of rationale
  - if not plain AGREE: the concrete alternative you'd lock instead

Then a final section "TOP RISKS" listing the 2-3 weakest points in the whole
proposal. Keep it tight; no preamble.

=== PROPOSAL ===
""" + PROPOSAL

PASS_B = """You are now in DEVIL'S-ADVOCATE mode. The author wrote these
recommendations and has an architectural preference for minimal new surface
area (reuse existing hooks/CLIs, push logic into ai_router rather than the
extension). Assume that bias may have led them astray. Build the STRONGEST
possible case AGAINST the most consequential choices, specifically:

1. Q1/Q3 — Is a network-fetched GitHub manifest actually worth adding a
   network dependency (even fail-open) to EVERY session start, versus just
   shipping the current-version as a constant in the (pinned) router plus a
   CI check? Argue the manifest is over-engineering. Then argue why it isn't.
   Also: is raw-on-master dangerous (consumers fetch a half-merged manifest)
   vs pinning to a tag?
2. Q6 — Folding the drift check into the existing start_session SessionStart
   invoker couples two unrelated concerns and means a repo can't get the
   guard without the orchestrator-writer hook. Argue for a SEPARATE, single-
   purpose hook instead.
3. Q9 — The author under-delivers Feature 2 by keeping the resolver in
   ai_router and NOT teaching the extension's copy-prompt/Explorer to accept
   a number, even though the spec's deliverable list says those surfaces
   accept a bare number. Argue this is scope-dodging.
4. Q7 — `--apply` re-introduces migration into a set whose explicit non-goal
   is "no silent auto-migration." Argue it's scope creep that should be cut.

For each of the four, give: the strongest counter-argument, then your FINAL
call (keep author's choice | flip to the alternative | compromise X). End
with "NET: which of the author's 11 dispositions should actually change."

=== PROPOSAL (same as before) ===
""" + PROPOSAL


def run_engine(label, primary_key, fallback_key, system, user):
    try:
        res, c = call(primary_key, system, user)
        return primary_key, res, c
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[{label}] {primary_key} failed: {e}\n  -> fallback {fallback_key}\n")
        res, c = call(fallback_key, system, user)
        return fallback_key, res, c


total = 0.0
out = []
for pass_label, prompt in (("pass-a", PASS_A), ("pass-b", PASS_B)):
    for engine_label, primary, fallback in (
        ("gemini", "gemini-pro", "gemini-pro"),
        ("openai", "gpt-5-4", "gpt-5-4-mini"),
    ):
        used, res, c = run_engine(f"{pass_label}/{engine_label}", primary, fallback, SYSTEM, prompt)
        total += c
        hdr = f"## {pass_label} — {engine_label} (model={used}, in={res.input_tokens} out={res.output_tokens} cost=${c:.4f})\n\n"
        (HERE / f"{pass_label}-{engine_label}.md").write_text(hdr + res.content, encoding="utf-8")
        out.append(f"{pass_label}/{engine_label}: {used} ${c:.4f} ({res.output_tokens} out)")
        print(f"DONE {pass_label}/{engine_label} -> {used} ${c:.4f}")

print("\n".join(out))
print(f"TOTAL CONSENSUS SPEND: ${total:.4f}")

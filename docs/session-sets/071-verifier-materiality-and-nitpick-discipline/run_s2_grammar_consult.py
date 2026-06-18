"""Set 071 S2 — operator-requested cross-provider consult on the verdict grammar.

The operator deferred the binary-vs-three-state decision to a routed consult:
ask GPT-5.4 and Gemini-Pro independently, then route both recommendations to a
fresh Claude (opus) for a synthesizing perspective. Operator is inclined toward
the simpler/binary grammar but wants another perspective. Raw outputs written to
disk first (L-064-3), then printed.
"""

from __future__ import annotations

from pathlib import Path

import ai_router

HERE = Path(__file__).resolve().parent

BRIEF = """\
# Decision: verifier verdict grammar for Set 071 Session 2

You are advising on a focused engineering decision. Give a crisp recommendation,
not an essay.

## The goal of the change
Set 071 stops a strong adversarial verifier from manufacturing immaterial
findings and stops the re-verify loop from churning rounds on nits — WITHOUT
weakening the devil's-advocate framing that catches real cross-file/correctness
defects (hard constraint L-069-2: never weaken framing to fix nitpick churn).
Session 1 already shipped, additively, a materiality "so what?" gate, an
anti-nitpick clause, merge-impact severity anchoring, a plausible-path-to-harm
anti-laundering guardrail, and a non-blocking `NITS` output section in BOTH
reviewer prompt templates. Session 2 adds the severity-aware blocking logic and
the re-verify loop discipline. The verdict-grammar choice below is what S2 must
settle first.

## The two options

### Option A — BINARY (keep VERIFIED / ISSUES_FOUND)
- Keep the existing two verdict tokens. A Minor-only / nits-only result is
  reported as VERIFIED with the immaterial points under a non-blocking `NITS`
  section.
- Add a pure-Python `is_blocking_verdict(verdict, issues)` classifier:
  >=1 Critical/Major finding => blocking (opens/continues a re-verify round);
  Minor-only / nits-only => non-blocking (recorded, not loop-opening);
  unknown/missing severity in an ISSUES_FOUND verdict defaults to BLOCKING
  (anti-laundering: when in doubt, escalate).
- NO change to `parse_verification_response`'s public `(verdict, issues)`
  contract, the `sN-issues.json` envelope schema, `session-issues-schema.md`, or
  the Set 070 framing-pin tests (which assert the literal `VERIFIED` /
  `ISSUES FOUND` tokens).

### Option B — THREE-STATE (add VERIFIED_WITH_NITS)
- Introduce a third verdict token, `VERIFIED_WITH_NITS`, for the
  correct-work-plus-immaterial-nits case.
- Requires changing `parse_verification_response`, the `sN-issues.json` envelope
  schema, `session-issues-schema.md`, every downstream consumer that switches on
  the verdict token (close_session `resolve_close_verdict`, the
  status->verdict fallback, the Explorer), and the framing-pin tests that assert
  the binary tokens. Larger blast radius this session.

## Context that matters
- The cross-provider consult that ORIGINALLY scoped this set split on exactly
  this point: Gemini proposed the third state (VERIFIED_WITH_NITS); GPT proposed
  keeping the binary grammar and redefining the *blocking threshold* instead. The
  spec adopted the binary default to preserve the machine contract, and flagged
  S2 as an operator decision point that may override to three-state.
- The functional anti-churn behaviour (Minor-only never blocks, never reopens the
  loop) is achievable under BOTH options — the question is whether the extra
  verdict token earns its blast radius, or whether the binary verdict + a
  separate `is_blocking` predicate captures the same information more cheaply.
- This repo's standard is "universal core, gated extensions"; additive, low-blast
  changes are strongly preferred, and a hand-written Python validator that mirrors
  a JSON Schema must hold parity in both directions (a known recurring defect
  class here — every envelope/schema change risks validator<->schema drift).

## What to return
1. **RECOMMENDATION:** exactly one of `BINARY` or `THREE-STATE`.
2. **RATIONALE:** 3-6 sentences. Weigh expressiveness vs. blast radius / contract
   stability / the validator-schema-parity risk.
3. **STRONGEST COUNTERARGUMENT:** the single best argument for the option you did
   NOT pick, stated fairly.
4. **MIGRATION NOTE (only if you pick THREE-STATE):** the minimum set of files
   that must change and the one most likely to be missed.
"""


def ask(model: str, label: str) -> str:
    res = ai_router.query(
        model=model,
        content=BRIEF,
        task_type="analysis",
        session_set=str(HERE),
        session_number=2,
    )
    out = HERE / f"s2-grammar-consult-{label}.md"
    out.write_text(
        f"MODEL: {model}\nCOST: {getattr(res, 'cost', 'n/a')}\n"
        f"{'=' * 70}\n{res.content}\n",
        encoding="utf-8",
    )
    print(f"[{label}] {model} -> {out.name} ({len(res.content)} chars, "
          f"cost={getattr(res, 'cost', 'n/a')})")
    return res.content


def main() -> None:
    gpt = ask("gpt-5-4", "gpt")
    gemini = ask("gemini-pro", "gemini")

    synth_brief = (
        BRIEF
        + "\n\n---\n\n## Two independent provider recommendations to weigh\n\n"
        + "### GPT-5.4 said:\n\n" + gpt
        + "\n\n### Gemini-Pro said:\n\n" + gemini
        + "\n\n---\n\nYou are a FRESH reviewer who has not seen this set before. "
        "Read both recommendations above, weigh them against the context, and give "
        "your own independent RECOMMENDATION (`BINARY` or `THREE-STATE`), a short "
        "rationale, and explicitly note where (if anywhere) the two providers' "
        "reasoning is weak or overstated. The operator is inclined toward the "
        "simpler/binary grammar; say plainly whether the evidence supports that "
        "lean or argues against it."
    )
    res = ai_router.query(
        model="opus",
        content=synth_brief,
        task_type="analysis",
        session_set=str(HERE),
        session_number=2,
    )
    out = HERE / "s2-grammar-consult-claude-synthesis.md"
    out.write_text(
        f"MODEL: opus (fresh Claude synthesis)\nCOST: {getattr(res, 'cost', 'n/a')}\n"
        f"{'=' * 70}\n{res.content}\n",
        encoding="utf-8",
    )
    print(f"[synthesis] opus -> {out.name} ({len(res.content)} chars, "
          f"cost={getattr(res, 'cost', 'n/a')})")


if __name__ == "__main__":
    main()

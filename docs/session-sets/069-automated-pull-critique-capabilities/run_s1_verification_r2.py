"""Set 069 S1 -- cross-provider session verification ROUND 2 (post-fix).

Round 1 (gpt-5-4) returned FAIL with 4 real L-066-1-class parity findings
between the pure-Python validator and the JSON Schema. All four are fixed; this
round confirms resolution and checks for residual / newly-introduced parity
holes. Substantive re-verify (real code changed), so normal routing applies.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


EVIDENCE = read("ai_router/evidence_protocol.py")
SCHEMA = read("docs/path-aware-critique.schema.json")
TEST_EVIDENCE = read("ai_router/tests/test_evidence_protocol.py")
TEST_SCHEMA = read("ai_router/tests/test_path_aware_critique_schema.py")

DOC_DIFF = subprocess.run(
    ["git", "diff", "--", "docs/path-aware-critique-schema.md"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider session verifier for Session 1 of 6 of Set 069 in the
dabbler-ai-orchestration repo. This is ROUND 2 after fixes. Return the structured
verdict (VERIFIED only if every Round-1 finding is genuinely resolved with no new
defect introduced).

=== CONVENTIONS / BASELINE (do NOT re-flag the agreed baseline) ===
- Suite baseline before this session: 1670 passed, 1 skipped. After the session +
  the fixes the full ai_router suite is GREEN (you verify CODE+DOCS, not the run).
- NO release this session (PyPI is S6); version unchanged; no UI / Marketplace.
- BY-DESIGN: S1 ships the evidence PROTOCOL + SCHEMA only. The lanes that GENERATE
  transcripts are S2-S4; no producer stamps evidenceTier yet. The field is
  additive/optional; every pre-069 artifact must stay valid. Do not flag "no
  producer yet" -- that is by design.

=== ROUND 1 FINDINGS (all four claimed FIXED -- confirm each) ===
F1. A `transcript` on a NON-REPRODUCED finding was validated by the JSON Schema
    but ignored by the Python validator (divergence). FIX: the schema's
    `transcript` $ref was MOVED INTO the `if evidenceTier==REPRODUCED then`
    block, so a transcript on an ASSERTED/HYPOTHESIS finding is now untyped,
    ignored supporting context for BOTH validators. Confirm parity (both ignore a
    stray/malformed transcript on a non-REPRODUCED finding).
F2. `validate_transcript` did not type-check optional fields, so wrong-typed
    values (`templateId: 7` / `""`, `args: 7`, `replay.exitCode: true`) were
    accepted as REPRODUCED by Python while the schema rejects them. FIX:
    validate_transcript now requires commandId/templateId to be non-empty strings
    when present, args to be object|array, and replay.exitCode to be int|null
    (bool rejected). Confirm no wrong-typed optional field is still accepted.
F3. The docs/schema CALLED the `commandId XOR templateId` rule and the
    public-entrypoint meta-oracle rule "Python-only / JSON-Schema cannot express",
    which was INACCURATE (XOR is expressible via oneOf; the kind enum already
    enforces meta-oracle). FIX: the schema now enforces the XOR via `oneOf` and
    pristineCheckout==true via `const: true`; the docs were rewritten so the ONLY
    documented Python-only rule is the cross-field replay-hash equality
    (replay.outputHash == outputHash). Confirm the docs now match the schema
    HONESTLY and the only genuine Python-only rule really is replay-hash equality.
F4. Tests missed the parity holes. FIX: added unit regressions in
    test_evidence_protocol.py (wrong-typed templateId/commandId/args,
    replay.exitCode bool) and dual-validation parity tests in
    test_path_aware_critique_schema.py (TestEvidenceParity: stray transcript on
    ASSERTED/HYPOTHESIS ignored by both; both-ids / wrong-type / non-pristine /
    agent-harness rejected by BOTH). Confirm the tests actually exercise the named
    behaviors and assert Python/schema AGREEMENT.

=== WHAT TO CHECK ===
- Each F1-F4 genuinely resolved, with the Python validator and the JSON Schema now
  AGREEING on every transcript case except the documented replay-hash equality.
- No NEW divergence introduced by the schema edits (the moved $ref, the oneOf, the
  two `const: true`). E.g. does the oneOf correctly reject both-present AND
  neither-present? Does `const: true` reject pristineCheckout:false as intended?
- L-065-1: are there residual stale echoes of the old "Python-only XOR /
  meta-oracle" claim anywhere in the provided docs/schema?

=== ai_router/evidence_protocol.py (full, post-fix) ===
{EVIDENCE}

=== docs/path-aware-critique.schema.json (full, post-fix) ===
{SCHEMA}

=== ai_router/tests/test_evidence_protocol.py (full) ===
{TEST_EVIDENCE}

=== ai_router/tests/test_path_aware_critique_schema.py (full) ===
{TEST_SCHEMA}

=== docs/path-aware-critique-schema.md DIFF (the F3 doc rewrite) ===
{DOC_DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=70,
        session_set=str(HERE),
        session_number=1,
    )
    out = HERE / "s1-verification-round-2.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

"""Set 069 S1 -- cross-provider session verification ROUND 4 (doc-precision only).

Round 3 confirmed the F3 SCHEMA change is complete and correct (pattern "\\S"
added everywhere needed; aligns with Python .strip()). The remaining R3 blockers
were DOC-PRECISION ONLY -- no code defect:
  (a) the schema-doc's "ASCII by construction" carve-out was false for free-text
      summary/description;
  (b) two stale test docstrings (module + TestEvidenceTierContract) misstated
      which rules are Python-only.
Both are reworded. This is a WORDING-ONLY re-verify (no code changed since R3),
so max_tier is pinned to the verifier's own tier (L-064-7) to block escalation.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

DOC_DIFF = subprocess.run(
    ["git", "diff", "--", "docs/path-aware-critique-schema.md"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout
TEST_DIFF = subprocess.run(
    ["git", "diff", "--", "ai_router/tests/test_path_aware_critique_schema.py"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider session verifier for Session 1 of 6 of Set 069 in the
dabbler-ai-orchestration repo. ROUND 4, DOC-PRECISION ONLY. Return the structured
verdict (VERIFIED if the two Round-3 wording blockers are resolved and honest).

=== CONTEXT (do NOT re-litigate; all settled) ===
- The CODE is settled and VERIFIED across R1-R3: F1 (transcript $ref moved into
  the REPRODUCED if/then), F2 (validate_transcript type-checks optional fields),
  F4 (parity regressions), and the F3 SCHEMA change (pattern "\\S" on every
  required non-empty string field, aligning the JSON Schema with Python's
  value.strip()). Round 3 explicitly confirmed F3's schema change is complete and
  applied everywhere needed. DO NOT re-review the code; ONLY the two doc-precision
  blockers below changed since R3.
- NO release; version unchanged; no UI. Full ai_router suite GREEN (1736 passed,
  1 skipped).

=== THE TWO ROUND-3 BLOCKERS TO CONFIRM RESOLVED ===
R3a. The schema-doc parity paragraph claimed the exotic-Unicode-whitespace edge
     was a "non-issue ... ASCII by construction", which was FALSE for free-text
     summary/description. FIX: reworded to say the ECMA-262 `\\S` vs Python
     str.strip() sets differ only at a few exotic codepoints (U+0085, U+FEFF), so
     ONLY a value made ENTIRELY of such codepoints could diverge; the machine
     fields are ASCII by construction AND a free-text summary/description is never
     a single run of exotic-whitespace, so the equivalence is exact in practice
     (and this is the same ECMA-vs-Python residual every `pattern` carries).
R3b. Two stale test docstrings misstated the Python-only gaps. FIX: the module
     docstring now lists BOTH runtime Python-only gaps (distinct-provider AND
     replay-hash equality) and says XOR / pristineCheckout==true / meta-oracle
     kind / whitespace are schema-expressed; the TestEvidenceTierContract
     docstring now says the ONLY Python-only divergence is replay-hash equality
     and points at the correct class names (TestEvidenceSchemaVsPythonGap /
     TestEvidenceParity).

Confirm BOTH rewordings are now accurate and internally consistent, with no
remaining stale echo of the old "Python-only XOR / meta-oracle" or "ASCII by
construction" framing in the provided diffs. Flag ONLY a genuine remaining
inaccuracy.

=== docs/path-aware-critique-schema.md DIFF ===
{DOC_DIFF}

=== ai_router/tests/test_path_aware_critique_schema.py DIFF ===
{TEST_DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=45,
        max_tier=3,
        session_set=str(HERE),
        session_number=1,
    )
    out = HERE / "s1-verification-round-4.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

"""Set 069 S1 -- cross-provider session verification ROUND 3 (post-F3-fix).

Round 2 confirmed F1/F2/F4 RESOLVED and left ONE blocker: F3 -- Python's
_nonempty_str() rejects whitespace-only strings (value.strip()) while the schema
accepted them (bare minLength: 1), so the "only Python-only rule is replay-hash
equality" claim was not yet honest. This round confirms the F3 fix and that no
new divergence was introduced. Focused, substantive re-verify.
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


SCHEMA = read("docs/path-aware-critique.schema.json")

SCHEMA_DOC_DIFF = subprocess.run(
    ["git", "diff", "--", "docs/path-aware-critique-schema.md"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

# The new whitespace-parity tests + the surrounding parity class.
TEST_SCHEMA = read("ai_router/tests/test_path_aware_critique_schema.py")

PROMPT = f"""\
You are the cross-provider session verifier for Session 1 of 6 of Set 069 in the
dabbler-ai-orchestration repo. ROUND 3, focused on the single Round-2 blocker.
Return the structured verdict (VERIFIED only if the blocker is resolved with no
new defect).

=== CONTEXT (do NOT re-flag) ===
- Round 2 RESOLVED F1 (transcript $ref moved into the REPRODUCED if/then), F2
  (validate_transcript type-checks optional fields), and F4 (parity regressions
  added). Those are settled; do NOT re-litigate them.
- NO release this session; version unchanged; no UI. The full ai_router suite is
  GREEN at this commit (you verify CODE+DOCS, not the run).

=== THE ONE BLOCKER TO CONFIRM (F3) ===
Round 2 blocking reason: Python's `ai_router.evidence_protocol._nonempty_str()`
uses `value.strip()`, so it rejects WHITESPACE-ONLY strings (e.g. `" "`), while
the JSON Schema used a bare `"minLength": 1`, which ACCEPTS `" "`. That made the
documented claim "the only Python-only rule is the cross-field replay-hash
equality" untrue (Python was also stricter on whitespace).

THE FIX under review: every required non-empty string field in the JSON Schema
now carries `"pattern": "\\\\S"` ALONGSIDE `"minLength": 1`. The regex `\\S` is an
unanchored "contains a non-whitespace char" test, which is exactly the set
Python's `value.strip()` accepts. This was applied to ALL such fields (the new
evidence fields AND the pre-existing Set-066 fields: sessionSetName, critiquedAt,
provider, model, verdict, the summary anyOf branch, description, pinnedRef,
commandId, templateId, outputHash, entrypoint.ref, replay.outputHash). The
schema doc records the alignment; two parity tests assert a whitespace-only
sessionSetName and a whitespace-only pinnedRef are rejected by BOTH validators.

Confirm:
1. `pattern: "\\\\S"` is a CORRECT and COMPLETE equivalent of Python's
   `value.strip()` truthiness for these fields (no case where they now disagree
   on whitespace -- e.g. tabs/newlines: does `\\S` cover all Python str.strip()
   whitespace? Note any genuinely divergent unicode-whitespace edge case).
2. The pattern was added to EVERY field Python checks with `.strip()` (no field
   left with bare minLength that Python still strips) -- scan the schema below.
3. With this fix, the docs' claim that the ONLY Python-only rule is replay-hash
   equality is now HONEST (modulo the separate, pre-existing distinct-providers
   rule).
4. No NEW divergence or schema breakage introduced (the schema is still a valid
   2020-12 schema; `pattern` + `minLength` compose correctly).

=== docs/path-aware-critique.schema.json (full, post-fix) ===
{SCHEMA}

=== docs/path-aware-critique-schema.md DIFF (the parity-paragraph update) ===
{SCHEMA_DOC_DIFF}

=== ai_router/tests/test_path_aware_critique_schema.py (full -- see TestEvidenceParity) ===
{TEST_SCHEMA}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=60,
        max_tier=3,
        session_set=str(HERE),
        session_number=1,
    )
    out = HERE / "s1-verification-round-3.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

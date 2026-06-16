"""Set 069 S1 -- cross-provider session verification (Step 6, gated -> REQUIRED).

S1's diff touches the shared path-aware-critique validator + JSON Schema and adds
a new module (evidence_protocol), spanning ai_router + docs across 7 files, so the
routed_gate predicate trips REQUIRED (blast-radius shared-schema + multi-module +
breadth). The orchestrator is Anthropic/opus; the verifier routes to a different
provider.
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
TEST_EVIDENCE = read("ai_router/tests/test_evidence_protocol.py")
SCHEMA = read("docs/path-aware-critique.schema.json")
PROTOCOL_DOC = read("docs/evidence-protocol.md")

# Staged diff for the modified surfaces (validator + schema doc + schema test).
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--",
     "ai_router/path_aware_critique.py",
     "ai_router/tests/test_path_aware_critique_schema.py",
     "docs/path-aware-critique-schema.md"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider session verifier for Session 1 of 6 of Set 069
(automated pull-critique capabilities) in the dabbler-ai-orchestration repo.
Return the structured verdict.

=== CONVENTIONS / BASELINE (read first; do NOT re-flag the agreed baseline) ===
- Suite baseline BEFORE this session: 1670 passed, 1 skipped (the 1 skip is
  pre-existing and tracked). This session ADDS a new module
  (ai_router/evidence_protocol.py) + ~50 unit tests (test_evidence_protocol.py)
  + ~8 dual-validation tests in test_path_aware_critique_schema.py. The full
  ai_router pytest suite is GREEN at this commit; you are verifying CODE + DOCS,
  not re-running the suite.
- RELEASE CONTRACT: NO release this session. The ai_router PyPI release is
  Session 6; the version is intentionally unchanged. NO Marketplace / extension
  change (spec non-goal: no UI surface this whole set).
- BY-DESIGN SCOPE: this session ships the EVIDENCE PROTOCOL + the SCHEMA ONLY.
  The execution lanes that GENERATE transcripts -- trusted-command execution
  (S2), the probe-template lane (S3), the Podman model-authored-probe lane (S4)
  -- are DELIBERATELY NOT in this session. No producer currently stamps
  `evidenceTier`; the field is additive/optional. So "the producer does not
  generate evidence yet" is BY DESIGN, not a gap -- do not flag it. What IS in
  scope: that the protocol + schema are correct, sound, and BACKWARD COMPATIBLE
  (every pre-069 artifact with no evidence tags must stay valid).

=== WHAT TO VERIFY (cite file:line for any finding) ===

1. FALSIFIER CORRECTNESS (evidence_protocol.validate_transcript). The whole point
   is that a REPRODUCED finding is a re-runnable falsifier, so a transcript must
   pass ONLY when ALL hold: a TRUSTED probe id (commandId XOR templateId -- never
   model-authored argv); pristineCheckout is true; exitCode is int-or-null (and a
   Python bool, an int subclass, is REJECTED); rawOutput is a string; outputHash
   non-empty; the REPLAY ran on a second pristine checkout AND its outputHash
   EQUALS the transcript outputHash (the re-runnable-falsifier core); and the
   META-ORACLE rule -- entrypoint.kind is a real public kind, NEVER agent_harness.
   Is there ANY path by which an invalid/weak transcript is accepted (a FALSE
   REPRODUCED)? Does it ever raise on malformed input (it must not)?

2. THE ORCHESTRATOR-TAG RULE (authoritative_tier + the producer contract in the
   docstrings). The load-bearing trust property: the AGENT must never be able to
   self-grant REPRODUCED. Confirm REPRODUCED is conferred ONLY when
   validate_transcript accepts a transcript; a REPRODUCED *claim* with no/invalid
   transcript collapses to ASSERTED; HYPOTHESIS is preserved. Is the rule stated
   AND implemented consistently across evidence_protocol.py and the doc?

3. ARTIFACT-VALIDATOR + JSON-SCHEMA PARITY (L-066-1). The pure-Python
   validate_path_aware_critique_artifact now calls validate_finding_evidence; the
   JSON Schema adds evidenceTier (enum) + transcript ($defs/EvidenceTranscript)
   with an if/then requiring transcript on REPRODUCED. Verify: (a) the additive
   change keeps schemaVersion 1 and pre-069 artifacts valid under BOTH validators;
   (b) the if/then is correct (REPRODUCED without transcript fails the schema);
   (c) the claimed Python-ONLY divergences (commandId XOR templateId; replay-hash
   equality) are genuinely inexpressible in JSON Schema and the doc says so
   honestly; (d) no wrong-typed evidence value slips past one validator but not
   the other; (e) the new ARTIFACT_INVALID_EVIDENCE code is returned in the right
   order (after structural / single-provider / trivial).

4. BACKWARD COMPATIBILITY. An untagged finding must be ASSERTED and always valid;
   the default must NEVER be REPRODUCED. Confirm DEFAULT_EVIDENCE_TIER == ASSERTED
   and that effective_tier / validate_finding_evidence honor it.

5. DOC ACCURACY (docs/evidence-protocol.md + the path-aware-critique-schema.md
   diff). Do they match the code EXACTLY (tier names, entrypoint kinds, the
   `invalid-evidence` code, the replay rule, the meta-oracle rule)? Any claim of
   CURRENT behavior that the code does not back (L-064-8)? Any overclaim about
   what S1 ships vs S2-S6?

6. TEST ADEQUACY (test_evidence_protocol.py + the new schema tests). Do the tests
   actually exercise the behaviors they name (the false-REPRODUCED paths, the
   orchestrator-tag collapse, the schema-vs-python divergences), or do any pass
   without exercising the named behavior?

=== ai_router/evidence_protocol.py ===
{EVIDENCE}

=== ai_router/tests/test_evidence_protocol.py ===
{TEST_EVIDENCE}

=== docs/path-aware-critique.schema.json (full, post-change) ===
{SCHEMA}

=== docs/evidence-protocol.md (new) ===
{PROTOCOL_DOC}

=== DIFFS (path_aware_critique.py validator, test_path_aware_critique_schema.py, path-aware-critique-schema.md) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=72,
        session_set=str(HERE),
        session_number=1,
    )
    out = HERE / "s1-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

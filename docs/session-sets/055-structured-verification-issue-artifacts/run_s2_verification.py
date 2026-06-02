"""Set 055 S2 cross-provider verification of the implementation bundle.

Verifier: gemini-2.5-pro (google) — a different provider from the
Claude/Opus orchestrator that wrote S2. Feeds the ACTUAL artifact files
plus neutral framing of the locked S1 design and the engineering calls
S2 made, and asks for a structured verdict. Mirrors the Set 052 S3 call
mechanics (direct providers.call_model; no RouteResult.provider access).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

FILES = [
    "docs/session-issues.schema.json",
    "docs/session-issues-schema-example.json",
    "docs/session-issues-schema.md",
    "ai_router/tests/test_session_issues_schema.py",
]


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def main():
    cfg = yaml.safe_load(
        (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
    )
    gcfg = cfg["providers"]["google"]
    model = next(
        m for m in cfg["models"].values() if m.get("model_id") == "gemini-2.5-pro"
    )

    blocks = "\n\n".join(f"=== FILE: {rel} ===\n{read(rel)}" for rel in FILES)

    system_prompt = (
        "You are a senior reviewer performing an independent cross-provider "
        "verification. You did NOT write this work. Be skeptical and concrete. "
        "Judge whether the implementation faithfully matches the locked design, "
        "whether the schema/example/test are internally consistent and correct, "
        "and whether the documentation updates are accurate and non-contradictory. "
        "Return ONLY a JSON object with keys: verdict (one of "
        "'VERIFIED' | 'VERIFIED_WITH_NOTES' | 'ISSUES_FOUND'), "
        "critical (array of {title, detail}), important (array of {title, detail}), "
        "nice_to_have (array of {title, detail}), "
        "decision_rulings (array of {decision, ruling, rationale}), summary (string)."
    )

    user_message = f"""## Context

This is Set 055 Session 2 (the final, implementation session) of the
dabbler-ai-orchestration repo. Session 1 locked a design for a new
root-level, machine-readable verifier-findings artifact named
`sN-issues.json`. The repo already persists verifier PROSE in
`sN-verification.md` and the session outcome in `disposition.json`, but
the structured `{{"verdict","issues"}}` list produced by
`ai_router.verification.parse_verification_response` was transient. The
old nested `issue-logs/` directory is RETIRED and must not be revived.

## The S1 locked design (authoritative, from verdict.md)

- Q1 One file per findings-bearing round: round 1 = `sN-issues.json`;
  later findings-bearing retries = `sN-issues-round-<M>.json`. Never
  overwrite.
- Q2 Small ENVELOPE, not a bare array: top-level `schemaVersion`,
  `sessionNumber`, `verificationRound`, `verificationVerdict`, `issues[]`.
- Q3 Preserve verifier issue fields verbatim (`description` the only
  reliable required field; `category`/`severity` loose strings) and allow
  optional, additive, ADVISORY resolution fields (`resolution_status`,
  `resolution_notes`, `resolved_in_round`).
- Q4 No empty file for VERIFIED rounds. Invariant: presence of an
  `sN-issues*.json` file MEANS that round found issues.
- Q5 Manual / `--no-router` flows MAY write the same envelope when they
  genuinely have structured findings, but are not required to fabricate
  JSON from prose; a missing file on a manual set is not an error.
- Q6 NO required helper. Docs/schema/example first; a helper is allowed
  only if it removes REAL duplication and stays convenience-only.
- Q7 NO runtime readers in Set 055 (close_session, gates, metrics,
  Explorer all ignore the artifact).
- Q8 Release ONLY if Python code ships. Docs/schema/example-only work
  needs no PyPI/Marketplace release.

## The actual artifacts under review

{blocks}

## Documentation updates S2 made (verify these claims for accuracy)

1. `docs/ai-led-session-workflow.md`:
   - Added an `sN-issues.json` row to the session-set artifact table
     describing the findings-bearing-only, never-overwrite, no-runtime-reader
     contract.
   - Marked the legacy `session-reviews/`/`issue-logs/` table row as
     RETIRED and pointed it at the new root-level artifact.
   - Added Step 6 item "4a": persist the structured findings to
     `sN-issues.json` ONLY when the verdict is not VERIFIED; a VERIFIED
     round writes no file; no runtime reader; do not revive `issue-logs/`.
   - Extended Step 7 ISSUES_FOUND item 3 to persist the structured list
     and optionally append advisory `resolution_*` annotations, while
     keeping prose canonical.
   - Updated the cancel-history sentence and the "what artifacts appear"
     paragraph to mention `sN-issues*.json`.
2. `docs/planning/session-set-authoring-guide.md`: added `sN-issues.json`
   to the per-session artifact list and reinforced `issue-logs/` retired.

## Engineering decisions S2 made — please rule on each

DECISION 1 — NO helper shipped (Q6). S2 judged there is no real
duplication to remove: no code in the `ai_router` package currently
writes verifier-findings artifacts (orchestrators across engines write
the prose/JSON files themselves), so a Python helper would have zero
in-repo callers and would be speculative. S2 therefore stayed
docs/schema/example/test-only. RULING REQUESTED: is "no helper" the
correct application of the locked Q6 "only if it removes real
duplication" test, or is there a real duplication point that justifies a
helper?

DECISION 2 — schema + example live under `docs/` (not in the packaged
`ai_router/schemas/`). The repo's disposition schema lives at
`ai_router/schemas/disposition.schema.json` (shipped in the wheel via
pyproject `schemas/*.json`) BECAUSE `disposition.py` validates against a
dataclass and a parity test enforces it. Set 055 has NO runtime reader
(Q7), so S2 placed `session-issues.schema.json` and the example under
`docs/` (alongside the existing `docs/session-state-schema-example.json`
precedent) to keep them decoupled from the wheel and avoid changing the
packaged surface — which keeps the set release-free per Q8. RULING
REQUESTED: is the `docs/` placement correct and consistent, or should the
schema have gone into `ai_router/schemas/` for discoverability parity
with disposition (which would arguably make it shippable code → a
release)?

DECISION 3 — the drift guard is a TEST, not a runtime reader. S2 proves
"the JSON shape is real" via `test_session_issues_schema.py`, which
validates the shipped example against the schema and asserts the locked
invariants (presence-means-issues, minimal envelope valid, resolution
fields optional, empty-issues rejected, closed envelope, open issue
objects). RULING REQUESTED: does a pytest that reads repo docs files and
runs jsonschema validation stay within the "no runtime readers" Q7 scope
(tests are not distributed runtime), and does it adequately satisfy the
S1 deliverable "at least one example fixture proving the JSON shape is
real"? Also: does shipping this test + a static JSON schema/example
(no new importable `ai_router` runtime module) correctly count as
"no Python code ships" under Q8, i.e. NO release required?

Review the artifacts, check the documentation claims for accuracy and
internal consistency, rule on the three decisions, and return the JSON
verdict. Flag any place where the schema, example, doc, or test
contradict each other or the locked design."""

    result = providers.call_model(
        provider_name="google",
        model_id="gemini-2.5-pro",
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=16000,
        config=gcfg,
        generation_params={"thinking_budget": 6000},
    )

    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print("=== VERIFIER RAW OUTPUT ===")
    print(result.content)
    print("=== USAGE ===")
    print(json.dumps({
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(in_cost + out_cost, 6),
        "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()

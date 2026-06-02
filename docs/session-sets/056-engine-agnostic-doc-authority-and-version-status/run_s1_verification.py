"""Set 056 S1 cross-provider verification of the audit & design-lock bundle.

Verifier: gemini-2.5-pro (google) — a different provider from the
Claude/Opus orchestrator that ran the audit. Feeds the ACTUAL migrated
files plus the audit record and asks the verifier to independently judge
whether the audit's claims are accurate, the locked contract is sound,
and the out-of-band migration (commit e5a3476) is complete and faithful.
Mirrors the Set 055 S2 call mechanics (direct providers.call_model; no
RouteResult.provider access; provider-scoped config; 16k tokens +
thinking_budget).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

FILES = [
    "docs/session-sets/056-engine-agnostic-doc-authority-and-version-status/s1-audit-record.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "docs/repository-reference.md",
    "docs/planning/project-guidance.md",
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
        "This is a documentation-authority audit session, not a code change. "
        "Judge whether the audit record's factual claims are TRUE against the "
        "actual file contents provided, whether the locked documentation-"
        "authority contract is sound and internally consistent, and whether the "
        "out-of-band migration is genuinely complete and faithful to the "
        "contract. Return ONLY a JSON object with keys: verdict (one of "
        "'VERIFIED' | 'VERIFIED_WITH_NOTES' | 'ISSUES_FOUND'), "
        "critical (array of {title, detail}), important (array of {title, detail}), "
        "nice_to_have (array of {title, detail}), "
        "claim_checks (array of {claim, holds (true|false), evidence}), "
        "summary (string)."
    )

    user_message = f"""## Context

This is Set 056 Session 1 (Audit & design-lock) of the
dabbler-ai-orchestration repo. The set's goal: promote a durable
principle that shared operational facts a future orchestrator needs must
live in an engine-agnostic doc or canonical package metadata, NOT only
in an engine-specific bootstrap file (`CLAUDE.md` = Claude Code only,
`AGENTS.md` = Codex/Copilot only, `GEMINI.md` = Gemini only). The
motivating incident: `AGENTS.md` froze at extension v0.8.0 (19 versions
behind) because the version walk was only maintained in `CLAUDE.md`.

## Unusual situation this audit reckons with

The substantive migration that Session 2 was scoped to perform was
applied OUT OF BAND by the operator in commit `e5a3476` ("misc fixes to
guidance.") BEFORE this audit ran, while `session-state.json` still
showed both sessions `not-started`. Session 1 therefore became
audit-and-RATIFY the already-committed migration, plus lock the contract
and supply the missing decision trail. The file `s1-audit-record.md`
(provided below) is that record.

## Spec deliverables (what the set must achieve)

1. A durable guiding principle: shared operational facts belong in
   engine-agnostic docs or package metadata, not only in the three
   engine bootstrap files.
2. A canonical `docs/repository-reference.md` section for current
   consumer repos, current release status, and a concise version walk.
3. Root engine files that POINT to the canonical section instead of
   carrying independent version histories.
4. Live planning/review docs retargeted to cite the engine-agnostic
   source, not `CLAUDE.md`, for release/version/consumer facts.

## The four open design questions (audit ratified all to "recommended")

Q1 canonical section location: keep inside repository-reference.md (not
a new version-status.md). Q2 history depth: concise recent walk +
changelog pointers (not full prose). Q3 root-file scope: keep only
concise stable facts + a pointer; no independent version history. Q4
secondary docs: at minimum retarget release-process docs + review-
criteria templates.

## Files under review (the actual current repo state)

{blocks}

## Your task

Independently verify, against the file contents above:

1. CLAIM CHECKS — for each of these audit claims, decide whether it
   holds and cite the concrete evidence (or counter-evidence):
   (a) The canonical "Documentation authority and release status"
       section exists in repository-reference.md and contains the
       guiding principle + a consumer table + a release-status table +
       a concise recent version walk.
   (b) All three engine files (CLAUDE.md, AGENTS.md, GEMINI.md) point to
       the canonical section and NO LONGER carry an independent version
       walk / "Extension versioning" history.
   (c) The guiding principle is recorded in
       docs/planning/project-guidance.md.
   (d) No engine file still presents stale frozen version facts (e.g.
       AGENTS.md's old v0.8.0 "Extension versioning" block is gone).

2. CONTRACT SOUNDNESS — is the locked contract in s1-audit-record.md §3
   sound, internally consistent, and a faithful realization of the four
   spec deliverables and the four recommended dispositions? Flag any
   contradiction or gap.

3. COMPLETENESS — is the migration genuinely COMPLETE, or did the audit
   miss a live surface that still treats an engine file as the canonical
   source of shared facts? The audit flags one residual nit (the
   consumer-table column header reads `ai_router` in CLAUDE.md but
   `ai_router copy` in AGENTS.md and GEMINI.md). Confirm whether that
   drift is real, and surface any OTHER drift you find.

Return the JSON verdict. A VERIFIED verdict means the audit's claims
hold, the contract is sound, and the only open items are the
non-blocking nits the audit already named."""

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

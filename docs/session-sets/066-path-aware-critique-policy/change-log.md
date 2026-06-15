# Change Log — 066-path-aware-critique-policy

> Ships **Path-Aware Critique** as a first-class, **tier-orthogonal** per-set
> policy — institutionalizing the manual, multi-provider, path-aware end-of-set
> review the team already practices (GitHub Copilot driving GPT-5.4 +
> Gemini-Pro over the repo). Released as `dabbler-ai-router` **0.20.0**. The
> automated tool-loop adapter (067) and the routed-fate / cadence study (068)
> are the sequenced follow-on sets.

## Sessions

### Session 1 — Policy surface + blast-radius predicate + artifact contract (VERIFIED)

- `pathAwareCritique: none | advisory | required` per-set attribute (parsed from
  the spec config; recorded **once at set start, immutable thereafter** as an
  `activity-log.json` entry, `kind: "path_aware_critique"`), mirroring the
  Set 057 `verificationMode` machinery. Tier-orthogonal.
- The multi-provider critique-artifact contract (`path-aware-critique.json`):
  JSON Schema (`docs/path-aware-critique.schema.json`) + a pure-Python runtime
  validator (`>= 2` **distinct** providers, content-non-trivial) + schema doc.
- The `P_set = any(P_task)` blast-radius predicate (`ai_router.blast_radius`) —
  **advisory only**, never a hard auto-set.
- 72 tests. Cross-provider verified (gpt-5.4, R1 ISSUES_FOUND -> R2 VERIFIED).

### Session 2 — Net-new content-aware close-out gate (VERIFIED)

- `validate_path_aware_critique_gate` + `close_session` wiring: on the
  **set-terminal** close, `required` -> hard-block in an interactive TTY /
  soft-warn headless (Set 057 Q6 fail-posture); `advisory` -> always soft-warn;
  `none` -> skip. Net-new on the Full-tier close path (the Lightweight-only
  `dedicated-verification` gate could not be reused — a verified erratum to the
  Set 065 proposal). Fail-open in the non-block direction (import inside the
  broad guard).
- 19 tests (suite 1391). Cross-provider verified (gpt-5.4, R1 1 Major fixed +
  1 Minor disproven as a cp1252 artifact -> R2 VERIFIED).

### Session 3 — Docs, prompt template, dogfood, release (VERIFIED via dogfood)

- Reusable operator prompt template
  `ai_router/prompt-templates/path-aware-critique.md` (packaged in the wheel).
- Canonical manual-workflow docs: the *end-of-set Path-Aware Critique stage* in
  `docs/ai-led-session-workflow.md`; pointers in `project-guidance.md` and
  `session-set-authoring-guide.md`.
- **Dogfood (the headline of this session).** This set declared
  `pathAwareCritique: required` and was gated by its own close-out gate. Its own
  multi-provider path-aware critique (GPT-5.4 + Gemini-Pro, run through Copilot)
  returned **ISSUES_FOUND** from both providers and caught **four real
  defects**, all fixed before release:
  1. A corrupt `activity-log.json` could **silently disarm** the gate
     (`required` collapsed to `none`). Fixed: a new
     `path_aware_critique_record_unreadable` helper + a loud, non-blocking
     warning at the set-terminal close.
  2. The gate accepted a **stale/cross-set artifact**. Fixed: an artifact
     **identity check** (`sessionSetName` must match the set;
     `pathAwareCritique` must match the recorded level).
  3. + 4. Two **validator/JSON-Schema parity gaps** (optional-field types;
     non-integer `schemaVersion` `1.0`/`True`). Fixed: the pure-Python validator
     now type-checks those fields.
  Regression tests added for all four; the raw verdicts are saved at
  `path-aware-critique.json` (the artifact) and the per-provider files
  `s3-path-aware-critique-gpt-5.4.md` / `path-aware-critique-gemini.md`.
- Release: `ai_router` 0.19.0 -> **0.20.0** (pyproject + `__init__` + CHANGELOG).
- Final suite green; drift guard clean.

## Net result

A shipped, tested, tier-orthogonal Path-Aware Critique policy enforceable at
close-out via the proven manual flow — hardened by its own dogfood. The
path-aware multi-provider critique demonstrated exactly the value the Set 065
evidence predicted: it caught a class of cross-artifact / parity / identity
defects a snippet-fed single-shot verifier would not have seen.

## Next session set (routed recommendation)

**067 — first-party tool-loop adapter + Experiment A** (confirmed by routed
analysis; see `s3-next-set-recommendation.md`). Recommended orchestrator for
067 S1: **claude-code / anthropic / claude-opus-4-8 / high**. Flagged
prerequisites: finalize the tool contract + Experiment A success criteria, and
confirm Anthropic/OpenAI/Google API access before bindings work begins.

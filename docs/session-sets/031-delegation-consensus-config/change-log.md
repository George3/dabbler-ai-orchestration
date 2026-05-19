# Set 031: Delegation Consensus Config V1

**Status:** Complete (2 of 2 sessions)
**Created:** 2026-05-19
**Closed:** 2026-05-19
**Total cost:** $0.051 of $5.00 NTE (Session 1: $0.020 Round A; Session 2: $0.031 across Round A + Round B + one wasted re-run from a bash/PowerShell env-var mix-up)
**PyPI release:** [`dabbler-ai-router 0.5.0`](https://pypi.org/project/dabbler-ai-router/0.5.0/) (tag-driven OIDC trusted publishing, workflow run [26128035426](https://github.com/darndestdabbler/dabbler-ai-orchestration/actions/runs/26128035426))

---

## Context

The Dabbler workflow already routes substantive reasoning through
`route(task_type=…)` and ends each session with mandatory cross-
provider verification. What it did NOT do is delegate in-session
design / architecture / process decisions to routed consensus before
falling back to `AskUserQuestion`. Set 031 ships the config knob that
lets a repo opt into that delegation.

Set 031 is the IMPLEMENTATION set for a design that was already
authored, cross-engine-vetted, and three-way approved by the operator
on 2026-05-17 (per [`docs/planning/delegation-consensus-config.md`](../../planning/delegation-consensus-config.md)).
The audit phase was intentionally skipped per memory
`feedback_audit_then_spec_for_substantial_features`'s carve-out
("operator wants three-way agreement before non-trivial work
begins" — three-way agreement was already on disk).

---

## Session 1: Schema acceptance + journal format + workflow doc

**Status:** Complete (2026-05-19)
**Orchestrator:** Claude Opus 4.7 @ effort=high
**Verification:** gemini-pro, $0.020, one Critical finding (addressed
mid-session: model entries with missing `provider` key could silently
bypass the engine-mismatch check)

### Three open questions (operator-confirmed at session start)

Asked via `AskUserQuestion` 2026-05-19; all three resolved to Claude's
recommended answer:

| # | Question | Operator decision |
|---|---|---|
| Q1 | Where does the implementation session set live? | **This repo (`dabbler-ai-orchestration`)** |
| Q2 | Default `categories` list — narrower or broader? | **Narrower V1: 4 mechanical categories** (`refactor-placement`, `file-layout`, `scoping`, `spec-clarification`) |
| Q3 | Journal git-tracked or gitignored? | **Committed JSONL + gitignored `consensus-decisions/` full-payload dir** |

### Shipped

1. **`delegation.decision_consensus` sub-block** in
   [`ai_router/router-config.yaml`](../../../ai_router/router-config.yaml).
   Default `enabled: false` (backward compatible — every existing
   repo's behavior unchanged). V1 defaults: 4 mechanical categories
   (`refactor-placement`, `file-layout`, `scoping`,
   `spec-clarification`); engines `[openai:gpt-5-4, google:gemini-pro]`;
   `unresolved_action: ask_user`; journal at
   `ai_router/consensus-decisions.jsonl`; full-payload sibling dir at
   `ai_router/consensus-decisions/`.
2. **Schema validation in [`ai_router/config.py`](../../../ai_router/config.py)** —
   `_validate_decision_consensus` invoked at the `load_config`
   boundary. Validates: engines parse as `provider:model` and
   cross-check against the configured `models:` table (model entries
   without a `provider` key are rejected per the S1 Round-A Critical
   finding); categories are one of the V1/V1.5/V2 whitelist slugs;
   `unresolved_action` is `ask_user` or
   `proceed_with_orchestrator_judgment`; `journal_path` and
   `journal_full_payloads_dir` are writable paths or `null`. Unknown
   sub-keys are tolerated with a one-time per-load warning
   (forward-compat).
3. **[`ai_router/consensus_journal.py`](../../../ai_router/consensus_journal.py)** — new module:
   `ConsensusRecord` dataclass, `compute_question_hash` (sha256:-prefix
   over question + category + ISO timestamp), `append_record` (POSIX
   append + flush + best-effort fsync), `write_full_payload`
   (temp+rename Markdown sibling file, `<ISO timestamp>-<hash>.md`),
   one-shot `write_consensus_record` convenience, and
   `validate_record_inputs` enum guard.
4. **AJV mirror** in
   [`tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts`](../../../tools/dabbler-ai-orchestration/src/configEditor/schemaValidator.ts)
   so the visual config editor accepts the new sub-block alongside the
   Python loader.
5. **[`docs/ai-led-session-workflow.md`](../../ai-led-session-workflow.md) → "Decision-time consensus" section** —
   new top-level section after "Cross-provider verification". Six-step
   decision tree, human-only vs consensus-eligible category split as a
   table, journal record example, opt-in path, three explicit limits-
   of-consensus guardrails.
6. **33 new tests** (17 schema + 16 journal). Full `ai_router` suite
   went 599 → 633 passed + 1 skipped.

### Round A — Critical fix landed mid-session

gemini-pro flagged: a `models:` entry that omitted the `provider` key
would slip past the engine-mismatch check, because the validator
joined `entry['provider'] + ':' + entry['model_id']` without first
asserting `provider` existed — a stray legacy entry could be silently
accepted as a valid `decision_consensus.engines` target. Fix landed
in `ai_router/config.py` with regression test
`test_engine_provider_missing_in_model_rejected`.

---

## Session 2: Per-agent pointers + PyPI release + cross-repo notification + close-out

**Status:** Complete (2026-05-19)
**Orchestrator:** Claude Opus 4.7 @ effort=high (operator override at
S2 start of S1 disposition's `sonnet-medium` recommendation;
reasoning headroom kept available in case the PyPI release surfaced
anything unexpected per spec R4)
**Verification:** gemini-pro Round A $0.008 (REQUEST CHANGES on
past-tense drift in CHANGELOG) + Round B $0.007 (APPROVE after the
fix) + one wasted $0.009 re-run from a bash-vs-PowerShell env-var
syntax mix-up = $0.031 total

### Shipped

1. **[`ai_router/CHANGELOG.md`](../../../ai_router/CHANGELOG.md) 0.5.0 entry** summarizing every
   Set 031 deliverable (Session 1's schema + validator + journal +
   docs + tests, plus Session 2's pointer blocks + version bump +
   gitignore).
2. **Version bumps** — `pyproject.toml` 0.4.0 → 0.5.0; matching
   `ai_router/__init__.py` `__version__` bump. The release workflow's
   tag-vs-pyproject check requires both agree on the canonical PEP
   440 form.
3. **`.gitignore`** — adds `ai_router/consensus-decisions/` (the
   default-on but disk-heavy full-payload sibling directory). The
   JSONL journal itself (`ai_router/consensus-decisions.jsonl`) is
   NOT gitignored — by design, follows the `router-metrics.jsonl`
   precedent so the audit trail survives across conversations.
4. **Per-agent instruction-file pointers.** Byte-identical
   "Decision-time consensus (pointer)" section added to
   [`CLAUDE.md`](../../../CLAUDE.md), [`AGENTS.md`](../../../AGENTS.md),
   and [`GEMINI.md`](../../../GEMINI.md). Keep-agent-instruction-
   files-in-sync convention: drift here would be a finding.
5. **Cross-repo notification.** Same byte-identical block added to
   `dabbler-platform/CLAUDE.md` and `dabbler-access-harvester/CLAUDE.md`
   (left uncommitted in those working trees — operator commits/pushes
   on their own timeline). **`dabbler-homehealthcare-accessdb`
   skipped** — Lightweight tier, no local `docs/ai-led-session-
   workflow.md` for the pointer to resolve against; the CHANGELOG
   note "consumer adoption doesn't require those edits" covers the
   Lightweight case.
6. **PyPI release** — `dabbler-ai-router 0.5.0` shipped via the
   documented tag-driven OIDC trusted-publishing workflow at
   [`.github/workflows/release.yml`](../../../.github/workflows/release.yml)
   (per [`docs/planning/release-process.md`](../../planning/release-process.md)).
   No `twine`, no long-lived API tokens. Workflow run
   [26128035426](https://github.com/darndestdabbler/dabbler-ai-orchestration/actions/runs/26128035426):
   classify ✓ build ✓ publish-to-PyPI ✓ (operator approved the
   `pypi` environment in the GitHub UI). PyPI live at
   `https://pypi.org/project/dabbler-ai-router/0.5.0/`.

### Round A — past-tense CHANGELOG over-claim, fixed

gemini-pro flagged: the CHANGELOG's "Consumer-repo notification"
bullet used past tense ("each got a one-liner...") at release time,
but the cross-repo writes are operator-gated and happen AFTER PyPI
publish. The bullet was rephrased to remove the past-tense
over-claim and to note that consumer adoption does not require those
edits. Round B confirmed APPROVE.

### Out-of-scope disclosures

- **Pre-existing test-collection gap.** Three test modules
  (`ai_router/tests/test_migrate_router_config_*`) import
  `migrate_router_config.py`, which depends on `ruamel.yaml` — a
  dependency present in `migrate_router_config.py` since Set 026 S3
  (commit fc2d117) but never declared in `pyproject.toml`. The local
  `.venv` had lost the install since the S1 close-out; S2 reinstalled
  `ruamel.yaml` ad-hoc to unblock the sanity-check and proceeded with
  633 passed + 1 skipped. Adding `ruamel.yaml` to
  `[project.optional-dependencies].tests` (or making the import lazy
  with a clean test-side skip) is a separate, defer-able fix — out of
  scope for Set 031, which is the schema set, not the packaging set.
- **Wasted verifier spend ($0.009).** A bash-vs-PowerShell env-var
  syntax mix-up (`$env:ROUND=2` vs `ROUND=2 cmd`) ran the second
  verifier call as Round A again before being corrected to Round B.
  Recorded here for future cost-discipline reference;
  bash-syntax-only on the Bash tool, even on Windows.

### Progress keys

- `session-002/agent-pointers-added` ✓ (byte-identical pointer
  block in CLAUDE.md + AGENTS.md + GEMINI.md, diff-verified)
- `session-002/changelog-entry-added` ✓ (`ai_router/CHANGELOG.md`
  0.5.0 entry, Round-A finding addressed in Round B)
- `session-002/version-bumped` ✓ (`pyproject.toml` and
  `ai_router/__init__.py` both at `0.5.0`)
- `session-002/pypi-released` ✓ (tag-driven OIDC, workflow run
  26128035426, operator approved the `pypi` environment, PyPI live)
- `session-002/cross-repo-pointers-added` ✓ (dabbler-platform +
  dabbler-access-harvester; healthcare-accessdb skipped per
  Lightweight-tier scoping decision)
- `session-002/gitignore-updated` ✓ (`ai_router/consensus-decisions/`
  excluded; JSONL stays committed)
- `session-002/round-a-verification` ✓ ($0.008, one Major finding)
- `session-002/round-b-verification` ✓ ($0.007, APPROVE)
- `session-002/change-log-generated` ✓ (this file)
- `session-002/close-session-succeeded` — pending invocation

---

## Final cost summary

| Session | Round A | Round B | Notes |
|---|---|---|---|
| Session 1 | $0.020 | — | one Critical finding addressed mid-session |
| Session 2 | $0.008 | $0.007 | Round B confirmed past-tense fix; $0.009 wasted on env-var syntax re-run |
| **Set total** | | | **$0.051** of $5.00 NTE (1.0%) |

Spec forecast was $0.07–$0.25; the set landed at $0.051, comfortably
below the lower bound. The pre-shipped, three-way-approved design
meant zero audit-cycle spend and tight per-round verifier prompts.

---

## What ships at the end

- **`dabbler-ai-router 0.5.0`** live on PyPI with the
  `decision_consensus` schema accepted, validated, and documented.
  Defaults to `enabled: false` so every existing consumer is unchanged.
- **[`docs/ai-led-session-workflow.md`](../../ai-led-session-workflow.md) → "Decision-time consensus"**
  section is the canonical reference for the feature's decision tree,
  category split, journal format, and opt-in path.
- **Per-agent instruction files** (CLAUDE.md / AGENTS.md / GEMINI.md
  in this repo, plus CLAUDE.md in dabbler-platform + dabbler-access-
  harvester) point at the new workflow section via a byte-identical
  "Decision-time consensus (pointer)" block.
- **`ai_router/consensus_journal.py`** ships the per-line JSON writer
  + optional full-payload writer. Ready for use by the
  orchestrator-side wiring that lands in a follow-on session set.

---

## What does NOT ship in 0.5.0 (deliberate)

The orchestrator-side wiring — the code that actually invokes
`route(task_type='decision-consensus')` on hitting a consensus-
eligible decision, synthesizes the recommendation, routes the journal
write, and threads the `unresolved_action` fallback — is **not** in
0.5.0. That lands in a follow-on session set. Until then,
`enabled: true` in a consumer's `router-config.yaml` is accepted by
the validator but does not change orchestrator behavior. The default
opt-out means this asymmetry is invisible to every existing consumer.

---

## Notable artifacts

- **PyPI:** https://pypi.org/project/dabbler-ai-router/0.5.0/
- **Workflow run:** https://github.com/darndestdabbler/dabbler-ai-orchestration/actions/runs/26128035426
- **Design proposal (three-way approved 2026-05-17):**
  [`docs/planning/delegation-consensus-config.md`](../../planning/delegation-consensus-config.md)
- **Session-1 verifier review:** [`session-reviews/session-001.md`](session-reviews/session-001.md)
- **Session-2 verifier review (Round A + Round B):**
  [`session-reviews/session-002.md`](session-reviews/session-002.md)

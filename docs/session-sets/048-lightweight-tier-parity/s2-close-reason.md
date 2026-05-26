# Set 048 Session 2 — Close-out reason and verification attestation

## Close-out reason

Session 2 shipped the **Lightweight-tier `--no-router` mode
infrastructure** per the audit-locked spec at
[`spec.md`](spec.md) §3.1 (activation), §3.4 (tri-state UAT/E2E
schema), §3.5 (external-verification.md soft gate), and §3.6 (spec
schema additions).

Four commits make up S2:

- **A** ([`44a1d45`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/44a1d45)) — spec.md schema additions:
  `tier` field + tri-state UAT/E2E (Python + TS parsers + 26 new tests).
- **B** ([`90b7c0c`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/90b7c0c)) — `--no-router` activation
  infrastructure: new `runtime_mode.py` with three-knob precedence
  (CLI > env > spec > default), CLI flags wired into start_session
  and close_session entry points, 29 new tests.
- **C** ([`1eed29a`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/1eed29a)) — `route()`/`verify()`
  short-circuit + `external-verification.md` soft gate with
  TTY/non-TTY branching, 17 new tests.
- **D** ([`bd94205`](https://github.com/darndestdabbler/dabbler-ai-orchestration/commit/bd94205)) — `suggestion_disposition`
  reader/writer helpers + CLI backward-compatibility regression
  tests + explicit deferral note for the runtime gate that
  consumes the disposition (deferred to S3 because Full-tier
  close_session has no existing UAT/E2E gate today, and adding
  one would touch Full behavior outside the audit scope).

The audit verdict's §3.4 reference to "Full-tier behavior
unchanged" for `requiresUAT: true` turned out to be technically
incorrect on inspection — there is no current UAT/E2E gate in
`close_session.py`. This was surfaced and dispositioned during S2
implementation: the suggestion_disposition helpers ship in S2 so
the AI-orchestrator question flow can land in S3 against ready
infrastructure, but the close-out gate itself is S3's territory.

## Cross-provider verification attestation

End-of-session cross-provider verification ran via
`docs/session-sets/048-lightweight-tier-parity/run_s2_verification.py`:

- **Route** — `claude-sonnet-4-6` (tier 2): ISSUES_FOUND, 7 findings.
  Cost: $0.132.
- **Verify** — `gemini-pro` (verifier): VERIFIED (review quality).
  Confirmed all 7 findings as valid with appropriate severity.
  Cost: $0.015.

**S2 routed cost: $0.147** of $10 NTE.
**Cumulative Set 048 spend: $0.250** (S1 $0.103 + S2 $0.147 = 2.5%).

### Round-A findings dispositioned in-flight (per `feedback_dont_hide_behind_out_of_scope`)

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | route/verify silent-swallow falls back to live LLM under exception | Critical | **FIXED** — fail-CLOSED with top-level import; no silent promotion |
| 2 | Bare imports (`from spec_config`) fail without sys.path | Major | **FALSE POSITIVE** — matches existing package convention via `conftest.py` |
| 3 | Race condition on `activity-log.json` read-modify-write | Major | **FIXED** — write-temp + atomic-rename pattern |
| 4 | `resolve_no_router_mode` re-entry silently overwrites cache | Major | **FIXED** — no-op on re-entry, returns cached value |
| 5 | False-positive tier detection from full-file fallback | Important | **FIXED** — `tier:` read only from canonical YAML block; UAT/E2E retain Set 015 fallback |
| 6 | Timestamp `.astimezone()` produces local time, not UTC | Minor | **FIXED** — `datetime.now(timezone.utc).isoformat()` |
| 7 | Lazy `is_no_router_mode` caching inconsistency | Suggestion | **DEFERRED** — production callers always resolve at entry-point startup |

Verification artifacts persisted at:
- [s2-verification-prompt.md](s2-verification-prompt.md)
- [s2-verification-route.md](s2-verification-route.md) — full 7-finding catalog
- [s2-verification-verify.md](s2-verification-verify.md)
- [s2-verification-result.json](s2-verification-result.json)

Two new regression tests lock in the I5 fix:
`test_tier_from_free_form_prose_is_ignored` and
`test_requiresUAT_in_plain_text_still_parses_set015_compat`.

## Test counts at close

- **Python:** 982 pass + 1 skipped (98 new for S2).
- **TypeScript:** 633 pass + 2 pre-existing failures unrelated to S2
  (`configEditor-foundation` panel-lifecycle + `notificationsSection`
  rendering — both predate Set 048).

## What ships in this commit

- `ai_router/spec_config.py` (new) + `ai_router/runtime_mode.py` (new)
  + `ai_router/suggestion_disposition.py` (new) + production-side
  edits to `ai_router/__init__.py`, `ai_router/close_session.py`,
  `ai_router/start_session.py`.
- TS schema additions in
  `tools/dabbler-ai-orchestration/src/types.ts` +
  `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`; 6 test
  fixtures updated for new required `tier` field.
- 6 new test files: `test_spec_config.py`, `test_runtime_mode.py`,
  `test_no_router_short_circuit.py`, `test_no_router_close_session.py`,
  `test_suggestion_disposition.py`, `test_no_router_backcompat.py`.
- Verification driver + artifacts under
  `docs/session-sets/048-lightweight-tier-parity/`.
- Activity-log entries 1-9 for S2.

## Next-session prerequisites

S3 (Copyable-prompt commands + Context-menu IA refresh — combined per
operator's Bias 7 disposition) starts against S2's `--no-router`
infrastructure. The S3 workflow doc update will document the AI-
orchestrator's UAT/E2E question flow; the close-out gate that
consumes `suggestion_disposition` entries lands in S3 as well.

The held Marketplace 0.22.0 publish remains queued — operator will
retry when Microsoft's gallery API recovers. PyPI 0.9.0 is live and
is S2's actual dependency; the held Marketplace publish is for end-
user delivery, not S2 implementation.

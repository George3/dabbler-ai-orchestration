# AI Assignment — `045-log-harvest-implementation`

> **Self-authored disclaimer (Session 1):** This file was authored by
> the orchestrator (Claude Opus 4.7) directly, not via
> `route(task_type="analysis")`. Workflow Step 3.5 normally mandates
> routing this analysis to avoid orchestrator self-opinion bias, but
> the standing operator directive ("AI router usage restricted to
> end-of-session verification — cost containment, until further
> notice") overrides for now. The recommendations below should be
> read with that bias caveat in mind: a Claude orchestrator
> recommending Claude warrants extra scrutiny from the operator.
> When the operator lifts the in-session router restriction, the
> next-session block should be re-routed for an independent read.

---

## Session 1: Open-question spike + joiner location decision

### Recommended orchestrator

claude-opus-4-7 @ effort=high (the running orchestrator).

### Rationale

S1 is a multi-faceted spike that requires reading dense Set 044
artifacts, writing throwaway Python/TypeScript prototypes against
real on-disk Claude+Copilot logs, and authoring two short resolution
docs. The work mixes file-spelunking, schema-aware Python coding, and
analytical synthesis — Opus's mix of breadth + careful reasoning fits
better than a Codex/Gemini handoff that would need to re-load all the
Set 044 context. Cost is bounded by the spike-only scope (no new
Claude API spend in S1 per the descope agreement; routed verification
only at end-of-session).

### Estimated routed cost

Low — single routed `session-verification` call at end-of-session
against a non-Anthropic verifier (Gemini Pro or GPT-5.4).

| Step | Action | Routing Decision |
|------|--------|------------------|
| Q2   | Deterministic correlation prototype (Python script joining synthetic launch record to real Claude + Copilot logs) | No routing; orchestrator writes script directly |
| Q3   | Claude phrasing-trigger analytical pass (diff S4a vs S4b phrasings; hypothesis matrix) | No routing; orchestrator analyzes Set 044 artifacts directly |
| Q1   | Bypass-rate self-observation log schema + first entry | No routing; orchestrator designs schema |
| Q4   | Python + TypeScript joiner sketches; benchmark; lock location | No routing; orchestrator writes both prototypes |
| Doc  | Author `open-question-resolution.md` + `joiner-location-decision.md` | No routing |
| Ver  | End-of-session cross-provider verification | `route(task_type="session-verification")` — Gemini Pro or GPT-5.4 |

### Actuals (filled after the session)

- Orchestrator used: claude-opus-4-7 @ effort=high
- Total routed cost: **$0.024** (single Gemini Pro session-verification
  call at the end; default GPT-5.4 endpoint returned sustained 429s,
  pivoted to Gemini Pro via in-process router-config monkey-patch —
  still cross-provider from Anthropic, no committed config touched)
- Deviations from recommendation: verifier model swapped GPT-5.4 →
  Gemini Pro mid-session due to OpenAI 429 rate-limit; same
  cross-provider intent preserved.
- Notes for next-session calibration: (1) the OpenAI 429 wall is
  worth flagging for S2; the workaround (in-process override to
  gemini-pro) is mechanical but the operator may want to consider
  flipping the default in `router-config.yaml.task_type_overrides`
  if the 429s persist. (2) Session 1 spike landed cleanly with no
  verifier issues; S2 can rely on the locked joiner location + Q2
  correlation evidence + the four defensive Claude template rules
  without revisiting them.

---

**Next-session orchestrator recommendation (Session 2 — Joiner design
+ canonical schema):**

claude-opus-4-7 @ effort=high — but reroute through ai_router if the
operator lifts the in-session router restriction by S2 start. S2's
joiner-spec authoring is the engineering center of gravity per Set
044's consensus, so the choice has high leverage. If routed, the
analysis should be biased toward a frontier model that can
cross-reference Set 044's proposal §4.4, the S1 correlation
prototype's edge cases, and the locked joiner-location decision.

Rationale: joiner-spec authoring needs deep spec-context retention +
schema-design care; Opus or GPT-5.4 are both reasonable; route the
choice rather than self-opine.

---

## Session 2: Joiner design + canonical schema

### Recommended orchestrator

claude-opus-4-7 @ effort=high (the running orchestrator).

### Self-authored disclaimer (Session 2)

This block was authored by the orchestrator (Claude Opus 4.7)
directly, not via `route(task_type="analysis")`. The standing
operator directive ("AI router usage restricted to end-of-session
verification — cost containment, until further notice") remains in
force. Read the recommendations below with the
orchestrator-self-opinion bias caveat in mind; the end-of-session
verifier provides the independent cross-provider check.

### Rationale

S2 is the engineering center of gravity for the whole set per Set
044's locked consensus: it specifies the joiner's conflict-
detection semantics, derives the canonical Harvest Record schema
FROM the joiner's needs (NOT the v0 §4.1 stub), and lands a real
Python skeleton at `ai_router/joiner/` plus Layer-1 tests. The work
is dense spec-authoring + careful Python module design + pytest-
fixture authoring — best handled by Opus in-process without
handoff. No new API spend in this session (routed verification
only at end-of-session).

### Estimated routed cost

Low — single routed `session-verification` call at end-of-session.
Given the GPT-5.4 429 cascade hit in S1 and across Set 036, expect
to either start with `task_type='verification'` (tier-routed; the
working pattern post-Set 036 S5) or pivot to Gemini Pro by
in-process router-config monkey-patch if GPT-5.4 returns 429s
again. Cumulative routed spend coming in: **$0.024 of $5 NTE**.

| Step | Action | Routing Decision |
|------|--------|------------------|
| 1    | Author `joiner-spec.md` (conflict modes 1–3, resolution priorities, output shape) | No routing; orchestrator drafts directly with S1 + Set 044 §4.4 in context |
| 2    | Derive canonical Harvest Record schema (joiner-needs-driven) and document in spec | No routing |
| 3    | Implement Python joiner skeleton: `ai_router/joiner/__init__.py`, `schema.py`, `parsers.py`, `conflicts.py`, `cli.py` | No routing; orchestrator writes module code |
| 4    | Layer-1 unit tests (pytest fixtures: synthetic state files + log fragments per mode); Layer-2 e2e where appropriate | No routing |
| 5    | `python -m pytest` smoke pass (full suite plus targeted joiner tests) | No routing |
| 6    | End-of-session cross-provider verification | `route(task_type="verification")` first; pivot to Gemini Pro via in-process override if 429 cascade reappears |

### Carry-forward inputs from Session 1 (locked, do not relitigate)

- Joiner lives in **Python** at `ai_router/joiner/` (Q4 lock).
- Join keys: `(workspace_cwd canonical, time_window=30s, conv_id post-bind)` (Q2 evidence).
- Native-log scrapers already prototyped at
  `spike-prototypes/correlation_prototype.py` (Claude JSONL +
  Copilot OTel JSONL). Promote and harden into
  `ai_router/joiner/parsers.py`; do NOT re-derive the scan logic.
- Conflict mode 1 (engine-mismatch) sketched in
  `spike-prototypes/joiner_python_sketch.py`. Promote into
  `ai_router/joiner/conflicts.py` and add modes 2 and 3.

### Actuals (filled after the session)

- Orchestrator used: claude-opus-4-7 @ effort=high
- Total routed cost: **$0.053066** (single gemini-pro
  session-verification call; went straight to gemini-pro per the
  Set 036 + Set 045 S1 GPT-5.4 429 cascade history, no 429 cost
  burned this session)
- Deviations from recommendation: verifier model preselected as
  gemini-pro rather than letting `task_type='verification'` route
  through tier-routing first; rationale recorded in
  `verify_session2.py` docstring (avoid known-broken path).
- Notes for next-session calibration: (1) joiner-spec.md got two
  nice-to-have doc refinements applied in-flight after the
  verifier called them out (§3.2 staleness vs. CheckoutPollService
  poll-timeout distinction; Mode B false-positive mitigation
  rule clarified to include exact-match-on-root). Both are doc-
  only edits; the code already handled both cases correctly.
  (2) S3 inherits a fully-locked schema + conflict-detection
  contract + 59 passing Layer-1 tests; the dabbler-launch wrapper
  + Copilot OTel parser hardening should target the canonical
  Harvest Record schema (§5 of joiner-spec.md) verbatim.

---

## Session 3: Wrapper + Copilot parser

### Recommended orchestrator

claude-opus-4-7 @ effort=high (the running orchestrator).

### Self-authored disclaimer (Session 3)

This block was authored by the orchestrator (Claude Opus 4.7)
directly, not via `route(task_type="analysis")`. The standing
operator directive ("AI router usage restricted to end-of-session
verification — cost containment, until further notice") remains in
force. Read the recommendations below with the
orchestrator-self-opinion bias caveat in mind; the end-of-session
verifier provides the independent cross-provider check.

### Rationale

S3 ships the three producer-side gaps left after S2: the
`dabbler-launch` wrapper that writes canonical Harvest Record §5
records to disk, the Copilot OTel parser hardened to per-event
emission, and the harvest() join wire-up that consumes both. The
work is module-level Python coding + pytest fixture authoring +
spec-fidelity checking against joiner-spec.md §4/§5 — best handled
by Opus in-process. No new API spend in this session (routed
verification only at end-of-session). Cumulative routed spend
coming in: **$0.077 of $5 NTE**.

### Estimated routed cost

Low–medium — single routed `session-verification` call at end-of-
session via gemini-pro (skipping the GPT-5.4 429 cascade history
per Set 036 + Set 045 S1). Note: if the verifier surfaces must-fix
issues, additional rounds are within scope; per the operator
memory `feedback_dont_hide_behind_out_of_scope`, small in-flight
fixes beat deferring.

| Step | Action | Routing Decision |
|------|--------|------------------|
| 1 | Author `ai_router/dabbler_launch.py` — headless wrapper CLI, canonical §5 record emission, raw_ref.launch_id (uuid4) | No routing |
| 2 | Harden Copilot OTel parser: add `read_copilot_session_events()` for per-event HarvestRecord emission; §7 redaction enforced | No routing |
| 3 | Wire wrapper launches into `harvest()` join (§4 algorithm: bound / unbound / ambiguous) | No routing |
| 4 | Layer-1 + Layer-2 test coverage of wrapper, parser, join | No routing |
| 5 | `python -m pytest` smoke pass | No routing |
| 6 | End-of-session cross-provider verification (Round A) | `route(model="gemini-pro", task_type="session-verification")` |
| 7+ | Round B / C if Round A surfaces must-fix items | Same routing |

### Carry-forward inputs from Session 2 (locked, do not relitigate)

- Canonical Harvest Record §5 schema is the producer contract;
  the wrapper writes that shape verbatim.
- Conflict-detection windows (engine-mismatch 5min, staleness 2h,
  writer-bypass ±2s) and join window (30s) are spec-locked.
- LaunchRecord parser projection — the `target_backend` field
  rename to `engine` happens at the parser layer; the on-disk
  format follows §5.
- §7 redaction posture (no raw tool_args; only summary) is the
  producer-side commitment — the Copilot parser must enforce.

### Actuals (filled after the session)

- Orchestrator used: claude-opus-4-7 @ effort=high
- Total routed cost: **$0.107** across three verification rounds
  - Round A: gemini-pro session-verification, $0.053, REJECTED on
    (1) normalize_engine missing from candidate predicate; (2)
    bound-native event stream missing per §4 + dup session_start
  - Round B: gemini-pro session-verification, $0.032, REJECTED on
    (1) single-bind invariant; (2) filter ordering; (3)
    normalize_engine breadth [deferred to spec §9]
  - Round C: gemini-pro session-verification, $0.022, VERIFIED
- Deviations from recommendation: three verification rounds
  rather than the projected one. The verifier surfaced 5
  must-fix issues across two rounds; all were addressed
  in-flight per the operator's "don't hide behind out-of-scope"
  directive. The third Round-B issue (normalize_engine breadth)
  was deferred to spec §9 row 5 as the in-flight expansion
  would have broadened the locked §3.1 contract without an
  audit pass.
- Notes for next-session calibration: (1) the multi-round
  verification cycle was empirically valuable — Rounds A and B
  caught real defects (vendor-variant join miss, double-bind,
  filter-then-bind ordering) that Layer-1 tests didn't surface.
  The cost ($0.107 cumulative) was within budget. (2) S4 (Claude
  per-event parser) inherits a working `_native_events_for`
  dispatch table; adding a Claude branch is a one-file change.
  (3) The Round-C nice-to-have about pre-S5 spec audit for
  vendor-prefix engine variants is worth surfacing to the
  operator before S5 starts — see project memory.
- Cumulative routed spend across Set 045 entering S4:
  $0.024 (S1) + $0.053066 (S2) + $0.107 (S3) = $0.184 of $5 NTE.

---

**Next-session orchestrator recommendation (Session 4 — Claude
parser + narration v1.1 template):**

claude-opus-4-7 @ effort=high — but reroute through ai_router if
the operator lifts the in-session router restriction by S4 start.
S4's Claude per-event parser plugs into the existing
`_native_events_for` engine-dispatch (the Copilot branch is the
working pattern); the narration v1.1 template authoring needs the
S1 Q3 phrasing-trigger defensive rules in context. Rationale:
S4 is the symmetric counterpart to S3's Copilot work — the
hardest part is template-authoring, not parser-coding, and the
defensive rules from S1 are local context Opus already has.

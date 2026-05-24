# Joiner Specification — Set 045 / Session 2

> **Status:** Authored 2026-05-24 in Set 045 / Session 2.
> **Lives in:** `ai_router/joiner/` (Q4 lock, Set 045 / Session 1).
> **Consumes:** Set 044 proposal v1 §4.1–§4.4 + Set 045 Session 1
> evidence ([`open-question-resolution.md`](open-question-resolution.md)).
> **Produces:** the canonical Harvest Record schema (§5 below) and
> the conflict-detection semantics (§3) that Set 045 S3–S5
> implement and consume.

---

## 1. Purpose

The joiner is the Set 045 deliverable that turns raw, multi-source
observational signals into a coherent view of "what AI did what in
which Dabbler session set." It does NOT write session-state itself
(that remains the writer-side path owned by `start_session` /
`close_session` / `mark_session_complete` per the Set 033 H1 / H2
verdicts). It only **observes** and **flags discrepancies**.

It has three distinct outputs:

1. **Harvest Records** — a normalized event stream derived from
   wrapper launch logs + per-backend native logs. (§5)
2. **Conflict Reports** — typed discrepancies between what the
   state file claims vs. what the native logs show happened.
   (§3)
3. **Coverage signals** — per-session-set summaries the Explorer
   can render as badges (e.g., "wrapper-launched", "native-log
   bound", "narration present"). (§6)

Per Set 044 Pass B consensus, **the joiner's correctness
requirements drive the canonical record schema, not the other way
around.** §5 is derived from §3's needs; the producers (wrapper in
S3, parsers in S3/S4) MUST emit to §5 verbatim.

---

## 2. Inputs the joiner sees

| Source | Path | Owner | Role |
|---|---|---|---|
| Wrapper launch log | `~/.dabbler/launch-log.jsonl` | `dabbler-launch` (S3) | Authoritative "Dabbler deliberately spawned this AI" |
| Claude native log  | `~/.claude/projects/<workspace-slug>/<conv_id>.jsonl` | Claude Code CLI | Authoritative "this AI was active in this workspace at this time" |
| Copilot native log | `~/.copilot/session-state/<conv_id>/events.jsonl` | Copilot CLI | Authoritative "this AI was active in this workspace at this time" |
| Session state | `<workspace>/docs/session-sets/<slug>/session-state.json` | `ai_router/session_state.py` | Authoritative "who's checked out, what session is in flight" |
| Bypass-observation log | `~/.dabbler/bypass-observation-log.jsonl` | operator (S1) → wrapper (S3+) | Self-observation, fraction-computation only — NOT a joiner input for conflict detection |

The Set 045 follow-on (Codex / Gemini parsers) may add more native
log sources; the joiner's parser layer is extensible to that.

### 2.1 What the joiner does NOT see

- Per-turn LLM API call records. The joiner observes the AI CLI's
  on-disk artifacts, not the underlying provider API. Per-turn
  fidelity is permanently OUT of the Set 044 v1.1 contract.
- IDE-specific UI state (Cursor / VS Code chat panes, etc.).
- Operator-private content of the session (the joiner reads
  metadata + tool calls but does not expose chat content to
  consumers).

---

## 3. Conflict-detection semantics

The joiner detects three conflict modes, all derived from Set 044
proposal §4.4 and refined by Session 1 evidence.

### 3.1 Mode A — Engine mismatch (coordination conflict)

**Definition.** The state file's `orchestrator.engine` says engine
**X** is checked out, but a native log shows engine **Y** ≠ X was
active in the same workspace_cwd within the conflict window of the
state file's `orchestrator.lastActivityAt`.

**Why it matters.** Two AIs are stepping on each other. The
checked-out AI thinks it has exclusive coordination access; the
other AI is writing files / running tests / committing without the
checkout machinery's knowledge. This is the closest analog to
the Set 033 H4 "two distinct chats on the same engine" problem,
escalated to "two distinct engines on the same set."

**Detection rule.**

```text
state_engine = state.orchestrator.engine  (canonicalized: drop -code, -cli suffixes)
state_activity = state.orchestrator.lastActivityAt
state_cwd = canonicalize(workspace containing state file)

for ns in native_sessions:
    if ns.cwd_canonical != state_cwd: continue
    if abs(ns.first_event_ts - state_activity) > conflict_window: continue
    if normalize_engine(ns.engine) == normalize_engine(state_engine): continue
    emit ConflictReport(kind="engine-mismatch", ...)
```

**Conflict window.** Default **5 minutes** for engine-mismatch.
The 30-second Q2 correlation window was for *deterministic
binding* (matching a specific launch to a specific log); the
conflict-detection window must be wider to catch the case where
a stray AI started up after the checkout activity and within the
"reasonable session length" envelope. 5 minutes balances
sensitivity (catches actual stepping-on) against false-positive
rate (avoids flagging an AI that started up after the operator
walked away from the checked-out session).

**Severity.** `high`. Engine mismatch is the strongest signal that
coordination has broken down.

### 3.2 Mode B — Stale-or-absent checkout (coordination conflict)

**Definition.** A native log shows AI activity in the
workspace_cwd of a Dabbler session set, but the session set's
`session-state.json` either has no `orchestrator` block (no
checkout) or has a stale `lastActivityAt` (older than the
staleness threshold).

**Why it matters.** Someone is editing inside a Dabbler session
set without registering a checkout. This is the writer-bypass
analog at the orchestrator-coordination layer: the writer-side
work proceeds without the explicit "I'm taking this on" signal,
which means the Explorer's checkout view is lying about who's
working.

**Detection rule.**

```text
for set_state in scan_session_states():
    set_cwd = canonicalize(workspace containing set_state)
    if set_state.orchestrator is None:
        # No checkout at all.
        for ns in native_sessions:
            if ns.cwd_canonical != set_cwd: continue
            # An AI is touching the workspace housing this set with
            # no checkout claim. Flag.
            emit ConflictReport(kind="bare-touch", ...)
    elif (now - set_state.orchestrator.lastActivityAt) > staleness_threshold:
        # Checkout is technically present but ancient.
        for ns in native_sessions:
            if ns.cwd_canonical != set_cwd: continue
            if ns.first_event_ts > set_state.orchestrator.lastActivityAt + staleness_threshold:
                emit ConflictReport(kind="stale-checkout-touch", ...)
```

**Staleness threshold.** Default **2 hours**. The existing
`CheckoutPollService` uses a 30-minute *poll timeout* — a UI-
update cadence for "is this checkout still alive?" — which is a
different concept than the conflict-detection staleness threshold
defined here. The joiner uses a more conservative 2-hour window
to avoid flagging short breaks (lunch, meetings) as conflicts
while still catching activity that lands in a long-abandoned
session. Configurable via the
`dabblerSessionSets.checkoutStaleAfterMinutes` config key (TBD;
S5 wires this).

**Severity.** `medium`. Less severe than engine-mismatch because
it can fire legitimately when an operator launches an
exploratory AI session outside the checkout flow. The Explorer
should surface it but not alarm.

**False-positive mitigation.** This rule fires when the native
session's workspace_cwd is *inside or equal to* the workspace
housing the state file. The joiner uses
`native_cwd == workspace_root` OR
`native_cwd.startswith(workspace_root + "/")` to scope; a Claude
session started at a sibling or unrelated workspace will NOT trip
the bare-touch rule for an in-repo session set. See §3.4 for the
precise rule.

### 3.3 Mode C — Out-of-band session-state write (writer-bypass)

**Definition.** `session-state.json`'s mtime changes (the writer-
visible signal) but the change cannot be attributed to any of the
canonical writers (`start_session.py`, `close_session.py`,
`mark_session_complete` flow, the cancellation/restoration
lifecycle from Set 035).

**Why it matters.** Set 033's H1 / H2 verdicts established that
the **router is the sole writer**. A direct edit to
session-state.json by an AI's `Edit` / `Write` tool would bypass
the lock + the gate checks + the events-ledger append. Detecting
this surfaces a class of correctness bugs (or operator manual
edits) that would otherwise be silent.

**Detection rule.**

```text
for set_state in scan_session_states():
    set_state_mtime = stat(set_state.path).st_mtime_ns
    # The canonical writers always append a corresponding event to
    # session-events.jsonl in the same transaction. Look for an
    # event within +/- 2 seconds of the mtime.
    events_path = set_state.path.with_name("session-events.jsonl")
    matched = False
    for evt in tail_events(events_path, lookback_seconds=10):
        if abs(evt.ts_ns - set_state_mtime) <= 2_000_000_000:
            matched = True
            break
    if not matched:
        emit ConflictReport(kind="writer-bypass", ...)
```

**Severity.** `high`. A writer-bypass write breaks the Set 033
invariant. Either the operator manually edited the file (low-
frequency; operator should know), or an AI's tool did (high-
severity bug worth investigating).

**False-positive guard.** Editor save-without-changes (e.g.,
opening + closing the file in an editor with auto-format) can
bump mtime without changing content. The rule should be tightened
in S5 to also check `(content_hash, prior_hash)` equality before
flagging; for the S2 spec lock, the mtime+event-correlation rule
is sufficient and a content-hash refinement is recorded as a
deferred follow-up.

### 3.4 Resolution priorities (what counts as authoritative)

When sources disagree, the joiner DOES NOT attempt to silently
pick one. It records the disagreement as a Conflict Report and
lets the operator decide. The conventions:

| Question | Authority | Notes |
|---|---|---|
| Who's checked out? | `session-state.json:orchestrator` | Writer-only field; trustworthy when present and fresh |
| What AI was actually active? | native log first-event timestamp + engine field | Authoritative for "this happened" |
| What did Dabbler launch? | wrapper launch log | Authoritative for "Dabbler deliberately spawned this" |
| Workspace boundary for a session set | `workspace_cwd = parents[N]` of the state file path, walking up to the first ancestor containing a `.git/` or that matches `<workspace>/docs/session-sets/<slug>/session-state.json` resolution | Heuristic; the joiner uses a canonicalized comparison and tolerates slight path drift |

When the joiner cannot resolve a workspace boundary deterministically
(rare; only when state file is moved during a session), it falls
back to the workspace root containing `.git/` and notes the
fallback in `raw_ref`.

### 3.5 Output shape — `ConflictReport`

```python
@dataclass(frozen=True)
class ConflictReport:
    kind: Literal["engine-mismatch", "bare-touch", "stale-checkout-touch", "writer-bypass"]
    severity: Literal["high", "medium", "low"]
    detected_at: datetime                      # joiner run timestamp
    set_slug: Optional[str]                    # None for orphan-touch cases
    state_file: str                            # absolute path
    workspace_cwd_canonical: str
    evidence: dict                             # mode-specific payload
    raw_refs: list[dict]                       # source file + line/offset per signal
    note: str                                  # human-readable summary
```

The `evidence` payload is keyed by mode:

- **engine-mismatch**: `{"state_engine", "native_engine", "native_conv_id", "delta_seconds"}`
- **bare-touch / stale-checkout-touch**: `{"native_engine", "native_conv_id", "checkout_age_seconds" | null, "first_event_ts"}`
- **writer-bypass**: `{"state_mtime_ns", "nearest_event_ts_ns", "delta_seconds", "content_hash"}` (the `content_hash` field is reserved for the S5 refinement; populated as `null` in S2)

`raw_refs` always carries enough information to back-trace to the
source artifact for audit. Producers (S3+) populate this; the
joiner threads it through without mutating.

---

## 4. The join itself (positive case)

Conflicts are the discrepancy view. The joiner also produces the
**positive view**: a stream of Harvest Records derived from the
canonical schema (§5), where wrapper-launch records + native-log
records have been deterministically joined.

**Algorithm** (re-stated from Q2 evidence, hardened):

```text
for launch in scan_launch_log():
    cwd_canon = canonicalize(launch.workspace_cwd)
    candidates = [
        ns for ns in native_sessions
        if ns.engine == launch.target_backend
        and ns.cwd_canonical == cwd_canon
        and abs(ns.first_event_ts - launch.launch_ts) <= bind_window
    ]
    if len(candidates) == 0:
        emit HarvestRecord(event_type="launch", ..., binding_state="unbound")
    elif len(candidates) == 1:
        emit HarvestRecord(event_type="launch", ..., binding_state="bound", conv_id=candidates[0].conv_id)
        for native_evt in candidates[0].events():
            emit HarvestRecord.from_native(launch, native_evt)
    else:
        # Ambiguous — surface a warning HarvestRecord and refuse to bind.
        emit HarvestRecord(event_type="launch", ..., binding_state="ambiguous", candidates=[c.conv_id for c in candidates])
```

**Bind window.** Default **30 seconds** (Q2 evidence: tight
enough to avoid spurious ambiguity in busy workspaces; wide
enough to absorb Claude's observed ~5 s subprocess-spawn-to-
first-event lag).

**Native-log events without a wrapper launch.** These are the
"free-running" sessions Set 044 §4.2's bypass discussion warns
about. The joiner emits them as Harvest Records with
`source="claude-native"` (or `"copilot-native"`) and no `launch`
record attached. Their `set_slug` and `session_number` are NULL
unless narration markers (Set 045 S4) inject them.

---

## 5. Canonical Harvest Record schema (derived from §3 and §4)

The schema is what producers MUST emit and what consumers
(Explorer, conflict detector, audit tools) MUST consume. It is
derived from the joiner's needs and supersedes the v0 sketch in
Set 044 proposal §4.1.

### 5.1 Field reference

```python
@dataclass(frozen=True)
class HarvestRecord:
    # --- Core identity ---
    ts: datetime                                 # event timestamp (UTC)
    event_type: Literal[
        "launch",            # wrapper-side: Dabbler spawned an AI subprocess
        "session_start",     # native-side: AI's first activity (corresponds to launch in positive case)
        "turn",              # native-side: a single AI conversational turn
        "tool_call",         # native-side: AI invoked a tool (Edit, Bash, etc.)
        "marker",            # narration-side: AGENTS.md / CLAUDE.md session-start marker injected text
        "usage",             # native-side: token usage report
        "session_end",       # native-side: AI's last activity / explicit termination
    ]
    source: Literal["wrapper", "claude-native", "copilot-native", "narration"]

    # --- Engine identity ---
    engine: Literal["claude", "copilot", "codex", "gemini"]
    provider: Optional[str]                      # "anthropic" | "github" | ...
    model: Optional[str]                         # "claude-opus-4-7" | "gpt-5.4" | ...
    conv_id: Optional[str]                       # provider conv/session id (None on unbound launch)

    # --- Workspace + session-set context ---
    workspace_cwd: str                           # original (uncanonicalized) cwd
    workspace_cwd_canonical: str                 # canonicalized (case-insensitive, fwd-slash, no trailing slash)
    set_slug: Optional[str]                      # populated by wrapper (S3) or narration (S4); None for free-running with no narration
    session_number: Optional[int]                # ditto

    # --- Binding state (only meaningful on launch records) ---
    binding_state: Optional[Literal["bound", "unbound", "ambiguous"]] = None
    bound_candidates: Optional[list[str]] = None # conv_ids when ambiguous

    # --- Event-specific payload (one populated per event_type) ---
    effort: Optional[str] = None                 # for launch + marker
    tool: Optional[str] = None                   # for tool_call
    tool_args_summary: Optional[dict] = None     # redacted snapshot of tool args
    tokens_in: Optional[int] = None              # for usage
    tokens_out: Optional[int] = None             # for usage

    # --- Audit / back-pointer ---
    raw_ref: dict                                # {"file": "...", "line": N | "offset": N}
```

### 5.2 What changed from the v0 proposal §4.1 sketch

The v0 sketch was a flat dict pre-committed in Set 044. Set 045
Pass B explicitly held: do NOT pre-commit it; derive it from joiner
needs. Concrete revisions:

1. **`event_type` enum tightened.** v0 had a loose tuple; v1
   tightens to a closed enum because the joiner branches on it
   for both correlation and conflict detection. New value
   `session_end` added (needed for "is this AI still active?"
   staleness checks). New value `marker` carved out from generic
   `marker` (was implicit in v0).
2. **`source` field added.** v0 had it but listed only two values;
   v1 enumerates four (wrapper / claude-native / copilot-native /
   narration). The joiner branches on this for the bypass-rate
   computation that S5 reads.
3. **`binding_state` + `bound_candidates` added.** v0 did not
   model ambiguity; v1 surfaces it explicitly because Q2's
   ambiguity probe demonstrated that the joiner must emit a
   structured warning rather than silently picking one.
4. **`workspace_cwd_canonical` added alongside `workspace_cwd`.**
   v0 had only one; v1 keeps both because the canonicalized form
   is the join key but the original is needed for audit (and may
   carry case/separator information the operator needs to see).
5. **`tool_args_summary` instead of `tool_args`.** v0 implied a
   verbatim dump; v1 commits to a redaction layer (the wrapper
   and parsers MUST emit a `*_summary` derived value, never the
   raw payload). This protects against accidentally exfiltrating
   chat content; see §7.

### 5.3 What is NOT in the schema (and why)

- **Per-turn message content.** Not in scope for v1.1 narration;
  not needed by the joiner. The native logs carry it on disk for
  the operator's own review tools.
- **AI-CLI exit code.** The wrapper does not capture this in v1
  (the wrapper's purpose is to spawn + record; subprocess-exit
  capture is deferred to a follow-on if a use case justifies it).
- **Per-turn `effort`.** Permanently out of contract per Set 044
  v1.1. `effort` on a `launch` or `marker` event applies for the
  whole session.

---

## 6. Coverage signals (Explorer-facing summary)

Per session set, the joiner exposes:

```python
@dataclass(frozen=True)
class CoverageSummary:
    set_slug: str
    workspace_cwd_canonical: str
    wrapper_launched: bool          # any launch record bound to a native session in this set's workspace
    narration_present: bool         # any marker event with this set_slug
    native_log_bound: bool          # any native log with first_event_ts within set's [startedAt, completedAt]
    last_signal_ts: Optional[datetime]
    bypass_inferred: bool           # native_log_bound and not wrapper_launched (a session that ran outside Dabbler)
```

The Explorer (S5) renders per-row badges from these. The
`bypass_inferred` field also feeds the Q1 bypass-rate computation
in S5.

---

## 7. Privacy / redaction posture

The joiner reads logs that contain operator + AI conversation
content. The redaction posture:

- **The joiner SHALL NOT expose raw `tool_args` payloads.** Only
  `tool_args_summary` — a derived dict with file paths preserved
  and content elided (e.g., `{"file": "src/foo.py", "lines": 12}`).
- **The joiner SHALL NOT extract message content from native
  logs.** Only metadata: timestamps, conv_id, cwd, tool names,
  token counts, engine + model identification.
- **The Conflict Reports SHALL NOT include raw payloads in
  `evidence`.** The `raw_refs` back-pointer lets an operator
  read the source artifact themselves; the report itself stays
  metadata-only.

This is a Set 044 §7 carry-forward (see Set 044
`harvest-objectives-and-redaction.md`) and is also a Lightweight-
tier compatibility commitment (operators on the Lightweight tier
should be able to consume joiner output safely in environments
where exposing raw chat would be problematic).

---

## 8. Module layout (the §5 / §3 / §6 producers)

The joiner is implemented under `ai_router/joiner/` per the Set
045 / Session 1 Q4 lock. The layout:

```text
ai_router/joiner/
    __init__.py        # public API: scan_conflicts(), harvest(), coverage()
    schema.py          # HarvestRecord, ConflictReport, CoverageSummary dataclasses + serialization
    parsers.py         # promoted from spike-prototypes/correlation_prototype.py
    conflicts.py       # promoted from spike-prototypes/joiner_python_sketch.py + Mode B + Mode C
    coverage.py        # CoverageSummary derivation
    cli.py             # python -m ai_router.joiner --conflicts | --coverage | --harvest [--set-slug ...] [--json]
```

Public API surface:

```python
from ai_router.joiner import scan_conflicts, harvest, coverage

# Conflict view, optionally scoped to a single session set.
reports: list[ConflictReport] = scan_conflicts(set_slug="045-log-harvest-implementation")

# Positive view — the joined Harvest Record stream, optionally scoped.
records: Iterable[HarvestRecord] = harvest(workspace_cwd=None, since=None)

# Per-set coverage summaries.
summaries: list[CoverageSummary] = coverage()
```

The CLI delegates to the same three entry points and emits
JSON-encoded results to stdout. The extension (S5) shells out to
the CLI per `SessionSetsProvider.getChildren()` refresh.

### 8.1 What S2 ships (vs. what S3–S5 add)

**S2 (this session) ships:**

- `schema.py` — full dataclass definitions + JSON serialization.
- `parsers.py` — Claude + Copilot scrapers promoted from S1
  prototype.
- `conflicts.py` — all three modes (A, B, C) implemented with
  Layer-1 unit-test coverage.
- `coverage.py` — `CoverageSummary` derivation from current
  inputs (returns empty wrapper-launched evidence until S3 ships
  the wrapper; the field is False).
- `cli.py` — entry point with `--conflicts`, `--coverage`,
  `--harvest`, `--set-slug`, `--json` flags.
- `__init__.py` — public API re-exports.
- `ai_router/tests/test_joiner_*.py` — Layer-1 coverage of each
  of the above (~6 test files, one per concern).

**S3 adds:**

- The `dabbler-launch` wrapper that writes records the joiner can
  consume. Until S3, `parsers.py`'s wrapper-launch scrape returns
  empty (the bypass-observation log is NOT consumed by the
  joiner; it's operator-self-observation).
- The Copilot OTel parser, replacing the spike-prototype scrape.

**S4 adds:**

- The Claude JSONL parser hardening + narration `marker` event
  parsing.

**S5 adds:**

- The Explorer integration; the joiner code itself does not
  change in S5 except for any small bug fixes surfaced by Layer-3
  Playwright coverage.

---

## 9. Open follow-ups (NOT in S2 scope — recorded for S3–S5)

| # | Question | Carry-forward |
|---|----------|---------------|
| 1 | Should the writer-bypass detector add a content-hash equality check to suppress editor-save-without-changes false positives? | S5 (Explorer wires the bypass-write surface) |
| 2 | What is the operator-perceived latency budget for `scan_conflicts()` at the Explorer's refresh cadence? | S5 (Layer-3 measurement) |
| 3 | Does the bypass-observation log eventually feed back into a `CoverageSummary.bypass_observed_count` field, or stay separate? | S5 (Q1 bypass-rate computation lands) |
| 4 | Codex / Gemini parser shims — extend `parsers.py` with new scrapers and an engine-extension registry? | Follow-on set after 045 |
| 5 | `normalize_engine()` strips ``-code`` / ``-cli`` suffixes per §3.1's stated contract; vendor variants outside that pattern (e.g. ``anthropic-claude``, ``github-copilot``) would miss the join. Should canonicalization graduate to an explicit alias map? (Surfaced by Set 045 S3 Round-B verification.) | Follow-on once a real-world variant breaks a join — speculative variants don't justify expanding the §3.1 contract today |

---

## 10. Cross-references

- Set 044 proposal v1 §4.1–§4.5 — the original architectural
  commitments this spec is implementing.
- Set 045 Session 1 [`open-question-resolution.md`](open-question-resolution.md)
  — Q2 correlation evidence, Q3 phrasing-trigger defensive rules,
  Q4 joiner-location lock.
- Set 045 Session 1 [`joiner-location-decision.md`](joiner-location-decision.md)
  — the Python lock + rationale.
- Set 033 H1 / H2 verdicts — "router is sole writer" + "state
  file is sole truth"; the joiner respects both.
- Set 035 cancellation-reader migration — the canonical
  `readCancellationState` reader is the model for how the joiner's
  state-file reads will work (state-file-first, markdown-files-as-
  audit-only).

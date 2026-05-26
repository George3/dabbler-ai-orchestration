# Set 048 Session 2 cross-provider verification request

## Context

Set 048 Session 2 ships the Lightweight-tier `--no-router` mode infrastructure. The audit-locked spec is at `docs/session-sets/048-lightweight-tier-parity/spec.md` §3.1 (activation), §3.4 (tri-state UAT/E2E + upfront positive-confirmation prompt), §3.5 (external-verification.md soft gate), and §3.6 (spec.md schema additions).

Four commits make up S2:
- A: spec.md schema additions (tier field + tri-state UAT/E2E) — Python + TS parsers + tests.
- B: --no-router activation infrastructure (runtime_mode.py with three-knob precedence).
- C: route()/verify() short-circuit + external-verification.md soft gate.
- D: suggestion_disposition reader/writer helpers + CLI backcompat tests + deferral note for the runtime gate.

Test counts:
- Python: 980 passed + 1 skipped (98 new for S2)
- TypeScript: 633 passed + 2 pre-existing failures unrelated to S2

## What I'm asking you to verify

1. **Correctness** — Does the code do what the spec says?
2. **Safety** — Could anything here accidentally call an LLM or hit credentials under --no-router?
3. **Backwards compatibility** — Will pre-Set-048 invocations break?
4. **Edge cases** — Are there race conditions, missing-file paths, or precedence-order bugs?
5. **Scope tightening** — Commit D's deferral of the runtime gate (consumes suggestion_disposition) is documented in the commit message. Is the deferral defensible?

## Code under review

### ai_router/spec_config.py (new, Commit A)

```python
"""Parser for the ``Session Set Configuration`` YAML block in ``spec.md``.

Set 048 Session 2: adds the ``tier`` field and tri-state ``requires_uat`` /
``requires_e2e`` enums to the spec schema. The Python parser mirrors the
TypeScript ``parseSessionSetConfig`` in
``tools/dabbler-ai-orchestration/src/utils/fileSystem.ts``.

Defaults are full-tier-conservative — ``tier="full"``, ``requires_uat=False``,
``requires_e2e=False``. Pre-Set-048 specs without explicit ``tier:``
resolve to ``"full"`` so existing sets continue to run under canonical
Full-tier discipline.

The parser is intentionally lightweight regex (not a YAML parser) to stay
dependency-free and tolerant of stray formatting in the spec block.
Schema validation that surfaces typos as errors lives in
``schema_validator.py`` (separate from this parser).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

TriStateFlag = Union[bool, Literal["suggested"]]
SessionSetTier = Literal["full", "lightweight"]


@dataclass(frozen=True)
class SessionSetConfig:
    """Parsed shape of the ``Session Set Configuration`` block."""

    tier: SessionSetTier
    requires_uat: TriStateFlag
    requires_e2e: TriStateFlag
    uat_scope: str


_DEFAULT = SessionSetConfig(
    tier="full",
    requires_uat=False,
    requires_e2e=False,
    uat_scope="none",
)


_CONFIG_BLOCK_RE = re.compile(
    r"##\s*Session Set Configuration[\s\S]*?```ya?ml\s*([\s\S]*?)```",
    re.IGNORECASE,
)

# Tri-state values: literal `true`, `false`, or `suggested` (optionally
# quoted). Trailing inline `# comment` tolerated.
def _tri_state_re(key: str) -> re.Pattern[str]:
    return re.compile(
        rf'^\s*{re.escape(key)}\s*:\s*(?:"(suggested)"|(true|false|suggested))\s*(?:#.*)?$',
        re.IGNORECASE | re.MULTILINE,
    )


def _string_re(key: str) -> re.Pattern[str]:
    return re.compile(
        rf'^\s*{re.escape(key)}\s*:\s*([\w-]+)\s*(?:#.*)?$',
        re.IGNORECASE | re.MULTILINE,
    )


def _parse_tri(m: re.Match[str] | None) -> TriStateFlag | None:
    if m is None:
        return None
    raw = (m.group(1) or m.group(2) or "").lower()
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "suggested":
        return "suggested"
    return None


def parse_session_set_config(spec_md_path: Path) -> SessionSetConfig:
    """Parse ``spec.md`` and return its ``SessionSetConfig``.

    Returns the Full-tier-conservative default when the file is missing,
    unreadable, or has no ``Session Set Configuration`` block. Unknown
    ``tier`` values silently fall back to ``"full"`` — schema validation
    is the responsibility of the validator, not this parser.
    """
    try:
        text = Path(spec_md_path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return _DEFAULT

    block_match = _CONFIG_BLOCK_RE.search(text)
    block = block_match.group(1) if block_match else text

    tier: SessionSetTier = "full"
    tier_match = _string_re("tier").search(block)
    if tier_match:
        v = tier_match.group(1).lower()
        if v in ("full", "lightweight"):
            tier = v  # type: ignore[assignment]

    uat = _parse_tri(_tri_state_re("requiresUAT").search(block))
    e2e = _parse_tri(_tri_state_re("requiresE2E").search(block))

    uat_scope = "none"
    scope_match = _string_re("uatScope").search(block)
    if scope_match:
        uat_scope = scope_match.group(1)

    return SessionSetConfig(
        tier=tier,
        requires_uat=uat if uat is not None else _DEFAULT.requires_uat,
        requires_e2e=e2e if e2e is not None else _DEFAULT.requires_e2e,
        uat_scope=uat_scope,
    )


__all__ = [
    "SessionSetConfig",
    "SessionSetTier",
    "TriStateFlag",
    "parse_session_set_config",
]

```

### ai_router/runtime_mode.py (new, Commit B)

```python
"""Resolves whether the current ai_router invocation is in --no-router mode.

Set 048 Session 2: the Lightweight tier suppresses AI router runtime
calls (no LLM API hits, no auto-verification). The mode is resolved
once at process start from three precedence-ordered sources:

  1. CLI flag ``--no-router`` (highest; one-off override)
  2. Env var ``DABBLER_NO_ROUTER`` (CI / shell-session default)
  3. Spec.md field ``tier: lightweight`` (declarative per-set default)
  4. Default ``full`` mode (lowest; router enabled)

When a higher-precedence source overrides a lower one (e.g., CLI
``--no-router`` on a ``tier: full`` spec), the resolver emits an
informational message naming the override so the operator sees what
just happened. No refusal — explicit overrides always win.

This module also handles the "lazy LLM-SDK imports" deliverable from
the audit (§3.1 A2). In this codebase, providers already call LLMs via
httpx (see ``ai_router/providers.py``) — there are NO module-level
``anthropic`` / ``openai`` / ``google-generativeai`` imports to make
lazy. The audit work for A2 is therefore a no-op for this codebase;
documenting it here for the next architect who wonders.

The next session (S2 Commit C) wires this into ``route()`` and
``verify()`` so they short-circuit cleanly under no-router mode and
return a manual-attestation result without ever issuing httpx calls.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ENV_VAR_NAME = "DABBLER_NO_ROUTER"

# Module-level cache: None means "not yet resolved." Once
# ``resolve_no_router_mode`` runs, the result is cached here so that
# ``is_no_router_mode`` calls from deep in the call stack don't have
# to re-parse the spec or the env var.
_NO_ROUTER_MODE: Optional[bool] = None


def _env_var_truthy() -> bool:
    """Return True if DABBLER_NO_ROUTER is set to a truthy value.

    Truthy set follows the operator's existing convention from the
    Set 033 enforcement flag: ``1``, ``true``, ``yes``, ``on``
    (case-insensitive). Anything else (including unset) is falsy.
    """
    raw = os.environ.get(ENV_VAR_NAME, "")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _spec_tier(session_set_dir: Optional[Path]) -> Optional[str]:
    """Return the spec.md's ``tier`` field, or None if no readable spec.

    Returns ``"lightweight"`` / ``"full"`` when the spec is parseable,
    or ``None`` when the dir is missing, the spec is missing, or the
    parser raised. The None case is distinct from ``"full"`` so the
    override-logging logic can tell "no spec" apart from "spec says
    full" — the former does not generate an override message; the
    latter does.
    """
    if session_set_dir is None:
        return None
    spec = Path(session_set_dir) / "spec.md"
    if not spec.exists():
        return None
    try:
        # Lazy-import the parser so this module stays cheap to import
        # even from test contexts that mock out spec.md.
        from spec_config import parse_session_set_config

        cfg = parse_session_set_config(spec)
        return cfg.tier
    except Exception:  # noqa: BLE001
        return None


def _spec_says_lightweight(session_set_dir: Optional[Path]) -> bool:
    """Convenience wrapper: True iff spec exists and says tier=lightweight."""
    return _spec_tier(session_set_dir) == "lightweight"


def resolve_no_router_mode(
    cli_flag: bool,
    session_set_dir: Optional[Path] = None,
) -> bool:
    """Resolve whether the current invocation is in --no-router mode.

    Precedence (high to low):
      1. ``cli_flag`` (explicit ``--no-router`` on the command line)
      2. ``DABBLER_NO_ROUTER`` env var
      3. ``tier: lightweight`` in ``<session_set_dir>/spec.md``
      4. Default (full mode)

    Side effect: caches the result in module-level ``_NO_ROUTER_MODE``.
    Subsequent calls to ``is_no_router_mode`` return the cached value
    without re-parsing.

    Logging: when a higher-precedence source contradicts a lower one,
    emits an ``INFO`` log line naming the source that won.
    """
    global _NO_ROUTER_MODE

    env_says = _env_var_truthy()
    tier = _spec_tier(session_set_dir)  # "lightweight" | "full" | None

    if cli_flag:
        if tier == "full":
            logger.info(
                "CLI flag --no-router overrides spec tier=full for this invocation"
            )
        elif tier == "lightweight":
            logger.info(
                "--no-router enabled via CLI flag (spec tier=lightweight agreed)"
            )
        else:
            logger.info("--no-router enabled via CLI flag")
        _NO_ROUTER_MODE = True
        return True

    if env_says:
        if tier == "full":
            logger.info(
                "Env var %s overrides spec tier=full for this invocation",
                ENV_VAR_NAME,
            )
        elif tier == "lightweight":
            logger.info(
                "--no-router enabled via env var %s (spec tier=lightweight agreed)",
                ENV_VAR_NAME,
            )
        else:
            logger.info("--no-router enabled via env var %s", ENV_VAR_NAME)
        _NO_ROUTER_MODE = True
        return True

    if tier == "lightweight":
        logger.info("--no-router enabled via spec tier=lightweight")
        _NO_ROUTER_MODE = True
        return True

    _NO_ROUTER_MODE = False
    return False


def is_no_router_mode() -> bool:
    """Return the cached --no-router resolution.

    If ``resolve_no_router_mode`` has not run yet, attempts a lazy
    resolution from env var + active-session-set spec only (no CLI
    flag context available). The lazy resolution does NOT cache —
    callers that need the result more than once should call
    ``resolve_no_router_mode`` explicitly at entry-point startup.
    """
    if _NO_ROUTER_MODE is not None:
        return _NO_ROUTER_MODE
    # Lazy resolution: env var + active session set's spec, no CLI
    if _env_var_truthy():
        return True
    try:
        # Avoid hard-coded import of find_active_session_set — that
        # module is heavy and may not be available in test contexts.
        from session_state import find_active_session_set

        active = find_active_session_set()
        if active:
            return _spec_says_lightweight(Path(active))
    except Exception:  # noqa: BLE001
        pass
    return False


def reset_for_tests() -> None:
    """Test helper: clear the cached resolution so each test starts fresh."""
    global _NO_ROUTER_MODE
    _NO_ROUTER_MODE = None


__all__ = [
    "ENV_VAR_NAME",
    "is_no_router_mode",
    "reset_for_tests",
    "resolve_no_router_mode",
]

```

### ai_router/suggestion_disposition.py (new, Commit D)

```python
"""Reader and writer helpers for ``suggestion_disposition`` activity-log entries.

Set 048 Session 2 §3.4: when a spec declares ``requiresUAT: "suggested"``
or ``requiresE2E: "suggested"`` AND the session has UX scope, the AI
orchestrator (Claude Code / Codex / etc.) prompts the operator at
session start:

  "E2E tests, UAT checklist, both, or neither?"

The operator's choice is recorded ONCE in the session set's
``activity-log.json`` as an entry with ``kind: suggestion_disposition``
and a ``choice`` field carrying one of the four answers. This module
provides read + write helpers for that record so:

  * The AI orchestrator (Claude Code etc.) can write the entry via
    ``record_suggestion_disposition()``.
  * Future close-out code (Set 048 S3+) can read the recorded
    choice via ``read_suggestion_disposition_for_session()`` to
    decide whether UAT/E2E close-out gates fire.

**Scope note:** the *runtime gate* that USES the recorded disposition
to block close-out under `requires_uat == "suggested"` is deferred to
Set 048 Session 3 (where the AI-orchestrator question is wired and
documented in ``docs/ai-led-session-workflow.md``). Adding the gate
in S2 would touch close-out behavior for Full-tier sessions in a way
the audit did not scope. S3 owns both the AI-orchestrator question
flow AND the close-out-side gate that consumes the recorded
disposition.

The entry shape (mirrors the existing activity-log schema):

  {
    "sessionNumber": <int>,
    "stepNumber": <int>,
    "stepKey": "session-NNN/suggestion-disposition",
    "dateTime": "<ISO-8601 timestamp>",
    "description": "Operator answered the UAT/E2E suggested-state prompt: <choice>.",
    "status": "complete",
    "routedApiCalls": [],
    "kind": "suggestion_disposition",
    "choice": "e2e" | "uat" | "both" | "neither"
  }

The ``kind`` field is the canonical discriminator the reader matches
on; it's an additive field that does not break the existing
activity-log schema readers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

SuggestionChoice = Literal["e2e", "uat", "both", "neither"]

VALID_CHOICES = ("e2e", "uat", "both", "neither")

ENTRY_KIND = "suggestion_disposition"


def record_suggestion_disposition(
    session_set_dir: str | Path,
    session_number: int,
    choice: SuggestionChoice,
    *,
    step_number: Optional[int] = None,
) -> None:
    """Append a ``suggestion_disposition`` entry to ``activity-log.json``.

    Writes the canonical entry shape above. If ``step_number`` is None,
    it's inferred as ``max(existing steps for this session) + 1``,
    falling back to ``1`` if no entries exist yet.

    Raises ``ValueError`` on unknown choice. Raises
    ``FileNotFoundError`` if the activity-log file is missing
    (callers create it via the normal session lifecycle; this helper
    does not create the file from scratch).
    """
    if choice not in VALID_CHOICES:
        raise ValueError(
            f"unknown suggestion choice {choice!r}; "
            f"expected one of {VALID_CHOICES}"
        )

    log_path = Path(session_set_dir) / "activity-log.json"
    if not log_path.exists():
        raise FileNotFoundError(
            f"activity-log.json not found at {log_path}; "
            "the session set must exist + have started before recording "
            "a suggestion disposition"
        )

    with log_path.open("r", encoding="utf-8") as f:
        log = json.load(f)

    entries = log.setdefault("entries", [])

    if step_number is None:
        step_number = (
            max(
                (
                    int(e.get("stepNumber", 0))
                    for e in entries
                    if e.get("sessionNumber") == session_number
                ),
                default=0,
            )
            + 1
        )

    timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    entry = {
        "sessionNumber": session_number,
        "stepNumber": step_number,
        "stepKey": f"session-{session_number:03d}/suggestion-disposition",
        "dateTime": timestamp,
        "description": (
            f"Operator answered the UAT/E2E suggested-state prompt: "
            f"{choice}."
        ),
        "status": "complete",
        "routedApiCalls": [],
        "kind": ENTRY_KIND,
        "choice": choice,
    }
    entries.append(entry)

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
        f.write("\n")


def read_suggestion_disposition_for_session(
    session_set_dir: str | Path,
    session_number: int,
) -> Optional[SuggestionChoice]:
    """Return the operator's recorded UAT/E2E choice, or None if not recorded.

    Walks ``activity-log.json`` looking for entries with
    ``kind == "suggestion_disposition"`` AND
    ``sessionNumber == session_number``. Returns the LAST matching
    ``choice`` value (most-recent decision wins if the operator answered
    more than once for the same session). Returns ``None`` when no
    matching entry exists — callers treat this as "operator did not
    answer," which the close-out gate's downstream logic must handle
    (Set 048 S3 will define that behavior).

    Returns None on any read error (missing file, malformed JSON,
    unknown choice value); never raises. Callers that need to
    distinguish "not recorded" from "read failure" should layer a
    direct file-existence check on top.
    """
    log_path = Path(session_set_dir) / "activity-log.json"
    if not log_path.exists():
        return None
    try:
        with log_path.open("r", encoding="utf-8") as f:
            log = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    last_choice: Optional[SuggestionChoice] = None
    for entry in log.get("entries", []):
        if entry.get("kind") != ENTRY_KIND:
            continue
        if entry.get("sessionNumber") != session_number:
            continue
        choice = entry.get("choice")
        if choice in VALID_CHOICES:
            last_choice = choice  # type: ignore[assignment]
    return last_choice


__all__ = [
    "ENTRY_KIND",
    "VALID_CHOICES",
    "SuggestionChoice",
    "read_suggestion_disposition_for_session",
    "record_suggestion_disposition",
]

```

### ai_router/close_session.py — Set 048 changes summary (Commits B + C)

Three changes to ai_router/close_session.py:

1. New --no-router and --accept-suggestions flags in _build_parser():

    p.add_argument('--no-router', action='store_true', dest='no_router', ...)
    p.add_argument('--accept-suggestions', action='store_true', dest='accept_suggestions', ...)

2. main() resolves runtime_mode at entry-point start (before run(args)):

    from runtime_mode import resolve_no_router_mode
    resolve_no_router_mode(
        cli_flag=bool(getattr(args, 'no_router', False)),
        session_set_dir=Path(args.session_set_dir) if args.session_set_dir else None,
    )

3. run() integration: 
   (a) manual_attestation block: if args.no_router and not args.manual_verify,
       auto-supply a stock attestation when no --reason-file (so the audit
       trail records Lightweight-tier intent).
   (b) method resolution: args.no_router branch sets method='manual'.
   (c) NEW soft-gate check after gate_checks pass + before state flip:
       fires only under --no-router; reads external-verification.md;
       branches on --accept-suggestions / TTY / non-TTY; aborts with
       result='aborted_at_soft_gate' + emits closeout_failed event
       on TTY non-affirmative answer.

Full close_session.py is ~1700 lines; only the changes above are new
in S2. The pre-existing flow (gate_checks, lock, event emission,
state flip) is unchanged.


### ai_router/__init__.py — Set 048 changes summary (Commit C)

Two changes to ai_router/__init__.py:

1. New module-level stub builders + constants:

    _NO_ROUTER_MODEL = 'no-router-mode'
    _NO_ROUTER_VERDICT = 'no_router_skipped'

    def _build_no_router_route_stub() -> RouteResult: ...
    def _build_no_router_verification_stub(generator_model: str) -> VerificationResult: ...

2. route() and verify() prologues short-circuit when no-router-mode is active:

    def route(content, ...):
        try:
            from runtime_mode import is_no_router_mode
            if is_no_router_mode():
                return _build_no_router_route_stub()
        except Exception:
            pass
        _init()  # original code resumes
        ...

    def verify(route_result, ...):
        try:
            from runtime_mode import is_no_router_mode
            if is_no_router_mode():
                return _build_no_router_verification_stub(
                    generator_model=route_result.model_name)
        except Exception:
            pass
        _init()  # original code resumes
        ...


### tools/dabbler-ai-orchestration/src/types.ts (Commit A schema)

```typescript
export type SessionState = "complete" | "in-progress" | "not-started" | "cancelled";

// Set 030 Session 1 — session-state.json schema v3 ledger.
// The set-level `SessionState` above is the extension's bucketing
// state (Cancelled / Complete / Active / Not Started). Set 030
// Session 3 unified the bucketing literal with the per-session
// status under the canonical name `complete`, retiring the older
// `done` label so JSON and display vocabulary match.
// The union below is the per-session status used in v3's
// `sessions[]` ledger and must match Python's `SESSION_STATUSES` in
// `ai_router/progress.py`.
export type SessionStatus = "not-started" | "in-progress" | "complete" | "cancelled";

export interface SessionRecord {
  number: number;
  title: string;
  status: SessionStatus;
}

export interface ProgressView {
  sessions: SessionRecord[];
  totalSessions: number;
  completedSessions: number[];
  currentSession: number | null;
  nextSession: number | null;
  isBetweenSessions: boolean;
}

// v3 session-state.json shape. Top-level fields mirror v2 except
// the legacy progress triple (currentSession / totalSessions /
// completedSessions) is replaced by the `sessions[]` ledger.
// Set 030 Session 2's dual-write writers emit BOTH shapes on disk
// so legacy readers keep working; this interface describes the v3
// canonical fields only.
export interface SessionStateV3 {
  schemaVersion: 3;
  sessionSetName: string;
  status: "not-started" | "in-progress" | "complete" | "cancelled";
  lifecycleState: "work_in_progress" | "closed" | null;
  startedAt: string | null;
  completedAt: string | null;
  verificationVerdict: string | null;
  orchestrator: OrchestratorInfo | null;
  sessions: SessionRecord[];
}

// Set 048 Session 2: tri-state UAT/E2E enum per audit decision D4.
// `true` blocks close-out until checklist evidence present; `false`
// skips; `"suggested"` triggers an upfront positive-confirmation prompt
// from the AI orchestrator at session start when the session has UX
// scope (per operator override of audit Bias 4), with the choice
// recorded in activity-log as a `suggestion_disposition` entry.
export type TriStateFlag = boolean | "suggested";

// Set 048 Session 2: tier field per audit §3.6. Lightweight tier
// follows the same writer/Explorer/state-file process as Full but
// suppresses AI router runtime calls and auto-verification (per
// operator-locked premises P1-P4). Pre-Set-048 specs default to
// `"full"` when the field is absent.
export type SessionSetTier = "full" | "lightweight";

export interface SessionSetConfig {
  requiresUAT: TriStateFlag;
  requiresE2E: TriStateFlag;
  uatScope: string;
  tier: SessionSetTier;
}

// Set 047 Session 5: prerequisites field schema landed by spec §3.3.
// Authored under the ``Session Set Configuration`` YAML block; the
// reader cross-references each set's prereqs against the target
// set's ``status`` to derive the ``blockedByPrereqs`` flag on
// SessionSet below. ``condition`` is an enum with one value today
// (``"complete"``) but is kept as a string field so a future spec
// can add (e.g.) ``"started"`` without rewriting consumers.
export interface SessionSetPrerequisite {
  slug: string;
  condition: "complete";
}

export interface UatSummary {
  totalItems: number;
  pendingItems: number;
  e2eRefs: string[];
}

export interface OrchestratorInfo {
  engine?: string;
  provider?: string;
  model?: string;
  effort?: string;
  // Set 033 Session 1: check-out / check-in nested timestamps under the
  // orchestrator block. `checkedOutAt` is set on transition to
  // status: in-progress and preserved across same-holder re-attaches
  // (H4 identity = engine + provider). `lastActivityAt` is bumped on
  // every re-attach. Both are `null`able for tolerated reads of pre-S1
  // in-flight files; next same-holder start_session populates them.
  checkedOutAt?: string;
  lastActivityAt?: string;
}

export interface LiveSession {
  currentSession: number | null;
  status: string | null;
  orchestrator: OrchestratorInfo | null;
  startedAt: string | null;
  completedAt: string | null;
  verificationVerdict: string | null;
  // Set 9 Session 3 (D-2 hard-scoping): true when the close-out path
  // was bypassed via ``--force`` / ``mark_session_complete(force=True)``.
  // Surfaced as a ``[FORCED]`` badge on the Session Set Explorer row so
  // reviewers can spot emergency-bypass close-outs at a glance. Absent
  // or false on every snapshot written by a normal close-out.
  forceClosed: boolean | null;
  // Set 022 Session 2: completedSessions[] is the authoritative
  // progress ledger under the state-first lifecycle protocol. Surfaced
  // here so the tree-view can compute the "currentSession is in flight"
  // predicate (currentSession not in completedSessions[]) without
  // re-reading the state file. Null when the snapshot pre-dates the
  // array (legacy sets); empty array when the protocol has been
  // applied but no session has closed yet.
  completedSessions: number[] | null;
}

export interface SessionSet {
  name: string;
  dir: string;
  specPath: string;
  activityPath: string;
  changeLogPath: string;
  statePath: string;
  aiAssignmentPath: string;
  uatChecklistPath: string;
  state: SessionState;
  totalSessions: number | null;
  sessionsCompleted: number;
  lastTouched: string | null;
  liveSession: LiveSession | null;
  config: SessionSetConfig;
  uatSummary: UatSummary | null;
  root: string;
  // Set 030 Session 5: true when this set's session-state.json needs
  // a one-shot migration to the next canonical schema. The tree
  // renders a "(needs migration)" badge and exposes a context-menu
  // migrate command. Default false; absent / broken state files do
  // not flag (the v3 reader's tolerant path already handles
  // missing-file display).
  //
  // Set 047 Session 3: extended to flag v3 → v4 migrations too. The
  // overall `needsMigration` boolean drives the badge (which is the
  // same colored chip regardless of target version); the
  // `migrationTargetSchemaVersion` field tells the ActionRegistry
  // which migrate command to surface in the right-click menu.
  needsMigration: boolean;
  // Set 047 Session 3: which canonical schema version is the
  // migration target. 3 → operator needs to run "Migrate to v3
  // schema" first (v1/v2 source, or broken-v3 with no sessions[]).
  // 4 → "Migrate to v4 schema" (canonical v3 with sessions[]). null
  // → no migration needed (already at v4 or no state file to act on).
  // Reading the badge: `needsMigration === (migrationTargetSchemaVersion !== null)`.
  migrationTargetSchemaVersion: 3 | 4 | null;
  // Set 047 Session 5 (spec §3.3): prerequisites authored under the
  // set's ``spec.md`` ``Session Set Configuration`` block. `null`
  // when the field is absent (no dependency declared); empty array
  // when the spec wrote `prerequisites: []` explicitly. Carried on
  // the SessionSet record so the renderer can surface the slug list
  // in tooltips / decorations without re-parsing the spec.
  prerequisites: SessionSetPrerequisite[] | null;
  // Set 047 Session 5 (spec §3.3): derived by `readSessionSets` —
  // `true` iff at least one prerequisite's target set has a `status`
  // that does not satisfy the declared `condition`. A `complete`
  // condition is satisfied by `state === "complete"`; everything
  // else is "still blocking". Unknown prereq slugs (typo, missing
  // set) keep `blockedByPrereqs: true` so a typo doesn't silently
  // unblock the row. False when `prerequisites` is null or empty.
  blockedByPrereqs: boolean;
}

export interface MetricsEntry {
  session_set: string;
  session_num: number;
  model: string;
  effort: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  timestamp: string;
}

export interface CostSummary {
  totalCost: number;
  bySessionSet: Record<string, { sessions: number; cost: number; lastRun: string }>;
  byModel: Record<string, number>;
  dailyCosts: Array<{ date: string; cost: number }>;
}

```

## Verdict format

Return a verdict (VERIFIED / ISSUES_FOUND) at the top of your response, then itemize concerns by Category (Correctness / Safety / Completeness / Backcompat / Edge-case / Other), Severity (Critical / Important / Nice-to-have), Location (file:line or section reference), Details, and Fix suggestion.

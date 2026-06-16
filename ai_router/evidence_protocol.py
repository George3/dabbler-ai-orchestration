"""Set 069 S1 - the single execution-evidence protocol for pull critiques.

Set 068's 0.22.x release exposed the automated-vs-manual pull-critique gap: the
automated :mod:`ai_router.pull_critique` producer drove its critics **read-only**
(``read_file`` / ``grep`` / ``list_dir``), so it was a *commentator* where the
**manual** critic (a frontier model in a Copilot editor with a terminal) was an
**evidence-producing probe runner**. The manual run reproduced two Major bugs by
*executing code*; the automated run could not.

The proposal panel
(``docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md``, rung 1)
made the **evidence protocol the first thing to ship** - before any new execution
lane. The reason is the **two-standards** problem: more execution without a shared
evidence contract just enlarges the bluff surface, and a human-watched terminal
must not mint stronger claims than automated evidence. So *both* the manual and
the automated critic speak this one protocol.

The protocol has four load-bearing parts, all implemented here:

1. **Evidence tiers.** Every finding carries an effective tier:

   - :data:`EVIDENCE_REPRODUCED` - the defect's failure was *reproduced by
     running a probe*, and the run is backed by a servant-captured transcript
     with a **pristine replay** (a re-runnable falsifier).
   - :data:`EVIDENCE_ASSERTED` - the critic claims the defect from *reading* the
     code; no execution. This is the natural tier of a read-only critique, and
     the **default** for an untagged finding (so every Set 066/067/068 artifact
     stays valid - the field is purely additive).
   - :data:`EVIDENCE_HYPOTHESIS` - a suspected issue flagged for follow-up;
     lowest confidence, agent-proposed.

2. **The orchestrator applies the tag, never the agent.** REPRODUCED is conferred
   by :func:`authoritative_tier` - the orchestrator-side helper - and *only* when
   a valid transcript exists. A REPRODUCED *claim* with no valid transcript
   collapses to ASSERTED. Trust never rests on the agent's word: the servant
   re-executes the falsifier. (The agent's ``submit_verdict`` tool surface never
   exposes the authoritative tier; the orchestrator stamps it post-hoc.)

3. **The pristine-replay requirement.** A transcript backs REPRODUCED only when
   the probe ran on a **pristine checkout**, a **replay on a second pristine
   checkout** produced a byte-identical raw result (matching :data:`outputHash`),
   and the probe is a **trusted command id / template id** - never model-authored
   argv. The replay is what turns "the agent says it ran" into "anyone can re-run
   this and watch it fail."

4. **The meta-oracle rule.** A reproduced finding must demonstrate the failure
   **through a real public entrypoint** (a CLI, a public API, an operator-authored
   test/command), **not an agent-built harness** that can "prove" a non-bug by
   baking in wrong assumptions or mocking its way to a failure. A transcript whose
   ``entrypoint.kind`` is :data:`ENTRYPOINT_AGENT_HARNESS` (or anything outside
   :data:`PUBLIC_ENTRYPOINT_KINDS`) is rejected.

Everything here is pure-Python, dependency-free, ASCII-only on every error
string, and **never raises** on malformed input (a bad transcript is reported as
not-ok, exactly like :func:`ai_router.path_aware_critique.validate_path_aware_critique_artifact`).
The Set 066 artifact validator (extended in this session) calls
:func:`validate_finding_evidence` so a finding tagged REPRODUCED without a valid
transcript makes the whole ``path-aware-critique.json`` artifact invalid - the
close-out gate then refuses it.

The JSON Schema parallel for the on-disk shape lives in
``docs/path-aware-critique.schema.json`` (the ``$defs/EvidenceTranscript`` block);
the narrative protocol doc is ``docs/evidence-protocol.md``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Evidence tiers
# ---------------------------------------------------------------------------

EVIDENCE_REPRODUCED = "REPRODUCED"
EVIDENCE_ASSERTED = "ASSERTED"
EVIDENCE_HYPOTHESIS = "HYPOTHESIS"
EVIDENCE_TIERS = (EVIDENCE_REPRODUCED, EVIDENCE_ASSERTED, EVIDENCE_HYPOTHESIS)
# An untagged finding is a read-claim (the read-only critique's natural tier),
# so the default is ASSERTED. This makes the ``evidenceTier`` field purely
# additive: every pre-Set-069 artifact (no evidence tags) stays valid, and an
# absent tag is never treated as REPRODUCED (which is the only tier with teeth).
DEFAULT_EVIDENCE_TIER = EVIDENCE_ASSERTED


# ---------------------------------------------------------------------------
# Meta-oracle: a reproduced finding must drive a REAL PUBLIC entrypoint
# ---------------------------------------------------------------------------

# A reproduced failure must be demonstrated through one of these public
# surfaces - not an agent-constructed harness (which could "prove" a non-bug).
ENTRYPOINT_PUBLIC_COMMAND = "public_command"  # an operator-authored command id
ENTRYPOINT_PUBLIC_API = "public_api"  # a public function / module entrypoint
ENTRYPOINT_CLI = "cli"  # a shipped CLI entrypoint (python -m ai_router.x)
ENTRYPOINT_TEST = "test_entrypoint"  # a vetted, operator-authored test target
PUBLIC_ENTRYPOINT_KINDS = (
    ENTRYPOINT_PUBLIC_COMMAND,
    ENTRYPOINT_PUBLIC_API,
    ENTRYPOINT_CLI,
    ENTRYPOINT_TEST,
)
# The BANNED kind: an agent-built harness is exactly what the meta-oracle rule
# forbids for a REPRODUCED finding. Named so a producer can stamp it honestly
# (and be rejected) rather than mislabel it as public.
ENTRYPOINT_AGENT_HARNESS = "agent_harness"


# ---------------------------------------------------------------------------
# Output hashing (the replay-match primitive)
# ---------------------------------------------------------------------------


def hash_output(raw: object) -> str:
    """Return the canonical ``sha256:<hex>`` digest of a probe's raw output.

    The single definition of "the output hash" both the original run and its
    pristine replay compute, so :func:`validate_transcript`'s replay-match check
    (``outputHash == replay.outputHash``) is deterministic by construction. A
    non-string is coerced (``None`` -> empty) so a producer never crashes here;
    execution that produces empty output still yields a stable hash.
    """
    if not isinstance(raw, str):
        raw = "" if raw is None else str(raw)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Result data model
# ---------------------------------------------------------------------------

# Stable machine tokens for EvidenceResult.code.
EVIDENCE_OK = "evidence-ok"
EVIDENCE_UNKNOWN_TIER = "evidence-unknown-tier"
EVIDENCE_NOT_AN_OBJECT = "evidence-not-an-object"
EVIDENCE_REPRODUCED_NO_TRANSCRIPT = "reproduced-no-transcript"
EVIDENCE_REPRODUCED_BAD_TRANSCRIPT = "reproduced-bad-transcript"


@dataclass(frozen=True)
class EvidenceResult:
    """Outcome of :func:`validate_finding_evidence`.

    ``ok`` is True when the finding's evidence is internally consistent: an
    untagged or non-REPRODUCED finding is always ok (no transcript needed); a
    REPRODUCED finding is ok only with a valid falsifier transcript. ``tier`` is
    the *effective* tier (the default applied when the field is absent).
    ``code`` is a stable machine token; ``reasons`` is human-readable ASCII.
    """

    ok: bool
    code: str
    tier: str
    reasons: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Transcript validation (the falsifier contract)
# ---------------------------------------------------------------------------


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_entrypoint(entrypoint: object) -> List[str]:
    """Meta-oracle check: the entrypoint must be a real PUBLIC surface."""
    reasons: List[str] = []
    if not isinstance(entrypoint, dict):
        reasons.append("transcript.entrypoint is missing or not an object")
        return reasons
    kind = entrypoint.get("kind")
    if kind == ENTRYPOINT_AGENT_HARNESS:
        reasons.append(
            "transcript.entrypoint.kind is 'agent_harness'; a REPRODUCED "
            "finding must drive a real public entrypoint (one of "
            f"{list(PUBLIC_ENTRYPOINT_KINDS)}), not an agent-built harness "
            "(meta-oracle rule)"
        )
    elif kind not in PUBLIC_ENTRYPOINT_KINDS:
        reasons.append(
            f"transcript.entrypoint.kind {kind!r} is not one of "
            f"{list(PUBLIC_ENTRYPOINT_KINDS)} (meta-oracle rule)"
        )
    if not _nonempty_str(entrypoint.get("ref")):
        reasons.append(
            "transcript.entrypoint.ref is missing or empty (name the public "
            "entrypoint the probe drives, e.g. 'ai_router.contract_gate')"
        )
    return reasons


def _validate_replay(replay: object, output_hash: object) -> List[str]:
    """Pristine-replay check: a second pristine run reproduced the same bytes."""
    reasons: List[str] = []
    if not isinstance(replay, dict):
        reasons.append(
            "transcript.replay is missing or not an object; a REPRODUCED "
            "finding requires a replay on a second pristine checkout"
        )
        return reasons
    if replay.get("pristineCheckout") is not True:
        reasons.append(
            "transcript.replay.pristineCheckout must be true (the replay must "
            "run on a second, fresh checkout)"
        )
    # replay.exitCode, when present, mirrors the schema's integer|null (bool is
    # an int subclass and is rejected, matching the transcript-level exitCode).
    if "exitCode" in replay:
        ec = replay.get("exitCode")
        if ec is not None and (not isinstance(ec, int) or isinstance(ec, bool)):
            reasons.append(
                "transcript.replay.exitCode, when present, must be an integer "
                "or null"
            )
    replay_hash = replay.get("outputHash")
    if not _nonempty_str(replay_hash):
        reasons.append("transcript.replay.outputHash is missing or empty")
    elif _nonempty_str(output_hash) and replay_hash != output_hash:
        reasons.append(
            "transcript.replay.outputHash does not match transcript.outputHash; "
            "the replay did not reproduce the same raw result, so the finding "
            "is not a re-runnable falsifier"
        )
    return reasons


def validate_transcript(transcript: object) -> Tuple[bool, List[str]]:
    """Validate a transcript as a REPRODUCED-grade falsifier.

    Returns ``(ok, reasons)``. A transcript is a valid falsifier only when ALL
    hold (proposal rungs 1 and 3.5):

    - it is an object;
    - ``pinnedRef`` is a non-empty string (the ref the probe ran against);
    - **exactly one** of ``commandId`` / ``templateId`` is a non-empty string -
      a **trusted, operator-authored** command/template, never model-authored
      argv;
    - ``pristineCheckout`` is ``true`` (the original run was on a fresh tree);
    - ``exitCode`` is present and an ``int`` or ``null`` (``null`` == killed /
      timed out, matching the run_test cage);
    - ``rawOutput`` is present and a string (raw, never summarized);
    - ``outputHash`` is a non-empty string;
    - ``entrypoint`` drives a real **public** surface (meta-oracle, via
      :func:`_validate_entrypoint`);
    - ``replay`` reproduced the same ``outputHash`` on a second pristine checkout
      (:func:`_validate_replay`).

    Never raises - a malformed transcript is reported, not thrown.
    """
    reasons: List[str] = []
    if not isinstance(transcript, dict):
        return False, ["transcript is missing or not an object"]

    if not _nonempty_str(transcript.get("pinnedRef")):
        reasons.append("transcript.pinnedRef is missing or empty")

    # commandId / templateId: EXACTLY ONE present (the XOR the schema's oneOf
    # also enforces), and each, WHEN PRESENT, must be a non-empty string -
    # otherwise a wrong-typed value (templateId: 7 / "") that the JSON Schema
    # rejects would pass here, drifting the Python validator looser than the
    # schema (L-066-1). Presence is keyed off the KEY, not validity, so the XOR
    # and the type check are independent.
    has_command_key = "commandId" in transcript
    has_template_key = "templateId" in transcript
    if has_command_key and not _nonempty_str(transcript.get("commandId")):
        reasons.append(
            "transcript.commandId, when present, must be a non-empty string"
        )
    if has_template_key and not _nonempty_str(transcript.get("templateId")):
        reasons.append(
            "transcript.templateId, when present, must be a non-empty string"
        )
    if has_command_key and has_template_key:
        reasons.append(
            "transcript carries both commandId and templateId; exactly one "
            "trusted-probe identifier is required"
        )
    elif not has_command_key and not has_template_key:
        reasons.append(
            "transcript needs a commandId OR a templateId (a trusted, "
            "operator-authored probe identifier - never model-authored argv)"
        )

    # args, when present, mirrors the schema's "type": ["object", "array"].
    if "args" in transcript and not isinstance(
        transcript.get("args"), (dict, list)
    ):
        reasons.append(
            "transcript.args, when present, must be an object or array"
        )

    if transcript.get("pristineCheckout") is not True:
        reasons.append(
            "transcript.pristineCheckout must be true (the probe must run on a "
            "fresh checkout)"
        )

    if "exitCode" not in transcript:
        reasons.append("transcript.exitCode is missing")
    else:
        exit_code = transcript.get("exitCode")
        if exit_code is not None and (
            not isinstance(exit_code, int) or isinstance(exit_code, bool)
        ):
            reasons.append(
                "transcript.exitCode must be an integer or null (null == the "
                "probe was killed / timed out)"
            )

    if "rawOutput" not in transcript:
        reasons.append("transcript.rawOutput is missing")
    elif not isinstance(transcript.get("rawOutput"), str):
        reasons.append("transcript.rawOutput must be a string (raw, unsummarized)")

    output_hash = transcript.get("outputHash")
    if not _nonempty_str(output_hash):
        reasons.append("transcript.outputHash is missing or empty")

    reasons.extend(_validate_entrypoint(transcript.get("entrypoint")))
    reasons.extend(_validate_replay(transcript.get("replay"), output_hash))

    return (not reasons), reasons


# ---------------------------------------------------------------------------
# Per-finding evidence validation (called by the Set 066 artifact validator)
# ---------------------------------------------------------------------------


def effective_tier(finding: object) -> str:
    """Return a finding's effective evidence tier (default applied).

    A finding with no ``evidenceTier`` is :data:`DEFAULT_EVIDENCE_TIER`
    (ASSERTED). An unrecognized value is returned verbatim so the caller can
    report it (``validate_finding_evidence`` flags it); use this only after
    validation when you want the resolved tier.
    """
    if not isinstance(finding, dict):
        return DEFAULT_EVIDENCE_TIER
    tier = finding.get("evidenceTier")
    if tier is None:
        return DEFAULT_EVIDENCE_TIER
    return tier if isinstance(tier, str) else str(tier)


def validate_finding_evidence(finding: object) -> EvidenceResult:
    """Validate one finding's evidence fields.

    The rule the Set 066 artifact validator enforces:

    - no ``evidenceTier`` -> ASSERTED, always ok (additive / backward compatible);
    - ``evidenceTier`` present must be one of :data:`EVIDENCE_TIERS`;
    - ``ASSERTED`` / ``HYPOTHESIS`` -> ok (a transcript, if present, is optional
      supporting context and is not deeply validated here);
    - ``REPRODUCED`` -> ok **only** with a transcript that
      :func:`validate_transcript` accepts (pristine replay + meta-oracle).

    Never raises.
    """
    if not isinstance(finding, dict):
        return EvidenceResult(
            ok=False,
            code=EVIDENCE_NOT_AN_OBJECT,
            tier=DEFAULT_EVIDENCE_TIER,
            reasons=("finding is not an object",),
        )

    raw_tier = finding.get("evidenceTier")
    if raw_tier is None:
        return EvidenceResult(ok=True, code=EVIDENCE_OK, tier=DEFAULT_EVIDENCE_TIER)
    if raw_tier not in EVIDENCE_TIERS:
        return EvidenceResult(
            ok=False,
            code=EVIDENCE_UNKNOWN_TIER,
            tier=DEFAULT_EVIDENCE_TIER,
            reasons=(
                f"evidenceTier {raw_tier!r} is not one of {list(EVIDENCE_TIERS)}",
            ),
        )

    if raw_tier != EVIDENCE_REPRODUCED:
        # ASSERTED / HYPOTHESIS: a read-claim or a flagged suspicion. No
        # transcript required; the falsifier discipline applies only to the
        # tier that claims a reproduction.
        return EvidenceResult(ok=True, code=EVIDENCE_OK, tier=raw_tier)

    transcript = finding.get("transcript")
    if transcript is None:
        return EvidenceResult(
            ok=False,
            code=EVIDENCE_REPRODUCED_NO_TRANSCRIPT,
            tier=raw_tier,
            reasons=(
                "a REPRODUCED finding requires a transcript (a servant-captured "
                "run with a pristine replay); none is present",
            ),
        )
    ok, reasons = validate_transcript(transcript)
    if ok:
        return EvidenceResult(ok=True, code=EVIDENCE_OK, tier=raw_tier)
    return EvidenceResult(
        ok=False,
        code=EVIDENCE_REPRODUCED_BAD_TRANSCRIPT,
        tier=raw_tier,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# The orchestrator-applied tag rule
# ---------------------------------------------------------------------------


def authoritative_tier(
    proposed_tier: Optional[str], transcript: Optional[Union[dict, object]]
) -> str:
    """The tier the ORCHESTRATOR stamps - never the agent's self-report.

    The load-bearing trust rule (proposal rung 1, the falsification reframe):
    REPRODUCED is conferred only by the orchestrator and only on a transcript
    that :func:`validate_transcript` accepts. The agent's *proposed* tier is
    advisory:

    - a valid transcript -> REPRODUCED (the servant re-ran it; trust rests on
      the artifact, not the agent's word);
    - no valid transcript -> a REPRODUCED *claim* collapses to ASSERTED (the
      agent's un-executed word); HYPOTHESIS is preserved (a flagged suspicion);
      anything else (including an unknown proposal) becomes ASSERTED.

    This is the function a producer calls when assembling an artifact, so the
    on-disk ``evidenceTier`` is always orchestrator-derived. ``transcript`` may
    be ``None`` (no execution happened).
    """
    if transcript is not None and validate_transcript(transcript)[0]:
        return EVIDENCE_REPRODUCED
    if proposed_tier == EVIDENCE_HYPOTHESIS:
        return EVIDENCE_HYPOTHESIS
    return EVIDENCE_ASSERTED

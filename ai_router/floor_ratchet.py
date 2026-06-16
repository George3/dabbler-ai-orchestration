"""Set 069 S5 - the quality-gated ceiling -> floor promotion ratchet.

Set 069 built the *executable ceiling*: a pull critic that can run trusted
commands (S2), parameterize operator-authored probe templates (S3), and (behind
a green spike) author probes inside a Podman container (S4). Every reproduced
probeable defect it finds is, today, a one-shot catch - the finding ships and the
knowledge evaporates. The proposal panel's rung 5
(``docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md`` Sec.1.5)
is the **ratchet** that stops that waste: a reproduced probeable defect pays rent
into the **deterministic floor** (the Set 068 contract gate) as a *permanent
falsifier*, so the cheap floor catches that class forever instead of the agent
re-discovering it at agent prices.

The danger the panel named in the same breath: an *ungated* ratchet **poisons the
floor** with brittle, agent-authored tests - the worst outcome, since the whole
layered architecture rests on the floor being trustworthy. So promotion is
**quality-gated and never automatic**. A reproduced probeable defect yields a
**candidate falsifier** (this module's artifact), and admission to the floor
requires ALL of:

- **fails-on-old** - the falsifier was recorded *failing* on the pre-fix ref;
- **passes-on-fixed** - and *passing* on the fixed ref (a real differential, so it
  is a regression test, not a tautology or an always-red check);
- **drives a public contract** - a real public entrypoint (the
  :mod:`ai_router.evidence_protocol` meta-oracle kinds), asserting on a
  **public contract**, never an incidental string match or a wall-clock timing;
- **survives an N-run flake check** - a majority of N pristine runs agreed
  (no false accusations of an honest, merely-flaky check; proposal Sec.4);
- **has an owner** - a named human who owns the falsifier;
- **carries human sign-off** - ``humanSignoff.status == "approved"``. This is the
  load-bearing safety property: a candidate is **never auto-merged**. The builder
  (:func:`build_candidate_from_finding`) always emits ``pending``; only a human can
  write ``approved``, exactly as the orchestrator (never the agent) stamps
  REPRODUCED in :mod:`ai_router.evidence_protocol`.

A candidate may instead carry ``humanSignoff.status == "waived"`` (an explicit
operator decision *not* to promote this one). A waiver satisfies the **mandatory**
coverage rule (every reproduced probeable defect must have a candidate or a
waiver) without admitting anything to the floor. And a candidate whose human
sign-off is ``approved`` but whose mechanical gates do **not** pass is
**rejected**, not admitted - the gate refuses to let a rubber-stamp poison the
floor (the safety analog of S4's "an authored probe can never mint REPRODUCED").

Everything here is pure-Python, dependency-free, ASCII-only on every error
string, and **never raises** on malformed input (a bad artifact is *reported* as
not-ok, exactly like :func:`ai_router.contract_gate.validate_contract_manifest`
and :func:`ai_router.evidence_protocol.validate_transcript`). The JSON Schema
parallel for the on-disk shape is ``docs/candidate-falsifier.schema.json``; the
pure-Python validator here is the runtime contract (L-066-1: it type-checks the
**optional** fields the schema constrains and guards ``int`` vs ``bool``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from ai_router.evidence_protocol import (
    EVIDENCE_REPRODUCED,
    PUBLIC_ENTRYPOINT_KINDS,
    effective_tier,
)

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

CANDIDATE_FALSIFIER_FILENAME = "candidate-falsifiers.json"
CANDIDATE_ARTIFACT_SCHEMA_VERSIONS = (1,)

# Human-sign-off states. ``pending`` is the only state the builder emits; a
# candidate is admitted to the floor ONLY on ``approved`` (a human writes it),
# and ``waived`` is the explicit operator decision not to promote.
SIGNOFF_PENDING = "pending"
SIGNOFF_APPROVED = "approved"
SIGNOFF_WAIVED = "waived"
SIGNOFF_STATES = (SIGNOFF_PENDING, SIGNOFF_APPROVED, SIGNOFF_WAIVED)

# The contract a falsifier asserts on. Only ``public_contract`` is admissible;
# ``incidental`` (a brittle string match / wall-clock timing) is rejected even
# when the entrypoint kind is public (proposal Sec.1.5).
CONTRACT_PUBLIC = "public_contract"
CONTRACT_INCIDENTAL = "incidental"
CONTRACT_KINDS = (CONTRACT_PUBLIC, CONTRACT_INCIDENTAL)

# The default minimum number of flake-check runs. A reproduced probeable defect
# must survive an N-run majority before its falsifier can gate the floor, so an
# honest-but-flaky check never gets promoted (and never falsely accuses a critic
# on a later re-run). Operator-tunable via ``min_flake_runs``.
DEFAULT_MIN_FLAKE_RUNS = 3

# Admission statuses.
ADMIT_ADMITTED = "admitted"  # all gates pass AND human approved -> joins the floor
ADMIT_PENDING = "pending"  # awaiting human approval, or evidence incomplete
ADMIT_WAIVED = "waived"  # explicit operator decision not to promote
ADMIT_REJECTED = "rejected"  # approved by a human but fails a mechanical gate

# Stable machine tokens for CandidateArtifactResult.code.
CANDIDATE_OK = "candidate-ok"
CANDIDATE_NOT_AN_OBJECT = "candidate-not-an-object"
CANDIDATE_BAD_SCHEMA_VERSION = "candidate-bad-schema-version"
CANDIDATE_IDENTITY_MISMATCH = "candidate-identity-mismatch"
CANDIDATE_BAD_STRUCTURE = "candidate-bad-structure"


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int_not_bool(value: object) -> bool:
    # JSON Schema "type": "integer" rejects bool; Python's isinstance(True, int)
    # is True, so guard it explicitly (L-066-1).
    return isinstance(value, int) and not isinstance(value, bool)


# The schema entrypoint.kind enum for a candidate falsifier (the PUBLIC kinds;
# agent_harness is deliberately NOT admissible here, matching the schema).
_ENTRYPOINT_KIND_ENUM = tuple(PUBLIC_ENTRYPOINT_KINDS)

# The closed top-level key set (the schema's additionalProperties: false). The
# Python validator rejects unknown top-level keys so it does not drift looser
# than the schema (L-066-1).
_ARTIFACT_TOP_KEYS = {"schemaVersion", "sessionSetName", "notes", "candidates"}


# ---------------------------------------------------------------------------
# Admission decision (the quality gate - the heart of the ratchet)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissionDecision:
    """The ratchet's verdict on one candidate falsifier.

    ``admitted`` is True only for :data:`ADMIT_ADMITTED` (every mechanical gate
    passed AND a human approved). ``status`` is one of the ``ADMIT_*`` tokens;
    ``reasons`` lists, in ASCII, every gate that is not yet satisfied (empty for
    an admitted or a clean waiver). ``gates`` records the per-gate pass/fail so a
    caller can render a checklist.
    """

    candidate_id: str
    status: str
    admitted: bool
    reasons: Tuple[str, ...] = ()
    gates: Tuple[Tuple[str, bool], ...] = ()


def _signoff_status(candidate: dict) -> Optional[str]:
    signoff = candidate.get("humanSignoff")
    if not isinstance(signoff, dict):
        return None
    status = signoff.get("status")
    return status if isinstance(status, str) else None


def _eval_mechanical_gates(candidate: dict, min_flake_runs: int) -> List[Tuple[str, bool, str]]:
    """Return [(gate_name, passed, reason_if_failed), ...] for the six gates.

    Each gate is evaluated independently so the caller can both decide admission
    and render a full checklist. ``reason_if_failed`` is ASCII and empty when the
    gate passed.
    """
    gates: List[Tuple[str, bool, str]] = []

    # 1. fails-on-old: a recorded FAILING run on the pre-fix ref.
    fails = candidate.get("failsOnOld")
    if not isinstance(fails, dict):
        gates.append(("fails-on-old", False,
                      "failsOnOld is missing or not an object"))
        old_ref = None
    else:
        old_ref = fails.get("ref")
        ok = (_is_nonempty_str(old_ref) and fails.get("failed") is True)
        gates.append(("fails-on-old", ok,
                      "" if ok else
                      "failsOnOld must record failed=true on a named pre-fix ref"))

    # 2. passes-on-fixed: a recorded PASSING run on a DIFFERENT (fixed) ref.
    passes = candidate.get("passesOnFixed")
    if not isinstance(passes, dict):
        gates.append(("passes-on-fixed", False,
                      "passesOnFixed is missing or not an object"))
    else:
        fixed_ref = passes.get("ref")
        ok = (_is_nonempty_str(fixed_ref) and passes.get("passed") is True)
        if ok and _is_nonempty_str(old_ref) and fixed_ref == old_ref:
            ok = False
            gates.append(("passes-on-fixed", False,
                          "passesOnFixed.ref must differ from failsOnOld.ref "
                          "(a real differential, not the same checkout)"))
        else:
            gates.append(("passes-on-fixed", ok,
                          "" if ok else
                          "passesOnFixed must record passed=true on a named "
                          "fixed ref"))

    # 3. drives a public contract: a public entrypoint AND a public (not
    #    incidental) contract assertion. Both, per the proposal: a public
    #    entrypoint that asserts on an incidental string/timing still poisons
    #    the floor with a brittle check.
    entrypoint = candidate.get("entrypoint")
    ep_kind = entrypoint.get("kind") if isinstance(entrypoint, dict) else None
    ep_ref = entrypoint.get("ref") if isinstance(entrypoint, dict) else None
    contract_kind = candidate.get("contractKind")
    public_entrypoint = ep_kind in PUBLIC_ENTRYPOINT_KINDS and _is_nonempty_str(ep_ref)
    public_contract = contract_kind == CONTRACT_PUBLIC
    ok = public_entrypoint and public_contract
    if ok:
        reason = ""
    elif not public_entrypoint:
        reason = (
            "entrypoint must drive a real public surface (kind one of "
            f"{list(PUBLIC_ENTRYPOINT_KINDS)} with a non-empty ref); a falsifier "
            "that drives an agent harness is not admissible (meta-oracle rule)"
        )
    else:
        reason = (
            "contractKind must be 'public_contract'; a falsifier asserting on an "
            "incidental string match or wall-clock timing is too brittle to "
            "promote to the floor"
        )
    gates.append(("drives-public-contract", ok, reason))

    # 4. survives an N-run flake check: a majority of N >= min runs agreed.
    flake = candidate.get("flakeCheck")
    if not isinstance(flake, dict):
        gates.append(("flake-check", False,
                      "flakeCheck is missing or not an object"))
    else:
        runs = flake.get("runs")
        agreeing = flake.get("agreeing")
        stable = flake.get("stable")
        if not (_is_int_not_bool(runs) and _is_int_not_bool(agreeing)):
            gates.append(("flake-check", False,
                          "flakeCheck.runs and flakeCheck.agreeing must be "
                          "integers"))
        elif runs < min_flake_runs:
            gates.append(("flake-check", False,
                          f"flakeCheck.runs ({runs}) is below the minimum "
                          f"({min_flake_runs}); run the falsifier at least that "
                          "many times before promoting it"))
        elif stable is not True:
            gates.append(("flake-check", False,
                          "flakeCheck.stable must be true (the falsifier flaked "
                          "across runs; an unstable check cannot gate the floor)"))
        elif agreeing * 2 <= runs:
            gates.append(("flake-check", False,
                          f"flakeCheck.agreeing ({agreeing}) is not a majority of "
                          f"runs ({runs})"))
        else:
            gates.append(("flake-check", True, ""))

    # 5. has an owner.
    owner = candidate.get("owner")
    ok = _is_nonempty_str(owner)
    gates.append(("has-owner", ok,
                  "" if ok else "owner must name the human who owns this "
                  "falsifier"))

    return gates


def admission_decision(
    candidate: object, *, min_flake_runs: int = DEFAULT_MIN_FLAKE_RUNS
) -> AdmissionDecision:
    """Decide whether one candidate falsifier may be promoted to the floor.

    The quality gate (proposal Sec.1.5). Returns an :class:`AdmissionDecision`:

    - ``humanSignoff.status == "waived"`` -> :data:`ADMIT_WAIVED` (an explicit
      operator decision not to promote; satisfies the mandatory coverage rule but
      admits nothing). A waiver must carry a non-empty ``note``.
    - all six mechanical gates pass AND ``humanSignoff.status == "approved"`` ->
      :data:`ADMIT_ADMITTED` (``admitted=True``) - it joins the floor.
    - the gates pass but sign-off is still ``pending`` (or absent) ->
      :data:`ADMIT_PENDING` (awaiting a human).
    - sign-off is ``approved`` but a mechanical gate fails ->
      :data:`ADMIT_REJECTED` - the gate refuses to admit a rubber-stamped
      falsifier that does not actually fail-on-old / pass-on-fixed / drive a
      public contract / survive the flake check (the safety property: a human
      approval cannot override a failing mechanical gate).

    ``admitted`` is True ONLY for :data:`ADMIT_ADMITTED`. Never raises.
    """
    cid = candidate.get("id") if isinstance(candidate, dict) else None
    cid = cid if _is_nonempty_str(cid) else "<unknown>"
    if not isinstance(candidate, dict):
        return AdmissionDecision(
            candidate_id=cid,
            status=ADMIT_PENDING,
            admitted=False,
            reasons=("candidate is not an object",),
        )

    if not _is_int_not_bool(min_flake_runs) or min_flake_runs < 1:
        min_flake_runs = DEFAULT_MIN_FLAKE_RUNS

    signoff_status = _signoff_status(candidate)

    # An explicit waiver short-circuits the mechanical gates: the operator has
    # decided not to promote this one. It must say why.
    if signoff_status == SIGNOFF_WAIVED:
        signoff = candidate.get("humanSignoff")
        note = signoff.get("note") if isinstance(signoff, dict) else None
        if _is_nonempty_str(note):
            return AdmissionDecision(
                candidate_id=cid, status=ADMIT_WAIVED, admitted=False
            )
        return AdmissionDecision(
            candidate_id=cid,
            status=ADMIT_WAIVED,
            admitted=False,
            reasons=("a waiver must carry a non-empty humanSignoff.note "
                     "explaining why the defect is not promoted to the floor",),
        )

    raw_gates = _eval_mechanical_gates(candidate, min_flake_runs)
    gates = tuple((name, passed) for name, passed, _ in raw_gates)
    failed = [reason for _, passed, reason in raw_gates if not passed and reason]
    all_pass = all(passed for _, passed, _ in raw_gates)

    approved = signoff_status == SIGNOFF_APPROVED
    if approved:
        signoff = candidate.get("humanSignoff")
        by = signoff.get("by") if isinstance(signoff, dict) else None
        if not _is_nonempty_str(by):
            all_pass = False
            failed.append(
                "humanSignoff.status is 'approved' but humanSignoff.by does not "
                "name the approver"
            )

    if approved and all_pass:
        return AdmissionDecision(
            candidate_id=cid, status=ADMIT_ADMITTED, admitted=True, gates=gates
        )
    if approved and not all_pass:
        # A human signed off, but a mechanical gate fails -> never admit. This is
        # the floor-poisoning guard: approval cannot override the gates.
        return AdmissionDecision(
            candidate_id=cid,
            status=ADMIT_REJECTED,
            admitted=False,
            reasons=tuple(failed),
            gates=gates,
        )
    # Not yet approved (pending / absent / unknown status): pending, with the
    # outstanding gates surfaced so the owner knows what is left.
    reasons = list(failed)
    if signoff_status not in (SIGNOFF_PENDING, None):
        reasons.append(
            f"humanSignoff.status {signoff_status!r} is not one of "
            f"{list(SIGNOFF_STATES)}"
        )
    reasons.append("awaiting human sign-off (humanSignoff.status == 'approved')")
    return AdmissionDecision(
        candidate_id=cid,
        status=ADMIT_PENDING,
        admitted=False,
        reasons=tuple(reasons),
        gates=gates,
    )


# ---------------------------------------------------------------------------
# Artifact validation (the on-disk contract; L-066-1 parity with the schema)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateArtifactResult:
    """Outcome of :func:`validate_candidate_falsifiers_artifact`.

    ``ok`` is True for a structurally valid artifact whose identity matches the
    set (when an expected name is given). ``decisions`` holds the per-candidate
    :class:`AdmissionDecision` (empty when the artifact is structurally invalid).
    ``session_set_name`` echoes the artifact identity for the caller's checks.
    """

    ok: bool
    code: str
    reasons: Tuple[str, ...] = ()
    session_set_name: Optional[str] = None
    decisions: Tuple[AdmissionDecision, ...] = ()


def _validate_candidate_structure(candidate: object, index: int) -> List[str]:
    """Structural checks for one candidate (the schema's required + typed fields).

    Mirrors ``docs/candidate-falsifier.schema.json``. Type-checks optional fields
    so the Python validator does not drift looser than the schema (L-066-1).
    """
    reasons: List[str] = []
    where = f"candidates[{index}]"
    if not isinstance(candidate, dict):
        return [f"{where} is not an object"]

    if not _is_nonempty_str(candidate.get("id")):
        reasons.append(f"{where}.id is missing or empty")

    defect = candidate.get("defect")
    if not isinstance(defect, dict):
        reasons.append(f"{where}.defect is missing or not an object")
    else:
        if not _is_nonempty_str(defect.get("findingRef")):
            reasons.append(f"{where}.defect.findingRef is missing or empty")
        if not _is_nonempty_str(defect.get("description")):
            reasons.append(f"{where}.defect.description is missing or empty")
        if "severity" in defect and not isinstance(defect.get("severity"), str):
            reasons.append(f"{where}.defect.severity, when present, must be a string")

    # The falsifier: exactly one of commandId / templateId (the trusted-probe
    # XOR, mirroring the evidence transcript). Never model-authored argv.
    falsifier = candidate.get("falsifier")
    if not isinstance(falsifier, dict):
        reasons.append(f"{where}.falsifier is missing or not an object")
    else:
        has_cmd = "commandId" in falsifier
        has_tpl = "templateId" in falsifier
        if has_cmd and not _is_nonempty_str(falsifier.get("commandId")):
            reasons.append(f"{where}.falsifier.commandId, when present, must be "
                           "a non-empty string")
        if has_tpl and not _is_nonempty_str(falsifier.get("templateId")):
            reasons.append(f"{where}.falsifier.templateId, when present, must be "
                           "a non-empty string")
        if has_cmd and has_tpl:
            reasons.append(f"{where}.falsifier carries both commandId and "
                           "templateId; exactly one trusted-probe id is required")
        elif not has_cmd and not has_tpl:
            reasons.append(f"{where}.falsifier needs a commandId OR a templateId "
                           "(a trusted, operator-authored probe id - never "
                           "model-authored argv)")
        if "args" in falsifier and not isinstance(falsifier.get("args"), (dict, list)):
            reasons.append(f"{where}.falsifier.args, when present, must be an "
                           "object or array")

    # entrypoint: required object (the meta-oracle surface). The schema constrains
    # kind to the PUBLIC enum (agent_harness is not admissible here), so the
    # structural validator enforces the enum too - not just a non-empty string -
    # to stay in parity (L-066-1).
    entrypoint = candidate.get("entrypoint")
    if not isinstance(entrypoint, dict):
        reasons.append(f"{where}.entrypoint is missing or not an object")
    else:
        kind = entrypoint.get("kind")
        if not _is_nonempty_str(kind):
            reasons.append(f"{where}.entrypoint.kind is missing or empty")
        elif kind not in _ENTRYPOINT_KIND_ENUM:
            reasons.append(f"{where}.entrypoint.kind must be one of "
                           f"{list(_ENTRYPOINT_KIND_ENUM)} (a public surface; "
                           "agent_harness is not admissible)")
        if not _is_nonempty_str(entrypoint.get("ref")):
            reasons.append(f"{where}.entrypoint.ref is missing or empty")

    if not _is_nonempty_str(candidate.get("contractKind")):
        reasons.append(f"{where}.contractKind is missing or empty")
    elif candidate.get("contractKind") not in CONTRACT_KINDS:
        reasons.append(f"{where}.contractKind must be one of {list(CONTRACT_KINDS)}")

    for key in ("failsOnOld", "passesOnFixed", "flakeCheck", "humanSignoff"):
        if not isinstance(candidate.get(key), dict):
            reasons.append(f"{where}.{key} is missing or not an object")

    # Type-check the OPTIONAL sub-fields the schema constrains, so the validator
    # does not drift looser than the schema on a wrong-typed value (L-066-1).
    fails = candidate.get("failsOnOld")
    if isinstance(fails, dict):
        if "ref" in fails and not isinstance(fails.get("ref"), str):
            reasons.append(f"{where}.failsOnOld.ref, when present, must be a string")
        if "failed" in fails and not isinstance(fails.get("failed"), bool):
            reasons.append(f"{where}.failsOnOld.failed, when present, must be a boolean")
        if "outputHash" in fails and not isinstance(fails.get("outputHash"), str):
            reasons.append(f"{where}.failsOnOld.outputHash, when present, must be a string")
    passes = candidate.get("passesOnFixed")
    if isinstance(passes, dict):
        if "ref" in passes and not isinstance(passes.get("ref"), str):
            reasons.append(f"{where}.passesOnFixed.ref, when present, must be a string")
        if "passed" in passes and not isinstance(passes.get("passed"), bool):
            reasons.append(f"{where}.passesOnFixed.passed, when present, must be a boolean")
    flake = candidate.get("flakeCheck")
    if isinstance(flake, dict):
        if "runs" in flake and not _is_int_not_bool(flake.get("runs")):
            reasons.append(f"{where}.flakeCheck.runs, when present, must be an integer")
        if "agreeing" in flake and not _is_int_not_bool(flake.get("agreeing")):
            reasons.append(f"{where}.flakeCheck.agreeing, when present, must be an integer")
        if "stable" in flake and not isinstance(flake.get("stable"), bool):
            reasons.append(f"{where}.flakeCheck.stable, when present, must be a boolean")

    # humanSignoff.status enum + typed optional fields.
    signoff = candidate.get("humanSignoff")
    if isinstance(signoff, dict):
        status = signoff.get("status")
        if not _is_nonempty_str(status):
            reasons.append(f"{where}.humanSignoff.status is missing or empty")
        elif status not in SIGNOFF_STATES:
            reasons.append(f"{where}.humanSignoff.status must be one of "
                           f"{list(SIGNOFF_STATES)}")
        for opt in ("by", "at", "note"):
            if opt in signoff and not isinstance(signoff.get(opt), str):
                reasons.append(f"{where}.humanSignoff.{opt}, when present, must be "
                               "a string")

    if not _is_nonempty_str(candidate.get("owner")):
        reasons.append(f"{where}.owner is missing or empty")

    return reasons


def validate_candidate_falsifiers_artifact(
    artifact: object,
    *,
    expected_set_name: Optional[str] = None,
    min_flake_runs: int = DEFAULT_MIN_FLAKE_RUNS,
) -> CandidateArtifactResult:
    """Validate a ``candidate-falsifiers.json`` artifact.

    Checks the envelope (``schemaVersion`` in
    :data:`CANDIDATE_ARTIFACT_SCHEMA_VERSIONS`, non-empty ``sessionSetName``, a
    ``candidates`` array), the optional identity match against
    ``expected_set_name`` (a stale/copied artifact must not satisfy another set),
    and each candidate's structure. On a structurally valid artifact it also
    computes the per-candidate :class:`AdmissionDecision`. Never raises.
    """
    if not isinstance(artifact, dict):
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_NOT_AN_OBJECT,
            reasons=("artifact is not an object",),
        )

    version = artifact.get("schemaVersion")
    if not _is_int_not_bool(version) or version not in CANDIDATE_ARTIFACT_SCHEMA_VERSIONS:
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_BAD_SCHEMA_VERSION,
            reasons=(f"schemaVersion must be one of "
                     f"{list(CANDIDATE_ARTIFACT_SCHEMA_VERSIONS)} (integer)",),
        )

    set_name = artifact.get("sessionSetName")
    if not _is_nonempty_str(set_name):
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_BAD_STRUCTURE,
            reasons=("sessionSetName is missing or empty",),
        )
    if expected_set_name is not None and set_name != expected_set_name:
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_IDENTITY_MISMATCH,
            session_set_name=set_name,
            reasons=(f"sessionSetName {set_name!r} does not match the set being "
                     f"closed ({expected_set_name!r})",),
        )

    candidates = artifact.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_BAD_STRUCTURE,
            session_set_name=set_name,
            reasons=("candidates must be a non-empty array",),
        )

    reasons: List[str] = []
    # The schema closes the top-level object (additionalProperties: false); reject
    # unknown top-level keys so the validator does not drift looser (L-066-1).
    extra = sorted(set(artifact) - _ARTIFACT_TOP_KEYS)
    if extra:
        reasons.append(f"unexpected top-level key(s): {extra}")
    if "notes" in artifact and not isinstance(artifact.get("notes"), str):
        reasons.append("notes, when present, must be a string")

    seen_ids: set = set()
    for i, candidate in enumerate(candidates):
        reasons.extend(_validate_candidate_structure(candidate, i))
        if isinstance(candidate, dict):
            cid = candidate.get("id")
            if _is_nonempty_str(cid):
                if cid in seen_ids:
                    reasons.append(f"candidates[{i}].id {cid!r} is duplicated")
                seen_ids.add(cid)

    if reasons:
        return CandidateArtifactResult(
            ok=False, code=CANDIDATE_BAD_STRUCTURE,
            session_set_name=set_name, reasons=tuple(reasons),
        )

    decisions = tuple(
        admission_decision(c, min_flake_runs=min_flake_runs) for c in candidates
    )
    return CandidateArtifactResult(
        ok=True, code=CANDIDATE_OK,
        session_set_name=set_name, decisions=decisions,
    )


# ---------------------------------------------------------------------------
# Building a candidate from a reproduced finding (the producer-side hook)
# ---------------------------------------------------------------------------


def build_candidate_from_finding(
    finding: dict,
    *,
    candidate_id: str,
    finding_ref: str,
    owner: str,
    fails_on_old: Optional[dict] = None,
    passes_on_fixed: Optional[dict] = None,
    flake_check: Optional[dict] = None,
    contract_kind: str = CONTRACT_PUBLIC,
) -> dict:
    """Assemble a *pending* candidate falsifier from a REPRODUCED finding.

    Extracts the trusted falsifier (commandId XOR templateId + args), the pinned
    ref, and the public entrypoint from the finding's evidence transcript - so the
    promoted falsifier IS the reproduced probe, not an agent re-authoring. The
    differential evidence (``fails_on_old`` / ``passes_on_fixed``) and the
    ``flake_check`` are passed in by the producer that ran them; absent ones are
    recorded as empty stubs the admission gate will (correctly) reject as
    incomplete.

    The result ALWAYS carries ``humanSignoff = {"status": "pending"}`` - the
    builder never mints an approval. This is the never-auto-merge property: only a
    human writes ``approved``. Raises ``ValueError`` on either of two programmer
    errors (both are inconsistent inputs the ratchet never receives in normal
    flow, since the S1 protocol guarantees a REPRODUCED finding carries a valid
    transcript - they are guardrails, not an input-validation path): a
    non-REPRODUCED finding, or a REPRODUCED finding with no transcript dict to
    extract the trusted falsifier from. Every *malformed-artifact* path is handled
    by :func:`validate_candidate_falsifiers_artifact`, which never raises.
    """
    if effective_tier(finding) != EVIDENCE_REPRODUCED:
        raise ValueError(
            "build_candidate_from_finding requires a REPRODUCED finding; the "
            "ratchet promotes reproduced probeable defects only"
        )
    transcript = finding.get("transcript")
    if not isinstance(transcript, dict):
        raise ValueError(
            "a REPRODUCED finding must carry a transcript to build a candidate "
            "falsifier from"
        )

    falsifier: dict = {}
    if _is_nonempty_str(transcript.get("commandId")):
        falsifier["commandId"] = transcript["commandId"]
    elif _is_nonempty_str(transcript.get("templateId")):
        falsifier["templateId"] = transcript["templateId"]
    if isinstance(transcript.get("args"), (dict, list)):
        falsifier["args"] = transcript["args"]

    entrypoint = transcript.get("entrypoint")
    entrypoint = dict(entrypoint) if isinstance(entrypoint, dict) else {}

    candidate: dict = {
        "id": candidate_id,
        "defect": {
            "findingRef": finding_ref,
            "description": finding.get("description", ""),
        },
        "falsifier": falsifier,
        "entrypoint": entrypoint,
        "contractKind": contract_kind,
        "failsOnOld": dict(fails_on_old) if isinstance(fails_on_old, dict)
        else {"ref": transcript.get("pinnedRef", ""), "failed": False},
        "passesOnFixed": dict(passes_on_fixed) if isinstance(passes_on_fixed, dict)
        else {},
        "flakeCheck": dict(flake_check) if isinstance(flake_check, dict) else {},
        "owner": owner,
        "humanSignoff": {"status": SIGNOFF_PENDING},
    }
    severity = finding.get("severity")
    if isinstance(severity, str) and severity:
        candidate["defect"]["severity"] = severity
    return candidate


# ---------------------------------------------------------------------------
# Mandatory coverage: every reproduced probeable defect -> a candidate or waiver
# ---------------------------------------------------------------------------


def reproduced_findings(critique_artifact: object) -> List[Tuple[str, dict]]:
    """Return ``[(critique_ref, finding), ...]`` for every REPRODUCED finding.

    Walks a ``path-aware-critique.json`` artifact (the Set 066 shape, evidence-
    tiered in S1). A REPRODUCED finding is, by construction, a reproduced
    *probeable* defect - it was reproduced by running a probe. ``critique_ref``
    is ``"<provider>:<index>"`` so a caller can name the source. Never raises.
    """
    out: List[Tuple[str, dict]] = []
    if not isinstance(critique_artifact, dict):
        return out
    critiques = critique_artifact.get("critiques")
    if not isinstance(critiques, list):
        return out
    for critique in critiques:
        if not isinstance(critique, dict):
            continue
        provider = critique.get("provider")
        provider = provider if isinstance(provider, str) and provider else "?"
        findings = critique.get("findings")
        if not isinstance(findings, list):
            continue
        for j, finding in enumerate(findings):
            if isinstance(finding, dict) and effective_tier(finding) == EVIDENCE_REPRODUCED:
                out.append((f"{provider}:{j}", finding))
    return out


@dataclass(frozen=True)
class CoverageResult:
    """Outcome of :func:`check_floor_ratchet_coverage`.

    ``ok`` is True when every reproduced probeable defect has a candidate
    falsifier (admitted, pending, or waived) whose ``defect.findingRef`` names it.
    ``uncovered`` lists the reproduced findings with no candidate (the mandatory
    rule's violations). ``admitted`` / ``pending`` / ``waived`` count the
    candidates by disposition for a close-out summary.
    """

    ok: bool
    uncovered: Tuple[str, ...] = ()
    admitted: int = 0
    pending: int = 0
    waived: int = 0
    rejected: int = 0
    reasons: Tuple[str, ...] = ()


def check_floor_ratchet_coverage(
    critique_artifact: object,
    candidate_artifact: object,
    *,
    min_flake_runs: int = DEFAULT_MIN_FLAKE_RUNS,
) -> CoverageResult:
    """Enforce the mandatory rule: every reproduced probeable defect is covered.

    A reproduced probeable defect (a REPRODUCED finding in the critique artifact)
    must have a candidate falsifier - admitted, pending, or explicitly waived -
    whose ``defect.findingRef`` references it. A pending candidate satisfies the
    mandatory rule (the work is queued for a human); only a *missing* candidate is
    a violation, so the gate does not block on the human's review latency. Never
    raises.
    """
    repro = reproduced_findings(critique_artifact)
    art = validate_candidate_falsifiers_artifact(
        candidate_artifact, min_flake_runs=min_flake_runs
    )

    # Index candidates by the findingRef they cover. A REJECTED candidate
    # (a human approved it but it fails a mechanical gate) does NOT satisfy the
    # mandatory rule - it is a broken candidate that needs fixing, not a covered
    # defect. Only admitted / pending / waived count toward coverage.
    covered_refs: set = set()
    admitted = pending = waived = rejected = 0
    if art.ok:
        candidates = candidate_artifact.get("candidates", [])
        for c, d in zip(candidates, art.decisions):
            if d.status == ADMIT_ADMITTED:
                admitted += 1
            elif d.status == ADMIT_WAIVED:
                waived += 1
            elif d.status == ADMIT_REJECTED:
                rejected += 1
            else:
                pending += 1
            if d.status == ADMIT_REJECTED:
                continue
            if isinstance(c, dict):
                defect = c.get("defect")
                if isinstance(defect, dict):
                    ref = defect.get("findingRef")
                    if _is_nonempty_str(ref):
                        covered_refs.add(ref)

    reasons: List[str] = []
    if repro and not art.ok:
        reasons.append(
            "there are reproduced probeable defects but no valid "
            f"candidate-falsifiers artifact ({art.code}: "
            f"{'; '.join(art.reasons)})"
        )

    uncovered: List[str] = []
    for ref, finding in repro:
        # A candidate covers a finding when its findingRef matches the
        # "<provider>:<index>" ref OR (looser) the finding's own description -
        # producers may key on either; the ref is the stable identifier.
        desc = finding.get("description") if isinstance(finding, dict) else None
        if ref in covered_refs:
            continue
        if _is_nonempty_str(desc) and desc in covered_refs:
            continue
        uncovered.append(ref)

    ok = not uncovered and not reasons
    return CoverageResult(
        ok=ok,
        uncovered=tuple(uncovered),
        admitted=admitted,
        pending=pending,
        waived=waived,
        rejected=rejected,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def find_candidate_falsifiers(session_set_dir: Union[str, Path]) -> Optional[Path]:
    """Return the path to the set's candidate-falsifiers artifact, or ``None``."""
    path = Path(session_set_dir) / CANDIDATE_FALSIFIER_FILENAME
    return path if path.is_file() else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    """CLI entry point. Returns an exit code; never calls ``sys.exit``.

    ``validate`` loads a candidate-falsifiers artifact, validates it, and prints
    each candidate's admission status (ASCII-only). A pending candidate is not an
    error (it is awaiting human sign-off); a structurally invalid artifact, an
    identity mismatch, or a *rejected* candidate (approved but failing a gate) is.
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="python -m ai_router.floor_ratchet",
        description=(
            "Quality-gated ceiling->floor ratchet (Set 069 S5): validate "
            "candidate falsifiers and print their admission status."
        ),
    )
    parser.add_argument("--session-set-dir", required=True)
    parser.add_argument(
        "--min-flake-runs", type=int, default=DEFAULT_MIN_FLAKE_RUNS,
        help=f"minimum flake-check runs (default {DEFAULT_MIN_FLAKE_RUNS})",
    )
    args = parser.parse_args(argv)

    path = find_candidate_falsifiers(args.session_set_dir)
    if path is None:
        print(f"[ ] no {CANDIDATE_FALSIFIER_FILENAME} at the session-set root")
        return 0
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[ ] {CANDIDATE_FALSIFIER_FILENAME} is unreadable: {exc}")
        return 2

    expected = Path(args.session_set_dir).resolve().name
    result = validate_candidate_falsifiers_artifact(
        artifact, expected_set_name=expected, min_flake_runs=args.min_flake_runs
    )
    if not result.ok:
        print(f"[ ] artifact invalid ({result.code}):")
        for r in result.reasons:
            print(f"    - {r}")
        return 1

    bad = False
    for d in result.decisions:
        mark = "x" if d.admitted else " "
        print(f"[{mark}] {d.candidate_id}: {d.status}")
        for r in d.reasons:
            print(f"    - {r}")
        if d.status == ADMIT_REJECTED:
            bad = True
    return 1 if bad else 0


__all__ = [
    "CANDIDATE_FALSIFIER_FILENAME",
    "CANDIDATE_ARTIFACT_SCHEMA_VERSIONS",
    "SIGNOFF_PENDING",
    "SIGNOFF_APPROVED",
    "SIGNOFF_WAIVED",
    "SIGNOFF_STATES",
    "CONTRACT_PUBLIC",
    "CONTRACT_INCIDENTAL",
    "CONTRACT_KINDS",
    "DEFAULT_MIN_FLAKE_RUNS",
    "ADMIT_ADMITTED",
    "ADMIT_PENDING",
    "ADMIT_WAIVED",
    "ADMIT_REJECTED",
    "AdmissionDecision",
    "CandidateArtifactResult",
    "CoverageResult",
    "admission_decision",
    "validate_candidate_falsifiers_artifact",
    "build_candidate_from_finding",
    "reproduced_findings",
    "check_floor_ratchet_coverage",
    "find_candidate_falsifiers",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - CLI entry
    import sys

    raise SystemExit(main(sys.argv[1:]))

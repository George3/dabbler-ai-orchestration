"""Tests for the Set 069 S1 execution-evidence protocol.

Covers the four load-bearing parts of ``ai_router.evidence_protocol``:

- the evidence tiers + the additive ``ASSERTED`` default,
- the transcript falsifier contract (trusted-probe id, pristine checkout,
  pristine-replay hash match, meta-oracle public entrypoint),
- the orchestrator-applies-the-tag rule (the agent never self-grants
  REPRODUCED),
- the per-finding rule the Set 066 artifact validator consumes.

No metered calls; everything here is pure-Python and deterministic.
"""

from __future__ import annotations

import evidence_protocol as ep  # conftest puts ai_router/ on sys.path


def _valid_transcript(output: str = "boom\nTraceback ...\n") -> dict:
    """A fully valid REPRODUCED-grade transcript (pristine replay, public ep)."""
    h = ep.hash_output(output)
    return {
        "pinnedRef": "abc1234",
        "commandId": "validator-malformed-bytes",
        "args": {"path": "bad.json"},
        "pristineCheckout": True,
        "exitCode": 1,
        "rawOutput": output,
        "outputHash": h,
        "entrypoint": {
            "kind": ep.ENTRYPOINT_PUBLIC_COMMAND,
            "ref": "ai_router.contract_gate",
        },
        "replay": {
            "pristineCheckout": True,
            "exitCode": 1,
            "outputHash": h,
        },
    }


class TestTiers:
    def test_tier_constants(self):
        assert ep.EVIDENCE_TIERS == (
            ep.EVIDENCE_REPRODUCED,
            ep.EVIDENCE_ASSERTED,
            ep.EVIDENCE_HYPOTHESIS,
        )

    def test_default_tier_is_asserted(self):
        # An untagged finding is a read-claim, never REPRODUCED.
        assert ep.DEFAULT_EVIDENCE_TIER == ep.EVIDENCE_ASSERTED

    def test_agent_harness_is_not_a_public_kind(self):
        assert ep.ENTRYPOINT_AGENT_HARNESS not in ep.PUBLIC_ENTRYPOINT_KINDS


class TestHashOutput:
    def test_sha256_prefixed_and_deterministic(self):
        a = ep.hash_output("hello")
        b = ep.hash_output("hello")
        assert a == b
        assert a.startswith("sha256:")
        assert len(a) == len("sha256:") + 64

    def test_distinct_inputs_distinct_hashes(self):
        assert ep.hash_output("a") != ep.hash_output("b")

    def test_non_string_coerced_not_raised(self):
        assert ep.hash_output(None) == ep.hash_output("")
        assert ep.hash_output(123).startswith("sha256:")


class TestValidateTranscript:
    def test_full_valid_transcript(self):
        ok, reasons = ep.validate_transcript(_valid_transcript())
        assert ok is True, reasons
        assert reasons == []

    def test_template_id_form_is_valid(self):
        t = _valid_transcript()
        del t["commandId"]
        t["templateId"] = "call-with-bad-parent-dir"
        ok, reasons = ep.validate_transcript(t)
        assert ok is True, reasons

    def test_exit_code_null_is_valid(self):
        # null exitCode == killed / timed out (matches the run_test cage).
        t = _valid_transcript()
        t["exitCode"] = None
        t["replay"]["exitCode"] = None
        ok, reasons = ep.validate_transcript(t)
        assert ok is True, reasons

    def test_not_an_object(self):
        ok, reasons = ep.validate_transcript("nope")
        assert ok is False
        assert any("not an object" in r for r in reasons)

    def test_missing_pinned_ref(self):
        t = _valid_transcript()
        del t["pinnedRef"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("pinnedRef" in r for r in reasons)

    def test_both_command_and_template_rejected(self):
        t = _valid_transcript()
        t["templateId"] = "x"
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("both commandId and templateId" in r for r in reasons)

    def test_neither_command_nor_template_rejected(self):
        # The model-authored-argv guard: a trusted identifier is mandatory.
        t = _valid_transcript()
        del t["commandId"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("commandId OR a templateId" in r for r in reasons)

    def test_template_wrong_type_rejected(self):
        # commandId valid + templateId: 7 -> both keys present (XOR) AND a
        # wrong-typed templateId; the L-066-1 parity hole the verifier caught.
        t = _valid_transcript()
        t["templateId"] = 7
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("templateId, when present, must be a non-empty" in r for r in reasons)

    def test_command_empty_string_rejected(self):
        t = _valid_transcript()
        del t["commandId"]
        t["templateId"] = "call-x"
        t["commandId"] = ""
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("commandId, when present, must be a non-empty" in r for r in reasons)

    def test_args_wrong_type_rejected(self):
        t = _valid_transcript()
        t["args"] = 7
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("args, when present, must be an object or array" in r for r in reasons)

    def test_args_list_form_allowed(self):
        t = _valid_transcript()
        t["args"] = ["--flag", "value"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is True, reasons

    def test_non_pristine_checkout_rejected(self):
        t = _valid_transcript()
        t["pristineCheckout"] = False
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("pristineCheckout must be true" in r for r in reasons)

    def test_missing_exit_code_rejected(self):
        t = _valid_transcript()
        del t["exitCode"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("exitCode is missing" in r for r in reasons)

    def test_bool_exit_code_rejected(self):
        # bool is an int subclass in Python; the schema wants a true integer.
        t = _valid_transcript()
        t["exitCode"] = True
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("exitCode must be an integer or null" in r for r in reasons)

    def test_missing_raw_output_rejected(self):
        t = _valid_transcript()
        del t["rawOutput"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("rawOutput is missing" in r for r in reasons)

    def test_empty_raw_output_is_allowed(self):
        # Execution can legitimately produce no output; the hash still pins it.
        t = _valid_transcript(output="")
        ok, reasons = ep.validate_transcript(t)
        assert ok is True, reasons

    def test_missing_output_hash_rejected(self):
        t = _valid_transcript()
        del t["outputHash"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("outputHash is missing" in r for r in reasons)


class TestPristineReplay:
    def test_replay_missing_rejected(self):
        t = _valid_transcript()
        del t["replay"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("replay is missing" in r for r in reasons)

    def test_replay_hash_mismatch_rejected(self):
        # The replay did not reproduce the same bytes -> not a falsifier.
        t = _valid_transcript()
        t["replay"]["outputHash"] = ep.hash_output("different output")
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("did not reproduce the same raw result" in r for r in reasons)

    def test_replay_not_pristine_rejected(self):
        t = _valid_transcript()
        t["replay"]["pristineCheckout"] = False
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("replay.pristineCheckout must be true" in r for r in reasons)

    def test_replay_exit_code_bool_rejected(self):
        # bool is an int subclass; the schema's replay.exitCode is integer|null.
        t = _valid_transcript()
        t["replay"]["exitCode"] = True
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("replay.exitCode, when present, must be an integer" in r for r in reasons)


class TestMetaOracle:
    def test_agent_harness_entrypoint_rejected(self):
        t = _valid_transcript()
        t["entrypoint"]["kind"] = ep.ENTRYPOINT_AGENT_HARNESS
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("agent-built harness" in r for r in reasons)

    def test_unknown_entrypoint_kind_rejected(self):
        t = _valid_transcript()
        t["entrypoint"]["kind"] = "mystery"
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("meta-oracle rule" in r for r in reasons)

    def test_entrypoint_missing_ref_rejected(self):
        t = _valid_transcript()
        del t["entrypoint"]["ref"]
        ok, reasons = ep.validate_transcript(t)
        assert ok is False
        assert any("entrypoint.ref is missing" in r for r in reasons)

    def test_each_public_kind_accepted(self):
        for kind in ep.PUBLIC_ENTRYPOINT_KINDS:
            t = _valid_transcript()
            t["entrypoint"]["kind"] = kind
            ok, reasons = ep.validate_transcript(t)
            assert ok is True, f"{kind}: {reasons}"


class TestValidateFindingEvidence:
    def test_untagged_finding_is_asserted_and_ok(self):
        res = ep.validate_finding_evidence({"description": "a read claim"})
        assert res.ok is True
        assert res.tier == ep.EVIDENCE_ASSERTED
        assert res.code == ep.EVIDENCE_OK

    def test_asserted_ok_without_transcript(self):
        res = ep.validate_finding_evidence(
            {"description": "x", "evidenceTier": ep.EVIDENCE_ASSERTED}
        )
        assert res.ok is True

    def test_hypothesis_ok_without_transcript(self):
        res = ep.validate_finding_evidence(
            {"description": "x", "evidenceTier": ep.EVIDENCE_HYPOTHESIS}
        )
        assert res.ok is True
        assert res.tier == ep.EVIDENCE_HYPOTHESIS

    def test_unknown_tier_rejected(self):
        res = ep.validate_finding_evidence(
            {"description": "x", "evidenceTier": "SORTA_SURE"}
        )
        assert res.ok is False
        assert res.code == ep.EVIDENCE_UNKNOWN_TIER

    def test_non_str_tier_rejected(self):
        res = ep.validate_finding_evidence(
            {"description": "x", "evidenceTier": 3}
        )
        assert res.ok is False
        assert res.code == ep.EVIDENCE_UNKNOWN_TIER

    def test_reproduced_without_transcript_rejected(self):
        res = ep.validate_finding_evidence(
            {"description": "x", "evidenceTier": ep.EVIDENCE_REPRODUCED}
        )
        assert res.ok is False
        assert res.code == ep.EVIDENCE_REPRODUCED_NO_TRANSCRIPT

    def test_reproduced_with_bad_transcript_rejected(self):
        finding = {
            "description": "x",
            "evidenceTier": ep.EVIDENCE_REPRODUCED,
            "transcript": {"pinnedRef": "abc"},  # incomplete
        }
        res = ep.validate_finding_evidence(finding)
        assert res.ok is False
        assert res.code == ep.EVIDENCE_REPRODUCED_BAD_TRANSCRIPT

    def test_reproduced_with_valid_transcript_ok(self):
        finding = {
            "description": "x",
            "evidenceTier": ep.EVIDENCE_REPRODUCED,
            "transcript": _valid_transcript(),
        }
        res = ep.validate_finding_evidence(finding)
        assert res.ok is True
        assert res.tier == ep.EVIDENCE_REPRODUCED

    def test_non_object_finding_rejected(self):
        res = ep.validate_finding_evidence("not a dict")
        assert res.ok is False
        assert res.code == ep.EVIDENCE_NOT_AN_OBJECT


class TestAuthoritativeTier:
    """The orchestrator-applies-the-tag rule: the agent never self-grants
    REPRODUCED."""

    def test_valid_transcript_confers_reproduced(self):
        # Even if the agent proposed nothing, a valid transcript -> REPRODUCED.
        assert (
            ep.authoritative_tier(None, _valid_transcript())
            == ep.EVIDENCE_REPRODUCED
        )

    def test_claimed_reproduced_without_transcript_collapses_to_asserted(self):
        assert (
            ep.authoritative_tier(ep.EVIDENCE_REPRODUCED, None)
            == ep.EVIDENCE_ASSERTED
        )

    def test_claimed_reproduced_with_bad_transcript_collapses_to_asserted(self):
        bad = {"pinnedRef": "abc"}
        assert (
            ep.authoritative_tier(ep.EVIDENCE_REPRODUCED, bad)
            == ep.EVIDENCE_ASSERTED
        )

    def test_hypothesis_preserved_without_transcript(self):
        assert (
            ep.authoritative_tier(ep.EVIDENCE_HYPOTHESIS, None)
            == ep.EVIDENCE_HYPOTHESIS
        )

    def test_unknown_proposal_becomes_asserted(self):
        assert ep.authoritative_tier("WHATEVER", None) == ep.EVIDENCE_ASSERTED

    def test_valid_transcript_overrides_hypothesis_proposal(self):
        # Execution evidence wins over the agent's lower self-estimate.
        assert (
            ep.authoritative_tier(ep.EVIDENCE_HYPOTHESIS, _valid_transcript())
            == ep.EVIDENCE_REPRODUCED
        )


class TestEffectiveTier:
    def test_absent_tier_defaults(self):
        assert ep.effective_tier({"description": "x"}) == ep.EVIDENCE_ASSERTED

    def test_present_tier_returned(self):
        assert (
            ep.effective_tier(
                {"description": "x", "evidenceTier": ep.EVIDENCE_REPRODUCED}
            )
            == ep.EVIDENCE_REPRODUCED
        )

    def test_non_dict_defaults(self):
        assert ep.effective_tier(None) == ep.EVIDENCE_ASSERTED

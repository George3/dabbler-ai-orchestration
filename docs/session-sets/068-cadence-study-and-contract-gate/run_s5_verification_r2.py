"""Set 068 S5 cross-provider verification ROUND 2 (route -> gpt-5-4).

R1 returned ISSUES_FOUND with one Major (malformed-but-parseable activity-log can
silently disarm a required gate / raise past the never-raises contract). This
round provides the R1 finding + the fix + the updated functions and asks the
verifier to confirm resolution and check for anything new the fix introduced.
"""
from __future__ import annotations

from pathlib import Path

from ai_router import route

SET = Path("docs/session-sets/068-cadence-study-and-contract-gate")


def _read(p):
    return Path(p).read_text(encoding="utf-8")


def _slice(path, start_marker, end_markers):
    text = _read(path).splitlines()
    out, capturing = [], False
    for ln in text:
        if start_marker in ln:
            capturing = True
        if capturing:
            out.append(ln)
            if any(m in ln for m in end_markers) and len(out) > 3:
                break
    return "\n".join(out)


def main():
    module = _read("ai_router/contract_gate.py")
    # Embed the four touched functions in full (they are contiguous near the top).
    helper_to_unreadable = "\n".join(
        module.split("def _read_activity_entries", 1)[1]
        .split("def record_contract_gate")[0]
        .splitlines()
    )
    record_fn = "def record_contract_gate" + module.split(
        "def record_contract_gate", 1
    )[1].split("def resolve_and_record_contract_gate")[0]

    prompt = f"""You are the cross-provider session verifier for Set 068 Session 5,
ROUND 2. You are a different provider than the orchestrator (Claude Opus 4.8).

In Round 1 you returned ISSUES_FOUND with ONE Major (no Criticals):

> A structurally corrupt but JSON-parseable activity-log.json can silently disarm
> a `required` contract gate and can make the policy readers raise (e.g. top-level
> `[]`, or `{{"entries": "bad"}}`): read_contract_gate / has_contract_gate_record
> call `.get()`/iterate assuming object/list shape; contract_gate_record_unreadable
> only treated JSON/IO failure as corrupt, so malformed-but-parseable shapes were
> not warned about and could close the set with no gate enforcement and no warning.
> Fix: shape-check after json.load; read_contract_gate -> default (no raise);
> has_contract_gate_record -> False (no raise); contract_gate_record_unreadable ->
> True for malformed-but-parseable structure; record_contract_gate -> controlled
> error instead of AttributeError.

THE FIX (implemented). A shared shape-guard `_read_activity_entries` now backs all
three readers; `record_contract_gate` shape-checks before mutating. Updated code:

--- ai_router/contract_gate.py (helper + the three readers) ---
def _read_activity_entries{helper_to_unreadable}

--- ai_router/contract_gate.py (record_contract_gate) ---
{record_fn}

New tests added (all pass): a parametrized case proving `[]`, `{{"entries":"bad"}}`,
`"a string"`, `42` are each (a) read as `none` without raising, (b) reported
False by has_contract_gate_record without raising, (c) flagged True by
contract_gate_record_unreadable; that `{{}}` is a legitimate `none` (NOT flagged);
that non-dict entries in a valid list are skipped (a real record after junk still
reads); and that record_contract_gate raises a controlled ValueError (not
AttributeError) on a malformed log. Full Python suite stays green (now 1639 pass /
1 skip; this session added 91 tests).

The close_session contract-gate block (unchanged from R1) reads the policy, checks
contract_gate_record_unreadable() at the set-terminal close and prints a loud,
non-blocking WARNING when True, then validates the gate; any exception in the
block is swallowed (fail-open). So with the fix, a malformed log now triggers the
loud warning path instead of a swallowed AttributeError.

YOUR TASK: Confirm the Round-1 Major is resolved by this fix, and check whether
the fix introduces any NEW correctness problem (e.g. a shape that still slips
through, a legitimate log now wrongly flagged as corrupt, or an inconsistency
between the three readers). Output exactly `VERIFIED` if there are no remaining
Critical/Major issues, else `ISSUES_FOUND` with labelled issues + concrete fixes.
Do not re-raise the already-fixed R1 issue as still-open if the code above
resolves it; do not invent issues to appear thorough."""

    out_path = SET / "s5-verification-round-2.md"
    r = route(prompt, task_type="session-verification", complexity_hint=70,
              session_set=str(SET), session_number=5)
    out_path.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out_path} ({len(r.content)} chars)")
    print("cost_usd:", round(getattr(r, "cost_usd", 0.0) or 0.0, 6))


if __name__ == "__main__":
    main()

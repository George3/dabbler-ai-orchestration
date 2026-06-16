"""Set 068 S5 cross-provider verification ROUND 3 (route -> gpt-5-4).

R2 returned ISSUES_FOUND with two Majors: (1) UnicodeDecodeError escaped the
guard; (2) non-dict items in `entries` were silently filtered as a clean
no-record. Both fixed. This round provides the R2 findings + the fix and asks for
confirmation + any new problem.
"""
from __future__ import annotations

from pathlib import Path

from ai_router import route

SET = Path("docs/session-sets/068-cadence-study-and-contract-gate")


def _read(p):
    return Path(p).read_text(encoding="utf-8")


def main():
    module = _read("ai_router/contract_gate.py")
    helper = "def _read_activity_entries" + module.split(
        "def _read_activity_entries", 1
    )[1].split("def read_contract_gate")[0]
    record_fn = "def record_contract_gate" + module.split(
        "def record_contract_gate", 1
    )[1].split("def resolve_and_record_contract_gate")[0]
    unreadable_fn = "def contract_gate_record_unreadable" + module.split(
        "def contract_gate_record_unreadable", 1
    )[1].split("def record_contract_gate")[0]

    prompt = f"""You are the cross-provider session verifier for Set 068 Session 5,
ROUND 3. Different provider than the orchestrator (Claude Opus 4.8).

Round 1 found one Major (malformed-but-parseable activity-log silently disarming
a required gate) -> fixed via a shared `_read_activity_entries` shape-guard.
Round 2 found two more Majors against that fix:

> Major 1 - `_read_activity_entries` caught OSError + JSONDecodeError but NOT
> UnicodeDecodeError, so invalid UTF-8 bytes still raised past the never-raises
> contract.
> Major 2 - non-dict items inside `entries` (e.g. {{"entries":["bad"]}}) were
> silently filtered and reported malformed=False, so a decayed durable record
> could vanish with no warning.

THE FIX (implemented):
- `_read_activity_entries` now also catches `UnicodeError` (parent of
  UnicodeDecodeError; it is a ValueError but not a JSONDecodeError), and now
  computes `malformed = len(dict_entries) != len(entries)` so ANY non-dict
  element flags corruption while reads stay tolerant (still scan the dicts).
- `contract_gate_record_unreadable` docstring updated; it delegates to the helper.
- `record_contract_gate` now refuses a log whose `entries` contains a non-dict
  element (controlled ValueError, not AttributeError).

New tests (all pass; this session now 1641 pass / 1 skip, 93 contract-gate tests):
- invalid UTF-8 bytes `{{"entries": [\\xff\\xfe]}}` -> read=none, has_record=False,
  unreadable=True, no raise;
- `{{"entries":["junk",42,<valid record>]}}` -> read still returns the valid
  record (tolerant) AND unreadable=True (flagged);
- record_contract_gate raises ValueError on `[]` and on `{{"entries":["junk"]}}`.

--- ai_router/contract_gate.py (updated helper) ---
{helper}

--- contract_gate_record_unreadable ---
{unreadable_fn}

--- record_contract_gate ---
{record_fn}

YOUR TASK: Confirm the two Round-2 Majors are resolved and check for any NEW
correctness problem the fix introduces (e.g. a legitimate log now wrongly flagged,
an exception type still uncaught, or an inconsistency among the three readers /
the writer). Output exactly `VERIFIED` if no Critical/Major issues remain, else
`ISSUES_FOUND` with labelled issues + concrete fixes. Do not re-raise the
already-fixed issues if the code above resolves them; do not invent issues."""

    out_path = SET / "s5-verification-round-3.md"
    r = route(prompt, task_type="session-verification", complexity_hint=70,
              session_set=str(SET), session_number=5)
    out_path.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out_path} ({len(r.content)} chars)")
    print("cost_usd:", round(getattr(r, "cost_usd", 0.0) or 0.0, 6))


if __name__ == "__main__":
    main()

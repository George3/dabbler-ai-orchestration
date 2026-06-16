"""Set 070 S2 -- cross-provider session verification ROUND 3 (confirm R2 fixes).

R2 (gpt-5-4) found that Fix 2 (malformed-log handling) was incomplete: the READERS
(has_/read_) and the stepNumber int() cast could still TypeError on a non-list
'entries' or a malformed stepNumber (the L-069-1 bug-class). All hardened now. This
round confirms the readers never raise + the writer ignores malformed stepNumbers +
the CLI never escapes a traceback. Routes to gpt-5-4 (tier 3, different provider).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

DIFF = subprocess.run(
    ["git", "diff", "--cached", "--",
     "ai_router/dual_surface_verify.py",
     "ai_router/tests/test_dual_surface_s2.py"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

R2 = (HERE / "s2-verification-round-2.md").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 2 of 3 of Set 070, ROUND 3.
Round 2 found Fix 2 INCOMPLETE (the malformed-activity-log bug-class extended to the
readers + the stepNumber cast). It is now hardened. Confirm the remediation is
complete and no new defect was introduced. Be a devil's advocate, but do NOT
re-litigate the agreed baseline (full ai_router suite GREEN; NO release this
session; net-new additive functions). Return the structured verdict (VERIFIED or
ISSUES FOUND, Issue N / Category / Severity).

=== ROUND 2 FINDINGS (now claimed fixed) ===
{R2}

=== THE R2 FIXES TO CONFIRM (cite file:line) ===

FIX A (R2 Issue 1 - readers must never raise on a non-list 'entries'). Both
read_dual_surface_mode AND has_dual_surface_mode_record now do
`entries = log.get("entries"); if not isinstance(entries, list): return <default>`
BEFORE iterating, so a parseable log with `entries: 1` collapses to off / False
instead of TypeError. record_dual_surface_mode's next-step computation no longer
calls int() on arbitrary data: it filters prior stepNumbers through _is_int_not_bool
and ignores malformed ones (so a `stepNumber: []` prior entry is ignored, not fed to
int()). main()'s record-mode branch adds TypeError to its controlled-exit except as
belt-and-suspenders. Confirm: is there ANY remaining path -- via read-mode,
record-mode, or resolve_and_record_dual_surface_mode -- where a parseable-but-
malformed activity log (`{{"entries": 1}}`, or a list entry with a non-int
stepNumber, or `entries` a string) escapes as an uncaught traceback? Is the
"repair non-list entries and record" behavior (exit 0) a defensible resolution
versus refusing (it never crashes and the durable record still lands)?

FIX B (R2 Issue 2 - tests pin the above). New tests:
test_readers_never_raise_on_non_list_entries (entries=1 -> off/False),
test_record_ignores_malformed_stepnumber (stepNumber=[] -> records at step 1),
test_record_mode_non_list_entries_does_not_crash (CLI, entries=1 -> exit 0, ASCII),
test_record_mode_bad_stepnumber_does_not_crash (CLI -> exit 0). Confirm these
actually exercise the previously-broken paths (the CLI record-mode path that goes
through has_dual_surface_mode_record), not just the writer in isolation.

NOTE (scoped + recorded, NOT a gap to re-flag): the SAME non-list-'entries'
iteration pattern exists in the PRE-EXISTING sibling readers
ai_router/path_aware_critique.py (~line 145, 209) and
ai_router/dedicated_verification.py (~line 178, 243). Those are out of S2's scope
(S2 owns dual_surface_verify.py); per lesson L-069-1 the residual is explicitly
RECORDED in the disposition as a deferred follow-up, not silently left. Do not
count it as an S2 defect.

=== STAGED DIFF (dual_surface_verify.py + test_dual_surface_s2.py, post-R2-fix) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=78,
        max_tier=3,
        session_set=str(HERE),
        session_number=2,
    )
    out = HERE / "s2-verification-round-3.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

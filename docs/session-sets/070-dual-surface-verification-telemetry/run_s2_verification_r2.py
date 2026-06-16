"""Set 070 S2 -- cross-provider session verification ROUND 2 (re-verify the fixes).

R1 (gpt-5-4, ISSUES FOUND) found 3 real issues; all are fixed. This round confirms
the three remediations and that no new defect was introduced. It re-routes to
gpt-5-4 (tier 3, the R1 verifier AND a different provider than the Anthropic
orchestrator) -- pinning max_tier=2 would have dropped to a same-provider tier-2
model, defeating cross-provider verification, so we keep tier 3.
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

R1 = (HERE / "s2-verification.md").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 2 of 3 of Set 070, ROUND 2.
Round 1 returned ISSUES FOUND with three findings (below). All three are now fixed.
Confirm each remediation is correct and complete, and that NO new defect was
introduced. Be a devil's advocate, but this is a re-verify: do NOT re-litigate the
agreed by-design scope/baseline from R1 (suite GREEN 2054->now 2059 passed, 5
skipped; NO release this session; net-new additive functions). Return the
structured verdict (VERIFIED or ISSUES FOUND, Issue N / Category / Severity).

=== ROUND 1 FINDINGS (now claimed fixed) ===
{R1}

=== THE FIXES TO CONFIRM (cite file:line) ===

FIX 1 (R1 Issue 1, High - provenanceComplete honesty). In
validate_comparison_artifact: a NEW unconditional check now rejects an artifact
where provenanceComplete is True AND (pushUnkeyed != 0 OR pullUnkeyed != 0), using
_is_int_not_bool so a bool count cannot sneak through - independent of whether an
unkeyed finding is present in the array. Additionally score_comparison now derives
provenance_complete (hence upper_bound) from BOTH the boolean flag AND
counts_clean (pushUnkeyed==0 and pullUnkeyed==0, int-not-bool), as defense in
depth. Confirm: can a malformed artifact still validate as complete while
declaring unmergeable findings, or can score_comparison still clear the upper-bound
warning on incomplete provenance? New tests:
test_provenance_complete_true_with_nonzero_unkeyed_count_rejected.

FIX 2 (R1 Issue 2, Medium - record-mode crash on malformed log). record_dual_
surface_mode now wraps json.load in try/except (json.JSONDecodeError, UnicodeError)
-> controlled ValueError, rejects a non-dict log with a controlled ValueError, and
resets a wrong-typed 'entries' to a real list. main()'s record-mode branch now
pre-checks dual_surface_mode_record_unreadable -> returns 2, and broadens its
except to (ValueError, OSError, JSONDecodeError, UnicodeError) -> returns 2 with
ASCII-only output. Confirm there is no remaining path where a malformed/ non-object/
invalid-UTF-8 activity log escapes as an uncaught traceback from record-mode. New
tests: test_record_mode_unreadable_log_returns_2,
test_record_non_object_log_raises_controlled_valueerror,
test_record_unparseable_log_raises_controlled_valueerror,
test_record_repairs_non_list_entries.

FIX 3 (R1 Issue 3, Medium - test adequacy). test_ordering_both_then_keyed_single_
then_unkeyed now asserts the actual defect_key sequence ['s','p',''] + the trailing
unkeyed contributor description, so a keyed/unkeyed swap is caught. The bogus
test_record_bad_mode_returns_2 (which passed a VALID 'off') is replaced by
test_record_mode_off_happy_path + test_record_mode_unreadable_log_returns_2 (a real
nonzero path). Confirm the new/changed tests actually exercise the behaviors named
and that the (provenanceComplete=true, nonzero unkeyed) rejection + malformed-log
record-mode handling are now pinned.

=== STAGED DIFF (dual_surface_verify.py + test_dual_surface_s2.py, post-fix) ===
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
    out = HERE / "s2-verification-round-2.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

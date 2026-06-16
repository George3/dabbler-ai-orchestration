"""Set 069 S6 -- cross-provider session re-verification ROUND 2 (Step 6).

R1 (s6-verification.md) returned ISSUES_FOUND with TWO Minor doc-accuracy issues:
  (1) the S5 ratchet prose said "six" mechanical gates while naming only five;
  (2) two summaries used a stale "0.21.x/0.22.x" baseline.
Both are wording-only. The fix:
  (1) "six" -> "five" everywhere the mechanical-gate count appears -- INCLUDING the
      floor_ratchet.py docstrings (line 159, 275) and test comments, which the code
      itself had miscounted (it appends exactly five: fails-on-old, passes-on-fixed,
      drives-public-contract, flake-check, has-owner); admission = five gates AND
      human sign-off. floor_ratchet tests still green (56 passed).
  (2) "0.21.x/0.22.x loop" -> "Set 067/068 loop" in CHANGELOG + change-log.md, to
      match the wording already used in pull-verifier.md + the strategy doc.
This is a wording-only re-verify; confirm both issues are resolved and no new
inconsistency was introduced. Verifier is gpt-5-4 (already top tier -- no
escalation risk, L-064-7).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

DOC_FILES = [
    "ai_router/CHANGELOG.md",
    "ai_router/docs/pull-verifier.md",
    "ai_router/floor_ratchet.py",
    "ai_router/tests/test_floor_ratchet.py",
    "docs/verification-surface-strategy.md",
    "docs/session-sets/069-automated-pull-critique-capabilities/change-log.md",
]
DIFF = subprocess.run(
    ["git", "diff", "HEAD", "--", *DOC_FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider session verifier for Session 6 of 6 of Set 069,
ROUND 2 (wording-only re-verify). Return the structured verdict.

In Round 1 you returned ISSUES_FOUND with exactly TWO Minor issues. Both have now
been fixed. Confirm each is resolved and that the fix introduced no NEW
inconsistency. Do NOT re-open the agreed baseline or invent new issues; this is a
narrow re-verify of two wording fixes.

ISSUE 1 (resolved?): the S5 ratchet prose said "six mechanical gates" but named
only five. GROUND TRUTH: `_eval_mechanical_gates` in floor_ratchet.py appends
exactly FIVE gates -- fails-on-old, passes-on-fixed, drives-public-contract,
flake-check, has-owner -- and admission requires those FIVE to pass AND
humanSignoff.status == "approved". The fix changed "six" -> "five" in EVERY echo:
the two floor_ratchet.py docstrings (the code had miscounted itself), the test
comments, the CHANGELOG 0.23.0 entry, pull-verifier.md, the strategy doc, and the
change-log.md. Confirm: (a) no remaining text claims "six" mechanical gates; (b)
"five" is the correct count given the ground truth; (c) the "AND human sign-off"
qualifier is still present so the distinction (five mechanical gates + sign-off) is
clear.

ISSUE 2 (resolved?): two summaries used "0.21.x/0.22.x loop". The fix changed them
to "Set 067/068 loop" in the CHANGELOG and the change-log.md, matching the wording
already in pull-verifier.md and the strategy doc. Confirm the baseline wording is
now consistent across all the docs and no stale "0.21.x/0.22.x" baseline remains.

Also confirm the fix did not break internal consistency anywhere else (the count
is now uniformly five; the baseline wording is now uniformly "Set 067/068").

Return: verdict (VERIFIED or ISSUES_FOUND), a one-line summary, and any residual
issue with file + quoted text + correction. If both issues are resolved and clean,
return VERIFIED.

=== DIFF SINCE ROUND 1 (the two wording fixes across all echoes) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=30,
        max_tier=3,
        session_set=str(HERE),
        session_number=6,
    )
    out = HERE / "s6-verification-round-2.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()

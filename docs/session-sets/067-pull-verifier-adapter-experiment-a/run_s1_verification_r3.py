"""Set 067 S1 cross-provider verification - ROUND 3 (final).

Round 2 confirmed the 4 R1 Critical/Major findings resolved but surfaced one
NEW Major (grep no longer filtered to regular files -> a broken in-tree symlink
could abort the grep) and the lingering Minor (verdict tool-schema vs parser
summary inconsistency). Both fixed. This round confirms only those two are
resolved and no further regression was introduced. Same verifier (gpt-5.4).
Persists raw output BEFORE printing (L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

module = (REPO / "ai_router" / "pull_verifier.py").read_text(encoding="utf-8")
tests = (REPO / "ai_router" / "tests" / "test_pull_verifier.py").read_text(
    encoding="utf-8"
)
r2 = (HERE / "s1-verification-round-2.md").read_text(encoding="utf-8")

FIXES = """\
ROUND-2 FINDINGS AND THE FIXES APPLIED (confirm each is resolved; scan for any
further regression):

[Major, NEW in R2] _walk_files appended every os.walk filename after
_within_sandbox without a regular-file check, so a broken in-tree symlink (or a
non-regular entry) could make _canonical_grep's f.read_text() abort the whole
grep -> FIXED. _walk_files now requires `f.is_file() and _within_sandbox(...)`
(is_file() is False for a broken symlink and for fifo/socket entries), and
_canonical_grep wraps the per-file read in try/except OSError so a file that
turns unreadable between walk and read is skipped, not fatal. Test:
test_broken_symlink_does_not_abort_grep (asserts grep still returns real matches,
not ERROR).

[Minor] _verdict_tool_schema required ['verdict','summary'] but _parse_verdict
coerced a missing summary to '' -> FIXED by aligning the schema: required is now
['verdict'] only, and _parse_verdict enforces the Set 066 content rule (non-empty
summary OR >=1 finding). Schema and parser now agree: verdict is structurally
required; content non-triviality is the parser's job. Test:
test_verdict_schema_required_aligns_with_parser.

Everything else (the R1 Critical grep breakout, the servant-guard error hole, the
byte-cap elision, the config=None pricing, the accepted post-hoc overshoot) was
already confirmed RESOLVED in round 2 and is unchanged.
"""

SYSTEM_PROMPT = (
    "You are the same cross-provider verifier (gpt-5.4) doing a FINAL re-review "
    "of Set 067 Session 1. The R1 Critical + Majors were already confirmed "
    "resolved in R2; focus on the two R2 findings (the regular-file grep filter "
    "and the verdict schema/parser alignment) and on whether the latest changes "
    "introduced any NEW defect. Be concrete and cite code. End with a JSON "
    'verdict block: {"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[...]} . '
    "Return VERIFIED only if both R2 findings are resolved and you find no new "
    "Critical/Major defect."
)

USER = f"""Set 067 S1 ships ONLY the Anthropic binding (S2 adds OpenAI/Gemini),
no release (S4), read-only tools (run_test=Set 068), FakeBinding unit tests, and
the full pytest suite is GREEN (1458 prior + 54 pull_verifier tests). Review as
production code.

{FIXES}

=== ROUND-2 VERIFICATION (for reference) ===
{r2}

=== UPDATED ai_router/pull_verifier.py ===
{module}

=== UPDATED ai_router/tests/test_pull_verifier.py ===
{tests}

Confirm the two R2 findings are resolved and scan for new defects. Return your
dispositions, any new findings, then the JSON verdict block."""


def main():
    cfg = yaml.safe_load(
        (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
    )
    pcfg = cfg["providers"]["openai"]
    model = next(
        m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4"
    )
    result = providers.call_model(
        provider_name="openai",
        model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT,
        user_message=USER,
        max_tokens=24000,
        config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s1-verification-round-3.md"
    out.write_text(
        "# Set 067 S1 -- Cross-provider verification (gpt-5.4) ROUND 3 (final)\n\n"
        "> Independent verifier: gpt-5.4 (openai). Final re-review.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(
        json.dumps(
            {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": round(in_cost + out_cost, 6),
                "stop_reason": result.stop_reason,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

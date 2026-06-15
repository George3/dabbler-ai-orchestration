"""Set 067 S2 - 3-provider headless capability check (metered live test).

Spec Session 2, Step 4: confirm each of the three pull-verifier bindings
(Anthropic tool_use / OpenAI tool_calls / Gemini function_declarations) drives
the read-only tool loop headless against a tiny fixture repo - actually issuing
probe tool calls and returning a schema-valid critique verdict.

This is a SMALL metered live test. It writes every raw PullResult to disk
(L-064-3) before printing, keeps the fixture tiny, and caps per-run cost. A run
with zero probe calls is a FAILED run, not a fast one (tool-contract section 5).

Run:  .venv/Scripts/python.exe docs/session-sets/.../run_s2_headless_check.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# ai_router on path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))

import pull_verifier as pv  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = OUT_DIR / "s2-headless-results.json"

# A tiny fixture repo with one obvious, path-discoverable defect: average()
# subtracts 1 from the mean, contradicting its own docstring and the README.
FIXTURE_FILES = {
    "stats.py": (
        "def average(numbers):\n"
        '    """Return the arithmetic mean of a non-empty list of numbers."""\n'
        "    total = 0\n"
        "    for n in numbers:\n"
        "        total += n\n"
        "    return total / len(numbers) - 1\n"
    ),
    "README.md": (
        "# stats\n\n"
        "`average(numbers)` returns the exact arithmetic mean of its input.\n"
    ),
}

INSTRUCTION = (
    "Review this tiny repository for real defects. Read stats.py and README.md "
    "using the read-only tools, then submit your structured critique verdict. "
    "Pay attention to whether average() matches its documented behavior."
)

# Each binding must issue >=1 probe and return a schema-valid verdict.
PROVIDERS = ["anthropic", "openai", "google"]


def _build_fixture(root: Path) -> None:
    for name, body in FIXTURE_FILES.items():
        (root / name).write_text(body, encoding="utf-8")


def main() -> int:
    results: dict = {}
    overall_ok = True

    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td) / "fixture"
        sandbox.mkdir()
        _build_fixture(sandbox)

        for provider in PROVIDERS:
            try:
                r = pv.pull_route(sandbox, INSTRUCTION, provider=provider)
                rec = r.to_dict()
                rec["_capability_ok"] = bool(
                    r.ok and r.trace.tool_call_count >= 1
                )
                # Did it actually catch the seeded "- 1" / not-the-mean defect?
                blob = json.dumps(rec.get("critique") or {}).lower()
                rec["_caught_seeded_defect"] = any(
                    k in blob for k in ("- 1", "minus", "subtract", "off-by", "mean")
                )
            except Exception as exc:  # record, do not abort the other providers
                rec = {"provider": provider, "error": repr(exc), "_capability_ok": False}
            results[provider] = rec
            overall_ok = overall_ok and rec.get("_capability_ok", False)

    # L-064-3: write raw to disk (utf-8) BEFORE printing.
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # ASCII-only summary.
    print(f"Wrote {RESULTS_PATH.name}")
    for provider in PROVIDERS:
        rec = results[provider]
        if "error" in rec:
            print(f"  [x] {provider}: ERROR {rec['error']}")
            continue
        tr = rec["trace"]
        print(
            f"  [{'x' if rec['_capability_ok'] else ' '}] {provider}: "
            f"model={rec['model']} ok={rec['ok']} "
            f"probes={tr['tool_call_count']} turns={tr['api_turns']} "
            f"stop={tr['stop_reason']} cost=${tr['cost_usd']:.4f} "
            f"caught_defect={rec['_caught_seeded_defect']} "
            f"verdict={(rec.get('critique') or {}).get('verdict')!r}"
        )
    print(f"OVERALL: {'PASS' if overall_ok else 'FAIL'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

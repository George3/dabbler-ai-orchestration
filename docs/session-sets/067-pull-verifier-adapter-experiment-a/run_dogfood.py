"""Set 067 S4 dogfood - produce this set's path-aware-critique.json via the NEW
producer over a focused sandbox of the files under review, using the DEFAULT
roster (GPT-5.4 + Gemini-Pro). After the S4 budget-aware-forced-verdict fix in
pull_route, GPT-5.4 commits a verdict near the budget instead of timing out
empty. The critics read the real S4 bytes; cross-file imports are irrelevant to
a read-only critique.
"""
from __future__ import annotations
import shutil, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import produce_path_aware_critique  # noqa: E402
SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"
REVIEW_FILES = [
    "ai_router/pull_critique.py",
    "ai_router/pull_verifier.py",
    "ai_router/path_aware_critique.py",
    "ai_router/tests/test_pull_critique.py",
    "ai_router/docs/pull-verifier.md",
]
INSTRUCTION = (
    "You are an adversarial path-aware reviewer. Your read-only sandbox contains "
    "the Set 067 Session 4 production code: the new opt-in path-aware-critique "
    "PRODUCER (pull_critique.py), the pull-verifier adapter it drives "
    "(pull_verifier.py), the Set 066 artifact contract + close-out gate it "
    "targets (path_aware_critique.py), the producer's tests, and the adapter "
    "doc. Use the read-only tools to OPEN AND READ the actual files - do not "
    "assume contents. Find real defects in the PRODUCER specifically: can "
    "produce_path_aware_critique ever (a) write an artifact the close-out gate "
    "(validate_path_aware_critique_gate) would reject, or (b) refuse a valid "
    "one? Check the >=2-DISTINCT-provider invariant (keyed off the "
    "adapter-stamped critique.provider), identity stamping of sessionSetName + "
    "the recorded pathAwareCritique level, the gate-identity write guard, "
    "validation-before-write, skip-not-fatal for a failing provider, the "
    "budget-aware forced verdict in pull_route, L-064-3 (utf-8 write) and "
    "ASCII-only output. Also check correctness, contract drift vs "
    "path_aware_critique.py, and whether the tests exercise these paths. Then "
    "submit your verdict (VERIFIED or ISSUES_FOUND) with concrete file-and-"
    "symbol findings. Keep output ASCII-only."
)
tmp = Path(tempfile.mkdtemp(prefix="dogfood-067-"))
try:
    for rel in REVIEW_FILES:
        dest = tmp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest)
    print(f"Focused sandbox: {tmp} ({len(REVIEW_FILES)} files)")
    res = produce_path_aware_critique(SET_DIR, sandbox_dir=tmp, instruction=INSTRUCTION)
    print(f"ok={res.ok} written_to={res.written_to}")
    for s in res.skipped: print(f"  [skipped] {s}")
    for r in res.reasons: print(f"  [reason] {r}")
    for pr in res.results:
        t = pr.trace
        print(f"  {pr.provider}/{pr.model}: ok={pr.ok} probes={t.tool_call_count} "
              f"stop={t.stop_reason} cost=${t.cost_usd:.4f} "
              f"verdict={pr.critique.verdict if pr.critique else None}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

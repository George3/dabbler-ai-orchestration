"""Session 2 verification driver — Set 035 (state-file sole truth).

Round A bundles the artifacts produced by Session 2:

  - docs/session-sets/035-.../scripts/harvest_glossary.py — NEW.
    The one-shot Python harvest tool: walks the solution looking
    for filename-like string literals, clusters by Levenshtein
    distance, surfaces clusters whose membership spans more than
    one distinct case-folded form.
  - docs/session-sets/035-.../glossary-harvest.md — NEW. The
    harvest report + Set 035 Session 2 disposition section
    (clusters touching canonical markers, follow-on candidates,
    writer parity check summary).
  - tools/dabbler-ai-orchestration/src/test/suite/cancelLifecycle.test.ts —
    UPDATED. New "cancelLifecycle — writer parity (Set 035 Session
    2)" suite (6 cases) pinning byte-level shape of CANCELLED.md
    and session-state.json output: LF newlines (no BOM/CR);
    JSON indent=2 + trailing newline; status+preCancelStatus the
    only deltas on cancel; round-trip preserves prior status for
    not-started / in-progress / complete; timestamp matches Python
    isoformat() shape exactly; re-cancel after restore preserves
    the original preCancelStatus.

Ground truth bundled alongside:

  - Set 035 spec.md Session 2 — the contract this session closes.
  - cancelLifecycle.ts + session_lifecycle.py — the two writers
    the disposition claims are byte-equivalent.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent
EXT_ROOT = REPO_ROOT / "tools" / "dabbler-ai-orchestration"


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def read_section(
    path: Path, start_marker: str, end_marker: str | None = None
) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        return f"=== FILE: {rel} (SECTION MISSING: {start_marker!r}) ==="
    if end_marker is None:
        section = text[start:]
    else:
        end = text.find(end_marker, start + len(start_marker))
        section = text[start:end] if end > 0 else text[start:]
    return f"=== FILE: {rel} (from {start_marker!r}) ===\n{section}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 035 extends the H2 single-source-of-truth verdict from Set 033
Session 2 to the cancellation lifecycle. Session 1 (closed
2026-05-21) migrated the TypeScript reader at fileSystem.ts:276 to
consult session-state.json's status field first, with the legacy
isCancelled() file-presence check surviving as the "unknown"
fallback.

Session 2 (THIS verification) is the writer-alignment + glossary-
harvest session. Two deliverables:

1. **Writer parity check** — confirm cancelLifecycle.ts (TS) and
   session_lifecycle.py (Python) produce byte-equivalent on-disk
   output. The two writers must agree byte-for-byte so a set
   cancelled on one platform reads identically on another. The
   parity summary (10-row table) is documented in the disposition
   section of glossary-harvest.md.

2. **Glossary harvest** — author a one-shot tool that walks the
   solution looking for filename-like string literals
   ([A-Za-z_][A-Za-z0-9_.\\-]+\\.(md|json|jsonl|toml|yaml|yml|txt|html)),
   groups by extension, clusters by Levenshtein distance <= 3
   within each extension bucket. The tool surfaced 40 clusters;
   the disposition section in glossary-harvest.md triages all 40
   into three categories per the spec: (a) acceptable variance,
   (b) real inconsistency / fix in-session, (c) follow-on
   candidate. Triage outcome: zero in-session fixes, one follow-
   on candidate (C1 — Python CLI print_session_set_status reader).

The trigger case (_cancelled.md vs CANCELLED.md) is rendered moot
by Session 1's reader migration; all _cancelled.md occurrences in
the codebase are self-references in this set's own spec / harvest
script docstring, or historical artifacts in closed-session
activity-log.json files. Documented in glossary-harvest.md's
"Resolution: _cancelled.md mismatch" section.

Session 2 added 6 new writer-parity unit tests to the existing
cancelLifecycle.test.ts suite. Full test count: 462 passing (was
456 after Session 1). The two pre-existing unrelated failures
(configEditor ViewColumn.One stub gap; notificationsSection
"wired in Set 026 Session 7" assertion) are unchanged.
ai_router/tests/test_session_lifecycle.py: 17 passed.

Typecheck (npx tsc --noEmit) clean.

Session 3 is doc alignment + Layer-3 Playwright. Session 4 is
final test sweep + dual-registry release.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 2 implementation faithfulness for writer parity
verification + glossary harvest.

You are Gemini Pro, asked to verify that Session 2 of Set 035
ships a defensible writer-parity claim, a sound glossary-harvest
tool + report + disposition, and adequate writer-side unit
tests.

Verify:

A. **Writer parity claim is sound.**

   1. The 10-row parity table in glossary-harvest.md's "Writer
      parity check summary (Session 2 step 1)" section is
      accurate. Compare the cited TS implementation (in
      cancelLifecycle.ts) against the cited Python implementation
      (in session_lifecycle.py) for each row:
      - Filename constants match (CANCELLED.md, RESTORED.md,
        session-state.json).
      - History header matches (`# Cancellation history`).
      - Timestamp format produces byte-equivalent shape: TS
        hand-rolls `${yyyy}-${mm}-${dd}T${HH}:${MM}:${SS}${sign}${offH}:${offM}`;
        Python uses `datetime.now().astimezone().replace(microsecond=0).isoformat()`.
        Both produce e.g. `2026-05-14T11:23:07-04:00` (local
        time, second precision, ±HH:MM offset).
      - Newlines: TS string literals use `\\n`; Python writes
        `content.encode("utf-8")` via `open(..., "wb")`. Neither
        translates to CRLF on Windows.
      - Atomic write: TS uses unique-suffix temp + `fs.renameSync`;
        Python uses `tempfile.mkstemp` + `os.replace`. Both
        same-filesystem rename, both PID-uniquified.
      - Prepend semantics: both produce
        `<verb> on <iso>\\n<reason>\\n\\n` self-terminating, with
        the `# Cancellation history\\n\\n` header on first write.
      - State-file flip: both set `status = "cancelled"` and
        `preCancelStatus = <prior>`; re-cancel preserves the
        original `preCancelStatus`.
      - Restore inference fallback: change-log.md → "complete";
        activity-log.json → "in-progress"; else "not-started".
        Matches Set 7 backfill rules; both sides identical.
      - JSON serialization: TS `JSON.stringify(state, null, 2) + "\\n"`;
        Python `json.dumps(state, indent=2) + "\\n"`. Same
        indent + trailing newline.
   2. No drift in either writer; the disposition's claim of "byte-
      equivalent on-disk shape" is faithful to the code.

B. **Glossary harvest script is correct.**

   1. The Levenshtein implementation in `harvest_glossary.py` is
      sound (standard two-row DP, returns 0 for equal strings).
   2. The clustering algorithm (union-find with O(n^2) comparisons)
      groups names where `levenshtein(a.lower(), b.lower()) <= threshold`.
   3. Excluded trees match what the spec calls for (node_modules,
      .venv, out, dist, .git, plus build, __pycache__, *.egg-info).
   4. The filename regex captures the spec's targets
      ([A-Z][A-Za-z_-]*\\.(md|json|toml|jsonl)) plus generous
      additional extensions (yaml/yml/txt/html). The leading-
      char class allows lowercase / underscore starts so the
      `_cancelled.md` trigger case is captured.
   5. Output Markdown structure is operator-readable: one
      `## .<ext> extension` heading per bucket; one `### Cluster:`
      heading per cluster; file list per member; canonical-marker
      badge applied where applicable.

C. **Disposition triage is defensible.**

   1. **Session-State.json / Session-state.json / session-state.json**
      cluster correctly marked (a) acceptable variance. The two
      non-canonical variants in lessons-learned.md (Title Case
      heading) and project-guidance.md (sentence-case prose at
      sentence start) are stylistic conventions, not typos.
   2. **CANCELLED.md / _cancelled.md / cancelled.md** cluster
      correctly marked (a) acceptable variance. All non-canonical
      occurrences are self-references (this set's own spec /
      harvest script docstring) or historical artifacts in closed
      Set 033's activity-log.json. The trigger case is moot post-
      Session-1 because the bucketing reader is state-file-first.
   3. **CHANGELOG.md / change-log.md** correctly marked (a)
      acceptable variance — two distinct canonical artifacts
      (PyPI/Marketplace release log vs per-session-set
      aggregation), Levenshtein-3 neighbors but semantically
      distinct.
   4. The "Other clusters" categorization (numbered-session
      families, distinct proposals/audits, test fixtures,
      sentence-case prose, historical incident references) is
      defensible. Each named cluster falls into the listed
      category with a sound rationale.
   5. **C1 follow-on candidate** is well-scoped: Python CLI
      print_session_set_status at __init__.py:935 still calls
      is_cancelled(path) file-presence-first, mirroring the TS
      pattern Session 1 migrated. The recommendation (add
      read_cancellation_state to session_lifecycle.py, refactor
      one CLI caller, add four parity tests, bump
      dabbler-ai-router patch version) is appropriately scoped
      as a follow-on, not a Session-2 inline fix.

D. **Writer-side unit tests pin the right invariants.**

   1. "CANCELLED.md uses LF newlines only" — scans every byte for
      0x0D (CR) and asserts none; also asserts no UTF-8 BOM
      (0xEF prefix). Catches a regression where Windows text-
      mode writes leak in.
   2. "session-state.json serialization matches Python
      json.dumps(state, indent=2) + '\\n'" — asserts trailing
      newline, no tabs, and 6-space indent for
      sessions[0] keys (confirming 2-space-per-level indent).
   3. "cancel writes only status + preCancelStatus, leaving
      sibling keys untouched" — uses a realistic baseline state
      object with 12 keys including nested orchestrator + sessions[];
      asserts deep equality on all 11 non-mutated keys post-cancel.
   4. "round-trip: cancel + restore returns status to the exact
      prior value" — parametric over the three canonical
      non-cancelled status values (not-started, in-progress,
      complete); asserts status restored AND preCancelStatus
      cleared.
   5. "cancel timestamp is local-time ISO-8601 with second
      precision and ±HH:MM offset (Python-mirror shape)" — regex
      `Cancelled on (\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2})\\n`;
      also negative-asserts no millisecond fractions and no
      `T<HH>:<MM>:<SS>Z` UTC suffix.
   6. "re-cancel after restore preserves the original
      preCancelStatus across the cycle" — three-write sequence
      C1 → R1 → C2; asserts post-C2 preCancelStatus is still
      "in-progress" (the original status, captured on C1 and
      re-captured on C2 from the post-R1 state).

E. **What's risky or missing.** Any edge case that would bite a
   real run?

   - The TS timestamp formatter uses `d.getTimezoneOffset()` which
     returns minutes-west-of-UTC (positive for west, negative for
     east) — the sign is then inverted (`offsetMin = -d.getTimezoneOffset()`)
     to match the ISO-8601 convention (positive for east, negative
     for west). Confirm the inversion is correct: e.g., for
     America/New_York (UTC-5 standard, UTC-4 DST), `getTimezoneOffset()`
     returns +300 / +240, so `offsetMin` becomes -300 / -240, and
     the sign-formatting yields `-05:00` / `-04:00`. That matches
     Python's `isoformat()` for the same locale.
   - The Python `tempfile.mkstemp` produces a temp filename with
     a longer random suffix than TS's `Math.random().toString(36).slice(2,8)`.
     Both are PID-uniquified plus random. Verify the longer
     Python suffix isn't problematic on filesystems with NAME_MAX
     constraints (Windows MAX_PATH; ext4 NAME_MAX=255). For the
     typical state-set folder names (~70 chars), both should fit
     comfortably.
   - The harvest script's regex anchors with `\\b` on both sides.
     The trailing `\\b` after `.md` would not match if the name is
     followed by a `.` (sub-extension) — by design, the regex
     intentionally only captures terminal-extension filenames, not
     `foo.md.bak` style. Confirm that's intended; an alternate
     reading is that we'd want to surface `foo.md.bak` as a "near-
     match of foo.md". The current design is the right call for
     this harvest (catches typos in the canonical-marker space)
     but worth noting.
   - The "two pre-existing unrelated failures" are unchanged.
     Confirm neither would mask a real Session-2-related
     regression — they don't touch cancelLifecycle.ts or
     session_lifecycle.py code paths (configEditor and
     notificationsSection are independent files).
   - The disposition's claim "zero in-session fixes" is the right
     call given the harvest's findings, but it relies on the
     judgment that sentence-case prose at heading/bullet boundaries
     is acceptable variance. A stricter posture would normalize
     every canonical-filename reference to its canonical casing
     regardless of position. The current call is defensible
     because the alternative requires rewriting stable historical
     docs and yields no functional benefit; flag if you disagree.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits.
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverable A — full cancelLifecycle.ts writer (TS).
        read_section(
            EXT_ROOT / "src" / "utils" / "cancelLifecycle.ts",
            "// Filenames for the cancel/restore audit-trail markdown files.",
            "/**\n * Discrete return values for :func:`readCancellationState`.",
        ),
        # Primary deliverable A — TS writer body (cancelSessionSet + restoreSessionSet).
        read_section(
            EXT_ROOT / "src" / "utils" / "cancelLifecycle.ts",
            "/**\n * Cancel *sessionSetDir*: rename ``RESTORED.md``",
        ),
        # Primary deliverable A — full Python writer mirror.
        read_file(
            REPO_ROOT / "ai_router" / "session_lifecycle.py",
        ),
        # Primary deliverable B — harvest script source.
        read_file(
            SET_DIR / "scripts" / "harvest_glossary.py",
        ),
        # Primary deliverable B — glossary-harvest.md disposition section.
        read_section(
            SET_DIR / "glossary-harvest.md",
            "## Triage and disposition (Set 035 Session 2",
        ),
        # Primary deliverable D — new writer-parity test suite.
        read_section(
            EXT_ROOT / "src" / "test" / "suite" / "cancelLifecycle.test.ts",
            'suite("cancelLifecycle — writer parity (Set 035 Session 2)"',
        ),
        # Ground truth — Session 2 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 2 of 4: Writer alignment + glossary harvest",
            "---\n\n## Session 3 of 4:",
        ),
    ]
    return "\n\n".join(parts)


def run_round(label: str, code_block: str, focus_prompt: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{label}] sending verification call to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=focus_prompt,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE ---\n{code_block}",
        session_set="035-state-file-sole-truth-marker-retirement",
        session_number=2,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, "
        f"out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


def main() -> None:
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session2.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-2-result.json",
        )
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated code.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round(
            "Round B",
            bundle,
            focus,
            out_dir / "round-b-session-2-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

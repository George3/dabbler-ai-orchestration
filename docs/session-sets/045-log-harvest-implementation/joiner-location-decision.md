# Joiner Location Decision — Set 045 / Session 1

> **Status:** LOCKED 2026-05-24.
> **Decision:** The joiner lives in **Python**, as a sibling to
> `ai_router/` (working path: **`ai_router/joiner/`**, importable as
> `ai_router.joiner` from existing Python tooling).
> **Pass A consensus (Set 044, gpt-5-4 + gemini-pro + opus-4-6):**
> 2-1 favored Python; Pass B did not relitigate.
> **This session's prototype benchmark:** confirms Pass A and adds
> two new pieces of evidence the consensus did not have access to:
> a 70× scan-time advantage for Python on real on-disk logs, and a
> direct LOC-comparable parity in the detector itself.

---

## 1. What the prototypes proved

Both [`spike-prototypes/joiner_python_sketch.py`](spike-prototypes/joiner_python_sketch.py)
and [`spike-prototypes/joiner_typescript_sketch.ts`](spike-prototypes/joiner_typescript_sketch.ts)
implement the same minimum-viable conflict detector
(*orchestrator-engine mismatch*: state file claims engine X is
checked out; native log shows engine Y active in the same workspace
within the conflict window). Both:

- Scan ~461 native session logs from `~/.claude/projects/` and
  `~/.copilot/session-state/`.
- Read the patched state file claiming a deliberate Copilot checkout
  on the Set 045 directory.
- Correctly detect the synthetic mismatch (the active Claude session
  `ef28a7ff…` in the same workspace) as a single conflict.
- Correctly produce 0 conflicts on the unpatched control state.

The detectors are correctness-equivalent on this scenario. The
differentiator is everything *around* the detector.

## 2. The benchmark surprise

Same algorithm, same input data, same conflict scenario:

| Stage | Python | TypeScript | Ratio |
|---|---|---|---|
| Scan 461 native sessions | **36 ms** | **2,589 ms** | TS is ~70× slower |
| Detect (synthetic mismatch) | 0.3 ms | 0.3 ms | parity |
| Detect (control, no match) | 0.1 ms | 0.1 ms | parity |

The TypeScript port uses `fs.readFileSync(path, "utf-8")` followed
by `.split(/\r?\n/)` on the whole file. For the large JSONLs in
`~/.claude/projects/` (some are 1.5 MB), that reads the entire file
before iterating. Python's `for line in open(path)` short-circuits
on the first `break`, reading only what's needed.

The TypeScript version is *fixable* — switch to `readline.createInterface`
on a stream, or use `fs.read` with a small buffer to read just the
first N records. But the fact that the *idiomatic* TypeScript port
is 70× slower than the *idiomatic* Python port is itself a signal:
this is fundamentally an I/O-bound file-walking workload, and
Python's stdlib happens to have nicer ergonomics for it.

**Production parity is achievable in TypeScript with more code.** That
is itself part of the decision rubric below: when one language
requires more care to hit the same correctness/perf bar, that's
language-specific friction worth accounting for.

## 3. Decision rubric

Weighting each criterion by how much it actually matters for the
joiner's day-to-day:

| Criterion | Python | TypeScript | Winner |
|-----------|--------|------------|--------|
| **Reuse of existing infra** — `ai_router/session_state.py`, `progress.py`, `gate_checks.py` etc. already implement state-file reads, status canonicalization, lifecycle event reads. Joiner imports and reuses directly. | strong reuse | partial parity via extension's `progress.ts` + `fileSystem.ts`, but adds a second copy of state-reading code | **Python** (strong) |
| **Headless testability** — joiner needs Layer-1 unit tests + Layer-1 e2e tests against synthetic state + log fixtures | pytest is trivial; existing `ai_router/tests/` infra | Layer-2 `@vscode/test-electron` is broken on Win11+VS Code 1.120 per CLAUDE.md; vscode-stub Layer-1 harness works but is more friction than pytest | **Python** (strong) |
| **Cross-tier reusability** (Full + Lightweight) — Lightweight tier doesn't ship the extension; a Python joiner can expose a CLI command (`python -m ai_router.joiner --conflicts`) for Lightweight operators | works on both tiers via PyPI | extension-only; Lightweight tier cannot consume | **Python** (strong) |
| **Perf on real workload** | 36 ms scan | 2,589 ms scan (idiomatic); fixable but adds code | **Python** (moderate; TS fixable) |
| **Debuggability** | pytest + standard Python debugger | extension-host debugger; more setup | **Python** (moderate) |
| **IPC to Explorer webview** | subprocess invocation + JSON stdout, or a watch-file pattern; ~50–100 ms per refresh | in-process; zero IPC | **TypeScript** (moderate) |
| **File-watching for live updates** | `watchdog` library, or polling at 1 s cadence (acceptable for Explorer latency budget) | `vscode.FileSystemWatcher`, already used in extension | **TypeScript** (moderate) |
| **LOC of detector itself** | 235 lines (correlation prototype + joiner sketch) | 210 lines (joiner sketch alone) | wash |
| **Consistency with existing engineering center of gravity** | engineering center of gravity for state-file + lifecycle + gate logic is `ai_router/` | engineering center of gravity for UI/Explorer is the extension | **Python** (joiner is state+lifecycle, not UI) |

Net: Python wins on the criteria that have the most leverage on
day-to-day maintenance — reuse, testability, cross-tier, perf,
debuggability. TypeScript wins only on IPC-to-Explorer and
file-watching, both of which are *bounded* costs Python can absorb
at the 1-second-latency budget the Explorer actually needs.

## 4. The IPC question, addressed

> *"In-process is always cheaper than subprocess. Why pay 50–100 ms
> per Explorer refresh for free?"*

Because the Explorer's actual latency budget is bounded by
*operator perception of "live"-ness*, not by sub-millisecond CPU
metrics. The Set 033 check-out mechanism already operates on
1-second-cadence file watching for `session-state.json` writes; the
operator does not perceive any lag between a `start_session` call
and the Explorer's accordion updating to the new state. The joiner
adds at most one more file-watch surface (the launch log + native
log directories) and one more subprocess invocation per refresh.

The integration pattern: the extension's existing `SessionSetsProvider`
polls `session-state.json` and re-renders. When it does, it shells
out to `python -m ai_router.joiner --conflicts --set-slug <slug>` and
reads the JSON-encoded conflict list from stdout. Total added
latency per refresh: ≤100 ms in the worst case. Well within the
Explorer's perceived-live budget.

If the latency budget tightens in a future iteration (e.g., the
Explorer adopts a sub-second refresh cadence), the joiner can
optionally run as a long-lived sidecar daemon that the extension
talks to via a named pipe or a watched-file pattern, dropping
per-refresh overhead to ≤10 ms. That migration is deferred —
unnecessary for the current Explorer cadence.

## 5. Architecture commitment

The Set 045 implementation sessions (S2–S5) consume this lock as a
fixed input:

- **S2 (joiner design + canonical schema):** the joiner's
  conflict-detection semantics and canonical Harvest Record schema
  are authored in Python. The schema is defined in
  `ai_router/joiner/schema.py` (or similar) and consumed by both
  the wrapper writer (S3) and the native-log parsers (S3, S4).
- **S3 (wrapper + Copilot parser):** `dabbler-launch` writes
  records to the canonical schema; the Copilot OTel JSONL parser
  also emits canonical records.
- **S4 (Claude parser + narration v1.1 template):** Claude parser
  reads `~/.claude/projects/*.jsonl` and emits canonical records.
- **S5 (Explorer integration + Layer-3 coverage):** the extension's
  `SessionSetsProvider` shells out to the Python joiner CLI on each
  refresh and renders the conflict + bypass-write signals as
  per-row badges + warnings. Layer-3 Playwright tests validate the
  rendered surface.

Working module name: **`ai_router.joiner`**. The exact internal
structure (single module vs `ai_router/joiner/__init__.py` package)
is a S2 design decision. The location parent is locked here.

## 6. What would flip this decision

For future sets considering reorganization, the lock would be worth
revisiting only if:

- **The Lightweight tier is permanently retired.** Then the
  cross-tier reusability argument collapses, and TypeScript becomes
  more attractive.
- **The Explorer cadence drops below 100 ms.** Then the IPC cost
  becomes meaningful enough to favor in-process.
- **`ai_router` itself migrates to TypeScript / Node** (entire-stack
  unification). Then the reuse argument collapses.

None of these are on the visible roadmap as of 2026-05-24. The lock
is firm for the foreseeable future.

## 7. Companion artifacts

- [`spike-prototypes/joiner_python_sketch.py`](spike-prototypes/joiner_python_sketch.py)
  — the Python prototype.
- [`spike-prototypes/joiner_typescript_sketch.ts`](spike-prototypes/joiner_typescript_sketch.ts)
  — the TypeScript prototype.
- [`spike-prototypes/joiner_python_report.json`](spike-prototypes/joiner_python_report.json)
  — Python run output.
- [`spike-prototypes/joiner_typescript_report.json`](spike-prototypes/joiner_typescript_report.json)
  — TypeScript run output.
- [`spike-prototypes/correlation_prototype.py`](spike-prototypes/correlation_prototype.py)
  — the Q2 prototype the joiner sketches reuse for native-log
  scanning.

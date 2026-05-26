# Route response

- **Provider:** claude-sonnet-4-6
- **Model:** sonnet
- **Cost:** 0.13178

---

## ISSUES_FOUND

---

### Summary

The three-knob precedence model is correctly structured, tri-state parsing is sound, and the TypeScript/Python schemas mirror each other correctly. However there are six concrete defects ranging from a safety-critical silent-swallow to a minor timestamp normalization issue, plus one architectural fragility worth flagging before S3 builds on top of this.

---

## Issue Catalogue

---

### 1. Safety — Critical

**Category:** Safety (accidental LLM call)
**Severity:** Critical
**Location:** `ai_router/__init__.py` — `route()` and `verify()` prologues (summarized in Commit C section)

**Issue:**
```python
try:
    from runtime_mode import is_no_router_mode
    if is_no_router_mode():
        return _build_no_router_route_stub()
except Exception:
    pass          # ← falls through to _init() and full LLM call
```
The bare `except Exception: pass` means any import failure, attribute error, or runtime exception inside `is_no_router_mode()` silently promotes the invocation to full mode and issues a live LLM/httpx call. Under `--no-router` this is exactly the behaviour the audit is designed to prevent. "Fail-open to full mode" is the wrong failure posture for a safety gate.

**Fix:**
```python
from runtime_mode import is_no_router_mode   # top-level import, not lazy
                                              # (module already exists at this point)

def route(content, ...):
    if is_no_router_mode():
        return _build_no_router_route_stub()
    _init()
    ...

def verify(route_result, ...):
    if is_no_router_mode():
        return _build_no_router_verification_stub(
            generator_model=route_result.model_name)
    _init()
    ...
```
If a lazy import is required for some other reason, at minimum re-raise rather than swallow:
```python
try:
    from runtime_mode import is_no_router_mode
    if is_no_router_mode():
        return _build_no_router_route_stub()
except ImportError:
    raise   # hard failure: no silent LLM promotion
except Exception:
    logger.exception("is_no_router_mode() failed; aborting route() to be safe")
    raise
```

---

### 2. Correctness / Backcompat — Major

**Category:** Correctness, Backcompat
**Severity:** Major
**Location:** `ai_router/runtime_mode.py` — `_spec_tier()` (line ~66) and `is_no_router_mode()` (line ~120)

**Issue:**
Both functions use bare unqualified module imports:
```python
from spec_config import parse_session_set_config   # _spec_tier()
from session_state import find_active_session_set  # is_no_router_mode()
```
In a package (`ai_router/`), these resolve against `sys.path`, not the package. They will fail with `ModuleNotFoundError` in any context where the package root is not explicitly on `sys.path` (e.g., `python -m pytest`, editable installs, VS Code test runner). Pre-S048 test suites that import anything from `ai_router` will now transitively pay the cost of this import path fragility.

**Fix:**
```python
# _spec_tier():
from ai_router.spec_config import parse_session_set_config
# or if intra-package relative imports are the project convention:
from .spec_config import parse_session_set_config

# is_no_router_mode():
from ai_router.session_state import find_active_session_set
# or:
from .session_state import find_active_session_set
```
Verify against the convention used in the rest of `ai_router/`; the bare-name style is consistent only if the project runs everything from the repo root with `src/` on `sys.path`.

---

### 3. Edge Case — Major

**Category:** Edge case (race condition)
**Severity:** Major
**Location:** `ai_router/suggestion_disposition.py` — `record_suggestion_disposition()` lines ~90–115

**Issue:**
The read-modify-write sequence on `activity-log.json` is not atomic:
```python
with log_path.open("r") as f:
    log = json.load(f)
# ← window: another writer can overwrite the file here
entries.append(entry)
with log_path.open("w") as f:
    json.dump(log, f, indent=2)
```
Two concurrent `record_suggestion_disposition` calls (AI orchestrator + a parallel close-out event emitter) will silently lose one entry. The `close_session.py` event emission already runs in the same process context where this is called.

**Fix:**
Use `fcntl.flock` (POSIX) or a lockfile via `filelock` (cross-platform) around the read-modify-write:
```python
import fcntl

with log_path.open("r+", encoding="utf-8") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    log = json.load(f)
    # ... mutate ...
    f.seek(0)
    f.truncate()
    json.dump(log, f, indent=2)
    f.write("\n")
```
Or adopt the same write-to-temp-then-rename pattern used elsewhere in this codebase if it exists.

---

### 4. Edge Case — Major

**Category:** Edge case (resolve_no_router_mode idempotency)
**Severity:** Major
**Location:** `ai_router/runtime_mode.py` — `resolve_no_router_mode()` (entire function)

**Issue:**
`_NO_ROUTER_MODE` is written unconditionally on every call. If `resolve_no_router_mode(cli_flag=True)` is called at entry-point startup and then `resolve_no_router_mode(cli_flag=False)` is called again later (e.g., by a test harness that forgot to call `reset_for_tests()`, or by a second entry point), the cache is silently overwritten to `False` and subsequent `is_no_router_mode()` calls return the wrong answer. The override logging then gives a misleading "agrees" or "overrides" message on the second call.

**Fix — two options:**
Option A (guard re-entry):
```python
def resolve_no_router_mode(cli_flag, session_set_dir=None):
    global _NO_ROUTER_MODE
    if _NO_ROUTER_MODE is not None:
        logger.debug("resolve_no_router_mode called again; cached=%s", _NO_ROUTER_MODE)
        return _NO_ROUTER_MODE
    ...
```
Option B (keep overwrite but document + warn):
```python
    if _NO_ROUTER_MODE is not None:
        logger.warning(
            "resolve_no_router_mode called a second time; overwriting cached=%s",
            _NO_ROUTER_MODE,
        )
```
Option A is safer given that `close_session.py` calls this at startup and test code may call it again.

---

### 5. Edge Case — Important

**Category:** Edge case (false positive tier detection)
**Severity:** Important
**Location:** `ai_router/spec_config.py` — `parse_session_set_config()` lines ~84–90

**Issue:**
```python
block_match = _CONFIG_BLOCK_RE.search(text)
block = block_match.group(1) if block_match else text   # ← fallback to FULL FILE
```
When a `spec.md` has no `## Session Set Configuration` / YAML fence, the parser searches the entire file for `tier:`, `requiresUAT:`, etc. Any free-form prose in the spec that happens to contain `tier: lightweight` (e.g., a table of contents, a note about another set, a quoted example) will be misread as a declarative config. For a pre-S048 spec that mentions the new lightweight tier in its design notes, this could silently activate `--no-router` mode.

**Fix:**
```python
if not block_match:
    return _DEFAULT    # no config block → canonical full-tier default
block = block_match.group(1)
```
The docstring already says "Returns the Full-tier-conservative default when the file is missing, unreadable, or has no `Session Set Configuration` block." The implementation contradicts the docstring.

---

### 6. Minor — Timestamp normalisation

**Category:** Correctness (data consistency)
**Severity:** Minor
**Location:** `ai_router/suggestion_disposition.py` — `record_suggestion_disposition()` line ~100

**Issue:**
```python
timestamp = datetime.now(timezone.utc).astimezone().isoformat()
```
`datetime.now(timezone.utc)` produces a UTC-aware datetime; `.astimezone()` with no argument converts it to the **local system timezone**. The recorded timestamp will therefore be in local time (e.g., `2025-06-01T10:30:00-04:00`) rather than UTC. If the activity log's other entries are written in UTC (common for server/CI processes), timestamps will be inconsistent and sort incorrectly.

**Fix:**
```python
timestamp = datetime.now(timezone.utc).isoformat()
# produces: 2025-06-01T14:30:00+00:00
```

---

### 7. Suggestion — `is_no_router_mode()` lazy path caching

**Category:** Correctness (subtle inconsistency)
**Severity:** Suggestion
**Location:** `ai_router/runtime_mode.py` — `is_no_router_mode()` lines ~110–130

**Issue:**
The docstring explicitly says the lazy path does not cache. This means repeated calls to `is_no_router_mode()` before `resolve_no_router_mode()` has run will re-evaluate the env var and spec on every call. If `DABBLER_NO_ROUTER` is unset and the spec is lightweight, the first call reads the spec (disk I/O), and so does the second. More importantly, if something mutates the env var between calls (possible in test contexts), the result flips silently. The route() and verify() callers both call `is_no_router_mode()`, so in an integration test that exercises both, this inconsistency is reachable.

**Fix:**
Either cache the lazy result:
```python
if _env_var_truthy():
    _NO_ROUTER_MODE = True   # cache the lazy result too
    return True
```
or document clearly that callers **must** call `resolve_no_router_mode()` at entry-point startup and treat `is_no_router_mode()` as an error if the cache is cold:
```python
if _NO_ROUTER_MODE is None:
    raise RuntimeError(
        "is_no_router_mode() called before resolve_no_router_mode(); "
        "call resolve_no_router_mode() at entry-point startup."
    )
return _NO_ROUTER_MODE
```

---

## Verification of the Five Specific Questions

| Question | Verdict | Notes |
|---|---|---|
| **Correctness — does code match spec?** | Mostly yes | Precedence order correct; tri-state parsing correct; short-circuit stubs correct. Defect #5 (false-positive tier detection) is the one functional divergence from the stated spec behaviour. |
| **Safety — no accidental LLM calls under --no-router?** | **No** — defect #1 | The `except Exception: pass` in `route()`/`verify()` prologues will silently promote to full mode (live LLM call) if the runtime-mode check itself throws. This is the single most important fix. |
| **Backwards compatibility** | Yes, conditional on fixes | `_DEFAULT = tier="full"` is correct. New CLI flags are additive. Defect #5 is the only backcompat risk: an old spec with a stray `tier: lightweight` in prose could activate no-router mode. |
| **Edge cases** | Three concrete gaps | Race condition on activity-log (#3), `resolve_no_router_mode()` re-invocation (#4), false-positive tier detection (#5). |
| **Deferral of S2 runtime gate defensible?** | Yes | The read/write helpers are complete, the deferral is documented in the commit message and module docstring, and adding the close-out gate in S2 would have touched Full-tier behaviour outside the audit scope. The S3 boundary is clean. |
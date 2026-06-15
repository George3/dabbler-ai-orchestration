"""Set 068 S3 Experiment B - the cadence arm runner (blind, staged snapshots).

Drives the four arms over the frozen numkit snapshots, per provider, K repeats:

    R  per-session routed   : providers.call_model over session_diff(S_i), i=1..n
    Q  end-of-set routed    : providers.call_model over Q_surface_files, once (S_n)
    E  end-of-set path-aware: pull_route over tree(S_n) + the run_test CAGE, once
    P  per-session path-aware (OPTIONAL): pull_route over tree(S_i), i=1..n

The routed arms (R, Q) are SNIPPET-bounded -- they see only the surface files,
the rest omitted (prereg Section 3a). The path-aware arms (E, P) get the whole
tree in a read-only sandbox AND, for E, the disposable-worktree `run_test` cage
(Set 068 S1) so the model may execute the snapshot's tests in a throwaway git
worktree -- the live, end-to-end use of run_test inside a metered loop (run-test
contract Section 6). Provider + reasoning knobs are held CONSTANT across a
contrast, exactly as Experiment A did.

Blind: no arm sees another arm's output. Every raw output is persisted to
raw/numkit/<arm>_<prov>_S<i>_k<k>.json IMMEDIATELY (L-064-3) so a mid-sweep crash
never loses paid output; an existing non-error raw file is skipped (resumable).
A path-aware run that stops on token-budget with NO verdict is recorded as a
FAILED arm, not silently dropped (L-067-1).

Usage:
  python run_arms.py --arms R Q E --providers google --k 1     # pilot (prereg Sec 10)
  python run_arms.py --arms E --providers openai --k 1         # GPT path-aware convergence check
  python run_arms.py                                           # full sweep R/Q/E, both providers, K=3
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ai_router"))

import providers  # noqa: E402
import pull_verifier as pv  # noqa: E402
from pull_verifier import RunTestConfig  # noqa: E402

RAW = HERE / "raw"
UNIT = "numkit"
SNAP = HERE / "snapshots" / UNIT
CAT = json.loads((HERE / "catalogue.json").read_text(encoding="utf-8"))
U = CAT["units"][UNIT]
N = U["n_snapshots"]
SESSION_DIFF = {int(k): v for k, v in U["session_diff_files"].items()}
Q_SURFACE = U["Q_surface_files"]
CONFIG = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))

# Identical defect-hunting task across all arms (blind, same task). Only the
# context surface + the per-context preamble differ. Mirrors Experiment A.
CORE_TASK = (
    "You are a meticulous code reviewer. Find every REAL defect in this code: "
    "correctness bugs, contract/documentation violations, wrong constants or "
    "conversion factors, inverted maths, precision loss, off-by-one and wrong "
    "initial values, wrong-order arguments, missing None/empty handling, and "
    "cross-file contract mismatches. For each defect name the file and function "
    "and explain the bug concretely. Only report genuine defects - do not invent "
    "issues. Keep output ASCII-only."
)
ROUTED_PREAMBLE = (
    "Review the following code (the change under review). This is the complete "
    "snippet you were handed; review it as given.\n\n"
)
PULL_PREAMBLE = (
    "Review the small Python package in your read-only sandbox. Use the tools to "
    "list and read its files before judging. You MAY also run the project's test "
    "suite with run_test (it executes in a disposable throwaway worktree). Then "
    "submit your critique.\n\n"
)

ARMS = {
    "R": {"context": "routed", "per_session": True},
    "Q": {"context": "routed", "per_session": False},
    "E": {"context": "path-aware", "per_session": False},
    "P": {"context": "path-aware", "per_session": True},
}
PROVIDER_MODEL = {"openai": "gpt-5.4", "google": "gemini-2.5-pro"}
# Routed reasoning knobs MATCH the pull_verifier executor block (fair contrast).
ROUTED_GEN = {"openai": {"reasoning_effort": "medium"}, "google": {"thinking_budget": 8192}}
ROUTED_MAX_TOKENS = 24000


def _read_files(snapshot: int, files: list[str]) -> str:
    parts = []
    root = SNAP / f"S{snapshot}"
    for fname in files:
        body = (root / fname).read_text(encoding="utf-8")
        parts.append(f"# ===== {fname} =====\n{body}")
    return "\n\n".join(parts)


def _surface_files(arm: str, i: int) -> list[str]:
    if arm == "R":
        return SESSION_DIFF[i]
    if arm == "Q":
        return Q_SURFACE
    raise ValueError(arm)


def _model_cfg(model_id: str) -> dict:
    for m in CONFIG["models"].values():
        if m.get("model_id") == model_id:
            return m
    raise KeyError(model_id)


def run_routed(arm: str, provider: str, i: int) -> dict:
    model = PROVIDER_MODEL[provider]
    pcfg = CONFIG["providers"][provider]
    snippet_snapshot = i if arm == "R" else N
    user = ROUTED_PREAMBLE + _read_files(snippet_snapshot, _surface_files(arm, i))
    t0 = time.time()
    res = providers.call_model(
        provider_name=provider, model_id=model,
        system_prompt=CORE_TASK, user_message=user,
        max_tokens=ROUTED_MAX_TOKENS, config=pcfg,
        generation_params=ROUTED_GEN[provider],
    )
    wall = time.time() - t0
    mc = _model_cfg(model)
    cost = (res.input_tokens / 1e6 * mc["input_cost_per_1m"]
            + res.output_tokens / 1e6 * mc["output_cost_per_1m"])
    return {
        "arm": arm, "provider": provider, "snapshot": i, "context": "routed",
        "model": model, "content": res.content,
        "input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
        "cost_usd": round(cost, 6), "stop_reason": res.stop_reason,
        "wall_seconds": round(wall, 2), "tool_call_count": None, "error": None,
    }


def _temp_git_repo(snapshot: int) -> Path:
    """Copy snapshot tree into a fresh temp dir and make it a one-commit git repo
    so run_test_in_cage can `git worktree add --detach` from HEAD."""
    tmp = Path(tempfile.mkdtemp(prefix="expb_cage_"))
    shutil.copytree(SNAP / f"S{snapshot}", tmp, dirs_exist_ok=True)
    env_id = ["-c", "user.email=expb@dabbler.local", "-c", "user.name=expb"]
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", *env_id, "add", "-A"], cwd=tmp, check=True)
    subprocess.run(["git", *env_id, "commit", "-q", "-m", "snapshot"], cwd=tmp, check=True)
    return tmp


def run_pull(arm: str, provider: str, i: int) -> dict:
    sandbox = SNAP / f"S{i}"
    cage_repo = None
    rtc = None
    try:
        # Arm E (end-of-set) gets the live run_test cage; arm P stays read-only to
        # bound L-067-1 over-probing across n per-session runs.
        if arm == "E":
            cage_repo = _temp_git_repo(i)
            rtc = RunTestConfig(
                repo_root=str(cage_repo), ref="HEAD",
                command=("python", "-m", "pytest", "-q"),
            )
        r = pv.pull_route(sandbox, PULL_PREAMBLE + CORE_TASK, provider=provider,
                          run_test_config=rtc)
        d = r.to_dict()
        tr = d["trace"]
        return {
            "arm": arm, "provider": provider, "snapshot": i, "context": "path-aware",
            "model": d["model"], "ok": d["ok"], "critique": d["critique"], "trace": tr,
            "input_tokens": tr["input_tokens"], "output_tokens": tr["output_tokens"],
            "cost_usd": tr["cost_usd"], "stop_reason": tr["stop_reason"],
            "wall_seconds": tr["wall_seconds"], "tool_call_count": tr["tool_call_count"],
            # L-067-1: a token-budget stop with NO verdict is a FAILED arm.
            "error": ("token-budget stop with no verdict"
                      if (not d["ok"] and tr.get("stop_reason") == "token-budget"
                          and not d.get("critique")) else None),
        }
    finally:
        if cage_repo is not None:
            shutil.rmtree(cage_repo, ignore_errors=True)


def run_cell(arm: str, provider: str, i: int) -> dict:
    spec = ARMS[arm]
    try:
        if spec["context"] == "routed":
            return run_routed(arm, provider, i)
        return run_pull(arm, provider, i)
    except Exception as exc:  # record, never abort the sweep
        return {
            "arm": arm, "provider": provider, "snapshot": i,
            "context": spec["context"], "model": PROVIDER_MODEL[provider],
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(), "cost_usd": 0.0,
        }


def _raw_path(arm: str, provider: str, i: int, k: int) -> Path:
    return RAW / UNIT / f"{arm}_{provider}_S{i}_k{k}.json"


def _already_done(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("error") is None
    except Exception:
        return False


def _snapshots_for(arm: str) -> list[int]:
    return list(range(1, N + 1)) if ARMS[arm]["per_session"] else [N]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=["R", "Q", "E"])
    ap.add_argument("--providers", nargs="*", default=["openai", "google"])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cells = [
        (a, p, i, k)
        for a in args.arms for p in args.providers
        for i in _snapshots_for(a) for k in range(1, args.k + 1)
    ]
    todo = [c for c in cells if args.force or not _already_done(_raw_path(*c))]
    print(f"Cells: {len(cells)} total, {len(cells) - len(todo)} done, {len(todo)} to run "
          f"(arms={args.arms} providers={args.providers} K={args.k} workers={args.workers}).")

    done = 0
    total_cost = 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_cell, a, p, i): (a, p, i, k) for (a, p, i, k) in todo}
        for fut in as_completed(futs):
            a, p, i, k = futs[fut]
            rec = fut.result()
            rec["k"] = k
            path = _raw_path(a, p, i, k)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")  # L-064-3
            done += 1
            cost = rec.get("cost_usd", 0.0) or 0.0
            total_cost += cost
            err = rec.get("error")
            print(f"  [{done}/{len(todo)}] {a} {p} S{i} k{k}: "
                  + (f"ERROR {err}" if err else
                     f"cost=${cost:.4f} probes={rec.get('tool_call_count')} "
                     f"stop={rec.get('stop_reason')}"))
    print(f"Done. This batch metered ~${total_cost:.4f} across {done} runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

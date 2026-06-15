"""Set 067 S3 Experiment A - the 2x2 arm runner (blind, frozen-tree).

Runs four arms on each tree's BUGGY (frozen pre-remediation) tree, K times each:

    A1 = routed   GPT    (providers.call_model openai gpt-5.4, snippet only)
    A2 = routed   Gemini (providers.call_model google gemini-2.5-pro, snippet only)
    B1 = path-aware GPT  (pull_route provider=openai, whole-tree sandbox + probes)
    B2 = path-aware Gemini (pull_route provider=google, whole-tree sandbox + probes)

Provider + reasoning are held CONSTANT across the context contrast (the routed
arms use the SAME reasoning knobs the pull_verifier executor block uses), so
B1-A1 and B2-A2 isolate context-access. The ONLY difference between A and B is
the context surface: routed sees only the per-tree SNIPPET (catalogue.json
trees[*].snippet); path-aware gets the whole tree and must probe.

Blind: no arm sees any other arm's output. Single-round per arm (cadence held
constant). Every raw output is persisted to raw/<tree>/<arm>_k<k>.json
IMMEDIATELY (L-064-3) so a mid-sweep crash never loses paid output, and the run
is RESUMABLE (an existing non-error raw file is skipped).

Usage:
  python run_arms.py                         # full sweep: all trees, all arms, K=3
  python run_arms.py --trees tree1_tokenizer --arms B1 --k 1   # pilot
"""

from __future__ import annotations

import argparse
import json
import sys
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

RAW = HERE / "raw"
CATALOGUE = json.loads((HERE / "catalogue.json").read_text(encoding="utf-8"))
CONFIG = yaml.safe_load(
    (REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8")
)

# The CORE defect-hunting task - identical across all four arms (blind, same
# task). Only the per-context preamble + the context surface differ.
CORE_TASK = (
    "You are a meticulous code reviewer. Find every REAL defect in this code: "
    "correctness bugs, contract/documentation violations, wrong-data bugs, "
    "silent coercion or default-injection, type/shape mismatches across "
    "surfaces, index/count errors, name collisions, too-narrow validation, and "
    "regressions. For each defect, name the file and function and explain the "
    "bug concretely. Only report genuine defects - do not invent issues. Keep "
    "output ASCII-only."
)

ROUTED_PREAMBLE = (
    "Review the following code snippet (the change under review). This is the "
    "complete snippet you were handed; review it as given.\n\n"
)
PULL_PREAMBLE = (
    "Review the small Python package in your read-only sandbox. Use the tools "
    "to list and read its files before judging, then submit your critique.\n\n"
)

ARMS = {
    "A1": {"context": "routed", "provider": "openai", "model": "gpt-5.4"},
    "A2": {"context": "routed", "provider": "google", "model": "gemini-2.5-pro"},
    "B1": {"context": "path-aware", "provider": "openai", "model": "gpt-5.4"},
    "B2": {"context": "path-aware", "provider": "google", "model": "gemini-2.5-pro"},
}

# Routed reasoning knobs MATCH the pull_verifier executor block (fair contrast).
ROUTED_GEN = {
    "openai": {"reasoning_effort": "medium"},
    "google": {"thinking_budget": 8192},
}
ROUTED_MAX_TOKENS = 24000  # match pull_verifier caps.max_output_tokens


def _tree_buggy(tree: str) -> Path:
    return HERE / "trees" / tree / "buggy"


def _model_cfg(model_id: str) -> dict:
    for m in CONFIG["models"].values():
        if m.get("model_id") == model_id:
            return m
    raise KeyError(model_id)


def _snippet_text(tree: str) -> str:
    root = _tree_buggy(tree)
    parts = []
    for fname in CATALOGUE["trees"][tree]["snippet"]:
        body = (root / fname).read_text(encoding="utf-8")
        parts.append(f"# ===== {fname} =====\n{body}")
    return "\n\n".join(parts)


def run_routed(tree: str, arm: str) -> dict:
    spec = ARMS[arm]
    provider, model = spec["provider"], spec["model"]
    pcfg = CONFIG["providers"][provider]
    user = ROUTED_PREAMBLE + _snippet_text(tree)
    t0 = time.time()
    res = providers.call_model(
        provider_name=provider,
        model_id=model,
        system_prompt=CORE_TASK,
        user_message=user,
        max_tokens=ROUTED_MAX_TOKENS,
        config=pcfg,
        generation_params=ROUTED_GEN[provider],
    )
    wall = time.time() - t0
    mc = _model_cfg(model)
    cost = (
        res.input_tokens / 1e6 * mc["input_cost_per_1m"]
        + res.output_tokens / 1e6 * mc["output_cost_per_1m"]
    )
    return {
        "tree": tree, "arm": arm, "context": "routed", "provider": provider,
        "model": model, "content": res.content, "input_tokens": res.input_tokens,
        "output_tokens": res.output_tokens, "cost_usd": round(cost, 6),
        "stop_reason": res.stop_reason, "wall_seconds": round(wall, 2),
        "tool_call_count": None, "error": None,
    }


def run_pull(tree: str, arm: str) -> dict:
    spec = ARMS[arm]
    sandbox = _tree_buggy(tree)
    instruction = PULL_PREAMBLE + CORE_TASK
    r = pv.pull_route(sandbox, instruction, provider=spec["provider"])
    d = r.to_dict()
    tr = d["trace"]
    return {
        "tree": tree, "arm": arm, "context": "path-aware",
        "provider": spec["provider"], "model": d["model"],
        "ok": d["ok"], "critique": d["critique"], "trace": tr,
        "input_tokens": tr["input_tokens"], "output_tokens": tr["output_tokens"],
        "cost_usd": tr["cost_usd"], "stop_reason": tr["stop_reason"],
        "wall_seconds": tr["wall_seconds"], "tool_call_count": tr["tool_call_count"],
        "error": None,
    }


def run_cell(tree: str, arm: str, k: int) -> dict:
    spec = ARMS[arm]
    try:
        rec = run_routed(tree, arm) if spec["context"] == "routed" else run_pull(tree, arm)
    except Exception as exc:  # record, never abort the sweep
        rec = {
            "tree": tree, "arm": arm, "context": spec["context"],
            "provider": spec["provider"], "model": spec["model"],
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "cost_usd": 0.0,
        }
    rec["k"] = k
    return rec


def _raw_path(tree: str, arm: str, k: int) -> Path:
    return RAW / tree / f"{arm}_k{k}.json"


def _already_done(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        return rec.get("error") is None
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trees", nargs="*", default=list(CATALOGUE["trees"].keys()))
    ap.add_argument("--arms", nargs="*", default=list(ARMS.keys()))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="re-run completed cells")
    args = ap.parse_args()

    cells = [
        (t, a, k)
        for t in args.trees
        for a in args.arms
        for k in range(1, args.k + 1)
    ]
    todo = [
        c for c in cells
        if args.force or not _already_done(_raw_path(*c))
    ]
    print(
        f"Cells: {len(cells)} total, {len(cells) - len(todo)} already done, "
        f"{len(todo)} to run (workers={args.workers})."
    )

    done = 0
    total_cost = 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_cell, *c): c for c in todo}
        for fut in as_completed(futs):
            tree, arm, k = futs[fut]
            rec = fut.result()
            path = _raw_path(tree, arm, k)
            path.parent.mkdir(parents=True, exist_ok=True)
            # L-064-3: persist raw (utf-8) immediately, before any summary print.
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            done += 1
            cost = rec.get("cost_usd", 0.0) or 0.0
            total_cost += cost
            err = rec.get("error")
            tcc = rec.get("tool_call_count")
            print(
                f"  [{done}/{len(todo)}] {tree} {arm} k{k}: "
                + (f"ERROR {err}" if err else
                   f"cost=${cost:.4f} probes={tcc} stop={rec.get('stop_reason')}")
            )

    print(f"Done. This batch metered ~${total_cost:.4f} across {done} runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

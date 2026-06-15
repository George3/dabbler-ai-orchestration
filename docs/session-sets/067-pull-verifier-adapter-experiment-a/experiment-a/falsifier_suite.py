"""Set 067 S3 Experiment A - deterministic falsifier suite.

One falsifier per seeded defect (the Q4 / contract-test arm), PRE-AUTHORED
before any agent runs. Each falsifier asserts the FIXED behaviour: it raises
(defect DETECTED) on the buggy tree and passes (defect ABSENT) on the fixed
tree. Run `validate()` to prove every discriminating falsifier actually
discriminates (fails on buggy, passes on fixed) - that is the instrument's
self-check before the experiment spends a cent.

The novel control D16 (latent / non-probeable) has NO discriminating falsifier
by design: no reachable input distinguishes buggy from fixed, so a behavioural
test cannot catch it. It is recorded with `falsifier=None` and
`discriminates=False`, which is the empirical content of the "non-probeable"
label.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREES = HERE / "trees"

TREE_MODULES = {
    "tree1_tokenizer": ["constants", "tokenizer"],
    "tree2_registry": ["operators", "registry"],
    "tree3_aggregator": ["analyzer", "index_builder"],
    "tree4_serializer": ["schema", "serializer"],
    "tree5_engine": ["engine", "evaluator"],
}

_ALL_TREE_MODULE_NAMES = sorted(
    {m for mods in TREE_MODULES.values() for m in mods}
)


def load(tree: str, variant: str) -> dict:
    """Import a tree's modules FRESH from its variant dir; return name->module.

    Purges any previously-imported tree modules so module-level state (e.g.
    evaluator._CACHE) never leaks across falsifiers or variants.
    """
    root = TREES / tree / variant
    for name in _ALL_TREE_MODULE_NAMES:
        sys.modules.pop(name, None)
    sys.path.insert(0, str(root))
    try:
        return {m: importlib.import_module(m) for m in TREE_MODULES[tree]}
    finally:
        sys.path.remove(str(root))


# --- Tree 1 -----------------------------------------------------------------

def f_D1(m):
    tk, C = m["tokenizer"], m["constants"]
    assert tk.tokenize(".5") == [(C.NUMBER, ".5")], tk.tokenize(".5")
    assert tk.tokenize("1.") == [(C.NUMBER, "1.")], tk.tokenize("1.")


def f_D2(m):
    tk, C = m["tokenizer"], m["constants"]
    assert tk.tokenize("$") == [(C.UNKNOWN, "$")], tk.tokenize("$")


def f_D3(m):
    tk = m["tokenizer"]
    assert tk.token_count("1 + 2") == 3, tk.token_count("1 + 2")


def f_D4(m):
    tk, C = m["tokenizer"], m["constants"]
    ks = tk.kinds("1+2")
    assert all(isinstance(k, str) for k in ks), ks
    assert ks == [C.NUMBER, C.OP, C.NUMBER], ks


# --- Tree 2 -----------------------------------------------------------------

def f_D5(m):
    reg, ops = m["registry"], m["operators"]
    assert len(reg.REGISTRY) == len(ops.OPERATORS), len(reg.REGISTRY)
    assert reg.REGISTRY["minus"].arity == 2, reg.REGISTRY["minus"].arity


def f_D6(m):
    reg = m["registry"]
    assert reg.precedence("+") == 1, reg.precedence("+")
    assert reg.precedence("*") == 2, reg.precedence("*")


def f_D7(m):
    reg, ops = m["registry"], m["operators"]
    unary = [op for op in ops.OPERATORS if op.arity == 1][0]
    binary = [op for op in ops.OPERATORS if op.arity == 2][0]
    assert reg.is_binary(unary) is False, "is_binary(unary) should be False"
    assert reg.is_binary(binary) is True, "is_binary(binary) should be True"


def f_D8(m):
    reg = m["registry"]
    try:
        reg.lookup("does_not_exist")
    except KeyError:
        return
    raise AssertionError("lookup of unknown name should raise KeyError")


# --- Tree 3 -----------------------------------------------------------------

def f_D9(m):
    an, ib = m["analyzer"], m["index_builder"]
    stmts = an.parse("a = foo\nbar(baz)\nreturn qux")
    idx = ib.build_index(stmts)
    # The index must be the superset: include the call ref and the return ref.
    assert "baz" in idx, idx
    assert "qux" in idx, idx


def f_D10(m):
    an, ib = m["analyzer"], m["index_builder"]
    idx = ib.build_index(an.parse("a = foo"))
    assert idx == ["foo"], idx


def f_D11(m):
    an = m["analyzer"]
    assert an.count_statements("a = 1\n\n\nb = 2") == 2, \
        an.count_statements("a = 1\n\n\nb = 2")


def f_D12(m):
    an = m["analyzer"]
    names = [r["name"] for r in an.collect_call_refs(["f(a, b)"])]
    assert "a" in names and "b" in names, names
    nested = [r["name"] for r in an.collect_call_refs(["g(h(x))"])]
    assert "x" in nested, nested


# --- Tree 4 -----------------------------------------------------------------

def f_D13(m):
    ser = m["serializer"]
    try:
        ser.to_record({"items": [1, 2]})
    except KeyError:
        return
    raise AssertionError("to_record without version should raise (required)")


def f_D14(m):
    ser = m["serializer"]
    rec = ser.to_record({"version": 1, "items": [1, 2, 3]})
    assert rec["count"] == 3 and isinstance(rec["count"], int), rec["count"]


def f_D15(m):
    ser = m["serializer"]
    good = {"version": 1, "count": 0, "items": []}
    bad = {"version": 1, "items": []}  # missing required "count"
    assert ser.validate([good, bad]) is False, "validate must check all records"


def f_D16(m):
    # NON-DISCRIMINATING by design (latent / non-probeable). No behavioural
    # assertion can distinguish buggy from fixed. Recorded as falsifier=None.
    raise NotImplementedError("D16 has no discriminating behavioural falsifier")


# --- Tree 5 -----------------------------------------------------------------

def f_D17(m):
    eng = m["engine"]
    try:
        eng.safe_div(1, 0)
    except ZeroDivisionError:
        return
    raise AssertionError("safe_div(1, 0) should raise, not return a number")


def f_D18(m):
    ev = m["evaluator"]
    try:
        ev.evaluate("no_such_op", 1, 2)
    except KeyError:
        return
    raise AssertionError("strict-mode evaluate of an unknown op should raise")


def f_D19(m):
    eng = m["engine"]
    assert eng.compute("mul", 2, 3) == 6, eng.compute("mul", 2, 3)


def f_D20(m):
    ev = m["evaluator"]
    ev.set_precision(2)
    r1 = ev.evaluate("div", 10, 3)
    ev.set_precision(4)
    r2 = ev.evaluate("div", 10, 3)
    assert r2 != r1, f"precision change ignored by cache: {r1} == {r2}"


FALSIFIERS = {
    "D1": f_D1, "D2": f_D2, "D3": f_D3, "D4": f_D4,
    "D5": f_D5, "D6": f_D6, "D7": f_D7, "D8": f_D8,
    "D9": f_D9, "D10": f_D10, "D11": f_D11, "D12": f_D12,
    "D13": f_D13, "D14": f_D14, "D15": f_D15, "D16": None,
    "D17": f_D17, "D18": f_D18, "D19": f_D19, "D20": f_D20,
}


def _catalogue() -> dict:
    return json.loads((HERE / "catalogue.json").read_text(encoding="utf-8"))


def run_falsifier(defect_id: str, tree: str, variant: str) -> bool:
    """Return True iff the falsifier DETECTS the defect in this variant.

    Detected = the falsifier raised (its fixed-behaviour assertion failed).
    """
    fn = FALSIFIERS[defect_id]
    if fn is None:
        return False  # no discriminating falsifier
    mods = load(tree, variant)
    try:
        fn(mods)
        return False  # passed -> defect absent
    except Exception:
        return True   # raised -> defect present


def validate() -> int:
    """Prove each discriminating falsifier fails on buggy and passes on fixed."""
    cat = _catalogue()
    bad = []
    coverage = {"discriminating": 0, "non_discriminating": 0}
    for d in cat["defects"]:
        did, tree = d["id"], d["tree"]
        if FALSIFIERS[did] is None or not d["discriminates"]:
            coverage["non_discriminating"] += 1
            print(f"  [.] {did}: non-discriminating (novel/latent) - no falsifier")
            continue
        coverage["discriminating"] += 1
        on_buggy = run_falsifier(did, tree, "buggy")
        on_fixed = run_falsifier(did, tree, "fixed")
        ok = on_buggy and not on_fixed
        flag = "x" if ok else " "
        print(f"  [{flag}] {did}: detect_on_buggy={on_buggy} detect_on_fixed={on_fixed}")
        if not ok:
            bad.append(did)
    total = len(cat["defects"])
    print(
        f"\nFalsifier coverage: {coverage['discriminating']}/{total} "
        f"discriminating, {coverage['non_discriminating']}/{total} "
        f"non-discriminating (novel/latent)."
    )
    if bad:
        print(f"FAIL: falsifiers that do not discriminate cleanly: {bad}")
        return 1
    print("OK: every discriminating falsifier fails on buggy and passes on fixed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())

"""Set 067 S3 Experiment A - seeded-defect mock-repo builder.

Writes 5 self-contained "frozen trees" (a small numeric toolkit) in TWO
variants each:

    trees/<tree>/buggy/   - the frozen pre-remediation tree the arms review
    trees/<tree>/fixed/   - identical EXCEPT the seeded defect(s) are corrected

The fixed/ variant exists so the deterministic falsifier suite can prove each
falsifier DISCRIMINATES (fails on buggy, passes on fixed). Re-runnable and
deterministic. NO production code is touched (spec S3: fixture dirs only).

20 defects across 5 trees span the forward-ab-design.md catalogue classes:
index/count undercount, name-collision/dup-key, too-narrow regex/validation,
type/shape contradiction across surfaces, silent coercion/default-injection,
cross-file contract/join-key drift, remediation-introduced regression, and 3
genuinely novel-reasoning controls (latent-not-triggerable / emergent invariant).

Each defect is labelled probeable|novel and in-snippet|cross-file in
catalogue.json (authored alongside this builder). The per-tree SNIPPET (the
single file a single-shot reviewer would be handed as the "diff") is what the
routed arms see; the path-aware arms get the whole tree and must probe.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TREES = HERE / "trees"


# ---------------------------------------------------------------------------
# Tree 1 - tokenizer.  snippet = tokenizer.py
#   D1 too-narrow regex (class 3, Major, in-snippet, probeable)
#   D2 silent coercion of unknown char -> "+" (class 5, Major, cross-file, probeable)
#   D3 token_count off-by-one undercount (class 1, Minor, in-snippet, probeable)
#   D4 kinds() returns tuples not kind-strings, vs README (class 4, Major, cross-file, probeable)
# ---------------------------------------------------------------------------

T1_CONSTANTS = '''\
"""Token kinds and the canonical operator set."""

NUMBER = "NUMBER"
OP = "OP"
UNKNOWN = "UNKNOWN"

# The COMPLETE set of operator characters this language supports. The tokenizer
# must map exactly these to OP; anything else is UNKNOWN - never guessed.
OP_CHARS = ("+", "-", "*", "/")
'''

T1_README = '''\
# tokenizer

A tiny tokenizer for arithmetic expressions.

## API contract

- `tokenize(text)` -> list of `(kind, value)` tuples. `kind` is one of
  `NUMBER`, `OP`, `UNKNOWN`. Numbers include decimals written `.5` and `1.`.
- `token_count(text)` -> the EXACT number of tokens in `text`.
- `kinds(text)` -> a list of the token **kind strings**, e.g. `["NUMBER","OP"]`.

Any character that is not a digit, `.`, or one of `+ - * /` MUST tokenize as
`UNKNOWN`. The tokenizer never guesses an operator.
'''

T1_TOKENIZER_BUGGY = '''\
import re

from constants import NUMBER, OP, UNKNOWN, OP_CHARS

# A number is an integer or decimal, including ".5" and "1." per the README.
NUMBER_RE = re.compile(r"\\d+\\.\\d+|\\d+")


def tokenize(text):
    """Return a list of (kind, value) token tuples for `text`."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        m = NUMBER_RE.match(text, i)
        if m:
            tokens.append((NUMBER, m.group()))
            i = m.end()
            continue
        if ch in OP_CHARS:
            tokens.append((OP, ch))
        else:
            tokens.append((OP, "+"))
        i += 1
    return tokens


def token_count(text):
    """Return the number of tokens in `text`."""
    return len(tokenize(text)) - 1


def kinds(text):
    """Return the list of token KIND strings (see README)."""
    return tokenize(text)
'''

T1_TOKENIZER_FIXED = '''\
import re

from constants import NUMBER, OP, UNKNOWN, OP_CHARS

# A number is an integer or decimal, including ".5" and "1." per the README.
NUMBER_RE = re.compile(r"\\d+\\.\\d*|\\.\\d+|\\d+")


def tokenize(text):
    """Return a list of (kind, value) token tuples for `text`."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        m = NUMBER_RE.match(text, i)
        if m:
            tokens.append((NUMBER, m.group()))
            i = m.end()
            continue
        if ch in OP_CHARS:
            tokens.append((OP, ch))
        else:
            tokens.append((UNKNOWN, ch))
        i += 1
    return tokens


def token_count(text):
    """Return the number of tokens in `text`."""
    return len(tokenize(text))


def kinds(text):
    """Return the list of token KIND strings (see README)."""
    return [kind for (kind, _value) in tokenize(text)]
'''


# ---------------------------------------------------------------------------
# Tree 2 - registry.  snippet = registry.py
#   D5 dup-key name collision drops an operator (class 2, Critical, cross-file, probeable)
#   D6 join-key drift: PRECEDENCE keyed by name but looked up by symbol (class 6, Major, cross-file, probeable)
#   D7 is_binary arity test wrong (local logic, Minor, in-snippet, probeable)
#   D8 lookup() silently defaults to identity op for unknown name (class 5, Minor, in-snippet, probeable)
# ---------------------------------------------------------------------------

T2_OPERATORS = '''\
"""The operator catalogue. Each operator has a unique `name` and `symbol`."""


class Operator:
    def __init__(self, name, symbol, arity, func):
        self.name = name
        self.symbol = symbol
        self.arity = arity
        self.func = func


# NOTE: "neg" and "minus" are DISTINCT operators but were both given the name
# "minus" below - a duplicate name. (Seeded defect D5: a name collision.)
OPERATORS = [
    Operator("add", "+", 2, lambda a, b: a + b),
    Operator("minus", "-", 2, lambda a, b: a - b),
    Operator("times", "*", 2, lambda a, b: a * b),
    Operator("divide", "/", 2, lambda a, b: a / b),
    Operator("minus", "_", 1, lambda a: -a),
]
'''

T2_OPERATORS_FIXED = '''\
"""The operator catalogue. Each operator has a unique `name` and `symbol`."""


class Operator:
    def __init__(self, name, symbol, arity, func):
        self.name = name
        self.symbol = symbol
        self.arity = arity
        self.func = func


OPERATORS = [
    Operator("add", "+", 2, lambda a, b: a + b),
    Operator("minus", "-", 2, lambda a, b: a - b),
    Operator("times", "*", 2, lambda a, b: a * b),
    Operator("divide", "/", 2, lambda a, b: a / b),
    Operator("neg", "_", 1, lambda a: -a),
]
'''

T2_README = '''\
# registry

Builds a lookup table over the operator catalogue (`operators.py`).

## Contract

- The registry indexes EVERY operator in `OPERATORS`; `len(registry) ==
  len(OPERATORS)`. Operator names are unique, so none is dropped.
- `precedence(symbol)` returns the binding precedence for an operator SYMBOL.
- `lookup(name)` returns the `Operator` with that name, or raises `KeyError`
  for an unknown name - it never substitutes a different operator.
- `is_binary(op)` is True only for two-operand (arity 2) operators.
'''

T2_REGISTRY_BUGGY = '''\
from operators import OPERATORS

# name -> Operator lookup table.
REGISTRY = {op.name: op for op in OPERATORS}

# Binding precedence.
PRECEDENCE = {"add": 1, "minus": 1, "times": 2, "divide": 2, "neg": 3}

IDENTITY = OPERATORS[0]


def lookup(name):
    """Return the Operator registered under `name`."""
    return REGISTRY.get(name, IDENTITY)


def precedence(symbol):
    """Return the binding precedence for an operator symbol."""
    return PRECEDENCE.get(symbol, 0)


def is_binary(op):
    """True iff `op` takes two operands."""
    return op.arity >= 1
'''

T2_REGISTRY_FIXED = '''\
from operators import OPERATORS

# name -> Operator. (Built from OPERATORS; names are unique.)
REGISTRY = {op.name: op for op in OPERATORS}

# Binding precedence, keyed by operator SYMBOL.
PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "_": 3}

IDENTITY = OPERATORS[0]


def lookup(name):
    """Return the Operator registered under `name`."""
    return REGISTRY[name]


def precedence(symbol):
    """Return the binding precedence for an operator symbol."""
    return PRECEDENCE.get(symbol, 0)


def is_binary(op):
    """True iff `op` takes two operands."""
    return op.arity == 2
'''


# ---------------------------------------------------------------------------
# Tree 3 - aggregator.  snippet = index_builder.py
#   D9 index undercount C9: only assignment refs fed to the index (class 1, Critical, cross-file, probeable)
#   D10 type/shape contradiction: refs are dicts {name,line}, stringified not ref["name"] (class 4, Major, cross-file, probeable)
#   D11 count_statements counts blank lines (local, Minor, in-snippet, probeable)
#   D12 too-narrow call-ref extraction: only a single bare-identifier arg captured; multi-arg/nested dropped (class 3, Major, cross-file, probeable)
# ---------------------------------------------------------------------------

T3_ANALYZER = '''\
"""Static analysis of a tiny statement list. Produces reference records."""


def parse(source):
    """Split source into non-empty, stripped statement lines."""
    return [ln.strip() for ln in source.splitlines() if ln.strip()]


def count_statements(source):
    """Return the number of STATEMENTS in source (blank lines excluded)."""
    return len(source.splitlines())


def collect_assignment_refs(statements):
    """Refs on the right-hand side of `x = <name>` assignments."""
    refs = []
    for i, st in enumerate(statements):
        if "=" in st and not st.startswith("return") and "(" not in st:
            rhs = st.split("=", 1)[1].strip()
            if rhs.isidentifier():
                refs.append({"name": rhs, "line": i})
    return refs


def collect_call_refs(statements):
    """Refs used as call arguments, e.g. `f(name)`."""
    refs = []
    for i, st in enumerate(statements):
        if "(" in st and ")" in st:
            inner = st[st.index("(") + 1:st.rindex(")")].strip()
            if inner.isidentifier():
                refs.append({"name": inner, "line": i})
    return refs


def collect_return_refs(statements):
    """Refs in `return <name>` statements."""
    refs = []
    for i, st in enumerate(statements):
        if st.startswith("return "):
            val = st[len("return "):].strip()
            if val.isidentifier():
                refs.append({"name": val, "line": i})
    return refs


def all_refs(statements):
    """EVERY reference the analyzer can see (assignment + call + return)."""
    return collect_assignment_refs(statements)
'''

T3_ANALYZER_FIXED = '''\
"""Static analysis of a tiny statement list. Produces reference records."""

import re


def parse(source):
    """Split source into non-empty, stripped statement lines."""
    return [ln.strip() for ln in source.splitlines() if ln.strip()]


def count_statements(source):
    """Return the number of STATEMENTS in source (blank lines excluded)."""
    return len([ln for ln in source.splitlines() if ln.strip()])


def collect_assignment_refs(statements):
    """Refs on the right-hand side of `x = <name>` assignments."""
    refs = []
    for i, st in enumerate(statements):
        if "=" in st and not st.startswith("return") and "(" not in st:
            rhs = st.split("=", 1)[1].strip()
            if rhs.isidentifier():
                refs.append({"name": rhs, "line": i})
    return refs


def collect_call_refs(statements):
    """Refs used as call arguments, e.g. `f(name)` or `f(g(x), y)`."""
    refs = []
    for i, st in enumerate(statements):
        if "(" in st and ")" in st:
            inner = st[st.index("(") + 1:st.rindex(")")]
            for name in re.findall(r"[A-Za-z_]\\w*", inner):
                refs.append({"name": name, "line": i})
    return refs


def collect_return_refs(statements):
    """Refs in `return <name>` statements."""
    refs = []
    for i, st in enumerate(statements):
        if st.startswith("return "):
            val = st[len("return "):].strip()
            if val.isidentifier():
                refs.append({"name": val, "line": i})
    return refs


def all_refs(statements):
    """EVERY reference the analyzer can see (assignment + call + return)."""
    return (
        collect_assignment_refs(statements)
        + collect_call_refs(statements)
        + collect_return_refs(statements)
    )
'''

T3_README = '''\
# aggregator

Builds the `unresolved` reference index over a parsed statement list.

## Contract

- `build_index(statements)` returns the index of UNRESOLVED references. It must
  be the SUPERSET of every reference the analyzer sees - assignment refs, call
  refs, AND return refs (`analyzer.all_refs`). The index size must equal the
  number of distinct unresolved references; nothing is silently dropped.
- A reference record is a dict `{"name": str, "line": int}` (see `analyzer`).
- `count_statements` counts statements, not blank lines.
'''

T3_INDEX_BUILDER_BUGGY = '''\
from analyzer import all_refs


KNOWN = {"x", "y", "total"}


def build_index(statements):
    """Return the index of unresolved references (the superset of all refs)."""
    index = []
    seen = set()
    for ref in all_refs(statements):
        name = str(ref)
        if name not in KNOWN and name not in seen:
            seen.add(name)
            index.append(name)
    return index
'''

T3_INDEX_BUILDER_FIXED = '''\
from analyzer import all_refs


KNOWN = {"x", "y", "total"}


def build_index(statements):
    """Return the index of unresolved references (the superset of all refs)."""
    index = []
    seen = set()
    for ref in all_refs(statements):
        name = ref["name"]
        if name not in KNOWN and name not in seen:
            seen.add(name)
            index.append(name)
    return index
'''


# ---------------------------------------------------------------------------
# Tree 4 - serializer.  snippet = serializer.py
#   D13 default version=1 injected, masking a missing REQUIRED field (class 5, Major, cross-file, probeable)
#   D14 count stringified: returns str(len(...)) where schema says int (class 4, Major, in-snippet, probeable)
#   D15 validate() checks only items[0], too-narrow (class 3, Minor, cross-file, probeable)
#   D16 NOVEL latent-not-triggerable: dead `version < 0` branch, unreachable (class 8, Major, in-snippet)
# ---------------------------------------------------------------------------

T4_SCHEMA = '''\
"""The record schema. `version` is REQUIRED and has NO default."""

FIELDS = {
    "version": {"type": "int", "required": True},   # no default - must be supplied
    "count": {"type": "int", "required": True},
    "items": {"type": "list", "required": True},
}


def field_type(name):
    return FIELDS[name]["type"]


def is_required(name):
    return FIELDS[name]["required"]
'''

T4_README = '''\
# serializer

Serializes an input mapping into a record per `schema.py`.

## Contract

- `to_record(data)` returns a record dict matching `schema.FIELDS`. Every
  REQUIRED field (including `version`, which has NO default) must come from the
  input; a missing required field is an error, never silently defaulted.
- `count` is an INTEGER equal to `len(items)` (schema type `int`).
- `validate(records)` validates EVERY record, not just the first.
'''

T4_SERIALIZER_BUGGY = '''\
import schema


def to_record(data):
    """Build a record dict from `data` per schema.FIELDS."""
    items = data.get("items", [])
    n = len(items)
    if n < 0:
        # Defensive clamp for a "negative count". (D16: len() is never
        # negative - this branch is DEAD and the intent is muddled; only
        # code-reading catches it, no input reaches it.)
        n = 0
    record = {
        "version": data.get("version", 1),
        "count": str(n),
        "items": list(items),
    }
    return record


def validate(records):
    """Return True iff the records satisfy the schema."""
    if not records:
        return True
    r = records[0]
    return all(name in r for name in schema.FIELDS if schema.is_required(name))
'''

T4_SERIALIZER_FIXED = '''\
import schema


def to_record(data):
    """Build a record dict from `data` per schema.FIELDS."""
    if "version" not in data:
        raise KeyError("version is required and has no default")
    items = data.get("items", [])
    record = {
        "version": data["version"],
        "count": len(items),
        "items": list(items),
    }
    return record


def validate(records):
    """Return True iff the records satisfy the schema."""
    for r in records:
        if not all(
            name in r for name in schema.FIELDS if schema.is_required(name)
        ):
            return False
    return True
'''


# ---------------------------------------------------------------------------
# Tree 5 - engine (post-"remediation").  snippet = evaluator.py
#   D17 remediation regression: safe_div returns 0 on div-by-zero (class 7, Major, in-snippet, probeable)
#   D18 cross-file contract drift: evaluator passes mode='strict' but engine.compute ignores it (class 6, Major, cross-file, probeable)
#   D19 name collision in OP_FUNCS dict literal drops an entry (class 2, Minor, in-snippet, probeable)
#   D20 NOVEL emergent: result cache key omits `precision`, returns stale results (class 8, Major, cross-file)
# ---------------------------------------------------------------------------

T5_CHANGELOG = '''\
# CHANGELOG

## Set X remediation
- Fixed: divide-by-zero in `safe_div` no longer raises.
- Added: strict mode to `evaluate` (rejects unknown operators).
'''

T5_README = '''\
# engine

Evaluates a parsed `(op, a, b)` triple.

## Contract

- `safe_div(a, b)` must signal divide-by-zero (raise), never return a wrong
  numeric answer that downstream code treats as a real result.
- `compute(op, a, b, mode="lenient")` in STRICT mode must REJECT an unknown
  operator (raise); lenient mode may pass it through.
- `evaluate(...)` caches results; the cache must not return a value computed
  under a different `precision` setting.
'''

T5_ENGINE_BUGGY = '''\
def safe_div(a, b):
    """Divide a by b, signalling divide-by-zero."""
    if b == 0:
        return 0
    return a / b


OP_FUNCS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": safe_div,
    "mul": lambda a, b: a + b,
}


def compute(op, a, b, mode="lenient"):
    """Compute `op` over a, b. In strict mode, reject an unknown operator."""
    func = OP_FUNCS.get(op)
    if func is None:
        return None
    return func(a, b)
'''

T5_ENGINE_FIXED = '''\
def safe_div(a, b):
    """Divide a by b, signalling divide-by-zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


OP_FUNCS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": safe_div,
}


def compute(op, a, b, mode="lenient"):
    """Compute `op` over a, b. In strict mode, reject an unknown operator."""
    func = OP_FUNCS.get(op)
    if func is None:
        if mode == "strict":
            raise KeyError("unknown operator: %s" % op)
        return None
    return func(a, b)
'''

T5_EVALUATOR_BUGGY = '''\
import engine

_CACHE = {}
_PRECISION = 2


def set_precision(p):
    global _PRECISION
    _PRECISION = p


def evaluate(op, a, b):
    """Evaluate via the engine in strict mode, with result caching."""
    key = (op, a, b)
    if key in _CACHE:
        return _CACHE[key]
    raw = engine.compute(op, a, b, mode="strict")
    result = round(raw, _PRECISION) if raw is not None else None
    _CACHE[key] = result
    return result
'''

T5_EVALUATOR_FIXED = '''\
import engine

_CACHE = {}
_PRECISION = 2


def set_precision(p):
    global _PRECISION
    _PRECISION = p


def evaluate(op, a, b):
    """Evaluate via the engine in strict mode, with result caching."""
    key = (op, a, b, _PRECISION)
    if key in _CACHE:
        return _CACHE[key]
    raw = engine.compute(op, a, b, mode="strict")
    result = round(raw, _PRECISION) if raw is not None else None
    _CACHE[key] = result
    return result
'''


TREES_SPEC = {
    "tree1_tokenizer": {
        "snippet": "tokenizer.py",
        "buggy": {
            "constants.py": T1_CONSTANTS,
            "README.md": T1_README,
            "tokenizer.py": T1_TOKENIZER_BUGGY,
        },
        "fixed": {
            "constants.py": T1_CONSTANTS,
            "README.md": T1_README,
            "tokenizer.py": T1_TOKENIZER_FIXED,
        },
    },
    "tree2_registry": {
        "snippet": "registry.py",
        "buggy": {
            "operators.py": T2_OPERATORS,
            "README.md": T2_README,
            "registry.py": T2_REGISTRY_BUGGY,
        },
        "fixed": {
            "operators.py": T2_OPERATORS_FIXED,
            "README.md": T2_README,
            "registry.py": T2_REGISTRY_FIXED,
        },
    },
    "tree3_aggregator": {
        "snippet": "index_builder.py",
        "buggy": {
            "analyzer.py": T3_ANALYZER,
            "README.md": T3_README,
            "index_builder.py": T3_INDEX_BUILDER_BUGGY,
        },
        "fixed": {
            "analyzer.py": T3_ANALYZER_FIXED,
            "README.md": T3_README,
            "index_builder.py": T3_INDEX_BUILDER_FIXED,
        },
    },
    "tree4_serializer": {
        "snippet": "serializer.py",
        "buggy": {
            "schema.py": T4_SCHEMA,
            "README.md": T4_README,
            "serializer.py": T4_SERIALIZER_BUGGY,
        },
        "fixed": {
            "schema.py": T4_SCHEMA,
            "README.md": T4_README,
            "serializer.py": T4_SERIALIZER_FIXED,
        },
    },
    "tree5_engine": {
        "snippet": "evaluator.py",
        "buggy": {
            "engine.py": T5_ENGINE_BUGGY,
            "evaluator.py": T5_EVALUATOR_BUGGY,
            "README.md": T5_README,
            "CHANGELOG.md": T5_CHANGELOG,
        },
        "fixed": {
            "engine.py": T5_ENGINE_FIXED,
            "evaluator.py": T5_EVALUATOR_FIXED,
            "README.md": T5_README,
            "CHANGELOG.md": T5_CHANGELOG,
        },
    },
}


def build() -> None:
    for tree, spec in TREES_SPEC.items():
        for variant in ("buggy", "fixed"):
            root = TREES / tree / variant
            root.mkdir(parents=True, exist_ok=True)
            for relpath, content in spec[variant].items():
                (root / relpath).write_text(content, encoding="utf-8")
    print(f"Built {len(TREES_SPEC)} trees (buggy + fixed) under {TREES}")


if __name__ == "__main__":
    build()

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

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

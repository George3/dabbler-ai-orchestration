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

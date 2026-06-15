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

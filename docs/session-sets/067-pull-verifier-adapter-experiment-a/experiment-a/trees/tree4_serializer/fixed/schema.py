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

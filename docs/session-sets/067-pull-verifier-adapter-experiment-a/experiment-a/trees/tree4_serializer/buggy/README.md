# serializer

Serializes an input mapping into a record per `schema.py`.

## Contract

- `to_record(data)` returns a record dict matching `schema.FIELDS`. Every
  REQUIRED field (including `version`, which has NO default) must come from the
  input; a missing required field is an error, never silently defaulted.
- `count` is an INTEGER equal to `len(items)` (schema type `int`).
- `validate(records)` validates EVERY record, not just the first.

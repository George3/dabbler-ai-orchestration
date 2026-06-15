# Path-aware cross-file catch evidence (Set 068 S2 symmetric re-grade)

For each B-arm x cross-file defect the arm is credited with (automated union), the finding(s) whose text triggers the predicate, with the matched tokens per group. Adjudication question (symmetric with the Set 067 routed audit): does the finding NAME THE ACTUAL MECHANISM?


---

## D5 (Critical, dup-key-name-collision) - tree tree2_registry

**Seeded mechanism:** operators.py defines two Operators both named 'minus' (binary subtraction and unary negation); REGISTRY = {op.name: op ...} silently drops the binary subtraction - wrong operator shipped under the name.

**Predicate:** `[["duplicate", "collision", "same name", "two operators", "overwrit", "dropped", "drops", "drop", "clobber", "conflict", "lost"], ["minus", "neg", "registry", "operator name", "name key", "unary"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] operators.py, module-level OPERATORS: the unary negation entry is created as Operator("minus", "_", 1, ...) instead of having its own unique name such as "neg". This duplicates the existing binary subtraction name "minus", violating the documented uniqueness guarantee. As a result, the catalogue cannot uniquely identify both operators by name.
    - [high] registry.py, module-level REGISTRY / lookup(name): REGISTRY is built as {op.name: op for op in OPERATORS}, so the duplicate "minus" name causes one operator to overwrite the other. With the current list order, the unary "_" operator replaces binary subtraction, so len(REGISTRY) is 4 while len(OPERATORS) is 5, and lookup("minus") returns the unary operator instead of subtraction. This is a wrong-data bug and breaks the README contract that every operator is indexed.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] operators.py, module-level OPERATORS: the unary negation operator is constructed as Operator("minus", "_", 1, ...) instead of having its own unique name. This duplicates the existing binary "minus" operator name, so names are not unique and any name-based lookup cannot distinguish binary subtraction from unary negation.
    - [high] registry.py, module-level REGISTRY construction: REGISTRY = {op.name: op for op in OPERATORS} silently overwrites one operator when names collide. With the current OPERATORS list, the second "minus" replaces the first, so len(REGISTRY) is smaller than len(OPERATORS) and the binary minus operator is dropped from the registry entirely.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] registry.py, REGISTRY initialization: REGISTRY is built as {op.name: op for op in OPERATORS}. Because OPERATORS contains two entries named "minus", the later unary operator overwrites the earlier binary one. The resulting registry does not index every operator and len(REGISTRY) is smaller than len(OPERATORS), contradicting the documented contract.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `operators.py`, two different operators are given the same name "minus": `Operator("minus", "-", 2, ...)` and `Operator("minus", "_", 1, ...)` for unary negation. This name collision is the root cause of other bugs. The comment in the file indicates the unary operator should have been named "neg".
    - [High] In `registry.py`, the `REGISTRY` is built by creating a dictionary from the `OPERATORS` list, using the operator name as the key. Due to the duplicate "minus" name in `operators.py`, the entry for the binary subtraction operator is overwritten by the unary negation operator. As a result, `lookup("minus")` will incorrectly return the unary negation operator instead of the binary subtraction one.

  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [HIGH] In `operators.py`, two operators share the name "minus". This name collision causes the binary subtraction operator to be overwritten by the unary negation operator during the construction of the `REGISTRY` map in `registry.py`. As a result, looking up "minus" in the registry will always return the unary negation operator, and the binary subtraction operator is inaccessible.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `operators.py`, two distinct operators (binary subtraction and unary negation) are given the same name "minus". This name collision causes one operator to be overwritten in the `REGISTRY` dictionary in `registry.py`, making the binary subtraction operator inaccessible by name. The unary negation operator should be renamed to "neg" to match its intended use in the `PRECEDENCE` table in `registry.py`.

---

## D6 (Major, join-key-drift) - tree tree2_registry

**Seeded mechanism:** PRECEDENCE is keyed by operator NAME ('add', 'minus'...) but precedence(symbol) is called with a SYMBOL ('+','*'); every lookup misses and returns the default 0.

**Predicate:** `[["precedence"], ["symbol", "name", "keyed", "key", "drift", "always 0", "default 0", "never match", "mismatch", "wrong key"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] registry.py, precedence(symbol): the function claims to accept an operator symbol, but PRECEDENCE is keyed by names ("add", "minus", "times", "divide", "neg") rather than symbols ("+", "-", "*", "/", "_"). Therefore valid calls such as precedence("+") or precedence("*") return 0 instead of 1 or 2. The unary operator symbol "_" also has no matching entry, and the table's "neg" key does not match any actual operator name in OPERATORS.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] registry.py, precedence(): the function is documented to accept an operator symbol, but PRECEDENCE is keyed by names ("add", "minus", "times", "divide", "neg"). As a result, valid symbol queries like precedence("+") or precedence("*") return 0 instead of their actual precedence.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] registry.py, precedence(symbol): the function claims to accept an operator symbol, but PRECEDENCE is keyed by operator names ("add", "minus", "times", "divide", "neg") rather than symbols ("+", "-", "*", "/", "_"). As a result, precedence("+") and the other real symbols return 0 instead of their documented binding powers. Unary negation is especially inconsistent: its actual symbol is "_", but the table uses "neg", which is not any operator's symbol.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [Medium] In `registry.py`, the `PRECEDENCE` dictionary has an entry for `"minus": 1` and `"neg": 3`. Because the unary operator is incorrectly named "minus", a call to `precedence("minus")` incorrectly returns `1` (the precedence for binary subtraction) instead of the correct precedence for unary negation, which would be `3`.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `operators.py`, two distinct operators (binary subtraction and unary negation) are given the same name "minus". This name collision causes one operator to be overwritten in the `REGISTRY` dictionary in `registry.py`, making the binary subtraction operator inaccessible by name. The unary negation operator should be renamed to "neg" to match its intended use in the `PRECEDENCE` table in `registry.py`.
    - [Medium] In `registry.py`, the `PRECEDENCE` dictionary is keyed by operator names, but includes the name "neg", which is not used by any operator in `operators.py`. The unary negation operator is incorrectly named "minus". This inconsistency means the precedence for unary negation cannot be looked up correctly.
    - [Low] In `registry.py`, the docstring for `precedence(symbol)` states it takes an operator symbol. However, the implementation uses the parameter to look up a key in the `PRECEDENCE` dictionary, which is keyed by operator names, not symbols (e.g., "add", not "+"). The parameter is misnamed and the docstring is incorrect.

---

## D9 (Critical, index-count-undercount) - tree tree3_aggregator

**Seeded mechanism:** analyzer.all_refs returns only collect_assignment_refs; the call refs and return refs it documents are never aggregated, so build_index is not the superset it claims (C9-class). Confirming this requires reading analyzer.py (omitted from the index_builder snippet).

**Predicate:** `[["all_refs", "analyzer"], ["assignment", "call ref", "return ref", "call-ref", "return-ref", "only returns", "only the assignment", "does not include", "drops", "missing", "not the superset", "incomplete", "subset"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py:all_refs silently drops call and return references. Its docstring says it should return every reference the analyzer can see '(assignment + call + return)', but it only returns collect_assignment_refs(statements). Any refs found by collect_call_refs() or collect_return_refs() never reach callers such as build_index.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py / all_refs: despite its docstring promising 'assignment + call + return', it returns only collect_assignment_refs(statements). Call references from collect_call_refs and return references from collect_return_refs are silently dropped, so downstream consumers never see the full reference set.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py:all_refs is documented as returning every reference the analyzer can see (assignment + call + return), but it returns only collect_assignment_refs(statements). Call references and return references are silently dropped, so any consumer relying on all_refs misses real references.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [HIGH] In `analyzer.py`, the function `all_refs` claims in its docstring to return "EVERY reference the analyzer can see (assignment + call + return)", but its implementation only returns the result of `collect_assignment_refs(statements)`, completely omitting call and return references.

  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] The `all_refs` function in `analyzer.py` claims in its docstring to return "EVERY reference the analyzer can see (assignment + call + return)". However, its implementation only returns the result of `collect_assignment_refs(statements)`, completely omitting the references found by `collect_call_refs` and `collect_return_refs`.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [] In `analyzer.py`, the `all_refs` function's docstring promises to return "EVERY reference... (assignment + call + return)", but its implementation only returns the result of `collect_assignment_refs(statements)`. It fails to include references from `collect_call_refs` and `collect_return_refs`, making it incomplete and not fulfilling its documented contract.

---

## D10 (Major, type-shape-contradiction) - tree tree3_aggregator

**Seeded mechanism:** analyzer refs are dicts {name,line}; build_index does name = str(ref) and indexes the stringified dict instead of ref['name'] - type/shape contradiction across the two surfaces.

**Predicate:** `[["index", "build_index", "ref"], ["dict", "string", "str(", "stringif", "{'name'", "\"name\"", "type", "shape", "not the name", "record", "repr"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py:all_refs silently drops call and return references. Its docstring says it should return every reference the analyzer can see '(assignment + call + return)', but it only returns collect_assignment_refs(statements). Any refs found by collect_call_refs() or collect_return_refs() never reach callers such as build_index.
    - [high] index_builder.py:build_index uses name = str(ref) instead of the reference name field. Each ref from analyzer is a dict like {'name': 'x', 'line': 0}, while KNOWN contains plain identifier strings such as 'x'. Because the code compares the dict string to KNOWN, known names are never recognized and are incorrectly reported as unresolved.
    - [high] index_builder.py:build_index deduplicates by the stringified whole ref record, not by the unresolved reference name. Distinct occurrences of the same unresolved name on different lines stringify differently, so both are kept. That violates the README requirement that the index size equal the number of distinct unresolved references; e.g. two refs {'name': 'z', 'line': 0} and {'name': 'z', 'line': 3} produce two index entries instead of one.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py / all_refs: despite its docstring promising 'assignment + call + return', it returns only collect_assignment_refs(statements). Call references from collect_call_refs and return references from collect_return_refs are silently dropped, so downstream consumers never see the full reference set.
    - [high] index_builder.py / build_index: each reference record dict is coerced with str(ref), and the function appends that string to the index. The README defines a reference record as {'name': str, 'line': int}, so this changes the public result shape from structured records to strings and silently discards typed access to name/line.
    - [high] index_builder.py / build_index: the unresolved-name filter is applied to the stringified whole record instead of the reference name. KNOWN contains bare identifiers like 'x', but the code compares values like "{'name': 'x', 'line': 0}" against KNOWN, so known references are incorrectly reported as unresolved.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] index_builder.py:build_index treats each reference record dict as the identifier name by doing name = str(ref) instead of using the reference's name field. This has multiple concrete effects: known names like x/y/total are never filtered out because "{'name': 'x', 'line': 0}" is not in KNOWN; the returned index contains serialized dict strings instead of identifier names/reference records; and repeated unresolved names on different lines are not deduplicated by name because the line number is part of the stringified dict. This violates the unresolved-index contract and produces wrong results.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [HIGH] In `analyzer.py`, the function `all_refs` claims in its docstring to return "EVERY reference the analyzer can see (assignment + call + return)", but its implementation only returns the result of `collect_assignment_refs(statements)`, completely omitting call and return references.
    - [HIGH] In `index_builder.py`, the `build_index` function processes reference objects incorrectly. The line `name = str(ref)` converts the reference dictionary (e.g., `{'name': 'z', 'line': 1}`) into its string representation, instead of extracting the variable name via `ref['name']`. This leads to the index containing stringified dictionaries instead of variable names.

  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] The `all_refs` function in `analyzer.py` claims in its docstring to return "EVERY reference the analyzer can see (assignment + call + return)". However, its implementation only returns the result of `collect_assignment_refs(statements)`, completely omitting the references found by `collect_call_refs` and `collect_return_refs`.
    - [High] In `index_builder.py`, the `build_index` function processes reference objects from the analyzer. It incorrectly uses `name = str(ref)` to get the reference's name. Since `ref` is a dictionary (e.g., `{'name': 'var', 'line': 1}`), this converts the entire dictionary into a string instead of extracting the variable name from the 'name' key with `ref['name']`. This causes the final index to be populated with useless strings like `"{'name': 'var', 'line': 1}"`.
    - [Medium] The `collect_call_refs` function in `analyzer.py` can only parse function calls with a single argument that is a simple identifier (e.g., `f(x)`). It fails for calls with no arguments, multiple arguments, or expressions as arguments because it checks if the entire substring between the parentheses `isidentifier()`.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [] In `index_builder.py`, the `build_index` function incorrectly extracts a reference name by using `str(ref)` on a dictionary object. It should use `ref['name']`. As a result, the function returns a list of stringified dictionaries (e.g., `["{'name': 'foo', 'line': 1}"]`) instead of a list of unique names (e.g., `['foo']`).
    - [] In `analyzer.py`, the `all_refs` function's docstring promises to return "EVERY reference... (assignment + call + return)", but its implementation only returns the result of `collect_assignment_refs(statements)`. It fails to include references from `collect_call_refs` and `collect_return_refs`, making it incomplete and not fulfilling its documented contract.

---

## D11 (Minor, local-logic) - tree tree3_aggregator

**Seeded mechanism:** count_statements returns len(source.splitlines()), counting blank lines despite documenting blank lines are excluded.

**Predicate:** `[["count_statements"], ["blank", "empty", "whitespace", "splitlines", "strip", "includes blank", "blank line"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [medium] analyzer.py:count_statements violates the documented contract to count statements with blank lines excluded. It currently returns len(source.splitlines()), so blank lines are counted as statements. For example, source 'a\n\n b\n' is reported as 3 even though parse() would yield only 2 statements.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [medium] analyzer.py / count_statements: the function claims to count statements with blank lines excluded, but it returns len(source.splitlines()), which counts blank lines that occur inside the source. For example, 'a\n\n b' yields 3 lines but only 2 statements. This violates both the function docstring and README contract.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [medium] analyzer.py:count_statements violates its own docstring and the README contract. It returns len(source.splitlines()), which counts blank lines as statements. For example, source "a\n\n b\n" produces 3 instead of 2 non-empty statements.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [MEDIUM] In `analyzer.py`, the `count_statements` function's docstring states "blank lines excluded", but its implementation `return len(source.splitlines())` includes blank lines in its count, violating its documented behavior.

  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [Medium] The docstring for `count_statements` in `analyzer.py` states that it returns the number of statements with "blank lines excluded". The implementation, `len(source.splitlines())`, does not exclude blank lines, counting them as statements. This violates the function's own contract.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [] In `analyzer.py`, the `count_statements` function's docstring claims that it excludes blank lines from the count. However, the implementation `len(source.splitlines())` counts every line, including blank ones, which violates its documented behavior.

---

## D12 (Major, too-narrow-validation) - tree tree3_aggregator

**Seeded mechanism:** collect_call_refs only captures a single bare-identifier argument (inner.isidentifier()); multi-argument and nested call refs are silently dropped.

**Predicate:** `[["collect_call_refs", "call ref", "call argument", "call-arg", "function call"], ["nested", "multi", "comma", "multiple argument", "two argument", "single identifier", "only one", "dropped", "missed", "silently", "isidentifier"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py:all_refs silently drops call and return references. Its docstring says it should return every reference the analyzer can see '(assignment + call + return)', but it only returns collect_assignment_refs(statements). Any refs found by collect_call_refs() or collect_return_refs() never reach callers such as build_index.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py / all_refs: despite its docstring promising 'assignment + call + return', it returns only collect_assignment_refs(statements). Call references from collect_call_refs and return references from collect_return_refs are silently dropped, so downstream consumers never see the full reference set.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] analyzer.py:all_refs is documented as returning every reference the analyzer can see (assignment + call + return), but it returns only collect_assignment_refs(statements). Call references and return references are silently dropped, so any consumer relying on all_refs misses real references.

**B2: CREDITED** (cross-file)


  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [Medium] The `collect_call_refs` function in `analyzer.py` can only parse function calls with a single argument that is a simple identifier (e.g., `f(x)`). It fails for calls with no arguments, multiple arguments, or expressions as arguments because it checks if the entire substring between the parentheses `isidentifier()`.

---

## D13 (Major, default-injection) - tree tree4_serializer

**Seeded mechanism:** to_record uses data.get('version', 1), injecting a default for a field schema.py declares REQUIRED with no default - a missing required field is silently fabricated.

**Predicate:** `[["version", "to_record"], ["default", "inject", "required", "missing", "masks", "fabricat", "silently", "get(\"version\"", "get('version'", "substitut", "no default"]]`


**B1: CREDITED** (cross-file)


  ### B1 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] serializer.py:to_record() silently defaults the required `version` field to `1` via `data.get("version", 1)`. README.md and schema.py both state that `version` is required and has no default, so a missing `version` must be rejected rather than fabricated.
    - [high] serializer.py:to_record() silently defaults the required `items` field to `[]` via `data.get("items", [])`. `items` is marked `required` in schema.py, and README.md says missing required fields are errors, never silently defaulted. This turns missing input into a seemingly valid empty record with `count` 0.

  ### B1 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] serializer.py:to_record silently supplies version=1 when data lacks "version" via data.get("version", 1). README.md and schema.py both state that version is required and has no default, so a missing version must be rejected rather than defaulted.
    - [high] serializer.py:to_record silently supplies items=[] when data lacks "items" via data.get("items", []). items is marked required in schema.FIELDS, so this injects a missing required field instead of reporting an error.

  ### B1 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [high] serializer.py::to_record silently injects version=1 when the input omits "version" (data.get("version", 1)). README.md and schema.py both say version is required and has no default, so a missing version must raise an error instead of being fabricated.
    - [high] serializer.py::to_record silently injects items=[] when the input omits "items" (data.get("items", [])). items is marked required in schema.FIELDS, so this turns a missing required field into a valid-looking record instead of reporting an error.
    - [high] serializer.py::validate checks only that required field names are present; it never verifies the schema-declared field types. As a result, records like {"version": "x", "count": "2", "items": []} pass validation even though schema.py requires version and count to be ints.

**B2: CREDITED** (cross-file)


  ### B2 k1
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `to_record`, the `version` field is documented as REQUIRED with NO default. The code violates this by silently injecting a default value of `1` if `version` is missing from the input data, using `data.get("version", 1)`.
    - [Medium] In `to_record`, the `items` field is marked as required in `schema.py`. The code violates this by providing an empty list (`[]`) as a default when `items` is not in the input data, using `data.get("items", [])`. The contract states required fields must come from the input.

  ### B2 k2
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `serializer.py`, the `to_record` function violates the schema's explicit contract by providing a default value for a required field. The `schema.py` file states that the "version" field is required and has no default, but `to_record` uses `data.get("version", 1)`, silently injecting a `version` if none is provided. This can lead to incorrect data being created without any error indication.
    - [Medium] The `validate` function in `serializer.py` performs incomplete validation. It only checks for the presence of required field names (e.g., "version", "count"). It fails to check if the values for these fields match the types specified in the schema (e.g., `int` for "version" and "count"). This allows records with structurally correct keys but incorrect data types to pass as valid.

  ### B2 k3
  - SINGLE-FINDING match (mechanism in one finding):
    - [High] In `to_record`, the `version` field is given a default value of 1 (`data.get("version", 1)`). This violates the explicit contract in `README.md` and `schema.py` which states that `version` is a required field with no default and must be supplied by the caller.
## Verdict

**NOT VERIFIED**

### F1 → RESOLVED
- The schema now validates `transcript` only inside the `if evidenceTier == REPRODUCED` `then` block.
- For `ASSERTED` / `HYPOTHESIS`, schema leaves `transcript` untyped and ignored; Python `validate_finding_evidence()` also ignores it.
- `TestEvidenceParity` explicitly covers stray malformed transcripts on both `ASSERTED` and `HYPOTHESIS` and asserts both validators accept them.

### F2 → RESOLVED
- Python now rejects:
  - `commandId` / `templateId` when present but not a non-empty string,
  - `args` when present but not `object|array`,
  - `replay.exitCode` when present but not `int|null` and specifically rejects `bool`.
- The added unit tests exercise these cases:
  - `templateId = 7`
  - `commandId = ""`
  - `args = 7`
  - `replay.exitCode = True`
- The parity tests also assert schema/Python agreement on these malformed `REPRODUCED` transcripts.

### F3 → NOT RESOLVED
**Issue →** The old inaccurate “Python-only XOR / meta-oracle” claim is gone, and the schema now correctly enforces XOR and `const: true`; however the replacement claim that the **only** Python-only rule is replay-hash equality is still not honest, because Python and schema still diverge on whitespace-only string fields.

**Location →**
- Python: `ai_router/evidence_protocol.py` → `_nonempty_str()` uses `value.strip()`, so whitespace-only strings are invalid.
- Schema: `docs/path-aware-critique.schema.json`
  - `$defs/EvidenceTranscript/properties/pinnedRef`
  - `$defs/EvidenceTranscript/properties/commandId`
  - `$defs/EvidenceTranscript/properties/templateId`
  - `$defs/EvidenceTranscript/properties/outputHash`
  - `$defs/EvidenceEntrypoint/properties/ref`
  - `$defs/EvidenceReplay/properties/outputHash`
  All use only `minLength: 1`, so `" "` is schema-valid.

**Fix →**
- Either tighten the schema for all `_nonempty_str`-backed fields to reject whitespace-only values, or relax `_nonempty_str()` to match `minLength: 1`.
- Until that is done, the docs/schema must not claim replay-hash equality is the only Python-only rule.

### F4 → RESOLVED
- `test_evidence_protocol.py` does exercise the named regression behaviors.
- `test_path_aware_critique_schema.py` does assert dual-validation agreement for:
  - stray transcript on `ASSERTED` / `HYPOTHESIS`,
  - both ids present,
  - wrong-typed/invalid optional fields,
  - non-pristine checkout,
  - `agent_harness`.
- The added tests are real parity tests, not one-sided tests.

### No-new-divergence check
- `oneOf` correctly rejects both-present and neither-present for `commandId` / `templateId`.
- Both `const: true` constraints correctly reject `pristineCheckout: false`.
- No residual stale echo of the old “Python-only XOR / meta-oracle” claim remains in the provided docs/schema.

### Blocking reason
**Issue →** Python and JSON Schema still do **not** agree on every transcript case except replay-hash equality.

**Location →** Whitespace-only values in schema `minLength: 1` fields vs Python `_nonempty_str()`.

**Fix →** Align schema and Python on whitespace-only string handling, then the “only Python-only rule is replay-hash equality” claim becomes true.
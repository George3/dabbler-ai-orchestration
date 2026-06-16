ISSUES_FOUND

- **Major**  
  **Issue** → A structurally corrupt but JSON-parseable `activity-log.json` can silently disarm a `required` contract gate and can make `validate_contract_gate()` raise, violating the intended "never raises" and loud-warning behavior. Examples: top-level `[]`, `{}`, or `{"entries": "bad"}`. `read_contract_gate()`/`has_contract_gate_record()` call `.get()` and iterate entries assuming object/list shape; `contract_gate_record_unreadable()` only treats JSON decode / I/O failure as corrupt, so these malformed-but-parseable cases are not warned about. In `close_session`, that exception is swallowed by the fail-open guard, so the set can close with no gate enforcement and no warning.  
  **Location** → `ai_router/contract_gate.py:read_contract_gate`, `ai_router/contract_gate.py:has_contract_gate_record`, `ai_router/contract_gate.py:contract_gate_record_unreadable` (surfacing in `ai_router/close_session.py` contract-gate block).  
  **Fix** → Validate activity-log structure immediately after `json.load()`: require a top-level `dict`, require `entries` to be a `list`, and ignore/skip non-`dict` entries when scanning. Treat any other shape as corrupt. Specifically:  
  - `read_contract_gate()` should return `DEFAULT_CONTRACT_GATE` without raising.  
  - `has_contract_gate_record()` should return `False` without raising.  
  - `contract_gate_record_unreadable()` should return `True` for malformed-but-parseable structure so `close_session` emits the intended non-blocking warning.  
  - `record_contract_gate()` should also shape-check and raise a controlled error instead of failing with `AttributeError` on malformed logs.
## Re-verify

- **Issue** → Round-1 #1: `providerEqual` / `modelEqual` were hard-coded `True`  
  **Location** → `run_dual_surface()`, the post-arm attestation block  
  **Fix** → **Resolved.** The attestation is now built after both arms complete, `providerEqual` / `modelEqual` are derived from the requested `provider` / `model` versus `push_result.provider/model` and `pull_result.provider/model`, the attestation records requested/push/pull identities, and `UnequalArmsError` is raised only after the arms report identities.

- **Issue** → Round-1 #2: pull framing was classified from rendered instruction  
  **Location** → `run_dual_surface()` `pull_template` / `pull_instruction` handling, plus `load_pull_template()`  
  **Fix** → **Resolved.** Pull framing is now classified from raw `pull_template`; `pull_instruction` is execution-only. The framing gate runs before `run_push()` and `run_pull()`, so the framing-refusal path still spends no metered LLM call.

- **Issue** → Round-1 #3: `committed_ref` overstated provenance when `head_ref` was empty  
  **Location** → `run_dual_surface()`, `committed_ref` assignment and docstring  
  **Fix** → **Resolved.** It now records `f"{base_ref}..{head_ref}"` when pinned and `f"{base_ref}..WORKTREE"` otherwise, and the docstring matches that behavior.

- **Issue** → **New defect introduced by fix #2:** pull framing attestation can drift from the instruction actually executed  
  **Location** → `run_dual_surface()`: `pull_template` defaults independently from `pull_instruction`, while framing is classified only from `pull_template`  
  **Fix** → As written, a caller can supply a custom `pull_instruction` without a matching `pull_template`; the gate will classify the shipped raw template, may attest `framingEqual=True` / `bothAdversarial=True`, and then execute a weaker or different instruction. That is a new fail-open / attestation-honesty bug. Require `pull_template` whenever `pull_instruction` is overridden, or render `pull_instruction` from the exact raw template being classified inside this function. Also record a truthful template identifier instead of always hard-coding `"path-aware-critique.md"` in that path.
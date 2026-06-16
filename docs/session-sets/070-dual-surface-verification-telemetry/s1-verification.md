1. **Issue:** Provider/model equality is not actually enforced, and the attestation can report equality when it is false.  
   **Location:** `ai_router/dual_surface_verify.py` → `run_dual_surface()`, at:
   - `attestation = {"providerEqual": True, "modelEqual": True, ...}`
   - the `require_equal` gate, which checks only `framing_equal` / `bothAdversarial`
   - the later use of `pull_res.provider` / `pull_res.model` without comparing them to the requested pair  
   **Fix:** Derive `providerEqual` and `modelEqual` from actual arm outputs, not from assumption. Compare the requested push pair to `pull_res.provider` / `pull_res.model` (and include provider/model in `_PushRaw` if you want the attestation to reflect actual push execution too). Raise `UnequalArmsError` when `require_equal=True` and either comparison fails. Do not hard-code these attestation fields to `True`.

2. **Issue:** Pull framing strength is classified from the rendered instruction, not the raw template text, so task/spec content can spoof an “adversarial” label and bypass the equal-framing invariant.  
   **Location:** `ai_router/dual_surface_verify.py` → `run_dual_surface()`:
   - `pull_instruction = build_instruction(set_dir)`
   - `classify_framing_strength(pull_instruction)`  
   **Fix:** Classify pull framing from the raw `path-aware-critique.md` template bytes/text before any session-specific interpolation. Use the rendered instruction only for execution. If needed, add a dedicated loader for the raw pull template or make `build_instruction()` expose both raw-template text and rendered instruction.

3. **Issue:** The runner does not enforce the “same committed state” contract, and its provenance becomes false when `head_ref == ""`.  
   **Location:** `ai_router/dual_surface_verify.py` → `run_dual_surface()`:
   - `head_ref: str = ""`
   - `committed_ref = "..".join(p for p in (base_ref, head_ref) if p) or base_ref`
   - `_dispatch_get_diff(diff_cfg)` for the push arm
   - `run_pull(sandbox_dir, pull_instruction, ...)` for the pull arm  
   **Fix:** Either enforce a real committed snapshot for both arms or stop claiming one. If committed-state parity is required, reject empty `head_ref`, materialize/validate `sandbox_dir` at the requested ref, and only then run both arms. At minimum, when `head_ref == ""`, record provenance as something like `"{base_ref}..WORKTREE"` instead of `base_ref`, because the current `committed_ref` field misstates what the push arm actually reviewed.
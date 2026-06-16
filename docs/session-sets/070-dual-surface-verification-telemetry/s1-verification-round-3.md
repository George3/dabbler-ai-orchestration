- **Issue →** Pull-arm attestation/execution drift is **still possible**. The new guard only forbids **single-sided** override, but it still allows a caller to supply an adversarial `pull_template` **and** a different/weaker `pull_instruction` together. The attestation/classification then uses `pull_template` while execution uses `pull_instruction`, so `(a)` is **not closed** and `(b)` remains **fail-open**. `(c)` the push arm is drift-free in this runner because `push_template` is the single prompt source both classified and executed.
- **Location →** `run_dual_surface`: the pairing guard
  ```python
  if (pull_template is None) != (pull_instruction is None):
      raise DualSurfaceError(...)
  ```
  followed by
  ```python
  pull_framing = ArmFraming(
      strength=classify_framing_strength(pull_template),
      ...
  )
  ```
  and later
  ```python
  pull_res: PullResult = run_pull(
      sandbox_dir,
      pull_instruction,
      ...
  )
  ```
- **Fix →** Remove independent `pull_instruction` override from this API, or make `run_dual_surface` derive `pull_instruction` itself from `pull_template` via a single renderer and execute only that derived value. If both parameters must remain, enforce exact correspondence by rendering from `pull_template` and rejecting any caller-supplied `pull_instruction` that does not exactly match the rendered result.
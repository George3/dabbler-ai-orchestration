# Session 1 close-out — Steelman push + the dual-surface comparison core

**Verdict:** VERIFIED (cross-provider, gpt-5-4, Round 4 after a 4-round
devil's-advocate loop). **Suite:** full `ai_router` green — 1988 passed, 5
skipped (the 5 are the Set 069 S4 real-Podman-on-Windows by-design skips).

## What shipped

- **Steelman push.** `ai_router/prompt-templates/verification.md` upgraded from
  the weak *"evaluate it objectively"* framing to the strong devil's-advocate
  framing pull already uses, so the standing per-session push runs at its
  strongest form (L-069-2). The machine contract
  (`build_verification_prompt` / `parse_verification_response`) is preserved.
  `test_verification_framing.py` pins the framing so a future silent weakening
  is caught.
- **contractGate-seed fix.** `start_session` now captures the `contractGate`
  seed at set start the same way it already captures `pathAwareCritique`
  (`--contract-gate` flag + `_capture_contract_gate`, delegating to the existing
  `resolve_and_record_contract_gate`). This closes the Set 069 S6 gap (the
  contractGate close-out gate had silently no-op'd). This set's own
  `contractGate: advisory` seed is now durably recorded.
- **Dual-surface runner.** `ai_router/dual_surface_verify.py` runs the push
  (snippet-fed, repo-blind) and pull (repo-reading, agentic) surfaces over the
  same committed state with provider + model + framing held **equal**, and
  returns both raw verdicts plus a recorded equal-arms attestation. **No merge**
  yet — that is Session 2.

## Why four verification rounds

Each round found genuinely new substance, not echoes of an accepted fix
(contrast L-065-1's echo-chasing): R1 caught a hard-coded equality attestation, a
spoofable framing classification, and a misstated provenance label; R2 caught a
two-input drift introduced by the R1 fix; R3 (devil's advocate) showed even a
paired guard left two divergent inputs; R4 verified the final **single source of
truth** design (one `pull_template` per arm — framing classified from its
unfilled body, instruction rendered from the same body). The end state — equality
*measured* not assumed, framing un-spoofable, one prompt source per arm — is
materially better than where R1 started.

## Next

Session 2: the provenance merge + the fair-shake telemetry + the dual-surface
verificationMode wiring. Routed recommendation (gemini-pro): claude/sonnet-4-6,
medium effort, with a caveat that the L-066-1 validator-parity trap is the
headline S2 risk (opus is a defensible upgrade). Operator decides.

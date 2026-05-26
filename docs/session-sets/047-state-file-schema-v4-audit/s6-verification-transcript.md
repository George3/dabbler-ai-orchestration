## Critical

- **Issue** → Per-session orchestrator close-out semantics are documented backwards. The doc says completed sessions clear `sessions[N].orchestrator` and that non-null orchestrator is valid only for `status == "in-progress"`, but the shipped writers preserve per-session orchestrator on close as historical metadata.  
  **Location** → `docs/session-state-schema.md` — `sessions[] — the canonical lifecycle ledger`; `Check-out / check-in (preserved from Set 033, enforcement disabled)`; `Invariants — the 8 v4 rules`; `Lightweight tier — one-field-flip worked example`; `Worked examples (v4)`; `Tier expectations`  
  **Fix** → Rewrite these sections so `sessions[N].orchestrator` is historical per-session attribution that may remain populated after close; document that only the **derived top-level** `orchestrator` is null when no session is in progress; remove the clear-on-close steps/rule and update examples to match the actual writer output.

- **Issue** → The reader contract conflates normalized-state fields with `get_progress()`/`read_progress()` output and incorrectly claims plan-less states work through `get_progress()`. In code, `normalize_to_v4_shape()` returns the derived top-level fields, but `get_progress()`/`readProgress()` only return progress counts/current/next/between-sessions and reject empty `sessions[]`.  
  **Location** → `docs/session-state-schema.md` — `Reader contract — every reader uses the normalize-to-v4 shim`; `Derived values — the shim's read-view`; `Plan-less carve-out`  
  **Fix** → Split the contract into two layers: (1) normalized state dict output from `normalize_to_v4_shape()` / `normalizeToV4Shape()` and (2) `ProgressView` output from `get_progress()` / `readProgress()`. Remove the claim that `ProgressView` includes `startedAt`/`completedAt`/`orchestrator`/`verificationVerdict`, and document plan-less handling as a shim-level shape with caller-side fallback rather than a `get_progress()` success case.

- **Issue** → `verificationVerdict` is documented as a strict 2-token enum, but the shipped implementation does not enforce that and the bundled live `session-state.json` already uses `ISSUES_FOUND_RESOLVED_IN_FLIGHT`.  
  **Location** → `docs/session-state-schema.md` — `v4 schema shape`; `sessions[] — the canonical lifecycle ledger`  
  **Fix** → Widen the documented field type to match reality (`string | null`, with known/common tokens listed), or enumerate every currently shipped token seen on disk.

## Important

- **Issue** → Derived top-level field semantics are misstated. `startedAt` is not derived from the earliest non-null session timestamp, `completedAt` is not the latest non-null per-session timestamp, and derived `lifecycleState` is not synthesized as `"closed"` for cancelled v4 inputs.  
  **Location** → `docs/session-state-schema.md` — `Top-level fields that v3 carried but v4 drops`; `Derived values — the shim's read-view`; `lifecycleState (derived, never written)`; `Reading a v3 file (compat path)`  
  **Fix** → Document the actual shim behavior: `startedAt` comes from the in-progress session if any, else the most-recently-completed session; `completedAt` is derived only when top-level `status == "complete"`; derived `lifecycleState` is currently synthesized for `in-progress` and `complete`, not `cancelled`.

- **Issue** → The doc says there is “exactly one reader path” through the normalize shim, but shipped code has exceptions: `readCancellationState()` reads raw `state.status`, the TS import path named in the doc is wrong, and the Python lazy-synth helper name is wrong.  
  **Location** → `docs/session-state-schema.md` — `Reader contract — every reader uses the normalize-to-v4 shim`; `When this applies`; `Cancel / restore > Canonical reader`  
  **Fix** → Narrow the “single reader path” claim to progress/state-normalization consumers; explicitly carve out `readCancellationState()` as a status-only reader; change the TS reference to `tools/dabbler-ai-orchestration/src/utils/progress.ts`; rename `ensure_state_file` to `ensure_session_state_file`.

- **Issue** → The support-horizon statement exceeds the audit-locked spec. The doc says v1/v2/v3 read support is “permanent,” but `spec.md` §3.4 only locks the shim for the post-ship transition window and explicitly schedules removal in a follow-on set.  
  **Location** → `docs/session-state-schema.md` — `v4 is canonical; v1/v2/v3 read support is permanent`  
  **Fix** → Reword to match the spec: v3 compatibility remains during the transition window, and any shim removal must land in a future explicitly-scoped set.

- **Issue** → The Session 6 change-log summary records the nonexistent orchestrator invariant as shipped work, so the close-out record conflicts with Session 4’s actual writer behavior and the bundled live state example.  
  **Location** → `docs/session-sets/047-state-file-schema-v4-audit/change-log.md` — `Session 6 — Schema-doc + authoring-guide revision + close-out + publish`  
  **Fix** → Replace the “rule 8 pins `sessions[N].orchestrator` non-null IFF `status == in-progress`” summary with the actual shipped behavior: per-session orchestrator is preserved historically, while the derived top-level orchestrator is only populated for the in-progress session.

## Nice-to-have

- **Issue** → “`lastActivityAt` is set on every write” overstates the implementation; the shipped writer bumps it on session start / same-holder reattach, not on close writes.  
  **Location** → `docs/session-state-schema.md` — `Check-out / check-in (preserved from Set 033, enforcement disabled)`  
  **Fix** → Rephrase to “set on session start and bumped on same-holder reattach writes.”

- **Issue** → “Top-level `status` uses the same vocabulary as the per-session ledger” is misleading because top-level allows `"cancelled"` while per-session explicitly does not.  
  **Location** → `docs/session-state-schema.md` — `Status — the canonical glossary > Top-level status`  
  **Fix** → Reword to say the vocabularies mostly align, except set-level `"cancelled"` remains reserved from the per-session ledger in v4.
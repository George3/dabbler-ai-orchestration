**VERIFIED**

- **Minor**  
  **Issue →** The deferred-repo note cites “§10” but only links `greenfield-matrix-protocol.md`; §10 is in `docs/verification-surface-strategy.md`, so the reference is inaccurate.  
  **Location →** `dabbler-access-migration-orchestrator` commit `f7547a4`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (“See the canonical protocol §5 (D4) / §10: …greenfield-matrix-protocol.md”).  
  **Fix →** Either remove “/ §10” or add a separate link/reference to `docs/verification-surface-strategy.md` §10.

- **Minor**  
  **Issue →** The close-out says Set 076 is the “un-gated fast-follow,” but the routed recommendation file defines an explicit prerequisite/gate (“Final approval of the seeded-recall experimental design and the initial defect corpus”). That is an internal contradiction.  
  **Location →** `docs/session-sets/075-greenfield-finding-power-pilot/change-log.md` (Session 2, routed next-set bullet) vs. `docs/session-sets/075-greenfield-finding-power-pilot/s2-next-set.md` (“Prerequisite / Gate”).  
  **Fix →** Reword the change-log to say the seeded-recall lane is not gated on consumer telemetry accumulation, while preserving the design-approval prerequisite.
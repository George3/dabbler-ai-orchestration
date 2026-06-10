# ISSUES FOUND

- **Issue** → Original Issue 2 is correctly resolved. The new `fileExists(p) = exists(p) && !isDirectory(p)` logic fixes the false-positive directory case for engine files and `project-plan.md`, and the added unit test covers both step 1 and step 2 regressions.  
  **Location** → `src/utils/gettingStartedDetection.ts`, `src/test/suite/gettingStartedDetection.test.ts`  
  **Fix** → None.

- **Issue** → Original Issue 3 is correctly resolved. `SnapshotPayload.gettingStarted` is now optional, which matches the runtime/backward-compat behavior the client already implements for `undefined`/`null`.  
  **Location** → `src/types/sessionSetsWebviewProtocol.ts`, `media/session-sets-tree/client.js`  
  **Fix** → None.

- **Issue** → Original Issue 1’s disposition is acceptable for Session 1. Keeping the mode flip keyed to “renderable session-set rows exist” (`hasAnySets`) is a coherent design choice: it avoids switching to a list view that cannot render any rows yet, while still letting D3 step 3 use the looser numbered-directory probe as a progress signal. That reasoning is sound for this session’s scope.  
  **Location** → `src/providers/CustomSessionSetsView.ts`  
  **Fix** → None.

- **Issue** → New completeness defect: the Getting Started completion state now depends on files/directories that are not shown to participate in the view’s refresh/watch set, so the UI can stay stale after step 1/step 2 changes, and after a bare `docs/session-sets/NNN-*` directory appears for D3 step 3. The new pure detection code is correct, but the host integration does not demonstrate any trigger that recomputes it when those inputs change.  
  **Location** → `src/providers/CustomSessionSetsView.ts` integration of `buildGettingStarted(all)`; existing refresh model/commentary indicates refresh is driven by session-set materialization (`spec.md`, etc.), not by `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `docs/planning/project-plan.md` / `.venv/.../ai_router` / numbered-dir creation.  
  **Fix** → Add refresh triggers for all Getting Started detection inputs, or explicitly rebuild the snapshot after the relevant scaffold/import actions complete. At minimum, ensure changes to these paths invalidate/re-render the view:
  - `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`
  - `docs/planning/project-plan.md`
  - `.venv/**/site-packages/ai_router`
  - `docs/session-sets/*` directory create/delete for the D3 step-3 dir probe
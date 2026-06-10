1. **Issue** → The getting-started → list flip is keyed off scanned `SessionSet[]` (`all.length > 0`), not off the D3/session-1 predicate of “a `docs/session-sets/NNN-*` directory exists,” so the approved “new numbered set dir appears ⇒ flip to list” behavior is not guaranteed. If the scanner needs more than the directory to materialize a `SessionSet`, step 3 can be complete while the Explorer stays in getting-started.  
   **Location** → `src/providers/CustomSessionSetsView.ts`, `buildGettingStarted()` passing `all.length > 0` into `computeGettingStarted(...)`.  
   **Fix** → Derive mode selection from the same raw numbered-directory predicate used for D3 step 3 (or a dedicated `hasSessionSetDirs` probe), not only from scanned rows. At minimum, make the mode input `all.length > 0 || detectCompletion(root, fsi).sessionSetsPresent`.

2. **Issue** → Step 1 and step 2 can be falsely marked complete by directories named like files. `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or `docs/planning/project-plan.md` only need to “exist” today; they do not need to be files.  
   **Location** → `src/utils/gettingStartedDetection.ts`, `engineFilesPresent()` and `planPresent: fsi.exists(...)` inside `detectCompletion()`.  
   **Fix** → Require non-directory entries for those paths (`exists && !isDirectory`), or extend `DetectionFs` with `isFile()`. Add unit tests proving directories do **not** satisfy the engine-file or project-plan checks.

3. **Issue** → The protocol type does not model the backward-compat case it claims to support. The client correctly handles `gettingStarted` being absent, but `SnapshotPayload` says the field is always present (or `null`), so the type contract and runtime contract diverge.  
   **Location** → `src/types/sessionSetsWebviewProtocol.ts`, `SnapshotPayload.gettingStarted`.  
   **Fix** → Change the field to optional: `gettingStarted?: GettingStartedPayload | null;` and keep the existing client fallback for `undefined`.
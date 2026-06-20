# Remediation report - dabbler-platform

- committed ref: 741b00d..WORKTREE
- generated at: 2026-06-20T19:16:11.822126-04:00
- provenance complete: False
- NOTE: provenance is incomplete (pushUnkeyed=5, pullUnkeyed=2); a defect both surfaces caught but neither keyed appears as two separate entries.
- findings: 7

## 1. [Major] Completeness / Correctness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) `WriteLocalNugetConfig` called but not defined in the diff and implausibly pre-existing
- **Category:** Completeness / Correctness
- **Severity:** Major

**Details:**

- **Violation:** The new test method `CrudSliceTool_AcquiredFromFeed_GeneratesSliceThatBuildsClean` calls `WriteLocalNugetConfig(tempDir, PackOutputDir)` \u2014 a method that writes a local-feed NuGet config into the temp directory. This method is not present anywhere in the diff's additions to `PackagingSmokeTests.cs`. The diff adds exactly four helpers: `LocateSmokeAppFixture`, `LocateSmokeSchema`, `ExtractVersion`, and `CopyDirectory`. `WriteLocalNugetConfig` is absent.

- **Impact:** If `WriteLocalNugetConfig` does not exist as a pre-existing method in the file (outside the diff), the project **will not compile**, making the entire deliverable non-functional. The method's purpose \u2014 writing a `nuget.config` that points restore at the local pack-output feed \u2014 is central to the consumer-validation gate's correctness (without it, `dotnet restore` cannot find `Dabbler.*` packages from the local feed and the build step will fail with NU1101). This changes the merge decision: the test cannot pass without this method.

- **Evidence:** The diff's helper section is bounded by `private static int FindFreePort()` (the pre-existing boundary marker shown in context). The four new helpers are added above it. `WriteLocalNugetConfig` is not among them, not shown as pre-existing context, and is a concept specific to this session's consumer-validation gate (local-feed isolation). The test commentary explicitly describes the nuget.config as the mechanism: *"NuGet discovers it by walking up from the project dir"* \u2014 proving the method is load-bearing, not decorative.

---

###

## 2. [Major] Completeness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) `README.md` declared in `.csproj` but absent from the diff
- **Category:** Completeness
- **Severity:** Major

**Details:**

- **Violation:** `Dabbler.CrudSlice.csproj` adds:
  ```xml
  <PackageReadmeFile>README.md</PackageReadmeFile>
  ...
  <None Include="README.md" Pack="true" PackagePath="\" />
  ```
  The file `tools/Dabbler.CrudSlice/README.md` does not appear in the diff's changed paths, which are exhaustively listed at the top of the response.

- **Impact:** `dotnet pack` with a declared `<None Include="README.md" Pack="true" .../>` referencing a non-existent file produces a build error (`NETSDK1152` or MSBuild file-not-found error), failing the `tools/pack.ps1` step entirely. This means the `Dabbler.CrudSlice.Tool` nupkg cannot be produced, which means the smoke test's `Skip.If(toolNupkg is null, ...)` guard fires and the consumer-validation gate is never exercised \u2014 defeating the session's primary deliverable.

- **Evidence:** The changed-paths list is: `Dabbler.Publish.slnf`, `session-events.jsonl`, `session-state.json`, `PackagingSmokeTests.cs`, `Dabbler.CrudSlice.csproj`, `Program.cs`, `TemplatePreflight.cs`, `pack.ps1`. No `README.md` appears. The `.csproj` unambiguously requires it for pack to succeed.

---

## 3. [Major] Completeness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) ** Missing `README.md` file
- **Category:** Completeness
- **Severity:** Major
- **Details:**
  - **Violation:** `tools/Dabbler.CrudSlice/Dabbler.CrudSlice.csproj` adds `<PackageReadmeFile>README.md</PackageReadmeFile>` and `<None Include="README.md" Pack="true" PackagePath="\" />`, both of which require a `tools/Dabbler.CrudSlice/README.md` file to exist at pack time.
  - **Impact:** `dotnet pack` will fail for this project with a missing-file error (MSBuild will complain the `None` item doesn't exist, or NuGet will fail to embed it). Since `tools/pack.ps1` now includes `tools/Dabbler.CrudSlice/Dabbler.CrudSlice.csproj` in `$LibraryProjects`, every pack run breaks. The smoke test depends on the pack output existing; it will always skip. This changes the merge decision: the session's primary deliverable (a packable tool) cannot actually be packed.
  - **Evidence:** The diff adds both `<PackageReadmeFile>README.md</PackageReadmeFile>` and `<None Include="README.md" Pack="true" PackagePath="\" />` to the `.csproj`, but there is no `diff --git a/tools/Dabbler.CrudSlice/README.md b/tools/Dabbler.CrudSlice/README.md` anywhere in the unified diff. The changed paths list does not include any `README.md`. The file is referenced but absent.

---

## 4. [Major] completeness - pull-only
- defect key: (unkeyed)
- surfaces: pull
- (pull) Violation: the prompt assumes a session set at "docs/session-sets/dabbler-platform" and a schema at "docs/path-aware-critique-schema.md". Impact: a reviewer cannot save or validate the required critique artifact, so the requested closeout flow is not actionable from this repository state and would block any reasonable merge/close decision for this task. Evidence: list_dir("docs") shows no path-aware-critique schema file at docs root; list_dir("docs/session-sets/dabbler-platform") fails because that directory does not exist; grep searches for "session-sets/dabbler-platform" and "path-aware-critique-schema" under docs return no matches. Fix: either provide the correct in-repo paths for the target session set and schema, or add the missing files/directories before asking for repository-grounded verification.

## 5. [Major] correctness - pull-only
- defect key: (unkeyed)
- surfaces: pull
- (pull) **Violation**: The `AddDabblerPlatformStubs` extension method conditionally registers services. Specifically, `AddStubArtifactCatalogProvider` and `AddStubUsageTrackingProvider` are only called if their corresponding data collections are non-empty. This is an unsafe dependency injection pattern.
**Impact**: If a consumer of this library expects services like `IArtifactCatalogProvider` or `IUsageTrackingProvider` to always be available (which is a standard assumption with DI), the application will crash at startup with a "service not registered" error if the stub platform is configured with empty `CatalogEntries` or `UsageRecords`. This creates a hidden coupling between data configuration and service availability, making the system brittle. A developer trying to configure a "blank" platform stub would unexpectedly break the application. This changes the merge decision because it's a runtime failure waiting to happen.
**Evidence**: The file `src/Libs/Dabbler.Platform.Stubs/DabblerStubServiceCollectionExtensions.cs` contains the following code:
```csharp
        // Reports sub-package helpers (conditional on non-empty collections)
        if (definition.CatalogEntries.Count > 0)
            services.AddStubArtifactCatalogProvider(definition.CatalogEntries);

        if (definition.UsageRecords.Count > 0)
            services.AddStubUsageTrackingProvider(definition.UsageRecords);
```
The fix is to remove the conditions and always register these services. The service implementations themselves should handle the case of an empty data source gracefully (e.g., by returning an empty list of results).

## 6. [(unspecified)] (uncategorized) - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) the `.csproj` declares `README.md` as a pack artifact but the file is absent from the diff's changed paths.

### 8. `toolExe` path \u2014 tool-path executables aren't laid out that way on all platforms

```csharp
var toolExe = Path.Combine(toolPath, OperatingSystem.IsWindows() ? "dabbler-crud-slice.exe" : "dabbler-crud-slice");
```
With `dotnet tool install --tool-path`, the executable shim is placed directly in the tool-path directory on Windows as `.exe`, and as a shell script (no extension) on Linux/macOS. This is correct behavior.

### 9. `dotnet tool uninstall` in finally \u2014 wrong semantics

```csharp
try { RunTool("dotnet", $"tool uninstall Dabbler.CrudSlice.Tool --tool-path \"{toolPath}\""); }
catch { /* best-effort */ }
TryDeleteDirectory(tempDir);
TryDeleteDirectory(hiveDir);
TryDeleteDirectory(toolPath);
```
The test already calls `TryDeleteDirectory(toolPath)` after uninstalling. The explicit `tool uninstall` followed by directory deletion is redundant but harmless. Not a defect.

### 10. Back to `WriteLocalNugetConfig` \u2014 the critical issue

Reviewing the full diff scope: the only new helpers added to `PackagingSmokeTests.cs` are:
- `LocateSmokeAppFixture()`
- `LocateSmokeSchema()`
- `ExtractVersion()`
- `CopyDirectory()`

`WriteLocalNugetConfig` is **not** in the diff additions. It is called at:
```csharp
WriteLocalNugetConfig(tempDir, PackOutputDir);
```
And `TryDeleteDirectory` is called twice in the finally block but also not added. `FindExactNupkg` and `RunTool` and `PackOutputDir` are more plausible as pre-existing (smoke test infrastructure).

`WriteLocalNugetConfig` is the most problematic. It's a highly specific operation \u2014 writing a `nuget.config` file pointing to a local directory \u2014 that is unlikely to exist in pre-existing smoke test infrastructure that predates this consumer-validation gate concept. Its absence from the diff while being called in new code is a **compilation defect if it doesn't pre-exist**.

The response under review doesn't discuss this gap or acknowledge it. The diff is presented as the complete change set.

---

## Verdict

**ISSUES FOUND**

---

###

## 7. [(unspecified)] (uncategorized) - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) **So what?**: The violation is sequential synchronous pipe draining when both stdout and stderr are redirected. The impact: in the specific invocation `dotnet new <shortname> -h`, the output is small enough that deadlock is practically impossible \u2014 the pipe buffer on all modern OSes is at least 4KB and `dotnet new -h` output is much smaller than that. There's no plausible CI failure path here. This is a nit-level code quality issue.

### `README.md` reference without a `README.md` in the diff

The `.csproj` adds `<None Include="README.md" Pack="true" PackagePath="\" />` and sets `<PackageReadmeFile>README.md</PackageReadmeFile>`. But the diff shows **no `README.md` file added** to `tools/Dabbler.CrudSlice/`. If the file doesn't exist, `dotnet pack` will fail with a build error when building `Dabbler.CrudSlice`.

**Violation:** The `.csproj` declares `<PackageReadmeFile>README.md</PackageReadmeFile>` and `<None Include="README.md" Pack="true" PackagePath="\" />`, but no `tools/Dabbler.CrudSlice/README.md` is present in the diff.

**Impact:** `dotnet pack` (and potentially `dotnet build`) will fail for `Dabbler.CrudSlice` with a file-not-found or pack error. The `tools/pack.ps1` addition of `Dabbler.CrudSlice` to `$LibraryProjects` means this will be hit on every pack run. The smoke test's pack prerequisite will never be satisfied, causing all `CrudSliceTool_AcquiredFromFeed_GeneratesSliceThatBuildsClean` tests to always skip. This is a broken deliverable.

**Evidence:** The diff adds `<None Include="README.md" Pack="true" PackagePath="\" />` and `<PackageReadmeFile>README.md</PackageReadmeFile>` in `tools/Dabbler.CrudSlice/Dabbler.CrudSlice.csproj`, but there is no `diff --git a/tools/Dabbler.CrudSlice/README.md` anywhere in the change set.

### `WriteLocalNugetConfig` \u2014 referenced but not in diff

The smoke test calls `WriteLocalNugetConfig(tempDir, PackOutputDir)` but this helper is not added in the diff. It must exist in the pre-existing file (since the test file already had other helpers). This is plausible \u2014 `FindExactNupkg` and `TryDeleteDirectory` also aren't in the diff and must pre-exist. Not a defect.

### `PackOutputDir` \u2014 not defined in diff

Same reasoning \u2014 must pre-exist. Not a defect.

### `FindExactNupkg` vs. `HasExactPackage`

The test uses `FindExactNupkg` (returns path) vs. `HasExactPackage` (returns bool) \u2014 consistent with the different use cases. Not a defect.

### `toolExe` path construction

```csharp
var toolExe = Path.Combine(toolPath, OperatingSystem.IsWindows() ? "dabbler-crud-slice.exe" : "dabbler-crud-slice");
```

On Linux/macOS, `dotnet tool install --tool-path` produces a shell script wrapper, not a binary. The wrapper file typically has no extension and is executable. The path construction looks correct for non-Windows. However, the actual executable name placed by `dotnet tool install --tool-path` is derived from `<ToolCommandName>`, which is set to `dabbler-crud-slice`. On Windows it's `.exe`. This looks correct.

### Session state: `session_number` in events vs. `number` in state

The events file uses `"session_number": 2` and the state file uses `"number": 2`. These are separate schemas and appear consistent with the pre-existing `session_number: 1` entries. Not a defect.

### `genArgs` \u2014 `--template-hive` flag

The generated args include `--template-hive "{hiveDir}"`. This flag must exist as a CLI option in `CliOptions` / `Program.cs`. It's used in `TemplatePreflight.EnsureTemplatesInstalled(opts)` as `opts.TemplateHive`. The diff shows this is being passed through `opts` \u2014 but the diff of `Program.cs` only shows the insertion of the `EnsureTemplatesInstalled` call; `CliOptions` is not in the diff, meaning `TemplateHive` either already existed or was added outside this session. Given the test passes `--template-hive` as a CLI arg and `TemplatePreflight` consumes `opts.TemplateHive`, there's an implicit assumption this property exists. But this pre-exists from Session 1 work and is not part of this change set to verify. Reasonable to assume it's there.

### `CopyDirectory` \u2014 no subdirectory recursion for fixtures

The `CopyDirectory` helper skips `bin` and `obj` subdirectories (good), and recursively copies others. The SmokeApp fixture might not have subdirectories that need copying for just a build test, so this should be fine.

---

## ISSUES FOUND


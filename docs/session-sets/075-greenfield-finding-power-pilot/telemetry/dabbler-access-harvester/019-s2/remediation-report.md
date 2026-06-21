# Remediation report - dabbler-access-harvester

- committed ref: 0fb87b8..WORKTREE
- generated at: 2026-06-20T20:34:01.179498-04:00
- provenance complete: False
- NOTE: provenance is incomplete (pushUnkeyed=5, pullUnkeyed=0); a defect both surfaces caught but neither keyed appears as two separate entries.
- findings: 5

## 1. [Major] Completeness / Correctness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) `THIRD-PARTY-NOTICES.txt` is packed but not present in the changeset and its existence is unverified

- **Category:** Completeness / Correctness
- **Severity:** Major
- **Violation:** The `.csproj` adds `<None Include="..\THIRD-PARTY-NOTICES.txt" Pack="true" PackagePath="\" Visible="false" />` and the inline comment asserts "BSD-3-Clause requires the copyright notice to travel with binary redistributions" \u2014 the pack entry is the stated compliance mechanism for this obligation.
- **Impact:** If `THIRD-PARTY-NOTICES.txt` does not exist at the repo root, `dotnet pack` will either error or silently omit the file. Silent omission means the published `.nupkg` ships without the BSD-3-Clause attribution that the code explicitly claims it carries, creating a license compliance failure for every consumer. A reviewer seeing this would require confirmation the file exists before merging.
- **Evidence:** The diff's changed paths are exhaustive for this commit range. `THIRD-PARTY-NOTICES.txt` does not appear anywhere in the changed paths or unified diff. The original response's description of the changeset does not flag this gap, treating the compliance claim as fulfilled when the file's existence is unverified by the evidence in front of us.

---

## 2. [Major] Completeness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) `THIRD-PARTY-NOTICES.txt` is referenced in the build but absent from the diff**
- **Category:** Completeness
- **Severity:** Major
- **Details:**
  - **Violation:** `AccessHarvester.Cli.csproj` adds `<None Include="..\THIRD-PARTY-NOTICES.txt" Pack="true" PackagePath="\" Visible="false" />` with the explicit rationale that "BSD-3-Clause requires the copyright notice to travel with binary redistributions." This is a functional build dependency.
  - **Impact:** If the file does not exist at the repo root, `dotnet pack` will fail, breaking the NuGet publish pipeline \u2014 the primary deliverable of this session set. Additionally, if the file is simply absent, the BSD-3-Clause compliance claim made in the `.csproj` comment is unsubstantiated and potentially a license violation.
  - **Evidence:** `THIRD-PARTY-NOTICES.txt` does not appear in `[changed paths]`. The diff range covers `0fb87b8..WORKTREE`. The `.csproj` comment treats this as a new addition tied to set 019 S2. No prior session (`matrix-run-s1` artifacts) mentions this file's pre-existence.

## 3. [Major] Completeness - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) `docs/harvester/nuget-publish.md` is linked in `install.md` but absent from the diff**
- **Category:** Completeness
- **Severity:** Major
- **Details:**
  - **Violation:** `install.md` adds the text: "The first public push additionally requires the maintainer's one-time nuget.org setup (account, trusted-publishing policy) \u2014 see [`docs/harvester/nuget-publish.md`](nuget-publish.md)." This is presented as a navigable link, not a placeholder.
  - **Impact:** The link is broken if the file doesn't exist. The session's stated purpose is "Publish pipeline + first-push guardrails" \u2014 the guardrail documentation is the core deliverable. A user or maintainer following the setup instructions hits a 404. This would change a reasonable reviewer's merge decision: published documentation with a broken link to the primary setup guide is not mergeable.
  - **Evidence:** `docs/harvester/nuget-publish.md` does not appear in `[changed paths]`. The session is marked `in-progress`, but the `install.md` change treats the link as a live reference, not a forward declaration.

---

## 4. [(unspecified)] (uncategorized) - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) S FOUND**

###

## 5. [(unspecified)] (uncategorized) - push-only
- defect key: (unkeyed)
- surfaces: push
- (push) S FOUND


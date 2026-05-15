```json
{
  "verdict": "ISSUES_FOUND",
  "issues": [
    {
      "category": "Correctness",
      "severity": "Major",
      "description": "The fallback count path is not strictly `state file totalSessions when state === \"done\"` as required. In `readSessionSets()`, `totalSessions` is populated from `activity-log.json` before `session-state.json`, and the final `state === \"done\"` fallback uses that shared variable. If the activity log's top-level `totalSessions` is stale or differs from the state file, `sessionsCompleted` will be derived from the wrong source. Use `sd.totalSessions` directly for the done fallback, or let the state-file value override the activity-log value before counting.",
      "location": "tools/dabbler-ai-orchestration/src/utils/fileSystem.ts — readSessionSets()"
    },
    {
      "category": "Completeness",
      "severity": "Major",
      "description": "The Session 2 contract required a v0.13.12 version bump in `package.json`, `package-lock.json`, `CHANGELOG.md`, and `CLAUDE.md`, but the supplied commit only shows the changelog update. Release metadata is incomplete from the provided changes.",
      "location": "tools/dabbler-ai-orchestration/package.json, tools/dabbler-ai-orchestration/package-lock.json, CLAUDE.md"
    }
  ]
}
```
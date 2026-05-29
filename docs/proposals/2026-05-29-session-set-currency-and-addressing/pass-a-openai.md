## pass-a — openai (model=gpt-5-4, in=4067 out=7100 cost=$0.1167)

Q1: AGREE-WITH-MODIFICATION
  - You need an upstream fact to detect stale pinned routers, but the local constant is still the only truthful statement of what this installation can actually read/write.
  - Lock two values: `upstreamCurrentSchemaVersion` from the manifest and `localSupportedSchemaVersion` from `ai_router`; warn on mismatch, and never offer `--apply` past the local supported version.

Q2: AGREE-WITH-MODIFICATION
  - Fail-open is correct for SessionStart; blocking on GitHub would make the hook itself the outage source. Hitting the network on every start with only a warning fallback is still too brittle and noisy.
  - Cache the manifest with a TTL; on fetch failure use cached manifest first, then the local constant, and only warn when falling past the cache.

Q3: DISAGREE
  - Raw URL on the canonical repo is fine, but a network-fetched manifest must not carry executable shell commands or ambiguous migrator-chain semantics. That is an unnecessary trust and compatibility hazard.
  - Lock a minimal declarative manifest at `docs/schema-current.json`: `manifestVersion`, `currentSchemaVersion`, `minimumAiRouterVersion`, `schemaDocUrl`, `migrationGuideUrl`, and optional symbolic migrator IDs; command resolution stays in local code.

Q4: AGREE-WITH-MODIFICATION
  - Bounded output is right, but dumping per-set names into every session-start context is still wasteful given old schemas are explicitly acceptable.
  - Make the hook output a one-line summary by default; reserve set-by-set listing for CLI `--verbose` or `--json`.

Q5: AGREE
  - Single-root walk-up matches the hook's execution model and avoids inventing cross-workspace semantics in a CLI that only sees one cwd.

Q6: AGREE
  - Reusing the existing SessionStart invoker is the only sane install path; a second hook would create ordering and duplicate-work bugs for no gain.

Q7: AGREE-WITH-MODIFICATION
  - An opt-in `--apply` is fine, but it must be capability-gated; otherwise a stale package can detect a newer upstream schema it cannot migrate to.
  - Lock `--apply` to locally-known migrator chains only, and refuse when `upstreamCurrentSchemaVersion > localSupportedSchemaVersion` with an explicit "upgrade ai_router first" message.

Q8: AGREE-WITH-MODIFICATION
  - Exact integer-prefix resolution with collision errors is the right behavior. "Nearest numbers" is fuzzy and risks nudging users toward the wrong set.
  - On no match, report `no set with prefix N` plus the sorted available numeric prefixes or `--next`, not heuristic nearest suggestions.

Q9: AGREE
  - The load-bearing path is CLI resolution in `start_session`; changing row-driven copy commands buys little and expands UI scope for no operational value.

Q10: AGREE-WITH-MODIFICATION
  - Allowing monotonic numeric prefixes is correct, but making them only "recommended" leaves the new addressing mode spotty and hard to rely on.
  - Lock numeric prefixes as required for all newly created sets in this repo and any future scaffolder output, with no retroactive renames for existing consumer repos.

Q11: AGREE-WITH-MODIFICATION
  - `max(prefix)+1` per repo is the right authority, but formatting is under-specified and will drift immediately in mixed-width repos.
  - Have `next_session_set_number()` return both the integer and a zero-padded string using `width = max(3, max existing numeric prefix width)`; if none exist, start at `001`.

TOP RISKS
- The manifest is over-trusted. Shipping shell commands and migration chain semantics from a mutable network document is the weakest part of the proposal and creates both security and compatibility failure modes.
- The hook as proposed adds an uncached GitHub dependency to every session start. Even fail-open, repeated fetches and warnings will create latency/noise and train people to ignore the output.
- Number-prefix adoption is too soft. If new sets are only "recommended" to use numeric prefixes, Feature 2 becomes inconsistent across repos and hard to teach or automate.
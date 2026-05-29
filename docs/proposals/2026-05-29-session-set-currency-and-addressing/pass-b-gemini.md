## pass-b — gemini (model=gemini-pro, in=4698 out=1668 cost=$0.0226)

This is a strong proposal, but the author's bias toward minimalism and back-end logic creates significant architectural risks and undermines key deliverables. My analysis follows.

### 1. Q1/Q3 — GitHub Manifest for "Current Version"

**Strongest Counter-Argument (Manifest is Over-Engineering):**
This introduces a runtime network dependency to solve a build-time dependency management problem. The root cause was a stale, *pinned* router. The correct, low-complexity solution is to enforce a policy of using floating dependencies (`dabbler-ai-orchestration>=0.24`) in consumer repos and adding a CI step that runs a simple, local-only check. A network call on *every session start* adds fragility (GitHub outages, corporate firewalls, rate limits) and complexity (fail-open logic, warning fatigue) for a problem better solved by `pip` and CI.

Furthermore, fetching from `master` is operationally reckless. It creates a race condition where a consumer could fetch a manifest declaring `v5` seconds after it was merged, but before the corresponding `v5` migrator code and reader-shim logic have been published in a new package version. The consumer's router (v4) would see a "drift" to a non-existent schema it can't handle. This breaks the system. A manifest *must* be versioned and fetched from a stable, immutable reference (a git tag, e.g., `v0.24.1`), not a moving target like `master`. The author's dismissal of tags is a critical error in judgment.

**Final Call: COMPROMISE.**
Keep the manifest, as it provides a valuable out-of-band update mechanism that doesn't rely on every consumer having perfect CI. **However, flip the source from `master` to a versioned tag.** The fetch URL must point to `raw.githubusercontent.com/.../<tag>/docs/schema-current.json`. When we publish router version `v0.25.0`, the manifest fetched from the `v0.25.0` tag will point to the schema version supported by *that exact release*, eliminating the race condition. The local constant remains the correct fallback.

### 2. Q6 — Folding Drift Check into SessionStart Hook

**Strongest Counter-Argument (For a Separate Hook):**
This violates the Single Responsibility Principle. The `SessionStart` invoker's job is to prepare and inject session context. A schema drift check is a repository health check. Coupling them forces any consumer who wants the safety of the guard to also adopt the `start_session` orchestration pattern. A repo that *only* wants the guard but uses a different session flow is now locked out.

This creates a brittle, monolithic hook. What's next? A check for stale prerequisites? A lint for `spec.md` quality? Piling unrelated checks into `SessionStart` leads to a slow, complex, and difficult-to-debug entrypoint. A separate, single-purpose `RepoHealth` hook is architecturally sound, modular, and allows consumers to compose their pre-session checks granularly. The author's fear of "ordering bugs" is a sign of poor hook design; hooks should be independent.

**Final Call: FLIP to the alternative.**
Define a new, single-purpose hook for repository health checks. Start with the schema drift check. This is more work now but establishes a clean, extensible pattern for the future. The author's preference for reusing existing surface area creates technical debt by coupling unrelated concerns. We will not build on a tangled foundation.

### 3. Q9 — Resolver in `ai_router` Only

**Strongest Counter-Argument (This is Scope-Dodging):**
This decision guts Feature 2 of its primary value. The feature is for *human* convenience. The primary human interface is the VS Code extension, not the `ai_router` CLI. If a developer cannot use the number `50` in the UI where they spend their time (the Explorer, the copy-prompt commands), the feature is a failure. The orchestrator can already be taught to resolve a number internally; the deliverable was to expose this affordance to the user.

The author's claim that this requires inventing a new UI is a failure of imagination. Augmenting the command palette with "Copy Session Slug (by number)..." which opens a standard VS Code quick-input box is trivial. Leaving this out creates a confusing asymmetry where the AI can use a shorthand the human cannot, directly degrading the user experience. This is not a reasonable "follow-up"; it is the core of the feature.

**Final Call: FLIP to the alternative.**
The spec implies user-facing surfaces accept a number. We will deliver that. The extension's `copySlug` and Explorer-related commands **will** be taught to resolve a bare number. The work is minor and the user-value is the entire point of the feature. Deferring this is unacceptable.

### 4. Q7 — The `--apply` Convenience Flag

**Strongest Counter-Argument (This is Scope Creep):**
The feature is a "drift guard," a detection mechanism. The explicit non-goal is "no silent auto-migration." Adding an `--apply` flag turns a detector into a mutator, fundamentally changing its nature and violating the stated design constraint. This is classic scope creep. The command `check_migrations` should do exactly that: check. It should not also `run_migrations`.

This muddies the water. We have existing, single-purpose migrator CLIs (`migrate_v3_to_v4`, etc.). Their names are clear and their function is unambiguous. Overloading the check command with mutation logic is confusing and creates a new vector for catastrophic error if the dispatch logic has a bug. The Explorer can and should invoke the simple, tested, single-purpose migrator scripts directly, as suggested by the hook's own output.

**Final Call: COMPROMISE.**
The counter-argument is correct: `check_migrations` must not mutate. However, the author is right that centralizing the dispatch logic is better than reimplementing it in the extension. Therefore, we will create a **new, separate CLI script**: `python -m ai_router.upgrade_sets`. This script will contain the `--in-place`/`--only`/`--yes` logic and the intelligence to route a v2 set to the Lightweight migrator and a v3 set to the v3→v4 migrator. The `check_migrations` script will remain read-only and will simply *recommend* running `upgrade_sets`. The Explorer's button will call the new `upgrade_sets` command. This preserves separation of concerns while providing the desired centralized convenience.

---

### NET: which of the author's 11 dispositions should actually change.

Four of the eleven dispositions must change. The author's bias led to pragmatism that bordered on corner-cutting. We will correct this.

1.  **Q3 (Manifest Location):** CHANGE. The manifest will be fetched from a stable git tag, not `master`.
2.  **Q6 (Extension Surface):** CHANGE. We will create a new, separate hook for the drift check, not overload `SessionStart`.
3.  **Q7 (`--apply`):** CHANGE. We will cut `--apply` from `check_migrations` and create a new, dedicated `upgrade_sets` CLI for the Explorer to call.
4.  **Q9 (Surfaces):** CHANGE. The extension's user-facing commands in the Explorer and command palette *will* be updated to accept a numeric prefix.

The dispositions for Q1, Q2, Q4, Q5, Q8, Q10, and Q11 stand as recommended.
/**
 * Pure-logic core for the ``Dabbler: Install ai-router`` /
 * ``Dabbler: Update ai-router`` commands.
 *
 * The VS Code wiring lives in ``commands/installAiRouterCommands.ts``;
 * everything here takes injected dependencies (process spawner, fs ops,
 * UI prompts) so the test suite can exercise the full PyPI / GitHub
 * branching, ``router-config.yaml`` preservation, and install-method
 * marker round-trip without spawning real subprocesses or touching the
 * real filesystem.
 *
 * Design follows the spec's risk note ("inject a ``processSpawner``
 * dependency into the command's helper functions, matching the existing
 * ``cancelLifecycleCommands.ts`` dependency-injection style"). The
 * dependency object is the only knob the test passes; production code
 * supplies real ``child_process.spawn`` and ``fs`` wrappers.
 */
export declare const PYPI_PACKAGE_NAME = "dabbler-ai-router";
export declare const REPO_URL = "https://github.com/darndestdabbler/dabbler-ai-orchestration.git";
export declare const ROUTER_CONFIG_REL: string;
export declare const INSTALL_METHOD_REL: string;
/**
 * Persistent location for the GitHub-path sparse checkout. Editable
 * installs need a stable source tree on disk — installing from a tmpdir
 * that is then deleted leaves a dangling .egg-link pointing nowhere
 * (Round 1 verifier catch). Keep the checkout under ``.dabbler/`` so
 * it sits next to the install-method marker and is one obvious thing
 * for an operator to clean up if they ever want to.
 */
export declare const GITHUB_CHECKOUT_REL: string;
export type InstallSource = "pypi" | "github";
export interface SpawnResult {
    exitCode: number | null;
    stdout: string;
    stderr: string;
}
export interface ProcessSpawner {
    (cmd: string, args: string[], opts?: {
        cwd?: string;
        timeoutMs?: number;
    }): Promise<SpawnResult>;
}
export interface FileOps {
    exists: (absPath: string) => boolean;
    readFile: (absPath: string) => string;
    writeFile: (absPath: string, content: string) => void;
    mkdirp: (absPath: string) => void;
    /** Recursively copy a directory (overwrites destination contents). */
    copyDir: (srcAbs: string, dstAbs: string) => void;
    /** Recursively remove a path; no-op when missing. */
    removeRecursive: (absPath: string) => void;
    /** Make a unique temporary directory and return its absolute path. */
    mkdtemp: (prefix: string) => string;
}
export interface InstallPrompts {
    /**
     * Ask the operator which install source to use. Returns ``undefined``
     * when the prompt is dismissed; the caller treats that as "abort".
     */
    pickSource: (defaultSource: InstallSource) => Promise<InstallSource | undefined>;
    /** Ask whether to create a venv at the given absolute path. */
    confirmCreateVenv: (venvAbsPath: string) => Promise<boolean>;
    /**
     * Ask which git ref to check out for the GitHub path. Returns
     * ``undefined`` when the prompt is dismissed (treat as abort);
     * returns the empty string when the operator wants the default
     * (latest released tag — :func:`runGitHubInstall` resolves this via
     * ``git ls-remote --tags --refs``).
     */
    promptGitHubRef: (defaultRef: string) => Promise<string | undefined>;
}
export interface ProgressReporter {
    /** Free-form status line shown in the VS Code progress notification. */
    (message: string): void;
}
export interface InstallDeps {
    /** Workspace root (the directory that owns ``ai_router/``). */
    workspaceRoot: string;
    /** Configured Python interpreter path (e.g. ``"python"`` or ``".venv/Scripts/python.exe"``). */
    pythonPath: string;
    /**
     * Repo URL the GitHub fallback path clones from. Defaults to the
     * upstream when omitted; the install command threads
     * ``dabblerSessionSets.aiRouterRepoUrl`` through here so fork-trackers
     * can point the fallback at their fork without editing the
     * extension source.
     */
    repoUrl?: string;
    spawner: ProcessSpawner;
    fileOps: FileOps;
    prompts: InstallPrompts;
    /** Optional — defaults to a no-op. */
    reportProgress?: ProgressReporter;
}
export interface InstallOutcome {
    ok: boolean;
    /** Operator-facing message. */
    message: string;
    /** Source actually used (null when the operator aborted before picking). */
    source: InstallSource | null;
    /** Absolute path to the venv exercised. */
    venvPath: string | null;
    /** True when an existing ``router-config.yaml`` was stashed and restored. */
    routerConfigPreserved: boolean;
    /**
     * For the GitHub path: which ref was actually checked out (null for
     * PyPI / aborts). Useful for the success message and for tests that
     * want to assert the latest-tag resolution worked.
     */
    resolvedRef?: string | null;
}
/**
 * Detects the precise stderr signature ``python -m ai_router.<x>`` emits when
 * ``ai_router`` is not on ``sys.path``. This must match exactly the messages
 * that ``runpy`` / ``python -m`` produce for that case so the providers can
 * surface a "Click here to install" tree-item instead of the existing red
 * error. False positives would mask real bugs; false negatives would surface
 * a less-useful error to first-time users.
 */
export declare function isAiRouterNotInstalled(stderr: string): boolean;
/**
 * Install ``ai_router`` into the workspace.
 *
 * Returns an :class:`InstallOutcome` describing what happened. Never throws
 * for spawn / fs failures — the outcome carries an operator-facing
 * ``message`` instead, so the UI can surface results uniformly.
 */
export declare function installAiRouter(deps: InstallDeps): Promise<InstallOutcome>;
/**
 * Update ``ai_router`` in the workspace.
 *
 * Reads the install-method marker written by a prior install. PyPI installs
 * use ``pip install -U``; GitHub installs re-pull the sparse-checkout. When
 * no marker is present, falls back to a fresh install flow.
 */
export declare function updateAiRouter(deps: InstallDeps): Promise<InstallOutcome>;
/**
 * Path-shape candidate for a venv root inferred from ``pythonPath``.
 *
 * Returns the grandparent directory when the immediate parent is
 * ``Scripts/`` or ``bin/`` (the two layouts ``python -m venv`` writes).
 * **The candidate is not validated here** — ``/usr/bin/python3`` would
 * yield ``/usr``, which is a system path, not a venv. Callers MUST
 * confirm the candidate by checking for a ``pyvenv.cfg`` marker (the
 * standard signature of a virtual environment) before treating the
 * candidate as the install target. ``ensureVenv`` does this.
 */
export declare function deriveVenvFromPythonPath(pythonPath: string): string | null;
/**
 * Resolve the venv's pip executable (or the venv's python, if pip is not
 * present as a top-level shim — falls back to ``<python> -m pip``).
 *
 * Returns absolute paths; production code passes them straight to the
 * spawner.
 */
export declare function venvPython(venvPath: string): string;
/**
 * Resolve the latest released tag (``vMAJOR.MINOR.PATCH``) from the
 * remote. Returns the highest semver tag, or ``null`` if the remote has
 * no release tags or the ls-remote call fails. Pre-release suffixes
 * (``-rc1``, etc.) are filtered out — this is the *released* tag.
 */
export declare function resolveLatestReleaseTag(deps: InstallDeps): Promise<string | null>;

"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.GITHUB_CHECKOUT_REL = exports.INSTALL_METHOD_REL = exports.ROUTER_CONFIG_REL = exports.REPO_URL = exports.PYPI_PACKAGE_NAME = void 0;
exports.isAiRouterNotInstalled = isAiRouterNotInstalled;
exports.installAiRouter = installAiRouter;
exports.updateAiRouter = updateAiRouter;
exports.deriveVenvFromPythonPath = deriveVenvFromPythonPath;
exports.venvPython = venvPython;
exports.resolveLatestReleaseTag = resolveLatestReleaseTag;
const path = __importStar(require("path"));
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
exports.PYPI_PACKAGE_NAME = "dabbler-ai-router";
exports.REPO_URL = "https://github.com/darndestdabbler/dabbler-ai-orchestration.git";
exports.ROUTER_CONFIG_REL = path.posix.join("ai_router", "router-config.yaml");
exports.INSTALL_METHOD_REL = path.posix.join(".dabbler", "install-method");
/**
 * Persistent location for the GitHub-path sparse checkout. Editable
 * installs need a stable source tree on disk — installing from a tmpdir
 * that is then deleted leaves a dangling .egg-link pointing nowhere
 * (Round 1 verifier catch). Keep the checkout under ``.dabbler/`` so
 * it sits next to the install-method marker and is one obvious thing
 * for an operator to clean up if they ever want to.
 */
exports.GITHUB_CHECKOUT_REL = path.posix.join(".dabbler", "ai-router-src");
const DEFAULT_GITHUB_REF = "<latest released tag>";
/** Matches release tags of the form ``vMAJOR.MINOR.PATCH`` (no pre-release suffix). */
const RELEASE_TAG_RE = /^v(\d+)\.(\d+)\.(\d+)$/;
// ---------- Module-not-installed detection (shared with the provider views) ----------
/**
 * Detects the precise stderr signature ``python -m ai_router.<x>`` emits when
 * ``ai_router`` is not on ``sys.path``. This must match exactly the messages
 * that ``runpy`` / ``python -m`` produce for that case so the providers can
 * surface a "Click here to install" tree-item instead of the existing red
 * error. False positives would mask real bugs; false negatives would surface
 * a less-useful error to first-time users.
 */
function isAiRouterNotInstalled(stderr) {
    if (!stderr)
        return false;
    if (/ModuleNotFoundError:\s*No module named ['"]ai_router['"]/.test(stderr))
        return true;
    // ``python -m ai_router.foo`` on a missing module emits:
    //   "Error while finding module specification for 'ai_router.foo'
    //    (ModuleNotFoundError: No module named 'ai_router')"
    // The ModuleNotFoundError check above already covers the parenthetical;
    // the leading "Error while finding module specification" is matched as a
    // belt-and-braces fallback in case the bundled error formatter changes.
    if (/Error while finding module specification for ['"]ai_router\./.test(stderr) &&
        /No module named ['"]ai_router['"]/.test(stderr)) {
        return true;
    }
    return false;
}
// ---------- Public entry points ----------
/**
 * Install ``ai_router`` into the workspace.
 *
 * Returns an :class:`InstallOutcome` describing what happened. Never throws
 * for spawn / fs failures — the outcome carries an operator-facing
 * ``message`` instead, mirroring the pattern in ``runPythonModule`` so the
 * UI can surface results uniformly.
 */
async function installAiRouter(deps) {
    return doInstall(deps, { mode: "install" });
}
/**
 * Update ``ai_router`` in the workspace.
 *
 * Reads the install-method marker written by a prior install. PyPI installs
 * use ``pip install -U``; GitHub installs re-pull the sparse-checkout. When
 * no marker is present, falls back to a fresh install flow.
 */
async function updateAiRouter(deps) {
    return doInstall(deps, { mode: "update" });
}
async function doInstall(deps, opts) {
    const report = deps.reportProgress ?? (() => { });
    // 1) Decide install source.
    let priorSource = null;
    if (opts.mode === "update") {
        priorSource = readInstallMethodMarker(deps);
    }
    const defaultSource = priorSource ?? "pypi";
    const source = await deps.prompts.pickSource(defaultSource);
    if (!source) {
        return {
            ok: false,
            message: "Install cancelled (no source chosen).",
            source: null,
            venvPath: null,
            routerConfigPreserved: false,
        };
    }
    // 2) Resolve / offer-to-create venv. Both paths need a venv because the
    //    PyPI path runs `pip install` and the GitHub path runs `pip install
    //    -e <persistent-checkout>` against the sparse-checked-out tree.
    const venvResult = await ensureVenv(deps);
    if (!venvResult.ok) {
        return {
            ok: false,
            message: venvResult.message,
            source,
            venvPath: null,
            routerConfigPreserved: false,
        };
    }
    const venvPath = venvResult.venvPath;
    if (source === "pypi") {
        return await runPyPiInstall(deps, { venvPath, mode: opts.mode, report });
    }
    return await runGitHubInstall(deps, { venvPath, report });
}
async function ensureVenv(deps) {
    // First, see if the configured pythonPath itself lives inside a venv —
    // an operator who pointed `dabblerSessionSets.pythonPath` at
    // `<somewhere>/.venv/Scripts/python.exe` has already chosen the venv,
    // and we should not overrule them by hunting for `.venv/` at the
    // workspace root. The candidate-from-path is path-shape-only; the
    // ``pyvenv.cfg`` marker check below is what distinguishes a real
    // venv from a system interpreter at e.g. `/usr/bin/python3` whose
    // parent dir happens to be ``bin/``.
    const fromPythonPath = deriveVenvFromPythonPath(deps.pythonPath);
    if (fromPythonPath &&
        deps.fileOps.exists(fromPythonPath) &&
        deps.fileOps.exists(path.join(fromPythonPath, "pyvenv.cfg"))) {
        return {
            ok: true,
            venvPath: fromPythonPath,
            message: `Using venv from configured pythonPath: ${fromPythonPath}`,
        };
    }
    const candidate = findExistingVenv(deps);
    if (candidate) {
        return { ok: true, venvPath: candidate, message: `Using existing venv at ${candidate}` };
    }
    const target = path.join(deps.workspaceRoot, ".venv");
    const create = await deps.prompts.confirmCreateVenv(target);
    if (!create) {
        return {
            ok: false,
            message: "No venv found at .venv/ or venv/. Install cancelled — create a venv first or accept the prompt to create .venv.",
            venvPath: null,
        };
    }
    // Choose a bootstrap interpreter for the `-m venv` call. The fix-
    // worthy case is the *ENOENT* one: the configured pythonPath has
    // venv shape AND points at a path that doesn't exist on disk yet
    // (e.g. ``.venv/Scripts/python.exe`` before ``.venv`` is created).
    // Spawning it would ENOENT instead of creating the venv. Fall back
    // to bare ``"python"`` from PATH for that case only. When the
    // configured interpreter exists (e.g. ``/usr/bin/python3``), we
    // honor it — the operator picked that Python version intentionally
    // and bootstrapping with bare ``"python"`` could pick up Python 2,
    // a different version, or nothing at all on PATH.
    const venvShaped = deriveVenvFromPythonPath(deps.pythonPath) !== null;
    const interpreterExists = path.isAbsolute(deps.pythonPath)
        ? deps.fileOps.exists(deps.pythonPath)
        : true; // bare commands rely on PATH; treat as "exists" and let spawn fail loudly if not
    const bootstrap = venvShaped && !interpreterExists ? "python" : deps.pythonPath;
    const result = await deps.spawner(bootstrap, ["-m", "venv", target], {
        cwd: deps.workspaceRoot,
        timeoutMs: 60000,
    });
    if (result.exitCode !== 0) {
        return {
            ok: false,
            message: `Failed to create venv at ${target} (using bootstrap '${bootstrap}'): ${oneLine(result.stderr || result.stdout) || `exit ${result.exitCode}`}`,
            venvPath: null,
        };
    }
    return { ok: true, venvPath: target, message: `Created venv at ${target}` };
}
function findExistingVenv(deps) {
    for (const rel of [".venv", "venv"]) {
        const abs = path.join(deps.workspaceRoot, rel);
        if (deps.fileOps.exists(abs))
            return abs;
    }
    return null;
}
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
function deriveVenvFromPythonPath(pythonPath) {
    if (!pythonPath || !path.isAbsolute(pythonPath))
        return null;
    const parent = path.basename(path.dirname(pythonPath));
    if (parent === "Scripts" || parent === "bin") {
        return path.dirname(path.dirname(pythonPath));
    }
    return null;
}
/**
 * Resolve the venv's pip executable (or the venv's python, if pip is not
 * present as a top-level shim — falls back to ``<python> -m pip``).
 *
 * Returns absolute paths; production code passes them straight to the
 * spawner.
 */
function venvPython(venvPath) {
    // Windows venvs put executables under Scripts/; POSIX under bin/.
    // Both layouts ship a ``python`` shim by name.
    const candidates = process.platform === "win32"
        ? [path.join(venvPath, "Scripts", "python.exe"), path.join(venvPath, "Scripts", "python")]
        : [path.join(venvPath, "bin", "python"), path.join(venvPath, "bin", "python3")];
    return candidates[0];
}
async function runPyPiInstall(deps, opts) {
    opts.report(opts.mode === "update"
        ? `Upgrading ${exports.PYPI_PACKAGE_NAME} from PyPI…`
        : `Installing ${exports.PYPI_PACKAGE_NAME} from PyPI…`);
    const pipArgs = opts.mode === "update"
        ? ["-m", "pip", "install", "-U", exports.PYPI_PACKAGE_NAME]
        : ["-m", "pip", "install", exports.PYPI_PACKAGE_NAME];
    const venvPy = venvPython(opts.venvPath);
    const result = await deps.spawner(venvPy, pipArgs, {
        cwd: deps.workspaceRoot,
        timeoutMs: 300000,
    });
    if (result.exitCode !== 0) {
        return {
            ok: false,
            message: `pip install failed: ${oneLine(result.stderr || result.stdout) || `exit ${result.exitCode}`}`,
            source: "pypi",
            venvPath: opts.venvPath,
            routerConfigPreserved: false,
        };
    }
    // Materialize ``ai_router/router-config.yaml`` into the workspace if
    // it isn't already there. The PyPI install puts the file under
    // ``<venv>/.../site-packages/ai_router/router-config.yaml`` (it ships
    // as package data), but the rest of the workflow — and the post-
    // install editor-open / tuning toast — assumes the workspace owns a
    // local copy that the operator edits without touching site-packages.
    // An *existing* local copy is left untouched.
    let materialized = false;
    const workspaceConfig = path.join(deps.workspaceRoot, exports.ROUTER_CONFIG_REL);
    if (!deps.fileOps.exists(workspaceConfig)) {
        const seed = await readBundledRouterConfig(deps, venvPy);
        if (seed !== null) {
            try {
                deps.fileOps.mkdirp(path.dirname(workspaceConfig));
                deps.fileOps.writeFile(workspaceConfig, seed);
                materialized = true;
            }
            catch {
                // Non-fatal: the install succeeded, the file copy didn't. The
                // operator can re-run or copy by hand. The success message
                // below still surfaces "installed".
            }
        }
    }
    writeInstallMethodMarker(deps, "pypi");
    return {
        ok: true,
        message: opts.mode === "update"
            ? `Upgraded ${exports.PYPI_PACKAGE_NAME} in ${opts.venvPath}.${materialized ? " Seeded ai_router/router-config.yaml from the installed package." : ""}`
            : `Installed ${exports.PYPI_PACKAGE_NAME} into ${opts.venvPath}.${materialized ? " Seeded ai_router/router-config.yaml from the installed package." : ""}`,
        source: "pypi",
        venvPath: opts.venvPath,
        routerConfigPreserved: materialized,
    };
}
/**
 * Read the bundled ``router-config.yaml`` out of the freshly-installed
 * ``ai_router`` package. Shells out to the venv's Python with a
 * one-liner that resolves the package's data file via
 * ``importlib.resources``; on any failure (path doesn't exist, the
 * package was installed without its package data, the spawn failed)
 * returns ``null`` so the caller can fall through gracefully without
 * derailing the install.
 */
async function readBundledRouterConfig(deps, venvPy) {
    const code = "from importlib.resources import files; " +
        "p = files('ai_router').joinpath('router-config.yaml'); " +
        "import sys; sys.stdout.write(p.read_text(encoding='utf-8'))";
    const result = await deps.spawner(venvPy, ["-c", code], {
        cwd: deps.workspaceRoot,
        timeoutMs: 30000,
    });
    if (result.exitCode !== 0 || !result.stdout)
        return null;
    return result.stdout;
}
/**
 * Resolve the latest released tag (``vMAJOR.MINOR.PATCH``) from the
 * remote. Returns the highest semver tag, or ``null`` if the remote has
 * no release tags or the ls-remote call fails. Pre-release suffixes
 * (``-rc1``, etc.) are filtered out — this is the *released* tag.
 */
async function resolveLatestReleaseTag(deps) {
    const repo = deps.repoUrl ?? exports.REPO_URL;
    const result = await deps.spawner("git", ["ls-remote", "--tags", "--refs", repo], { cwd: deps.workspaceRoot, timeoutMs: 60000 });
    if (result.exitCode !== 0)
        return null;
    const tags = [];
    for (const line of result.stdout.split(/\r?\n/)) {
        const m = /^[0-9a-f]+\s+refs\/tags\/(.+)$/.exec(line.trim());
        if (!m)
            continue;
        const tag = m[1];
        const sm = RELEASE_TAG_RE.exec(tag);
        if (!sm)
            continue;
        tags.push({
            raw: tag,
            sortable: [Number(sm[1]), Number(sm[2]), Number(sm[3])],
        });
    }
    if (tags.length === 0)
        return null;
    tags.sort((a, b) => {
        for (let i = 0; i < 3; i++) {
            if (a.sortable[i] !== b.sortable[i])
                return b.sortable[i] - a.sortable[i];
        }
        return 0;
    });
    return tags[0].raw;
}
async function runGitHubInstall(deps, opts) {
    // Ask up-front for the ref. Empty string ⇒ caller wants the latest
    // released tag (resolved below); undefined ⇒ caller dismissed the
    // prompt, treat as abort.
    const userRef = await deps.prompts.promptGitHubRef(DEFAULT_GITHUB_REF);
    if (userRef === undefined) {
        return {
            ok: false,
            message: "Install cancelled (no GitHub ref chosen).",
            source: "github",
            venvPath: opts.venvPath,
            routerConfigPreserved: false,
            resolvedRef: null,
        };
    }
    const explicitRef = userRef.trim() === "" || userRef === DEFAULT_GITHUB_REF ? null : userRef;
    let refToUse = explicitRef;
    if (refToUse === null) {
        opts.report("Resolving latest released tag…");
        refToUse = await resolveLatestReleaseTag(deps);
        if (refToUse === null) {
            return {
                ok: false,
                message: "Could not resolve the latest released tag from the remote. Re-run and supply a tag/branch explicitly.",
                source: "github",
                venvPath: opts.venvPath,
                routerConfigPreserved: false,
                resolvedRef: null,
            };
        }
    }
    // 1) Stash router-config.yaml if it exists. The stash is in-memory
    //    because the file is small UTF-8 text. The restore happens in the
    //    outer try/finally below so a copyDir / writeFile failure can't
    //    leave the operator's tuned config lost (Round 1 verifier catch).
    const routerConfigAbs = path.join(deps.workspaceRoot, exports.ROUTER_CONFIG_REL);
    let stashedConfig = null;
    if (deps.fileOps.exists(routerConfigAbs)) {
        stashedConfig = deps.fileOps.readFile(routerConfigAbs);
    }
    let preserved = false;
    let lastRestoreError = null;
    /**
     * Attempt to restore the stashed router-config.yaml. Idempotent and
     * retry-safe: returns ``true`` once the stash has been written
     * back to disk (or there was nothing to restore in the first place),
     * ``false`` on failure. Does NOT mark itself "done" on failure —
     * that's the round-4 bug — so the outer-finally retry can re-attempt
     * after the named-failure branches give it another chance.
     */
    const restoreStash = () => {
        if (stashedConfig === null)
            return true;
        if (preserved)
            return true;
        try {
            deps.fileOps.writeFile(routerConfigAbs, stashedConfig);
            preserved = true;
            lastRestoreError = null;
            return true;
        }
        catch (err) {
            lastRestoreError = err instanceof Error ? err.message : String(err);
            return false;
        }
    };
    /**
     * Wraps an outcome before returning so the install never reports
     * ``ok: true`` while the operator's tuned router-config.yaml is
     * unrestored. Round-4 verifier catch: the previous restoreStash
     * implementation could swallow a write failure on the success path
     * and leave the workspace with the upstream default file (or a
     * missing file), while the user saw a green install message.
     */
    const finalize = (outcome) => {
        if (stashedConfig !== null && !preserved) {
            return {
                ...outcome,
                ok: false,
                message: `Failed to restore operator-tuned ai_router/router-config.yaml after install (${lastRestoreError ?? "unknown error"}). The install changes have been applied but your tuned config was not put back. Check the workspace's ai_router/router-config.yaml before continuing.`,
                routerConfigPreserved: false,
            };
        }
        return outcome;
    };
    // 2) Sparse-clone into a temp dir.
    const repo = deps.repoUrl ?? exports.REPO_URL;
    opts.report(`Sparse-cloning ${repo}…`);
    const tmp = deps.fileOps.mkdtemp("dabbler-ai-router-install-");
    try {
        const cloneArgs = ["clone", "--depth", "1", "--filter=blob:none", "--sparse"];
        cloneArgs.push("--branch", refToUse);
        cloneArgs.push(repo, tmp);
        const cloneResult = await deps.spawner("git", cloneArgs, {
            cwd: deps.workspaceRoot,
            timeoutMs: 300000,
        });
        if (cloneResult.exitCode !== 0) {
            restoreStash();
            return finalize({
                ok: false,
                message: `git clone failed: ${oneLine(cloneResult.stderr || cloneResult.stdout) || `exit ${cloneResult.exitCode}`}`,
                source: "github",
                venvPath: opts.venvPath,
                routerConfigPreserved: preserved,
                resolvedRef: refToUse,
            });
        }
        opts.report("Configuring sparse-checkout…");
        const sparseResult = await deps.spawner("git", ["-C", tmp, "sparse-checkout", "set", "ai_router", "pyproject.toml"], { cwd: deps.workspaceRoot, timeoutMs: 60000 });
        if (sparseResult.exitCode !== 0) {
            restoreStash();
            return finalize({
                ok: false,
                message: `git sparse-checkout failed: ${oneLine(sparseResult.stderr || sparseResult.stdout) || `exit ${sparseResult.exitCode}`}`,
                source: "github",
                venvPath: opts.venvPath,
                routerConfigPreserved: preserved,
                resolvedRef: refToUse,
            });
        }
        // 3) Copy the sparse-checkout into the workspace at a stable
        //    location (.dabbler/ai-router-src/) AND the legacy
        //    ai_router/ position. The stable location is what the
        //    editable install points at — installing from a tmpdir that
        //    we then delete leaves a dangling .egg-link (Round 1 verifier
        //    catch). The workspace ai_router/ copy is the operator-facing
        //    location for fork-trackers who want to edit the source.
        const stableSrc = path.join(deps.workspaceRoot, exports.GITHUB_CHECKOUT_REL);
        const dstAiRouter = path.join(deps.workspaceRoot, "ai_router");
        opts.report("Copying sparse-checkout into the workspace…");
        try {
            deps.fileOps.removeRecursive(stableSrc);
            deps.fileOps.copyDir(tmp, stableSrc);
            // Wipe the destination ai_router/ before copying so files that
            // existed in an older ref but are gone in the new one don't
            // linger as ghosts. Round-2 verifier catch: copyDir overwrites
            // colliding files but never deletes; an upgrade from v0.9.0 to
            // v1.0.0 that drops a module would leave the dropped module
            // behind without this. The stashed router-config.yaml is
            // restored below, so this temporary wipe is safe.
            deps.fileOps.removeRecursive(dstAiRouter);
            deps.fileOps.copyDir(path.join(stableSrc, "ai_router"), dstAiRouter);
        }
        catch (err) {
            // restoreStash() runs in the outer finally too, but we want it
            // to happen *before* we return so the outcome reflects the
            // current state of the file.
            restoreStash();
            return finalize({
                ok: false,
                message: `Failed to copy ai_router/ into the workspace: ${err instanceof Error ? err.message : String(err)}`,
                source: "github",
                venvPath: opts.venvPath,
                routerConfigPreserved: preserved,
                resolvedRef: refToUse,
            });
        }
        // 4) Restore the stashed router-config.yaml *before* the editable
        //    install — the install doesn't touch the config, but having
        //    the file in its final state before the install completes is
        //    cleaner if the operator inspects the workspace mid-flow.
        restoreStash();
        // 5) Editable install of the persistent checkout so verifier
        //    scripts (`import ai_router`) work and the source tree is
        //    something the operator can edit-and-reload.
        opts.report("Installing the sparse-checked-out tree (editable)…");
        const pipResult = await deps.spawner(venvPython(opts.venvPath), ["-m", "pip", "install", "-e", stableSrc], { cwd: deps.workspaceRoot, timeoutMs: 300000 });
        if (pipResult.exitCode !== 0) {
            return finalize({
                ok: false,
                message: `pip install -e <sparse-checkout> failed: ${oneLine(pipResult.stderr || pipResult.stdout) || `exit ${pipResult.exitCode}`}`,
                source: "github",
                venvPath: opts.venvPath,
                routerConfigPreserved: preserved,
                resolvedRef: refToUse,
            });
        }
        writeInstallMethodMarker(deps, "github");
        return finalize({
            ok: true,
            message: `Installed ai_router from GitHub (${refToUse})${preserved ? " — preserved existing router-config.yaml" : ""}.`,
            source: "github",
            venvPath: opts.venvPath,
            routerConfigPreserved: preserved,
            resolvedRef: refToUse,
        });
    }
    finally {
        // Belt-and-braces: if any path above fell out without restoring
        // the stash, do it now. (Idempotent — when `preserved` is already
        // true, this is a no-op; when an earlier attempt failed, this
        // gives it a second crack now that any in-flight error has
        // unwound.) The actual data-loss safeguard sits in `finalize()`,
        // which downgrades ok=true outcomes to ok=false if the config
        // ultimately stayed unrestored.
        restoreStash();
        // Clean up the sparse-checkout tmpdir whether the install
        // succeeded or failed — the editable install resolves to
        // `.dabbler/ai-router-src/` (under the workspace), not the tmp.
        try {
            deps.fileOps.removeRecursive(tmp);
        }
        catch {
            // intentional swallow — the operator already has the
            // success/failure outcome above and the tmpdir is non-load-
            // bearing.
        }
    }
}
// ---------- install-method marker ----------
function readInstallMethodMarker(deps) {
    const markerAbs = path.join(deps.workspaceRoot, exports.INSTALL_METHOD_REL);
    if (!deps.fileOps.exists(markerAbs))
        return null;
    const raw = deps.fileOps.readFile(markerAbs).trim();
    if (raw === "pypi" || raw === "github")
        return raw;
    return null;
}
function writeInstallMethodMarker(deps, source) {
    const markerAbs = path.join(deps.workspaceRoot, exports.INSTALL_METHOD_REL);
    const markerDir = path.dirname(markerAbs);
    deps.fileOps.mkdirp(markerDir);
    // Single line + trailing newline so the file diffs cleanly if a future
    // version ever embeds extra metadata.
    deps.fileOps.writeFile(markerAbs, `${source}\n`);
}
// ---------- helpers ----------
function oneLine(s) {
    // Trim and collapse to the last few non-empty lines so the operator-facing
    // message reads cleanly even when pip / git emits a stack trace.
    const trimmed = (s || "").trim();
    if (!trimmed)
        return "";
    const lastLines = trimmed.split(/\r?\n/).filter(Boolean).slice(-2).join(" / ");
    return lastLines;
}
//# sourceMappingURL=aiRouterInstall.js.map
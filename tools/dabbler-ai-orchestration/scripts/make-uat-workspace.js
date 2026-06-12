#!/usr/bin/env node
// Set 062 Session 4 (spec D6) — assemble a disposable UAT workspace.
//
// Copies the committed fixture matrix (test-fixtures/uat-matrix/) into a
// fresh temp folder OUTSIDE the repo and prints the .code-workspace path
// to open. The copy is disposable: re-run the script for a clean one, or
// delete the printed folder when done. Nothing in the repo is touched,
// so the repo-level drift guards never see the generated copy.
//
//   npm run make-uat-workspace            (from tools/dabbler-ai-orchestration)
//
// Output is ASCII-only (Windows cp1252 console lesson).

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const MATRIX_DIR = path.resolve(__dirname, "..", "test-fixtures", "uat-matrix");
const WORKSPACE_FILE = "uat-matrix.code-workspace";

/**
 * The orchestration repo's own venv interpreter, when this checkout has
 * one. The fixture projects carry no `.venv`, so without a pinned
 * interpreter the python-backed row actions (Set Up Dedicated
 * Verification on completed sets, Migrate to v4 schema) would fall back
 * to bare `python` inside the generated workspace and fail on hosts
 * whose system python lacks `ai_router`. Returns null when the checkout
 * has no venv (the generated copy is then left unpinned).
 */
function repoVenvInterpreter() {
  const repoRoot = path.resolve(__dirname, "..", "..", "..");
  const interp =
    process.platform === "win32"
      ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
      : path.join(repoRoot, ".venv", "bin", "python");
  return fs.existsSync(interp) ? interp : null;
}

/**
 * Copy the matrix into a fresh temp dir and return the generated
 * workspace-file path. `targetParent` overrides the temp root so the
 * unit test can generate into its own sandbox.
 *
 * The generated (never the committed) `.code-workspace` gets
 * `dabblerSessionSets.pythonPath` pinned to this checkout's venv when
 * one exists, so the writer-backed row actions work in the disposable
 * workspace with zero operator setup.
 */
function makeUatWorkspace(targetParent) {
  if (!fs.existsSync(path.join(MATRIX_DIR, WORKSPACE_FILE))) {
    throw new Error(
      `fixture matrix not found at ${MATRIX_DIR} — run from a full checkout ` +
        "(the matrix is committed, not generated)."
    );
  }
  const parent = targetParent || os.tmpdir();
  const dest = fs.mkdtempSync(path.join(parent, "dabbler-uat-workspace-"));
  fs.cpSync(MATRIX_DIR, dest, { recursive: true });
  const workspacePath = path.join(dest, WORKSPACE_FILE);
  const interp = repoVenvInterpreter();
  if (interp) {
    const ws = JSON.parse(fs.readFileSync(workspacePath, "utf8"));
    ws.settings = ws.settings || {};
    ws.settings["dabblerSessionSets.pythonPath"] = interp;
    fs.writeFileSync(workspacePath, JSON.stringify(ws, null, 2) + "\n");
  }
  return workspacePath;
}

function main() {
  const workspacePath = makeUatWorkspace();
  const dest = path.dirname(workspacePath);
  console.log("[make-uat-workspace] Disposable UAT workspace generated.");
  console.log(`[make-uat-workspace]   folder:    ${dest}`);
  console.log(`[make-uat-workspace]   open this: ${workspacePath}`);
  const interp = repoVenvInterpreter();
  if (interp) {
    console.log(
      `[make-uat-workspace]   python:    pinned to ${interp} (writer-backed ` +
        "row actions work without setup)"
    );
  } else {
    console.log(
      "[make-uat-workspace]   python:    NOT pinned (no repo .venv found) - " +
        "writer-backed row actions need dabblerSessionSets.pythonPath set " +
        "to an interpreter with ai_router installed."
    );
  }
  console.log(
    "[make-uat-workspace] In VS Code: File > Open Workspace from File... " +
      "then open the Dabbler AI Orchestration view. See " +
      "test-fixtures/uat-matrix/README.md for what each row demonstrates."
  );
  console.log(
    "[make-uat-workspace] The copy is disposable - delete the folder (or " +
      "just re-run this script) when done."
  );
}

if (require.main === module) {
  main();
}

module.exports = { MATRIX_DIR, WORKSPACE_FILE, makeUatWorkspace, repoVenvInterpreter };

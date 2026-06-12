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
 * Copy the matrix into a fresh temp dir and return the generated
 * workspace-file path. `targetParent` overrides the temp root so the
 * unit test can generate into its own sandbox.
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
  return path.join(dest, WORKSPACE_FILE);
}

function main() {
  const workspacePath = makeUatWorkspace();
  const dest = path.dirname(workspacePath);
  console.log("[make-uat-workspace] Disposable UAT workspace generated.");
  console.log(`[make-uat-workspace]   folder:    ${dest}`);
  console.log(`[make-uat-workspace]   open this: ${workspacePath}`);
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

module.exports = { MATRIX_DIR, WORKSPACE_FILE, makeUatWorkspace };

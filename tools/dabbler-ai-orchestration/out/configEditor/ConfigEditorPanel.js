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
exports.ConfigEditorPanel = void 0;
exports.registerConfigEditorCommand = registerConfigEditorCommand;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const yamlReadWrite_1 = require("./yamlReadWrite");
const schemaValidator_1 = require("./schemaValidator");
const routingAndVerificationSection_1 = require("./sections/routingAndVerificationSection");
const budgetSection_1 = require("./sections/budgetSection");
const providersTableSection_1 = require("./sections/providersTableSection");
const significanceFlaggingSection_1 = require("./sections/significanceFlaggingSection");
const notificationsSection_1 = require("./sections/notificationsSection");
const localOverridesSummarySection_1 = require("./sections/localOverridesSummarySection");
const patch_1 = require("./patch");
function getNonce() {
    let text = "";
    const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (let i = 0; i < 32; i++)
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}
class ConfigEditorPanel {
    static createOrShow(context) {
        if (ConfigEditorPanel.currentPanel) {
            ConfigEditorPanel.currentPanel._panel.reveal(vscode.ViewColumn.One);
            ConfigEditorPanel.currentPanel._refresh();
            return;
        }
        const panel = vscode.window.createWebviewPanel("dabblerConfigEditor", "Dabbler Config Editor", vscode.ViewColumn.One, {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, "webview")],
        });
        ConfigEditorPanel.currentPanel = new ConfigEditorPanel(panel, context.extensionUri);
    }
    constructor(panel, extensionUri) {
        this._loaded = null;
        this._validation = null;
        this._parseIssues = [];
        this._lastSaveSnapshot = null;
        this._recovery = null;
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._loadFiles();
        this._panel.webview.html = this._getHtml();
        this._panel.onDidDispose(() => {
            ConfigEditorPanel.currentPanel = undefined;
        });
        this._panel.webview.onDidReceiveMessage((msg) => {
            switch (msg.command) {
                case "save":
                    this._handleSave(msg.payload);
                    break;
                case "refresh":
                    this._refresh();
                    break;
                case "runFlagCommand":
                    this._runFlagDecisionCommand();
                    break;
                case "openLocalOverrides":
                    this._openLocalOverridesFile();
                    break;
                case "retryFailedWrite":
                    this._retryFailedWrite();
                    break;
                case "acceptHalfBatch":
                    this._acceptHalfBatchAsBaseline();
                    break;
                case "reapplyLastSave":
                    this._reapplyLastSave();
                    break;
            }
        });
    }
    _findAiRouterDir() {
        const roots = vscode.workspace.workspaceFolders;
        if (!roots?.length)
            return null;
        for (const folder of roots) {
            const candidate = path.join(folder.uri.fsPath, "ai_router");
            if (fs.existsSync(candidate))
                return candidate;
        }
        return null;
    }
    _loadFiles() {
        const aiRouterDir = this._findAiRouterDir();
        if (!aiRouterDir) {
            this._loaded = null;
            this._validation = null;
            return;
        }
        const routerConfigPath = path.join(aiRouterDir, "router-config.yaml");
        const budgetPath = path.join(aiRouterDir, "budget.yaml");
        const localOverridesPath = path.join(aiRouterDir, "local-overrides.yaml");
        const routerResult = (0, yamlReadWrite_1.readYamlFile)(routerConfigPath);
        const budgetResult = (0, yamlReadWrite_1.readYamlFile)(budgetPath);
        const localResult = (0, yamlReadWrite_1.readYamlFile)(localOverridesPath);
        this._loaded = {
            routerConfigPath,
            budgetPath,
            localOverridesPath,
            localOverridesFileExists: localResult !== null,
            routerConfigDoc: routerResult?.doc ?? null,
            budgetDoc: budgetResult?.doc ?? null,
            localOverridesDoc: localResult?.doc ?? null,
            routerConfigText: routerResult?.text ?? null,
            budgetText: budgetResult?.text ?? null,
            localOverridesText: localResult?.text ?? null,
        };
        this._parseIssues = [];
        if (routerResult) {
            for (const err of routerResult.parseErrors) {
                this._parseIssues.push({ file: "router-config.yaml", err });
            }
        }
        if (budgetResult) {
            for (const err of budgetResult.parseErrors) {
                this._parseIssues.push({ file: "budget.yaml", err });
            }
        }
        if (localResult) {
            for (const err of localResult.parseErrors) {
                this._parseIssues.push({ file: "local-overrides.yaml", err });
            }
        }
        // Schema validation only on cleanly-parsed files.
        const routerHasParse = this._parseIssues.some((p) => p.file === "router-config.yaml");
        const budgetHasParse = this._parseIssues.some((p) => p.file === "budget.yaml");
        const localHasParse = this._parseIssues.some((p) => p.file === "local-overrides.yaml");
        const routerConfigObj = !routerHasParse
            ? (routerResult?.doc.toJSON() ?? null)
            : null;
        const budgetObj = !budgetHasParse
            ? (budgetResult?.doc.toJSON() ?? null)
            : null;
        const localObj = !localHasParse
            ? (localResult?.doc.toJSON() ?? null)
            : null;
        this._validation = (0, schemaValidator_1.validateBatch)({
            routerConfig: routerConfigObj,
            budget: budgetObj,
            localOverrides: localObj,
        });
        // Half-batch / external-drift detection: compare current on-disk content
        // hashes to the last successful save snapshot. If we have a snapshot and
        // any file's hash has changed, surface the recovery banner.
        this._recovery = this._detectDrift();
    }
    _detectDrift() {
        if (!this._lastSaveSnapshot || !this._loaded)
            return null;
        const drifted = [];
        const currentRouter = this._loaded.routerConfigText
            ? (0, patch_1.stringContentHash)(this._loaded.routerConfigText)
            : null;
        const currentBudget = this._loaded.budgetText
            ? (0, patch_1.stringContentHash)(this._loaded.budgetText)
            : null;
        const currentLocal = this._loaded.localOverridesText
            ? (0, patch_1.stringContentHash)(this._loaded.localOverridesText)
            : null;
        if (currentRouter && currentRouter !== this._lastSaveSnapshot.routerConfigHash) {
            drifted.push("router-config.yaml");
        }
        if (currentBudget && currentBudget !== this._lastSaveSnapshot.budgetHash) {
            drifted.push("budget.yaml");
        }
        if (currentLocal !== this._lastSaveSnapshot.localOverridesHash &&
            // Only flag drift if either side knew about a local-overrides hash
            (currentLocal !== null || this._lastSaveSnapshot.localOverridesHash !== null)) {
            drifted.push("local-overrides.yaml");
        }
        if (drifted.length === 0)
            return null;
        return { succeeded: [], failed: [], drifted };
    }
    _deriveState() {
        if (!this._loaded) {
            return {
                routerConfig: null,
                budget: null,
                localOverrides: null,
                envVarPresence: {},
                localOverridesFileExists: false,
            };
        }
        const routerObj = this._loaded.routerConfigDoc?.toJSON() ?? null;
        const budgetObj = this._loaded.budgetDoc?.toJSON() ?? null;
        const localObj = this._loaded.localOverridesDoc?.toJSON() ?? null;
        // Collect every env var name referenced in providers + notifications
        const envVars = new Set();
        const sharedProviders = (routerObj && typeof routerObj === "object" ? routerObj["providers"] : null);
        if (sharedProviders) {
            for (const v of Object.values(sharedProviders)) {
                const ent = v;
                if (typeof ent?.api_key_env === "string")
                    envVars.add(ent.api_key_env);
            }
        }
        const localProviders = (localObj && typeof localObj === "object" ? localObj["providers"] : null);
        if (localProviders) {
            for (const v of Object.values(localProviders)) {
                const ent = v;
                if (typeof ent?.api_key_env === "string")
                    envVars.add(ent.api_key_env);
            }
        }
        const pushover = localObj && typeof localObj === "object"
            ? localObj["notifications"]?.["pushover"]
            : undefined;
        if (pushover) {
            if (typeof pushover.api_key_env === "string")
                envVars.add(pushover.api_key_env);
            if (typeof pushover.user_key_env === "string")
                envVars.add(pushover.user_key_env);
        }
        const envVarPresence = {};
        for (const name of envVars) {
            const v = process.env[name];
            envVarPresence[name] = typeof v === "string" && v.length > 0;
        }
        return {
            routerConfig: routerObj,
            budget: budgetObj,
            localOverrides: localObj,
            envVarPresence,
            localOverridesFileExists: this._loaded.localOverridesFileExists,
        };
    }
    _handleSave(payload) {
        if (!this._loaded) {
            vscode.window.showErrorMessage("No config files loaded.");
            return;
        }
        if (this._parseIssues.length > 0) {
            vscode.window.showErrorMessage(`Save aborted — ${this._parseIssues.length} YAML parse error(s). Fix the parse errors in the source files before saving.`);
            return;
        }
        if (!payload) {
            vscode.window.showErrorMessage("Save aborted — no payload from webview.");
            return;
        }
        // 1) Ensure all three Documents exist. If the operator's save introduces
        //    a local override and local-overrides.yaml doesn't exist on disk yet,
        //    create an in-memory Document.
        if (!this._loaded.routerConfigDoc || !this._loaded.budgetDoc) {
            vscode.window.showErrorMessage("Save aborted — required config files are missing.");
            return;
        }
        if (!this._loaded.localOverridesDoc) {
            this._loaded.localOverridesDoc = (0, patch_1.emptyLocalOverridesDoc)();
        }
        // 2) Apply the patch to the in-memory yaml docs.
        let applyResult;
        try {
            applyResult = (0, patch_1.applyPatch)(this._loaded.routerConfigDoc, this._loaded.budgetDoc, this._loaded.localOverridesDoc, payload);
        }
        catch (err) {
            vscode.window.showErrorMessage(`Save aborted — patch application failed: ${err instanceof Error ? err.message : String(err)}`);
            return;
        }
        // 3) Pre-validate the in-memory batch.
        const routerObj = this._loaded.routerConfigDoc.toJSON() ?? null;
        const budgetObj = this._loaded.budgetDoc.toJSON() ?? null;
        const localObj = this._loaded.localOverridesDoc.toJSON() ?? null;
        const validation = (0, schemaValidator_1.validateBatch)({ routerConfig: routerObj, budget: budgetObj, localOverrides: localObj });
        if (!validation.valid) {
            const msgs = validation.errors.map((e) => `${e.file}${e.path}: ${e.message}`).join("\n");
            vscode.window.showErrorMessage(`Save aborted — ${validation.errors.length} validation error(s):\n${msgs}`, { modal: false });
            return;
        }
        // 4) Write each file. Track per-file success/failure for half-batch recovery.
        const succeeded = [];
        const failed = [];
        const tryWrite = (file, target, doc, write) => {
            if (!write)
                return;
            try {
                (0, yamlReadWrite_1.writeYamlFile)(target, doc);
                succeeded.push(file);
            }
            catch (err) {
                failed.push({
                    file,
                    reason: err instanceof Error ? err.message : String(err),
                });
            }
        };
        tryWrite("router-config.yaml", this._loaded.routerConfigPath, this._loaded.routerConfigDoc, applyResult.routerConfigChanged);
        tryWrite("budget.yaml", this._loaded.budgetPath, this._loaded.budgetDoc, applyResult.budgetChanged);
        // local-overrides: only write if the in-memory doc has any content OR the file already exists.
        const localJson = this._loaded.localOverridesDoc.toJSON();
        const localHasContent = localJson && Object.keys(localJson).length > 0;
        const shouldWriteLocal = applyResult.localOverridesChanged && (localHasContent || this._loaded.localOverridesFileExists);
        tryWrite("local-overrides.yaml", this._loaded.localOverridesPath, this._loaded.localOverridesDoc, shouldWriteLocal);
        if (failed.length > 0 && succeeded.length > 0) {
            // Half-batch failure. Surface a recovery banner on the next render.
            this._recovery = { succeeded, failed, drifted: [] };
            this._refresh();
            vscode.window.showErrorMessage(`Partial save — ${succeeded.length} file(s) saved, ${failed.length} failed. See the recovery banner in the editor.`);
            return;
        }
        if (failed.length > 0) {
            // All writes that were attempted failed; nothing got through.
            this._refresh();
            vscode.window.showErrorMessage(`Save failed: ${failed.map((f) => `${f.file}: ${f.reason}`).join("; ")}`);
            return;
        }
        // 5) Update last-save snapshot for drift detection.
        const routerHash = this._loaded.routerConfigDoc
            ? (0, patch_1.stringContentHash)(this._loaded.routerConfigDoc.toString())
            : "";
        const budgetHash = this._loaded.budgetDoc
            ? (0, patch_1.stringContentHash)(this._loaded.budgetDoc.toString())
            : "";
        const localHash = shouldWriteLocal && this._loaded.localOverridesDoc
            ? (0, patch_1.stringContentHash)(this._loaded.localOverridesDoc.toString())
            : null;
        this._lastSaveSnapshot = {
            routerConfigHash: routerHash,
            budgetHash: budgetHash,
            localOverridesHash: localHash,
            at: Date.now(),
        };
        if (applyResult.warnings.length > 0) {
            vscode.window.showWarningMessage(applyResult.warnings.join(" "));
        }
        vscode.window.showInformationMessage("Dabbler config saved.");
        this._refresh();
    }
    _retryFailedWrite() {
        if (!this._recovery || this._recovery.failed.length === 0 || !this._loaded)
            return;
        const stillFailed = [];
        const newSucceeded = [...this._recovery.succeeded];
        for (const f of this._recovery.failed) {
            let target = null;
            let doc = null;
            if (f.file === "router-config.yaml") {
                target = this._loaded.routerConfigPath;
                doc = this._loaded.routerConfigDoc;
            }
            else if (f.file === "budget.yaml") {
                target = this._loaded.budgetPath;
                doc = this._loaded.budgetDoc;
            }
            else if (f.file === "local-overrides.yaml") {
                target = this._loaded.localOverridesPath;
                doc = this._loaded.localOverridesDoc;
            }
            if (!target || !doc) {
                stillFailed.push({ file: f.file, reason: "internal: no target/doc" });
                continue;
            }
            try {
                (0, yamlReadWrite_1.writeYamlFile)(target, doc);
                newSucceeded.push(f.file);
            }
            catch (err) {
                stillFailed.push({ file: f.file, reason: err instanceof Error ? err.message : String(err) });
            }
        }
        if (stillFailed.length === 0) {
            this._recovery = null;
            vscode.window.showInformationMessage("Retry succeeded — all files saved.");
        }
        else {
            this._recovery = { succeeded: newSucceeded, failed: stillFailed, drifted: [] };
            vscode.window.showErrorMessage(`Retry partial — ${stillFailed.length} file(s) still failing.`);
        }
        this._refresh();
    }
    _acceptHalfBatchAsBaseline() {
        // Operator chose to accept the current on-disk state as the new baseline.
        // Clear recovery state and re-snapshot to current contents.
        this._recovery = null;
        if (this._loaded) {
            this._lastSaveSnapshot = {
                routerConfigHash: this._loaded.routerConfigText
                    ? (0, patch_1.stringContentHash)(this._loaded.routerConfigText)
                    : "",
                budgetHash: this._loaded.budgetText
                    ? (0, patch_1.stringContentHash)(this._loaded.budgetText)
                    : "",
                localOverridesHash: this._loaded.localOverridesText
                    ? (0, patch_1.stringContentHash)(this._loaded.localOverridesText)
                    : null,
                at: Date.now(),
            };
        }
        this._refresh();
        vscode.window.showInformationMessage("On-disk state accepted as new baseline.");
    }
    _reapplyLastSave() {
        // The drifted state is what's currently in memory (re-read from disk).
        // "Re-apply" means: write the in-memory docs back out. This is a no-op
        // for a single-process editor; for true cross-load recovery it would
        // re-apply the cached snapshot. For Session 5 scope, this just re-writes
        // the current in-memory docs so the operator can confirm the editor's
        // view becomes the disk truth.
        if (!this._loaded)
            return;
        try {
            if (this._loaded.routerConfigDoc) {
                (0, yamlReadWrite_1.writeYamlFile)(this._loaded.routerConfigPath, this._loaded.routerConfigDoc);
            }
            if (this._loaded.budgetDoc) {
                (0, yamlReadWrite_1.writeYamlFile)(this._loaded.budgetPath, this._loaded.budgetDoc);
            }
            if (this._loaded.localOverridesDoc) {
                const localJson = this._loaded.localOverridesDoc.toJSON();
                if (localJson && Object.keys(localJson).length > 0) {
                    (0, yamlReadWrite_1.writeYamlFile)(this._loaded.localOverridesPath, this._loaded.localOverridesDoc);
                }
            }
            this._recovery = null;
            vscode.window.showInformationMessage("In-memory state re-applied to disk.");
            this._refresh();
        }
        catch (err) {
            vscode.window.showErrorMessage(`Re-apply failed: ${err instanceof Error ? err.message : String(err)}`);
        }
    }
    async _runFlagDecisionCommand() {
        const all = await vscode.commands.getCommands();
        if (all.includes("dabbler.flagDecisionForReview")) {
            await vscode.commands.executeCommand("dabbler.flagDecisionForReview");
            return;
        }
        vscode.window.showInformationMessage("dabbler.flagDecisionForReview is not registered yet — it ships in Set 026 Session 6. " +
            "Until then, hand-edit the active session-set's decision-review-queue.jsonl directly.");
    }
    async _openLocalOverridesFile() {
        if (!this._loaded)
            return;
        const target = this._loaded.localOverridesPath;
        if (!fs.existsSync(target)) {
            vscode.window.showInformationMessage("local-overrides.yaml does not exist yet. Save any per-operator override and the file is created automatically.");
            return;
        }
        const doc = await vscode.workspace.openTextDocument(target);
        await vscode.window.showTextDocument(doc);
    }
    _refresh() {
        this._loadFiles();
        this._panel.webview.html = this._getHtml();
    }
    _getHtml() {
        const nonce = getNonce();
        const cspSource = this._panel.webview.cspSource;
        if (!this._loaded) {
            return this._noWorkspaceHtml(nonce, cspSource);
        }
        const hasRouterConfig = this._loaded.routerConfigDoc !== null;
        const hasBudget = this._loaded.budgetDoc !== null;
        if (!hasRouterConfig) {
            return this._missingFilesHtml(nonce, cspSource, this._loaded.routerConfigPath);
        }
        if (!hasBudget) {
            return this._missingFilesHtml(nonce, cspSource, this._loaded.budgetPath);
        }
        const validationPassed = this._validation?.valid ?? false;
        const errors = this._validation?.errors ?? [];
        const parseIssues = this._parseIssues;
        const hasParseIssues = parseIssues.length > 0;
        const savedStatus = this._lastSaveSnapshot
            ? `All changes saved (${new Date(this._lastSaveSnapshot.at).toLocaleTimeString()}).`
            : "No unsaved changes.";
        const fileList = [
            "ai_router/router-config.yaml",
            hasBudget ? "ai_router/budget.yaml" : null,
            this._loaded.localOverridesFileExists ? "ai_router/local-overrides.yaml" : null,
        ]
            .filter(Boolean)
            .join(" + ");
        const parseBanner = hasParseIssues
            ? `<div class="banner banner-error">
          <strong>&#9888; YAML parse error</strong> — ${parseIssues.length} parse issue(s). Save is blocked until resolved.
          <ul>${parseIssues
                .map((p) => `<li><code>${p.file}</code>${p.err.line != null ? ` (line ${p.err.line})` : ""}: ${escapeHtml(p.err.message)}</li>`)
                .join("")}</ul>
        </div>`
            : "";
        const driftBanner = !validationPassed && !hasParseIssues
            ? `<div class="banner banner-error">
          <strong>&#9888; Drift detected</strong> — ${errors.length} validation error(s). Sections remain editable but Save will reject until fixed.
          <ul>${errors.map((e) => `<li><code>${escapeHtml(e.file + e.path)}</code>: ${escapeHtml(e.message)}</li>`).join("")}</ul>
        </div>`
            : "";
        const recoveryBanner = this._recovery ? this._renderRecoveryBanner(this._recovery) : "";
        const state = this._deriveState();
        const s1 = (0, routingAndVerificationSection_1.render)(state);
        const s2 = (0, budgetSection_1.render)(state);
        const s3 = (0, providersTableSection_1.render)(state);
        const s4 = (0, significanceFlaggingSection_1.render)(state);
        const s5 = (0, notificationsSection_1.render)(state);
        const s6 = (0, localOverridesSummarySection_1.render)(state);
        const sections = [
            { num: 1, label: "Routing &amp; Verification", body: s1.html },
            { num: 2, label: "Budget", body: s2.html },
            { num: 3, label: "Providers", body: s3.html },
            { num: 4, label: "Significance flagging", body: s4.html },
            { num: 5, label: "Notifications", body: s5.html },
            { num: 6, label: "Local overrides summary", body: s6.html },
        ];
        const sectionNav = sections
            .map((s) => `<button class="section-btn" data-section="${s.num}">&rsaquo; ${s.label}</button>`)
            .join("\n");
        const sectionContent = sections
            .map((s) => `<div class="section-panel" id="section-${s.num}" style="display:${s.num === 1 ? "block" : "none"}">
          <h2>${s.label}</h2>
          ${s.body}
        </div>`)
            .join("\n");
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src ${cspSource} 'unsafe-inline';">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Dabbler Config Editor</title>
  <style>
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); background: var(--vscode-editor-background); margin: 0; padding: 0; }
    .header { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: var(--vscode-sideBarSectionHeader-background); border-bottom: 1px solid var(--vscode-panel-border); }
    .header h1 { font-size: 1em; margin: 0; }
    .header-actions { display: flex; gap: 8px; }
    .meta { padding: 6px 16px; font-size: 0.85em; color: var(--vscode-descriptionForeground); border-bottom: 1px solid var(--vscode-panel-border); }
    .banner { padding: 8px 16px; margin: 8px 16px; border-radius: 3px; font-size: 0.85em; }
    .banner ul { margin: 4px 0 0 16px; padding: 0; }
    .banner-error { background: var(--vscode-inputValidation-errorBackground); border: 1px solid var(--vscode-inputValidation-errorBorder); }
    .banner-warning { background: var(--vscode-inputValidation-warningBackground); border: 1px solid var(--vscode-inputValidation-warningBorder); }
    .layout { display: flex; min-height: calc(100vh - 80px); }
    .nav { width: 220px; min-width: 180px; border-right: 1px solid var(--vscode-panel-border); padding: 8px 0; display: flex; flex-direction: column; }
    .section-btn { background: none; border: none; color: var(--vscode-foreground); padding: 6px 16px; text-align: left; cursor: pointer; font-size: 0.9em; width: 100%; }
    .section-btn:hover, .section-btn.active { background: var(--vscode-list-hoverBackground); }
    .section-btn.active { color: var(--vscode-list-activeSelectionForeground); background: var(--vscode-list-activeSelectionBackground); }
    .content { flex: 1; padding: 16px; overflow-y: auto; }
    .section-panel h2 { font-size: 1.1em; margin-top: 0; margin-bottom: 16px; }
    .section-block { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--vscode-panel-border); }
    .section-block h3 { font-size: 1em; margin-bottom: 6px; }
    .section-help { color: var(--vscode-descriptionForeground); font-size: 0.85em; margin: 0 0 10px 0; }
    .section-info { color: var(--vscode-descriptionForeground); font-size: 0.85em; margin: 6px 0; font-style: italic; }
    .field-row { display: flex; align-items: center; gap: 8px; margin: 6px 0; flex-wrap: wrap; }
    .field-row label { min-width: 140px; }
    .field-row input[type="number"], .field-row input[type="text"], .field-row select { padding: 2px 6px; }
    .src-indicator { font-size: 0.78em; padding: 1px 4px; border-radius: 2px; cursor: pointer; }
    .src-shared { color: var(--vscode-descriptionForeground); background: rgba(127,127,127,0.1); }
    .src-local { color: var(--vscode-charts-orange); background: rgba(255,150,0,0.1); }
    .src-default { color: var(--vscode-descriptionForeground); background: rgba(127,127,127,0.05); cursor: default; }
    .env-badge { font-size: 0.85em; padding: 1px 4px; border-radius: 2px; }
    .env-set { color: var(--vscode-charts-green); }
    .env-unset { color: var(--vscode-descriptionForeground); font-style: italic; }
    .placeholder { color: var(--vscode-descriptionForeground); font-style: italic; }
    .preview-block { background: rgba(127,127,127,0.06); padding: 8px 12px; border-radius: 3px; }
    .preview-block p { margin: 6px 0; }
    .preview-detail { color: var(--vscode-descriptionForeground); }
    .slider-value { min-width: 40px; font-variant-numeric: tabular-nums; }
    .provider-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    .provider-table th, .provider-table td { padding: 4px 6px; text-align: left; border-bottom: 1px solid var(--vscode-panel-border); vertical-align: middle; }
    .provider-table th { font-size: 0.85em; color: var(--vscode-descriptionForeground); }
    .provider-row input[type="text"] { width: 100%; }
    .legend { font-size: 0.8em; color: var(--vscode-descriptionForeground); margin-top: 8px; }
    .command-box { background: var(--vscode-textCodeBlock-background, rgba(127,127,127,0.1)); padding: 6px 10px; border-radius: 3px; margin: 4px 0; }
    .code-sample { background: var(--vscode-textCodeBlock-background, rgba(127,127,127,0.1)); padding: 8px 10px; border-radius: 3px; margin: 6px 0; }
    .numbered-list { padding-left: 18px; }
    .numbered-list li { margin-bottom: 12px; }
    .override-list { list-style: none; padding-left: 0; }
    .override-row { background: rgba(127,127,127,0.06); padding: 8px 12px; margin: 6px 0; border-radius: 3px; }
    .override-path { font-weight: bold; margin-bottom: 4px; }
    .override-side { font-size: 0.9em; margin: 2px 0; }
    button.primary { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 4px 12px; cursor: pointer; border-radius: 2px; font-size: 0.9em; }
    button.primary:hover { background: var(--vscode-button-hoverBackground); }
    button.secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); border: none; padding: 4px 12px; cursor: pointer; border-radius: 2px; font-size: 0.9em; }
    button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Dabbler Config Editor</h1>
    <div class="header-actions">
      <button class="primary" id="btn-save">Save</button>
    </div>
  </div>
  <div class="meta">
    Editing: <strong>${escapeHtml(fileList)}</strong> &nbsp;|&nbsp; ${escapeHtml(savedStatus)}
  </div>
  ${parseBanner}
  ${driftBanner}
  ${recoveryBanner}
  <div class="layout">
    <div class="nav">
      ${sectionNav}
    </div>
    <div class="content">
      ${sectionContent}
    </div>
  </div>
  <script nonce="${nonce}">
    (function() {
      const vscode = acquireVsCodeApi();

      // --- Section nav ---
      const buttons = document.querySelectorAll('.section-btn');
      const panels = document.querySelectorAll('.section-panel');
      buttons.forEach((btn, i) => {
        if (i === 0) btn.classList.add('active');
        btn.addEventListener('click', () => {
          buttons.forEach(b => b.classList.remove('active'));
          panels.forEach(p => { p.style.display = 'none'; });
          btn.classList.add('active');
          const sectionNum = btn.getAttribute('data-section');
          const panel = document.getElementById('section-' + sectionNum);
          if (panel) panel.style.display = 'block';
        });
      });

      // --- §1 dropdown constraint: outsourcing-mode -> verification options ---
      const outsourcingSel = document.getElementById('s1-outsourcing-mode');
      const verificationSel = document.getElementById('s1-verification-method');
      const apiConstraintInfo = document.getElementById('s1-api-constraint');
      const manualTemplate = document.getElementById('s1-manual-template');
      function applyOutsourcingConstraint() {
        if (!outsourcingSel || !verificationSel) return;
        const disabled = outsourcingSel.value === 'disabled';
        const apiOpt = verificationSel.querySelector('option[value="api"]');
        if (apiOpt) apiOpt.disabled = disabled;
        if (apiConstraintInfo) apiConstraintInfo.style.display = disabled ? '' : 'none';
        if (disabled && verificationSel.value === 'api') {
          verificationSel.value = 'manual-via-other-engine';
        }
      }
      function applyManualTemplateVisibility() {
        if (!verificationSel || !manualTemplate) return;
        manualTemplate.style.display = verificationSel.value === 'manual-via-other-engine' ? '' : 'none';
      }
      if (outsourcingSel) outsourcingSel.addEventListener('change', () => { applyOutsourcingConstraint(); applyManualTemplateVisibility(); });
      if (verificationSel) verificationSel.addEventListener('change', applyManualTemplateVisibility);
      applyOutsourcingConstraint();
      applyManualTemplateVisibility();

      // --- §2 slider live update + preview re-render ---
      const warnSlider = document.getElementById('s2-warn-at-percent');
      const warnValueEl = document.getElementById('s2-warn-at-percent-value');
      const thresholdInput = document.getElementById('s2-threshold-usd');
      const previewBlock = document.getElementById('s2-preview');
      function fmtUsd(n) { return '$' + (Math.round(n * 100) / 100).toFixed(2); }
      function rerenderPreview() {
        if (!warnSlider || !thresholdInput || !previewBlock) return;
        const pct = Number(warnSlider.value);
        const thr = Number(thresholdInput.value);
        const warn = (pct * thr) / 100;
        if (warnValueEl) warnValueEl.textContent = pct + '%';
        previewBlock.innerHTML =
          '<p><strong>Below ' + pct + '% of ' + fmtUsd(thr) + ' (' + fmtUsd(warn) + '):</strong> ' +
          '<span class="preview-detail">Silent &mdash; no prompt, just log to cost dashboard.</span></p>' +
          '<p><strong>Between ' + pct + '% and 100% (' + fmtUsd(warn) + '&ndash;' + fmtUsd(thr) + '):</strong> ' +
          '<span class="preview-detail">Heads-up &mdash; non-blocking notification, one per band.</span></p>' +
          '<p><strong>At or above ' + fmtUsd(thr) + ':</strong> ' +
          '<span class="preview-detail">Confirm-or-abort &mdash; modal dialog before the call proceeds.</span></p>';
      }
      if (warnSlider) warnSlider.addEventListener('input', rerenderPreview);
      if (thresholdInput) thresholdInput.addEventListener('input', rerenderPreview);

      // --- §3 provider popover toggle ---
      document.querySelectorAll('.popover-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
          const target = btn.getAttribute('data-target');
          if (!target) return;
          const row = document.getElementById(target);
          if (row) row.style.display = row.style.display === 'none' ? '' : 'none';
        });
      });

      // --- §4 run-flag-command button ---
      const flagBtn = document.getElementById('s4-run-flag-command');
      if (flagBtn) flagBtn.addEventListener('click', () => { vscode.postMessage({ command: 'runFlagCommand' }); });

      // --- §6 open-local-overrides button ---
      const openLocalBtn = document.getElementById('s6-open-local-overrides');
      if (openLocalBtn) openLocalBtn.addEventListener('click', () => { vscode.postMessage({ command: 'openLocalOverrides' }); });

      // --- recovery banner buttons ---
      const retryBtn = document.getElementById('recovery-retry');
      const acceptBtn = document.getElementById('recovery-accept');
      const reapplyBtn = document.getElementById('recovery-reapply');
      if (retryBtn) retryBtn.addEventListener('click', () => { vscode.postMessage({ command: 'retryFailedWrite' }); });
      if (acceptBtn) acceptBtn.addEventListener('click', () => { vscode.postMessage({ command: 'acceptHalfBatch' }); });
      if (reapplyBtn) reapplyBtn.addEventListener('click', () => { vscode.postMessage({ command: 'reapplyLastSave' }); });

      // --- (shared)/(local override) toggle ---
      document.querySelectorAll('.src-indicator').forEach(ind => {
        const source = ind.getAttribute('data-source');
        if (source === 'not-overridable' || source === 'default') return;
        ind.addEventListener('click', () => {
          const cur = ind.getAttribute('data-source');
          const next = cur === 'local' ? 'shared' : 'local';
          ind.setAttribute('data-source', next);
          ind.className = 'src-indicator src-' + next;
          ind.textContent = next === 'local' ? '(local override)' : '(shared)';
        });
      });

      // --- Save gather ---
      function gatherPayload() {
        const payload = {};
        // §1
        if (outsourcingSel) {
          const ind = outsourcingSel.parentElement && outsourcingSel.parentElement.querySelector('.src-indicator');
          const src = (ind && ind.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          payload.outsourcingMode = { value: outsourcingSel.value, source: src };
        }
        if (verificationSel) payload.verificationMethod = verificationSel.value;
        // §2
        if (thresholdInput) {
          const ind = thresholdInput.parentElement && thresholdInput.parentElement.querySelector('.src-indicator');
          const src = (ind && ind.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          payload.thresholdUsd = { value: Number(thresholdInput.value), source: src };
        }
        const scopeSel = document.getElementById('s2-scope');
        if (scopeSel) payload.scope = scopeSel.value;
        if (warnSlider) {
          const ind = warnSlider.parentElement && warnSlider.parentElement.querySelector('.src-indicator');
          const src = (ind && ind.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          payload.warnAtPercent = { value: Number(warnSlider.value), source: src };
        }
        // §3 providers
        const providerRows = document.querySelectorAll('tr.provider-row');
        payload.providers = [];
        providerRows.forEach(row => {
          const id = row.getAttribute('data-provider-id');
          if (!id) return;
          const enabledInput = row.querySelector('input[data-field="enabled"]');
          const labelInput = row.querySelector('input[data-field="displayLabel"]');
          const keyInput = row.querySelector('input[data-field="apiKeyEnv"]');
          const urlInput = row.querySelector('input[data-field="baseUrl"]');
          const enabledInd = enabledInput && enabledInput.parentElement && enabledInput.parentElement.querySelector('.src-indicator');
          const enabledSrc = (enabledInd && enabledInd.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          const keyInd = keyInput && keyInput.parentElement && keyInput.parentElement.querySelector('.src-indicator');
          const keySrc = (keyInd && keyInd.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          const urlInd = urlInput && urlInput.parentElement && urlInput.parentElement.querySelector('.src-indicator');
          const urlSrc = (urlInd && urlInd.getAttribute('data-source') === 'local') ? 'local' : 'shared';
          const pp = { id: id };
          if (enabledInput) pp.enabled = { value: !!enabledInput.checked, source: enabledSrc };
          if (labelInput) pp.displayLabel = labelInput.value;
          if (keyInput) pp.apiKeyEnv = { value: keyInput.value, source: keySrc };
          if (urlInput) pp.baseUrl = { value: urlInput.value, source: urlSrc };
          payload.providers.push(pp);
        });
        // §4
        const honorChk = document.getElementById('s4-honor-annotations');
        if (honorChk) payload.honorAnnotations = !!honorChk.checked;
        // §5
        const puEnabled = document.getElementById('s5-pushover-enabled');
        const puApiKey = document.getElementById('s5-pushover-api-key-env');
        const puUserKey = document.getElementById('s5-pushover-user-key-env');
        if (puEnabled) payload.pushoverEnabled = !!puEnabled.checked;
        if (puApiKey) payload.pushoverApiKeyEnv = puApiKey.value;
        if (puUserKey) payload.pushoverUserKeyEnv = puUserKey.value;
        return payload;
      }
      document.getElementById('btn-save').addEventListener('click', () => {
        const payload = gatherPayload();
        vscode.postMessage({ command: 'save', payload: payload });
      });
    })();
  </script>
</body>
</html>`;
    }
    _renderRecoveryBanner(r) {
        if (r.failed.length > 0 && r.succeeded.length > 0) {
            const succeededList = r.succeeded.map((f) => `<code>${f}</code>`).join(", ");
            const failedList = r.failed
                .map((f) => `<li><code>${f.file}</code>: ${escapeHtml(f.reason)}</li>`)
                .join("");
            return `<div class="banner banner-warning">
          <strong>&#9888; Half-batch save</strong> — ${r.succeeded.length} file(s) saved (${succeededList}); ${r.failed.length} failed.
          <ul>${failedList}</ul>
          <div style="margin-top:8px;display:flex;gap:8px;">
            <button id="recovery-retry" class="primary">Retry failed write</button>
            <button id="recovery-accept" class="secondary">Accept current state as new baseline</button>
          </div>
        </div>`;
        }
        if (r.drifted.length > 0) {
            const driftedList = r.drifted.map((f) => `<code>${f}</code>`).join(", ");
            return `<div class="banner banner-warning">
          <strong>&#9888; External modification detected</strong> — ${r.drifted.length} file(s) changed on disk since your last save: ${driftedList}.
          <div style="margin-top:8px;display:flex;gap:8px;">
            <button id="recovery-reapply" class="secondary">Re-apply my last save (overwrites on-disk)</button>
            <button id="recovery-accept" class="secondary">Accept on-disk as new baseline</button>
          </div>
        </div>`;
        }
        return "";
    }
    _noWorkspaceHtml(nonce, cspSource) {
        return `<!DOCTYPE html><html lang="en"><head>
      <meta charset="UTF-8">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'unsafe-inline';">
      <title>Dabbler Config Editor</title>
      <style>body{font-family:var(--vscode-font-family);padding:16px;color:var(--vscode-foreground);background:var(--vscode-editor-background);}</style>
    </head><body>
      <h1>Dabbler Config Editor</h1>
      <p>No workspace folder is open. Open a folder containing an <code>ai_router/</code> directory to use the config editor.</p>
    </body></html>`;
    }
    _missingFilesHtml(nonce, cspSource, missingFilePath) {
        const fileName = path.basename(missingFilePath);
        return `<!DOCTYPE html><html lang="en"><head>
      <meta charset="UTF-8">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'unsafe-inline';">
      <title>Dabbler Config Editor</title>
      <style>body{font-family:var(--vscode-font-family);padding:16px;color:var(--vscode-foreground);background:var(--vscode-editor-background);}</style>
    </head><body>
      <h1>Dabbler Config Editor</h1>
      <p>Could not find <code>${escapeHtml(fileName)}</code> at:<br><code>${escapeHtml(missingFilePath)}</code></p>
      <p>Run the Dabbler project setup wizard to create the config files, or create them manually.</p>
    </body></html>`;
    }
}
exports.ConfigEditorPanel = ConfigEditorPanel;
function registerConfigEditorCommand(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.openConfigEditor", () => {
        ConfigEditorPanel.createOrShow(context);
    }));
}
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
//# sourceMappingURL=ConfigEditorPanel.js.map
"use strict";
// Manual-override quickpick stub (Session 2 placeholder).
//
// The full implementation lands in Session 3 (per Set 029 spec) with
// MRU + multi-step flow + hotkey-bindable args + force-override
// confirmation. Session 2 ships the command identifier so the webview's
// install-CTA can dispatch to it via `dabbler.setOrchestrator`.
//
// Until Session 3 ships, the command surfaces a "coming in 0.14.x"
// message rather than a no-op silent failure — operators clicking
// through the empty-state CTA flow shouldn't think they hit a dead end.
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
exports.registerSetOrchestratorManualStub = registerSetOrchestratorManualStub;
const vscode = __importStar(require("vscode"));
function registerSetOrchestratorManualStub(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.setOrchestrator", async () => {
        const picked = await vscode.window.showInformationMessage("Manual orchestrator override lands in the next release (Session 3 of " +
            "Set 029). For now, install the Claude Code SessionStart hook to get " +
            "live signal, or set the marker file by hand at ~/.dabbler/current-orchestrator.json.", "Install Claude Code hook");
        if (picked === "Install Claude Code hook") {
            vscode.commands.executeCommand("dabbler.installOrchestratorHook.claudeCode");
        }
    }));
}
//# sourceMappingURL=setOrchestratorManualStub.js.map
"use strict";
// Opens ~/.dabbler/orchestrator-writer.log for operator diagnostics.
//
// The marker writer (scripts/write-orchestrator-marker.js) appends one
// JSON-lines entry per skipped write so the operator can see why a
// configured-default Codex signal didn't make it through (or why a
// manual quickpick was overridden by a live SessionStart). The log is
// best-effort — losing it doesn't change behavior, just visibility.
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
exports.registerOpenOrchestratorWriterLog = registerOpenOrchestratorWriterLog;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
function registerOpenOrchestratorWriterLog(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.openOrchestratorWriterLog", async () => {
        const logPath = path.join(os.homedir(), ".dabbler", "orchestrator-writer.log");
        if (!fs.existsSync(logPath)) {
            vscode.window.showInformationMessage(`No writer log yet — ${logPath} hasn't been touched. ` +
                `Logged entries appear when a marker write is skipped (e.g., ` +
                `a configured-default Codex signal blocked by a fresh Claude SessionStart).`);
            return;
        }
        const doc = await vscode.workspace.openTextDocument(logPath);
        await vscode.window.showTextDocument(doc);
    }));
}
//# sourceMappingURL=openOrchestratorWriterLog.js.map
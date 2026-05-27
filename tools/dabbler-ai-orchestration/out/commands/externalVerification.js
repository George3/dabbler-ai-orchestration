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
exports.registerExternalVerificationCommand = registerExternalVerificationCommand;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const fileSystem_1 = require("../utils/fileSystem");
const FILE_NAME = "external-verification.md";
async function pickSet(sets) {
    if (sets.length === 0) {
        vscode.window.showInformationMessage("No session sets found in this workspace.");
        return undefined;
    }
    if (sets.length === 1)
        return sets[0];
    const picked = await vscode.window.showQuickPick(sets.map((s) => ({
        label: s.name,
        description: s.state,
        detail: s.dir,
        set: s,
    })), {
        placeHolder: "Pick a session set to open external-verification.md for",
    });
    return picked?.set;
}
async function openOrCreate(set) {
    const filePath = path.join(set.dir, FILE_NAME);
    // Per §3.8 the file is intentionally free-form — no templated
    // header. Create-if-missing with an empty file so the editor opens
    // on an untouched canvas.
    if (!fs.existsSync(filePath)) {
        try {
            fs.writeFileSync(filePath, "", { encoding: "utf-8", flag: "wx" });
        }
        catch (err) {
            // EEXIST is a benign race (another process / a parallel save
            // already created it); fall through to open. Any other error is
            // surface-worthy so the operator can fix permissions etc.
            const e = err;
            if (e?.code !== "EEXIST") {
                vscode.window.showErrorMessage(`Could not create ${FILE_NAME} in ${set.name}: ${e?.message ?? String(err)}`);
                return;
            }
        }
    }
    await vscode.commands.executeCommand("vscode.open", vscode.Uri.file(filePath));
}
function registerExternalVerificationCommand(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.openExternalVerificationDoc", async (item) => {
        // Item-shape invocation (right-click context, programmatic
        // callers passing a TreeItem) takes the bound set directly.
        if (item?.set) {
            await openOrCreate(item.set);
            return;
        }
        // Command Palette invocation: enumerate workspace sets and
        // pick. The picker is skipped when there's only one set so
        // the common single-set case is one click.
        const sets = (0, fileSystem_1.readAllSessionSets)();
        const picked = await pickSet(sets);
        if (picked) {
            await openOrCreate(picked);
        }
    }));
}
//# sourceMappingURL=externalVerification.js.map
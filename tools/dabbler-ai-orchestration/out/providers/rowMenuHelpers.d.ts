import type * as vscode from "vscode";
import type { CategorizedActions, RowAction } from "./ActionRegistry";
export interface TopLevelPickItem extends vscode.QuickPickItem {
    dabblerKind: "openFile" | "copyEval" | "action";
    action?: RowAction;
}
export interface SubmenuPickItem extends vscode.QuickPickItem {
    action: RowAction;
}
export declare function buildTopLevelItems(categorized: CategorizedActions): TopLevelPickItem[];
export declare function buildSubmenuItems(submenu: RowAction[]): SubmenuPickItem[];
export interface LeftClickPlan {
    openCommand: {
        commandId: string;
        setName: string;
    };
    clipboardWrite: {
        text: string;
        toast: string;
    } | null;
}
export declare function planLeftClickActivation(setName: string, state: "in-progress" | "not-started" | "complete" | "cancelled"): LeftClickPlan;

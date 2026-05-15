import * as vscode from "vscode";
import { SessionSet } from "../types";
export declare function isCurrentSessionInFlight(set: SessionSet): boolean;
export declare function progressText(set: SessionSet): string;
export declare function forceClosedBadge(set: SessionSet): string;
export declare function modeBadge(_set: SessionSet): string;
export declare class SessionSetsProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private readonly extensionUri;
    private _onDidChangeTreeData;
    readonly onDidChangeTreeData: vscode.Event<void | vscode.TreeItem | null | undefined>;
    _cache: SessionSet[] | null;
    constructor(extensionUri: vscode.Uri);
    refresh(): void;
    getTreeItem(element: vscode.TreeItem): vscode.TreeItem;
    getChildren(element?: vscode.TreeItem): vscode.TreeItem[];
    private makeGroup;
    private makeSetItem;
}

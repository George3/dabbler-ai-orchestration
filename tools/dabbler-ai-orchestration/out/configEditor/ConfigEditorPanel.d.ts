import * as vscode from "vscode";
export declare class ConfigEditorPanel {
    static currentPanel: ConfigEditorPanel | undefined;
    private readonly _panel;
    private readonly _extensionUri;
    private _loaded;
    private _validation;
    private _parseIssues;
    private _lastSaveSnapshot;
    private _recovery;
    static createOrShow(context: vscode.ExtensionContext): void;
    private constructor();
    private _findAiRouterDir;
    private _loadFiles;
    private _detectDrift;
    private _deriveState;
    private _handleSave;
    private _retryFailedWrite;
    private _acceptHalfBatchAsBaseline;
    private _reapplyLastSave;
    private _runFlagDecisionCommand;
    private _openLocalOverridesFile;
    private _refresh;
    private _getHtml;
    private _renderRecoveryBanner;
    private _noWorkspaceHtml;
    private _missingFilesHtml;
}
export declare function registerConfigEditorCommand(context: vscode.ExtensionContext): void;

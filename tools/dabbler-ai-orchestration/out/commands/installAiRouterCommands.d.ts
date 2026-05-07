import * as vscode from "vscode";
/**
 * VS Code wiring for the ``Dabbler: Install ai-router`` and
 * ``Dabbler: Update ai-router`` commands.
 *
 * Pure logic lives in :mod:`utils/aiRouterInstall`; this module provides
 * the ``vscode.window`` prompts, the ``cp.spawn`` adapter, and the ``fs``
 * adapter, then surfaces the outcome through ``showInformationMessage``
 * /``showErrorMessage``.
 */
export declare function registerInstallAiRouterCommands(context: vscode.ExtensionContext): void;

import * as vscode from "vscode";
import { SessionSet } from "../types";
type ReviewKind = "spec" | "session" | "set";
interface BuildContext {
    readReviewCriteria: (root: string, kind: ReviewKind) => string | null;
    fileExists: (filePath: string) => boolean;
}
declare function defaultFileExists(filePath: string): boolean;
declare function defaultReadReviewCriteria(root: string, kind: ReviewKind): string | null;
declare function relFromRoot(root: string, abs: string): string;
declare function reviewCriteriaTrailer(root: string, kind: ReviewKind, ctx: BuildContext): string;
export declare function buildSpecReviewPrompt(set: SessionSet, ctx?: BuildContext): string;
export declare function buildSessionAccomplishmentsPrompt(set: SessionSet, ctx?: BuildContext): string;
export declare function buildSetAccomplishmentsPrompt(set: SessionSet, ctx?: BuildContext): string;
export declare function sanitizeSlugForPrompt(slug: string): string;
export declare function buildStartNextSessionPrompt(set: SessionSet): string;
export declare function buildStartNextParallelSessionPrompt(set: SessionSet): string;
export declare function registerCopyPromptCommands(context: vscode.ExtensionContext): void;
export declare const __forTests: {
    defaultBuildContext: BuildContext;
    defaultFileExists: typeof defaultFileExists;
    defaultReadReviewCriteria: typeof defaultReadReviewCriteria;
    relFromRoot: typeof relFromRoot;
    reviewCriteriaTrailer: typeof reviewCriteriaTrailer;
};
export {};

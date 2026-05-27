import { SessionSet } from "../types";
export interface ActionSupports {
    uat: boolean;
    e2e: boolean;
}
export type ActionCategory = "openFile" | "copyEval" | "flat";
export interface RowAction {
    id: string;
    label: string;
    group: number;
    category: ActionCategory;
    when: (set: SessionSet, supports: ActionSupports) => boolean;
}
export declare const ROW_ACTIONS: RowAction[];
export declare function applicableActions(set: SessionSet, supports: ActionSupports): RowAction[];
export interface CategorizedActions {
    openFile: RowAction[];
    copyEval: RowAction[];
    flat: RowAction[];
}
export declare function categorizedActions(set: SessionSet, supports: ActionSupports): CategorizedActions;

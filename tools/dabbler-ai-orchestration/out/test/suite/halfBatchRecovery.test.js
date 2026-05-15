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
/**
 * Half-batch recovery: when the panel's batch save writes succeed for
 * some files and fail for others, the operator needs a way to retry the
 * failed writes or accept the on-disk state as the new baseline. This
 * test exercises the content-hash drift detection that the panel uses to
 * surface the recovery banner on next load.
 */
const assert = __importStar(require("assert"));
const yaml_1 = require("yaml");
const patch_1 = require("../../configEditor/patch");
suite("halfBatchRecovery — content-hash drift detection", () => {
    test("matching content yields equal hashes (no drift)", () => {
        const text = "foo: 1\nbar: 2\n";
        const h1 = (0, patch_1.stringContentHash)(text);
        const h2 = (0, patch_1.stringContentHash)(text);
        assert.strictEqual(h1, h2, "identical text must produce identical hash");
    });
    test("different content yields different hashes (drift detected)", () => {
        const original = "foo: 1\n";
        const mutated = "foo: 2\n";
        assert.notStrictEqual((0, patch_1.stringContentHash)(original), (0, patch_1.stringContentHash)(mutated));
    });
    test("docContentHash distinguishes structurally-different docs", () => {
        const a = (0, yaml_1.parseDocument)("threshold_usd: 10\nscope: per-project\n");
        const b = (0, yaml_1.parseDocument)("threshold_usd: 20\nscope: per-project\n");
        assert.notStrictEqual((0, patch_1.docContentHash)(a), (0, patch_1.docContentHash)(b));
    });
    test("comment-only edits register as drift (preserves the byte-for-byte comparison)", () => {
        const a = "# comment v1\nfoo: 1\n";
        const b = "# comment v2\nfoo: 1\n";
        assert.notStrictEqual((0, patch_1.stringContentHash)(a), (0, patch_1.stringContentHash)(b));
    });
});
function classifyAttempts(attempts) {
    const ok = attempts.filter((a) => a.succeeded).length;
    if (ok === attempts.length)
        return "all-succeeded";
    if (ok === 0)
        return "all-failed";
    return "half-batch";
}
suite("halfBatchRecovery — classify save attempts", () => {
    test("classifies all-succeeded correctly", () => {
        assert.strictEqual(classifyAttempts([
            { file: "router-config.yaml", succeeded: true },
            { file: "budget.yaml", succeeded: true },
        ]), "all-succeeded");
    });
    test("classifies half-batch correctly (1 succeeded, 1 failed)", () => {
        assert.strictEqual(classifyAttempts([
            { file: "router-config.yaml", succeeded: true },
            { file: "budget.yaml", succeeded: false },
        ]), "half-batch");
    });
    test("classifies half-batch correctly (2 succeeded, 1 failed)", () => {
        assert.strictEqual(classifyAttempts([
            { file: "router-config.yaml", succeeded: true },
            { file: "budget.yaml", succeeded: true },
            { file: "local-overrides.yaml", succeeded: false },
        ]), "half-batch");
    });
    test("classifies all-failed correctly", () => {
        assert.strictEqual(classifyAttempts([
            { file: "router-config.yaml", succeeded: false },
            { file: "budget.yaml", succeeded: false },
        ]), "all-failed");
    });
});
//# sourceMappingURL=halfBatchRecovery.test.js.map
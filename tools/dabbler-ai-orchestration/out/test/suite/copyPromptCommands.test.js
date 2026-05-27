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
const assert = __importStar(require("assert"));
const path = __importStar(require("path"));
const copyPromptCommands_1 = require("../../commands/copyPromptCommands");
// Set 048 Session 3 — copyPromptCommands tests. The four prompt
// builders are pure (no clipboard / no vscode API), so we exercise:
//
//   - L1: prompts reference paths, never embed file contents.
//   - §3.2 path-reference format: relative-to-repo-root paths, slash-
//     separated regardless of OS path separator.
//   - §3.9 review-criteria embedding when the per-repo override file
//     exists; default hint copy when it does not.
//   - "if present" change-log conditional inclusion.
function fakeSet(slug, over = {}) {
    const root = path.join("/repo");
    const dir = path.join(root, "docs", "session-sets", slug);
    return {
        name: slug,
        dir,
        specPath: path.join(dir, "spec.md"),
        activityPath: path.join(dir, "activity-log.json"),
        changeLogPath: path.join(dir, "change-log.md"),
        statePath: path.join(dir, "session-state.json"),
        aiAssignmentPath: path.join(dir, "ai-assignment.md"),
        uatChecklistPath: path.join(dir, `${slug}-uat-checklist.json`),
        state: "in-progress",
        totalSessions: 5,
        sessionsCompleted: 1,
        lastTouched: null,
        liveSession: null,
        config: { requiresUAT: false, requiresE2E: false, uatScope: "none", tier: "full" },
        uatSummary: null,
        root,
        needsMigration: false,
        migrationTargetSchemaVersion: null,
        prerequisites: null,
        blockedByPrereqs: false,
        ...over,
    };
}
const noCriteria = {
    readReviewCriteria: () => null,
    fileExists: (_p) => false,
};
const withCriteria = (text) => ({
    readReviewCriteria: () => text,
    fileExists: (_p) => true,
});
suite("copyPromptCommands — spec review prompt", () => {
    test("references spec.md relative to repo root, never embeds contents", () => {
        const out = (0, copyPromptCommands_1.buildSpecReviewPrompt)(fakeSet("048-lightweight"), noCriteria);
        assert.ok(out.includes("docs/session-sets/048-lightweight/spec.md"));
        assert.ok(!out.includes("---\n"), "should not contain spec front-matter (which would imply embedded contents)");
    });
    test("uses forward slashes regardless of OS path separator (L1)", () => {
        const out = (0, copyPromptCommands_1.buildSpecReviewPrompt)(fakeSet("xy"), noCriteria);
        assert.ok(!out.includes("\\"), `path should use forward slashes; got: ${out}`);
    });
    test("falls back to default hint when docs/review-criteria/spec.md absent (§3.9)", () => {
        const out = (0, copyPromptCommands_1.buildSpecReviewPrompt)(fakeSet("xy"), noCriteria);
        assert.ok(out.includes("No `docs/review-criteria/spec.md` present"));
    });
    test("embeds review-criteria content when the per-repo file is present (§3.9)", () => {
        const out = (0, copyPromptCommands_1.buildSpecReviewPrompt)(fakeSet("xy"), withCriteria("Project-specific spec checks:\n- thing A\n- thing B"));
        assert.ok(out.includes("Operator review criteria (from docs/review-criteria/spec.md)"));
        assert.ok(out.includes("- thing A"));
        assert.ok(out.includes("- thing B"));
        assert.ok(!out.includes("No `docs/review-criteria/spec.md` present"));
    });
});
suite("copyPromptCommands — session accomplishments prompt", () => {
    test("always references spec.md and activity-log.json", () => {
        const out = (0, copyPromptCommands_1.buildSessionAccomplishmentsPrompt)(fakeSet("xy"), noCriteria);
        assert.ok(out.includes("docs/session-sets/xy/spec.md"));
        assert.ok(out.includes("docs/session-sets/xy/activity-log.json"));
    });
    test("includes change-log.md only when present", () => {
        const without = (0, copyPromptCommands_1.buildSessionAccomplishmentsPrompt)(fakeSet("xy"), noCriteria);
        assert.ok(!without.includes("docs/session-sets/xy/change-log.md"));
        const withChangeLog = (0, copyPromptCommands_1.buildSessionAccomplishmentsPrompt)(fakeSet("xy"), withCriteria("session-specific criteria"));
        assert.ok(withChangeLog.includes("docs/session-sets/xy/change-log.md"));
    });
    test("embeds git commands with prev-session-ref placeholder", () => {
        const out = (0, copyPromptCommands_1.buildSessionAccomplishmentsPrompt)(fakeSet("xy"), noCriteria);
        assert.ok(out.includes("git log --oneline <prev-session-ref>..HEAD"));
        assert.ok(out.includes("git diff <prev-session-ref>..HEAD"));
    });
});
suite("copyPromptCommands — set accomplishments prompt", () => {
    test("references spec.md and change-log.md when present", () => {
        const out = (0, copyPromptCommands_1.buildSetAccomplishmentsPrompt)(fakeSet("xy", { state: "complete", sessionsCompleted: 5 }), withCriteria("set-wide criteria"));
        assert.ok(out.includes("docs/session-sets/xy/spec.md"));
        assert.ok(out.includes("docs/session-sets/xy/change-log.md"));
    });
    test("omits change-log.md when the file is absent", () => {
        const out = (0, copyPromptCommands_1.buildSetAccomplishmentsPrompt)(fakeSet("xy", { state: "complete", sessionsCompleted: 5 }), noCriteria);
        assert.ok(!out.includes("docs/session-sets/xy/change-log.md"));
    });
    test("embeds set-wide git commands with set-start-ref placeholder", () => {
        const out = (0, copyPromptCommands_1.buildSetAccomplishmentsPrompt)(fakeSet("xy", { state: "complete" }), noCriteria);
        assert.ok(out.includes("git log --oneline <set-start-ref>..HEAD"));
        assert.ok(out.includes("git diff <set-start-ref>..HEAD"));
    });
});
suite("copyPromptCommands — start-next-session prompt (L5 + §3.3 mirror)", () => {
    test("returns the exact one-line text the L5 left-click writes", () => {
        const out = (0, copyPromptCommands_1.buildStartNextSessionPrompt)(fakeSet("048-lightweight"));
        assert.strictEqual(out, "Start the next session of `048-lightweight`.");
    });
    test("uses the set's slug verbatim (no path traversal possible — slug is filesystem name)", () => {
        const out = (0, copyPromptCommands_1.buildStartNextSessionPrompt)(fakeSet("with-dashes-and-numbers-123"));
        assert.strictEqual(out, "Start the next session of `with-dashes-and-numbers-123`.");
    });
    test("sanitizes backticks in slug to avoid breaking the markdown payload (S3 verifier-flagged edge case)", () => {
        // Filesystem names with backticks are unusual but POSIX-legal;
        // a backtick inside the L5 backtick-delimited payload would
        // truncate the rendering. The sanitize replaces ` with ' so the
        // markdown stays well-formed.
        assert.strictEqual((0, copyPromptCommands_1.sanitizeSlugForPrompt)("evil`-name"), "evil'-name");
        const out = (0, copyPromptCommands_1.buildStartNextSessionPrompt)(fakeSet("evil`-name"));
        assert.strictEqual(out, "Start the next session of `evil'-name`.");
        assert.ok(!out.includes("``"), "double-backtick is unsafe in markdown");
    });
});
suite("copyPromptCommands — start-next-parallel-session prompt (Set 049 S1 hygiene)", () => {
    test("returns the parallel-variant text matching copyCommand.ts's parallel preset", () => {
        const out = (0, copyPromptCommands_1.buildStartNextParallelSessionPrompt)(fakeSet("049-orchestrator-coordination-removal"));
        assert.strictEqual(out, "Start the next parallel session of `049-orchestrator-coordination-removal`.");
    });
    test("sanitizes backticks consistent with the non-parallel variant", () => {
        const out = (0, copyPromptCommands_1.buildStartNextParallelSessionPrompt)(fakeSet("evil`-name"));
        assert.strictEqual(out, "Start the next parallel session of `evil'-name`.");
        assert.ok(!out.includes("``"));
    });
});
//# sourceMappingURL=copyPromptCommands.test.js.map
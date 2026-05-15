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
const yaml_1 = require("yaml");
const patch_1 = require("../../configEditor/patch");
function newRouterConfig() {
    return (0, yaml_1.parseDocument)(`# router-config.yaml
providers:
  anthropic:
    display_label: Anthropic
    enabled: true
    api_key_env: ANTHROPIC_API_KEY
    base_url: https://api.anthropic.com/v1/messages
  google:
    enabled: true
    api_key_env: GEMINI_API_KEY
routing:
  outsourcing_mode: whenever-helpful
models:
  sonnet:
    provider: anthropic
`);
}
function newBudget() {
    return (0, yaml_1.parseDocument)(`# budget.yaml
threshold_usd: 10
scope: per-project
warn_at_percent: 80
verification_method: api
`);
}
suite("patch — §1 routing & verification", () => {
    test("writing outsourcing_mode shared updates router-config.yaml", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const payload = {
            outsourcingMode: { value: "verification-only", source: "shared" },
        };
        const result = (0, patch_1.applyPatch)(router, budget, local, payload);
        assert.ok(result.routerConfigChanged);
        const json = router.toJSON();
        assert.strictEqual(json.routing.outsourcing_mode, "verification-only");
    });
    test("writing outsourcing_mode local routes to local-overrides + removes from router-config", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const payload = {
            outsourcingMode: { value: "disabled", source: "local" },
        };
        const result = (0, patch_1.applyPatch)(router, budget, local, payload);
        assert.ok(result.localOverridesChanged);
        assert.ok(result.routerConfigChanged, "router-config should drop the shared key when promoting to local");
        const localJson = local.toJSON();
        assert.strictEqual(localJson.routing.outsourcing_mode, "disabled");
        const routerJson = router.toJSON();
        assert.ok(!routerJson.routing || !("outsourcing_mode" in routerJson.routing));
    });
    test("writing verification_method always lands in budget.yaml", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const payload = { verificationMethod: "skipped" };
        const result = (0, patch_1.applyPatch)(router, budget, local, payload);
        assert.ok(result.budgetChanged);
        const json = budget.toJSON();
        assert.strictEqual(json.verification_method, "skipped");
    });
});
suite("patch — §2 budget", () => {
    test("threshold_usd shared writes to budget.yaml", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            thresholdUsd: { value: 25, source: "shared" },
        });
        assert.ok(result.budgetChanged);
        const json = budget.toJSON();
        assert.strictEqual(json.threshold_usd, 25);
    });
    test("scope is shared-only", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, { scope: "per-session-set" });
        assert.ok(result.budgetChanged);
        const json = budget.toJSON();
        assert.strictEqual(json.scope, "per-session-set");
    });
    test("warn_at_percent local writes to local-overrides", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            warnAtPercent: { value: 70, source: "local" },
        });
        assert.ok(result.localOverridesChanged);
        const localJson = local.toJSON();
        assert.strictEqual(localJson.warn_at_percent, 70);
        // Warning issued for the project-canonical question
        assert.ok(result.warnings.some((w) => w.toLowerCase().includes("warn_at_percent")));
    });
});
suite("patch — §3 providers", () => {
    test("update provider enabled (shared) modifies router-config", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            providers: [{ id: "google", enabled: { value: false, source: "shared" } }],
        });
        assert.ok(result.routerConfigChanged);
        const json = router.toJSON();
        assert.strictEqual(json.providers.google.enabled, false);
    });
    test("update provider api_key_env (local) writes to local-overrides + clears shared", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            providers: [
                { id: "google", apiKeyEnv: { value: "MY_PERSONAL_GEMINI_KEY", source: "local" } },
            ],
        });
        assert.ok(result.localOverridesChanged);
        const localJson = local.toJSON();
        assert.strictEqual(localJson.providers.google.api_key_env, "MY_PERSONAL_GEMINI_KEY");
        // router-config.yaml's google.api_key_env should be removed (move-not-copy)
        const routerJson = router.toJSON();
        assert.ok(!("api_key_env" in routerJson.providers.google), "shared api_key_env should be cleared when promoting to local");
    });
    test("removed provider is deleted from both files", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        // First add a local override for google so we can verify removal cleans both
        (0, patch_1.applyPatch)(router, budget, local, {
            providers: [{ id: "google", apiKeyEnv: { value: "MY_KEY", source: "local" } }],
        });
        // Now remove google entirely
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            providers: [{ id: "google", removed: true }],
        });
        assert.ok(result.routerConfigChanged);
        const routerJson = router.toJSON();
        assert.ok(!("google" in routerJson.providers));
        const localJson = local.toJSON();
        assert.ok(!localJson.providers || !("google" in localJson.providers));
    });
    test("display_label is shared-only (no local-overrides routing)", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            providers: [{ id: "anthropic", displayLabel: "Claude (Anthropic)" }],
        });
        assert.ok(result.routerConfigChanged);
        const json = router.toJSON();
        assert.strictEqual(json.providers.anthropic.display_label, "Claude (Anthropic)");
    });
});
suite("patch — §4 significance flagging", () => {
    test("honor_annotations writes to local-overrides decision_review block", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, { honorAnnotations: false });
        assert.ok(result.localOverridesChanged);
        const json = local.toJSON();
        assert.strictEqual(json.decision_review.honor_annotations, false);
    });
});
suite("patch — §5 notifications", () => {
    test("pushover fields write to local-overrides notifications.pushover", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const result = (0, patch_1.applyPatch)(router, budget, local, {
            pushoverEnabled: true,
            pushoverApiKeyEnv: "PUSHOVER_API_KEY",
            pushoverUserKeyEnv: "PUSHOVER_USER_KEY",
        });
        assert.ok(result.localOverridesChanged);
        const json = local.toJSON();
        assert.strictEqual(json.notifications.pushover.enabled, true);
        assert.strictEqual(json.notifications.pushover.api_key_env, "PUSHOVER_API_KEY");
        assert.strictEqual(json.notifications.pushover.user_key_env, "PUSHOVER_USER_KEY");
    });
});
suite("patch — comment preservation across applyPatch", () => {
    test("top-level comments survive a save", () => {
        const router = newRouterConfig();
        const budget = newBudget();
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        (0, patch_1.applyPatch)(router, budget, local, {
            thresholdUsd: { value: 99, source: "shared" },
        });
        const serialized = budget.toString();
        assert.ok(serialized.includes("# budget.yaml"), "header comment should survive applyPatch");
        assert.ok(serialized.includes("threshold_usd: 99"));
    });
});
suite("patch — content hash helper", () => {
    test("docContentHash returns null for null doc", () => {
        assert.strictEqual((0, patch_1.docContentHash)(null), null);
    });
    test("identical docs produce identical hashes", () => {
        const a = (0, yaml_1.parseDocument)("foo: 1\n");
        const b = (0, yaml_1.parseDocument)("foo: 1\n");
        assert.strictEqual((0, patch_1.docContentHash)(a), (0, patch_1.docContentHash)(b));
    });
    test("different docs produce different hashes", () => {
        const a = (0, yaml_1.parseDocument)("foo: 1\n");
        const b = (0, yaml_1.parseDocument)("foo: 2\n");
        assert.notStrictEqual((0, patch_1.docContentHash)(a), (0, patch_1.docContentHash)(b));
    });
});
//# sourceMappingURL=patch.test.js.map
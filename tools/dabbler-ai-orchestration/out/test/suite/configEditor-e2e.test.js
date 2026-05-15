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
 * End-to-end smoke for the config editor: load three YAMLs, derive section
 * state, render all six sections, apply a multi-section patch, write,
 * re-load, confirm values persisted. Exercises the panel + section +
 * patch + yaml-read-write pipeline end-to-end without a real webview.
 */
const assert = __importStar(require("assert"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const yamlReadWrite_1 = require("../../configEditor/yamlReadWrite");
const schemaValidator_1 = require("../../configEditor/schemaValidator");
const patch_1 = require("../../configEditor/patch");
const routingAndVerificationSection_1 = require("../../configEditor/sections/routingAndVerificationSection");
const budgetSection_1 = require("../../configEditor/sections/budgetSection");
const providersTableSection_1 = require("../../configEditor/sections/providersTableSection");
const significanceFlaggingSection_1 = require("../../configEditor/sections/significanceFlaggingSection");
const notificationsSection_1 = require("../../configEditor/sections/notificationsSection");
const localOverridesSummarySection_1 = require("../../configEditor/sections/localOverridesSummarySection");
function makeTmpDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-e2e-test-"));
}
function deriveState(routerObj, budgetObj, localObj, fileExists) {
    return {
        routerConfig: routerObj,
        budget: budgetObj,
        localOverrides: localObj,
        envVarPresence: {},
        localOverridesFileExists: fileExists,
    };
}
suite("configEditor end-to-end smoke", () => {
    test("all six sections render against a realistic state without throwing", () => {
        const state = {
            routerConfig: {
                providers: {
                    anthropic: { display_label: "Anthropic", enabled: true, api_key_env: "ANTHROPIC_API_KEY" },
                    google: { display_label: "Google", enabled: true, api_key_env: "GEMINI_API_KEY" },
                },
                routing: { outsourcing_mode: "whenever-helpful" },
            },
            budget: { threshold_usd: 15, scope: "per-project", warn_at_percent: 80, verification_method: "api" },
            localOverrides: { notifications: { pushover: { enabled: true, api_key_env: "PUSHOVER_API_KEY", user_key_env: "PUSHOVER_USER_KEY" } } },
            envVarPresence: { ANTHROPIC_API_KEY: true, GEMINI_API_KEY: true, PUSHOVER_API_KEY: false, PUSHOVER_USER_KEY: false },
            localOverridesFileExists: true,
        };
        const s1 = (0, routingAndVerificationSection_1.render)(state);
        const s2 = (0, budgetSection_1.render)(state);
        const s3 = (0, providersTableSection_1.render)(state);
        const s4 = (0, significanceFlaggingSection_1.render)(state);
        const s5 = (0, notificationsSection_1.render)(state);
        const s6 = (0, localOverridesSummarySection_1.render)(state);
        for (const html of [s1.html, s2.html, s3.html, s4.html, s5.html, s6.html]) {
            assert.ok(typeof html === "string" && html.length > 50);
        }
        // Each section's HTML appears in the combined render
        assert.ok(s1.html.includes("s1-outsourcing-mode"));
        assert.ok(s2.html.includes("s2-threshold-usd"));
        assert.ok(s3.html.includes("provider-row"));
        assert.ok(s4.html.includes("s4-honor-annotations"));
        assert.ok(s5.html.includes("s5-pushover-enabled"));
        assert.ok(s6.html.includes("notifications.pushover.enabled"));
    });
    test("save round-trip: edit one field per section, write, reload, confirm values persisted", () => {
        const dir = makeTmpDir();
        const routerPath = path.join(dir, "router-config.yaml");
        const budgetPath = path.join(dir, "budget.yaml");
        const localPath = path.join(dir, "local-overrides.yaml");
        fs.writeFileSync(routerPath, `# router-config.yaml
providers:
  anthropic:
    display_label: Anthropic
    enabled: true
    api_key_env: ANTHROPIC_API_KEY
routing:
  outsourcing_mode: whenever-helpful
`, "utf8");
        fs.writeFileSync(budgetPath, `# budget.yaml
threshold_usd: 10
scope: per-project
warn_at_percent: 80
verification_method: api
`, "utf8");
        // Load
        const router = (0, yamlReadWrite_1.readYamlFile)(routerPath);
        const budget = (0, yamlReadWrite_1.readYamlFile)(budgetPath);
        assert.ok(router && budget);
        // Patch (apply changes across multiple sections)
        const local = (0, patch_1.emptyLocalOverridesDoc)();
        const payload = {
            outsourcingMode: { value: "verification-only", source: "shared" },
            verificationMethod: "manual-via-other-engine",
            thresholdUsd: { value: 25, source: "shared" },
            providers: [
                { id: "anthropic", enabled: { value: false, source: "local" } },
            ],
            honorAnnotations: false,
            pushoverEnabled: true,
            pushoverApiKeyEnv: "MY_PUSHOVER_TOKEN",
            pushoverUserKeyEnv: "MY_PUSHOVER_USER",
        };
        const applyResult = (0, patch_1.applyPatch)(router.doc, budget.doc, local, payload);
        assert.ok(applyResult.routerConfigChanged);
        assert.ok(applyResult.budgetChanged);
        assert.ok(applyResult.localOverridesChanged);
        // Validate
        const v = (0, schemaValidator_1.validateBatch)({
            routerConfig: router.doc.toJSON(),
            budget: budget.doc.toJSON(),
            localOverrides: local.toJSON(),
        });
        assert.ok(v.valid, `validation failed: ${JSON.stringify(v.errors)}`);
        // Write
        (0, yamlReadWrite_1.writeYamlFile)(routerPath, router.doc);
        (0, yamlReadWrite_1.writeYamlFile)(budgetPath, budget.doc);
        (0, yamlReadWrite_1.writeYamlFile)(localPath, local);
        // Reload + re-derive state
        const routerR = (0, yamlReadWrite_1.readYamlFile)(routerPath);
        const budgetR = (0, yamlReadWrite_1.readYamlFile)(budgetPath);
        const localR = (0, yamlReadWrite_1.readYamlFile)(localPath);
        assert.ok(routerR && budgetR && localR);
        const routerObj = routerR.doc.toJSON();
        const budgetObj = budgetR.doc.toJSON();
        const localObj = localR.doc.toJSON();
        // Verify saved values
        assert.strictEqual(routerObj.routing.outsourcing_mode, "verification-only");
        assert.strictEqual(budgetObj.verification_method, "manual-via-other-engine");
        assert.strictEqual(budgetObj.threshold_usd, 25);
        assert.strictEqual(localObj.providers.anthropic.enabled, false);
        assert.strictEqual(localObj.decision_review.honor_annotations, false);
        assert.strictEqual(localObj.notifications.pushover.enabled, true);
        // Re-render sections from reloaded state — verify the operator would see the new values
        const state = deriveState(routerObj, budgetObj, localObj, true);
        assert.ok((0, routingAndVerificationSection_1.render)(state).html.includes('value="verification-only" selected'));
        assert.ok((0, budgetSection_1.render)(state).html.includes('value="25.00"'));
        assert.ok((0, localOverridesSummarySection_1.render)(state).html.includes("decision_review.honor_annotations"));
        fs.rmSync(dir, { recursive: true });
    });
    test("hand-edit introducing invalid value surfaces in next-load validation", () => {
        const dir = makeTmpDir();
        const routerPath = path.join(dir, "router-config.yaml");
        const budgetPath = path.join(dir, "budget.yaml");
        fs.writeFileSync(routerPath, "providers: {}\n", "utf8");
        // Hand-edit introduces lowercase env var name → schema violation
        fs.writeFileSync(budgetPath, "threshold_usd: -50\n", "utf8");
        const router = (0, yamlReadWrite_1.readYamlFile)(routerPath);
        const budget = (0, yamlReadWrite_1.readYamlFile)(budgetPath);
        const v = (0, schemaValidator_1.validateBatch)({
            routerConfig: router?.doc.toJSON(),
            budget: budget?.doc.toJSON(),
            localOverrides: null,
        });
        assert.ok(!v.valid);
        assert.ok(v.errors.some((e) => e.file === "budget.yaml"));
        fs.rmSync(dir, { recursive: true });
    });
});
//# sourceMappingURL=configEditor-e2e.test.js.map
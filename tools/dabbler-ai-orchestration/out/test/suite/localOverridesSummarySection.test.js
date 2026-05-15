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
const localOverridesSummarySection_1 = require("../../configEditor/sections/localOverridesSummarySection");
function baseState(over = {}) {
    return {
        routerConfig: null,
        budget: null,
        localOverrides: null,
        envVarPresence: {},
        localOverridesFileExists: false,
        ...over,
    };
}
suite("localOverridesSummarySection — rendering", () => {
    test("absent file: shows 'No local overrides' message; no Open button", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState());
        assert.ok(html.includes("does not exist yet"));
        assert.ok(!html.includes('id="s6-open-local-overrides"'), "open button should be absent when file is absent");
    });
    test("empty local-overrides: shows summary + Open button", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState({
            localOverrides: {},
            localOverridesFileExists: true,
        }));
        assert.ok(html.includes("no override entries"));
        assert.ok(html.includes('id="s6-open-local-overrides"'));
    });
    test("populated local-overrides: lists each override path side-by-side with shared value", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState({
            routerConfig: { providers: { google: { api_key_env: "GEMINI_API_KEY" } } },
            localOverrides: {
                providers: { google: { api_key_env: "MY_PERSONAL_GEMINI_KEY" } },
            },
            localOverridesFileExists: true,
        }));
        assert.ok(html.includes("providers.google.api_key_env"), "override path should be listed");
        assert.ok(html.includes("GEMINI_API_KEY"), "shared value should be shown");
        assert.ok(html.includes("MY_PERSONAL_GEMINI_KEY"), "local value should be shown");
    });
    test("notifications.* paths show '(local-only section)' as shared value", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState({
            localOverrides: {
                notifications: { pushover: { enabled: true } },
            },
            localOverridesFileExists: true,
        }));
        assert.ok(html.includes("notifications.pushover.enabled"));
        assert.ok(html.includes("(local-only section)"));
    });
    test("Open local-overrides button is present when file exists", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState({
            localOverrides: { decision_review: { honor_annotations: false } },
            localOverridesFileExists: true,
        }));
        assert.ok(html.includes('id="s6-open-local-overrides"'));
    });
    test("scalar override values are rendered as their primitive string form", () => {
        const { html } = (0, localOverridesSummarySection_1.render)(baseState({
            routerConfig: { routing: { outsourcing_mode: "whenever-helpful" } },
            localOverrides: { routing: { outsourcing_mode: "disabled" } },
            localOverridesFileExists: true,
        }));
        assert.ok(html.includes("routing.outsourcing_mode"));
        assert.ok(html.includes("disabled"));
        assert.ok(html.includes("whenever-helpful"));
    });
});
//# sourceMappingURL=localOverridesSummarySection.test.js.map
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
const routingAndVerificationSection_1 = require("../../configEditor/sections/routingAndVerificationSection");
function baseState(over = {}) {
    return {
        routerConfig: { routing: { outsourcing_mode: "whenever-helpful" } },
        budget: { threshold_usd: 10, verification_method: "api" },
        localOverrides: null,
        envVarPresence: {},
        localOverridesFileExists: false,
        ...over,
    };
}
suite("routingAndVerificationSection — basic render", () => {
    test("renders both dropdowns with correct selected values from shared config", () => {
        const { html } = (0, routingAndVerificationSection_1.render)(baseState());
        assert.ok(html.includes('id="s1-outsourcing-mode"'));
        assert.ok(html.includes('id="s1-verification-method"'));
        assert.ok(/<option value="whenever-helpful" selected/.test(html), "outsourcing default selection");
        assert.ok(/<option value="api" selected/.test(html), "verification default selection");
    });
    test("disabled outsourcing greys out 'Automatic via API' option", () => {
        const state = baseState({
            routerConfig: { routing: { outsourcing_mode: "disabled" } },
        });
        const { html } = (0, routingAndVerificationSection_1.render)(state);
        // The api option carries disabled attribute when outsourcing = disabled
        assert.ok(/<option value="api"[^>]*disabled/.test(html), "api option should be disabled");
        // Constraint info paragraph is visible (not display:none)
        assert.ok(html.includes('id="s1-api-constraint"') && !/id="s1-api-constraint"[^>]*display:none/.test(html), "api constraint info should be visible when outsourcing = disabled");
    });
    test("manual verification surfaces the template URL block", () => {
        const state = baseState({
            budget: { threshold_usd: 10, verification_method: "manual-via-other-engine" },
        });
        const { html } = (0, routingAndVerificationSection_1.render)(state);
        assert.ok(html.includes("verification.md"));
        // Manual template div should not be hidden
        assert.ok(/id="s1-manual-template"[^>]*style=""/.test(html), "manual template should be visible");
    });
    test("(local override) indicator shows when local-overrides has routing.outsourcing_mode", () => {
        const state = baseState({
            localOverrides: { routing: { outsourcing_mode: "verification-only" } },
        });
        const { html } = (0, routingAndVerificationSection_1.render)(state);
        assert.ok(html.includes("(local override)"), "should show local override indicator");
        assert.ok(/<option value="verification-only" selected/.test(html), "effective value comes from local");
    });
    test("(shared) indicator shows on routing dropdown when no local override", () => {
        const { html } = (0, routingAndVerificationSection_1.render)(baseState());
        assert.ok(html.includes("(shared)"), "should show shared indicator");
    });
    test("verification dropdown indicator is suppressed (not locally overridable)", () => {
        const { html } = (0, routingAndVerificationSection_1.render)(baseState());
        // The verification block should not include a local-override indicator
        // for the verificationMethod field — Appendix B says it's project-canonical.
        const verificationBlockStart = html.indexOf('id="s1-verification-method"');
        const verificationBlockEnd = html.indexOf("</select>", verificationBlockStart);
        const verifSlice = html.slice(verificationBlockStart, verificationBlockEnd + 20);
        assert.ok(!/data-field="verificationMethod"[^]*\(local override\)/m.test(verifSlice), "verification method must not surface a local-override indicator");
    });
});
//# sourceMappingURL=routingAndVerificationSection.test.js.map
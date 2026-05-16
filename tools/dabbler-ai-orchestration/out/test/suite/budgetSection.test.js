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
const budgetSection_1 = require("../../configEditor/sections/budgetSection");
function baseState(over = {}) {
    return {
        routerConfig: null,
        budget: { threshold_usd: 15, scope: "per-session-set", warn_at_percent: 80 },
        localOverrides: null,
        envVarPresence: {},
        localOverridesFileExists: false,
        ...over,
    };
}
suite("budgetSection — rendering", () => {
    test("renders threshold + scope + warn-at-percent inputs from shared budget", () => {
        const { html } = (0, budgetSection_1.render)(baseState());
        assert.ok(html.includes('id="s2-threshold-usd"'));
        assert.ok(html.includes('value="15.00"'));
        assert.ok(/<option value="per-session-set" selected/.test(html));
        assert.ok(html.includes('id="s2-warn-at-percent"'));
        assert.ok(html.includes('value="80"'));
    });
    test("3-state preview block computes warn amount from threshold + percent", () => {
        const { html } = (0, budgetSection_1.render)(baseState({
            budget: { threshold_usd: 20, scope: "per-project", warn_at_percent: 50 },
        }));
        // $10 = 50% of $20
        assert.ok(/Below 50% of \$20\.00 \(\$10\.00\)/.test(html), "preview should compute correct warn dollar amount");
        assert.ok(/Between 50% and 100% \(\$10\.00.{1,3}\$20\.00\)/.test(html));
        assert.ok(/At or above \$20\.00/.test(html));
    });
    test("cost-messaging copy includes all four feedback_user_facing_cost_messaging elements", () => {
        const { html } = (0, budgetSection_1.render)(baseState());
        // Memory: feedback_user_facing_cost_messaging requires
        //   (1) explicit dollar ranges, (2) multi-week scale,
        //   (3) open-source caveat, (4) dashboard pointer.
        assert.ok(html.includes("$0") && html.includes("$50/week"), "(1) explicit dollar range required");
        assert.ok(html.includes("/month") || /\d+\s*(?:weeks|week\s|-week)/i.test(html), "(2) multi-week scale required (e.g., per-month or N-week framing)");
        assert.ok(html.toLowerCase().includes("open-source"), "(3) open-source caveat required");
        assert.ok(html.toLowerCase().includes("cost dashboard"), "(4) dashboard pointer required");
    });
    test("local threshold override surfaces (local override) indicator", () => {
        const { html } = (0, budgetSection_1.render)(baseState({
            localOverrides: { threshold_usd: 5 },
        }));
        assert.ok(html.includes('value="5.00"'), "effective value comes from local");
        assert.ok(html.includes("(local override)"), "indicator should reflect local source");
    });
    test("scope dropdown is shared-only (no indicator pill)", () => {
        const { html } = (0, budgetSection_1.render)(baseState());
        // scope is Appendix-B "Local-override allowed? No"
        // Find the scope field-row and verify it has no clickable indicator
        const scopeAnchor = html.indexOf('id="s2-scope"');
        const scopeRow = html.slice(scopeAnchor, scopeAnchor + 600);
        assert.ok(!scopeRow.includes("(local override)"), "scope must not have local-override indicator");
        assert.ok(!scopeRow.includes("(shared)"), "scope is not-overridable and should suppress indicator entirely");
    });
    test("per-session option appears only when current scope is per-session", () => {
        const visible = (0, budgetSection_1.render)(baseState({
            budget: { threshold_usd: 10, scope: "per-session" },
        }));
        assert.ok(visible.html.includes('value="per-session"'), "per-session option should be present when active");
        const hidden = (0, budgetSection_1.render)(baseState());
        assert.ok(!hidden.html.includes('value="per-session"'), "per-session option must be hidden by default per G7");
    });
});
//# sourceMappingURL=budgetSection.test.js.map
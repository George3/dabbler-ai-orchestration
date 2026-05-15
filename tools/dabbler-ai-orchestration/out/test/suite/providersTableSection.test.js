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
const providersTableSection_1 = require("../../configEditor/sections/providersTableSection");
function baseState(over = {}) {
    return {
        routerConfig: {
            providers: {
                anthropic: {
                    display_label: "Anthropic (Claude)",
                    enabled: true,
                    api_key_env: "ANTHROPIC_API_KEY",
                    base_url: "https://api.anthropic.com/v1/messages",
                },
                google: {
                    enabled: false,
                    api_key_env: "GEMINI_API_KEY",
                },
            },
        },
        budget: null,
        localOverrides: null,
        envVarPresence: { ANTHROPIC_API_KEY: true, GEMINI_API_KEY: false },
        localOverridesFileExists: false,
        ...over,
    };
}
suite("providersTableSection — rendering", () => {
    test("renders one row per provider in router-config", () => {
        const { html } = (0, providersTableSection_1.render)(baseState());
        const rowCount = (html.match(/class="provider-row"/g) ?? []).length;
        assert.strictEqual(rowCount, 2);
        assert.ok(html.includes('data-provider-id="anthropic"'));
        assert.ok(html.includes('data-provider-id="google"'));
    });
    test("env-var-set provider shows ✓ badge; unset provider shows (unset) badge", () => {
        const { html } = (0, providersTableSection_1.render)(baseState());
        const anthropicRowStart = html.indexOf('data-provider-id="anthropic"');
        const googleRowStart = html.indexOf('data-provider-id="google"');
        const anthropicSlice = html.slice(anthropicRowStart, googleRowStart);
        const googleSlice = html.slice(googleRowStart);
        assert.ok(/&#10003;/.test(anthropicSlice), "anthropic env var is set → ✓ badge");
        assert.ok(googleSlice.includes("(unset)"), "google env var is unset → (unset) badge");
    });
    test("display label defaults to title-cased id when missing", () => {
        const { html } = (0, providersTableSection_1.render)(baseState({
            routerConfig: { providers: { "my-custom-provider": { api_key_env: "MY_KEY" } } },
            envVarPresence: { MY_KEY: false },
        }));
        assert.ok(html.includes('value="My Custom Provider"'));
    });
    test("provider ID column is rendered as <code>", () => {
        const { html } = (0, providersTableSection_1.render)(baseState());
        assert.ok(/<code>anthropic<\/code>/.test(html));
        assert.ok(/<code>google<\/code>/.test(html));
    });
    test("popover toggle button + hidden popover row per provider", () => {
        const { html } = (0, providersTableSection_1.render)(baseState());
        const popoverButtons = (html.match(/class="secondary popover-toggle"/g) ?? []).length;
        assert.strictEqual(popoverButtons, 2);
        const popoverRows = (html.match(/class="provider-popover"/g) ?? []).length;
        assert.strictEqual(popoverRows, 2);
        assert.ok(html.includes('id="popover-anthropic"'));
        assert.ok(html.includes('id="popover-google"'));
        // hidden by default
        assert.ok(/id="popover-anthropic"[^>]*style="display:none;"/.test(html));
    });
    test("local override on api_key_env surfaces (local override) indicator and uses local value", () => {
        const { html } = (0, providersTableSection_1.render)(baseState({
            localOverrides: {
                providers: { anthropic: { api_key_env: "MY_PERSONAL_ANTHROPIC_KEY" } },
            },
            envVarPresence: { ANTHROPIC_API_KEY: true, MY_PERSONAL_ANTHROPIC_KEY: false, GEMINI_API_KEY: false },
        }));
        const anthropicRow = html.slice(html.indexOf('data-provider-id="anthropic"'), html.indexOf('data-provider-id="google"'));
        assert.ok(anthropicRow.includes("MY_PERSONAL_ANTHROPIC_KEY"), "input value should reflect local override");
        assert.ok(anthropicRow.includes("(local override)"), "indicator should reflect local source");
    });
    test("empty providers block renders placeholder row", () => {
        const { html } = (0, providersTableSection_1.render)(baseState({ routerConfig: { providers: {} } }));
        assert.ok(html.includes("No providers configured"));
    });
    test("env var input has uppercase-pattern validation attribute", () => {
        const { html } = (0, providersTableSection_1.render)(baseState());
        assert.ok(/pattern="\^\[A-Z_\]\[A-Z0-9_\]\*\$"/.test(html));
    });
});
//# sourceMappingURL=providersTableSection.test.js.map
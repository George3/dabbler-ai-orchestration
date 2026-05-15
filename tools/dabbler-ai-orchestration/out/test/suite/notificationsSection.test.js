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
const notificationsSection_1 = require("../../configEditor/sections/notificationsSection");
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
suite("notificationsSection — rendering", () => {
    test("renders all three controls", () => {
        const { html } = (0, notificationsSection_1.render)(baseState());
        assert.ok(html.includes('id="s5-pushover-enabled"'));
        assert.ok(html.includes('id="s5-pushover-api-key-env"'));
        assert.ok(html.includes('id="s5-pushover-user-key-env"'));
    });
    test('test-notification button is disabled with "wired in Set 026 Session 7" label', () => {
        const { html } = (0, notificationsSection_1.render)(baseState());
        assert.ok(/id="s5-test-notification"[^>]*disabled/.test(html));
        assert.ok(html.includes("Session 7"));
    });
    test("env var inputs default to PUSHOVER_API_KEY / PUSHOVER_USER_KEY", () => {
        const { html } = (0, notificationsSection_1.render)(baseState());
        assert.ok(html.includes('value="PUSHOVER_API_KEY"'));
        assert.ok(html.includes('value="PUSHOVER_USER_KEY"'));
    });
    test("env-var presence badge: set → ✓; unset → (unset)", () => {
        const setState = baseState({
            localOverrides: {
                notifications: { pushover: { api_key_env: "MY_PUSHOVER_TOKEN", user_key_env: "MY_PUSHOVER_USER" } },
            },
            envVarPresence: { MY_PUSHOVER_TOKEN: true, MY_PUSHOVER_USER: false },
        });
        const { html } = (0, notificationsSection_1.render)(setState);
        // Find ✓ next to api_key_env input
        const apiKeyIdx = html.indexOf('id="s5-pushover-api-key-env"');
        const userKeyIdx = html.indexOf('id="s5-pushover-user-key-env"');
        const apiSlice = html.slice(apiKeyIdx, userKeyIdx);
        const userSlice = html.slice(userKeyIdx);
        assert.ok(/&#10003;/.test(apiSlice), "set env var should show ✓ badge");
        assert.ok(userSlice.includes("(unset)"), "unset env var should show (unset) badge");
    });
    test("(local override) indicator shows for enabled when explicitly set in local-overrides", () => {
        const state = baseState({
            localOverrides: { notifications: { pushover: { enabled: true } } },
        });
        const { html } = (0, notificationsSection_1.render)(state);
        assert.ok(html.includes("(local override)"));
    });
    test("(default) indicator shows for enabled when no local-overrides value", () => {
        const { html } = (0, notificationsSection_1.render)(baseState());
        assert.ok(html.includes("(default)"));
    });
    test("env var pattern validation attribute on inputs", () => {
        const { html } = (0, notificationsSection_1.render)(baseState());
        assert.ok(/pattern="\^\[A-Z_\]\[A-Z0-9_\]\*\$"/.test(html));
    });
});
//# sourceMappingURL=notificationsSection.test.js.map
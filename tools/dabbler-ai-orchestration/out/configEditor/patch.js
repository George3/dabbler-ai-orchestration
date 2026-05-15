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
exports.applyPatch = applyPatch;
exports.docContentHash = docContentHash;
exports.stringContentHash = stringContentHash;
exports.emptyLocalOverridesDoc = emptyLocalOverridesDoc;
const yaml_1 = require("yaml");
const crypto = __importStar(require("crypto"));
/**
 * Apply a SavePayload to the three loaded YAML documents in place.
 *
 * Caller owns: validating before this call (`validateBatch`), persisting
 * after (`writeYamlFile`), and creating localOverridesDoc if it's null
 * and a write needs it.
 */
function applyPatch(routerConfigDoc, budgetDoc, localOverridesDoc, payload) {
    const result = {
        routerConfigChanged: false,
        budgetChanged: false,
        localOverridesChanged: false,
        warnings: [],
    };
    // --- §1 Routing & Verification ----------------------------------------
    if (payload.outsourcingMode !== undefined) {
        const { value, source } = payload.outsourcingMode;
        if (source === "local") {
            setIn(localOverridesDoc, ["routing", "outsourcing_mode"], value);
            deleteIfPresent(routerConfigDoc, ["routing", "outsourcing_mode"], result, "routerConfigChanged");
            result.localOverridesChanged = true;
        }
        else {
            setIn(routerConfigDoc, ["routing", "outsourcing_mode"], value);
            deleteIfPresent(localOverridesDoc, ["routing", "outsourcing_mode"], result, "localOverridesChanged");
            // Clean up an empty routing: {} container in local-overrides
            pruneEmptyContainer(localOverridesDoc, ["routing"], result, "localOverridesChanged");
            result.routerConfigChanged = true;
        }
    }
    if (payload.verificationMethod !== undefined) {
        setIn(budgetDoc, ["verification_method"], payload.verificationMethod);
        result.budgetChanged = true;
    }
    // --- §2 Budget --------------------------------------------------------
    if (payload.thresholdUsd !== undefined) {
        const { value, source } = payload.thresholdUsd;
        if (source === "local") {
            setIn(localOverridesDoc, ["threshold_usd"], value);
            result.localOverridesChanged = true;
            result.warnings.push("threshold_usd is project-canonical per Appendix B and may be rejected by the local-overrides allowlist.");
        }
        else {
            setIn(budgetDoc, ["threshold_usd"], value);
            result.budgetChanged = true;
        }
    }
    if (payload.scope !== undefined) {
        setIn(budgetDoc, ["scope"], payload.scope);
        result.budgetChanged = true;
    }
    if (payload.warnAtPercent !== undefined) {
        const { value, source } = payload.warnAtPercent;
        if (source === "local") {
            setIn(localOverridesDoc, ["warn_at_percent"], value);
            result.localOverridesChanged = true;
            result.warnings.push("warn_at_percent is project-canonical per Appendix B and may be rejected by the local-overrides allowlist.");
        }
        else {
            setIn(budgetDoc, ["warn_at_percent"], value);
            result.budgetChanged = true;
        }
    }
    // --- §3 Providers -----------------------------------------------------
    if (payload.providers !== undefined) {
        for (const p of payload.providers) {
            if (p.removed) {
                deleteIfPresent(routerConfigDoc, ["providers", p.id], result, "routerConfigChanged");
                deleteIfPresent(localOverridesDoc, ["providers", p.id], result, "localOverridesChanged");
                pruneEmptyContainer(localOverridesDoc, ["providers"], result, "localOverridesChanged");
                continue;
            }
            if (p.displayLabel !== undefined) {
                setIn(routerConfigDoc, ["providers", p.id, "display_label"], p.displayLabel);
                result.routerConfigChanged = true;
            }
            if (p.enabled !== undefined) {
                applyOverridableField(routerConfigDoc, localOverridesDoc, ["providers", p.id, "enabled"], p.enabled.value, p.enabled.source, result);
            }
            if (p.apiKeyEnv !== undefined) {
                applyOverridableField(routerConfigDoc, localOverridesDoc, ["providers", p.id, "api_key_env"], p.apiKeyEnv.value, p.apiKeyEnv.source, result);
            }
            if (p.baseUrl !== undefined) {
                applyOverridableField(routerConfigDoc, localOverridesDoc, ["providers", p.id, "base_url"], p.baseUrl.value, p.baseUrl.source, result);
            }
        }
        // After provider edits, prune empty containers in local-overrides
        pruneEmptyProvidersBlock(localOverridesDoc, result);
    }
    // --- §4 Significance flagging ----------------------------------------
    if (payload.honorAnnotations !== undefined) {
        setIn(localOverridesDoc, ["decision_review", "honor_annotations"], payload.honorAnnotations);
        result.localOverridesChanged = true;
    }
    // --- §5 Notifications ------------------------------------------------
    // These three live exclusively in local-overrides per Appendix B.
    if (payload.pushoverEnabled !== undefined) {
        setIn(localOverridesDoc, ["notifications", "pushover", "enabled"], payload.pushoverEnabled);
        result.localOverridesChanged = true;
    }
    if (payload.pushoverApiKeyEnv !== undefined) {
        setIn(localOverridesDoc, ["notifications", "pushover", "api_key_env"], payload.pushoverApiKeyEnv);
        result.localOverridesChanged = true;
    }
    if (payload.pushoverUserKeyEnv !== undefined) {
        setIn(localOverridesDoc, ["notifications", "pushover", "user_key_env"], payload.pushoverUserKeyEnv);
        result.localOverridesChanged = true;
    }
    return result;
}
/**
 * Apply a field that has both shared and local-override homes. Writing to
 * one side cleans up the other so the file-of-record stays unambiguous.
 */
function applyOverridableField(routerConfigDoc, localOverridesDoc, path, value, source, result) {
    if (source === "local") {
        setIn(localOverridesDoc, path, value);
        deleteIfPresent(routerConfigDoc, path, result, "routerConfigChanged");
        result.localOverridesChanged = true;
    }
    else {
        setIn(routerConfigDoc, path, value);
        deleteIfPresent(localOverridesDoc, path, result, "localOverridesChanged");
    }
}
function setIn(doc, path, value) {
    doc.setIn(path, value);
}
function deleteIfPresent(doc, path, result, flag) {
    if (doc.hasIn(path)) {
        doc.deleteIn(path);
        result[flag] = true;
    }
}
/** Remove a container path if it's an empty object after a delete. */
function pruneEmptyContainer(doc, path, result, flag) {
    if (!doc.hasIn(path))
        return;
    const node = doc.getIn(path);
    if (node && typeof node === "object" && "items" in node) {
        const items = node.items;
        if (Array.isArray(items) && items.length === 0) {
            doc.deleteIn(path);
            result[flag] = true;
        }
    }
}
/**
 * After provider edits, walk local-overrides.providers and remove any
 * provider entry whose value is an empty map. Also remove the providers:
 * block itself if no entries remain.
 */
function pruneEmptyProvidersBlock(doc, result) {
    const providersNode = doc.getIn(["providers"]);
    if (!providersNode || typeof providersNode !== "object" || !("items" in providersNode))
        return;
    const items = providersNode.items ?? [];
    // Iterate in reverse so deletions don't shift earlier indices.
    for (let i = items.length - 1; i >= 0; i--) {
        const key = items[i]?.key?.value;
        if (typeof key !== "string")
            continue;
        const providerEntry = doc.getIn(["providers", key]);
        if (providerEntry && typeof providerEntry === "object" && "items" in providerEntry) {
            const innerItems = providerEntry.items;
            if (Array.isArray(innerItems) && innerItems.length === 0) {
                doc.deleteIn(["providers", key]);
                result.localOverridesChanged = true;
            }
        }
    }
    pruneEmptyContainer(doc, ["providers"], result, "localOverridesChanged");
}
/** Stable content hash of a document's serialized form. */
function docContentHash(doc) {
    if (!doc)
        return null;
    return crypto.createHash("sha256").update(doc.toString()).digest("hex");
}
/** Compute content hash for a raw string (used for read-then-compare). */
function stringContentHash(text) {
    return crypto.createHash("sha256").update(text).digest("hex");
}
/** Build an empty local-overrides Document operators can write into. */
function emptyLocalOverridesDoc() {
    // Minimal header comment so the file is self-documenting when created.
    const text = `# ai_router/local-overrides.yaml
# Machine-local overrides; this file is .gitignored.
# Appendix B (Set 025 spec) defines which paths are locally overridable.
{}
`;
    return (0, yaml_1.parseDocument)(text);
}
//# sourceMappingURL=patch.js.map
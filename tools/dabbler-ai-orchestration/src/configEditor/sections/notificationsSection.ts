import { SectionState, SectionRenderResult } from "./types";
import { asString, envVarBadge, escapeHtml, fieldSource, getByPath, indicatorHtml } from "./helpers";

/**
 * §5 Notifications.
 *
 * Pushover toggle + two env-var-name inputs with ✓/(unset) badges.
 * The "Send a test notification now" button fires a live Pushover call
 * using the configured env vars; the result surfaces via a VS Code
 * info/error notification.
 *
 * Appendix B: all three fields live in local-overrides.yaml only.
 */
export function render(state: SectionState): SectionRenderResult {
  const enabledRaw = getByPath(state.localOverrides, "notifications.pushover.enabled");
  const apiKeyRaw = getByPath(state.localOverrides, "notifications.pushover.api_key_env");
  const userKeyRaw = getByPath(state.localOverrides, "notifications.pushover.user_key_env");

  const enabled = typeof enabledRaw === "boolean" ? enabledRaw : false;
  const apiKeyEnv = asString(apiKeyRaw, "PUSHOVER_API_KEY");
  const userKeyEnv = asString(userKeyRaw, "PUSHOVER_USER_KEY");

  const enabledSource = fieldSource(state, "localOnly", "", "notifications.pushover.enabled", true);
  const apiKeySource = fieldSource(state, "localOnly", "", "notifications.pushover.api_key_env", true);
  const userKeySource = fieldSource(state, "localOnly", "", "notifications.pushover.user_key_env", true);

  const html = `
<div class="section-block">
  <h3>Pushover notifications at end-of-session</h3>

  <div class="field-row">
    <label><input type="checkbox" id="s5-pushover-enabled" data-field="pushoverEnabled"${enabled ? " checked" : ""} /> Enable Pushover</label>
    ${indicatorHtml(enabledSource, "pushoverEnabled")}
  </div>

  <div class="field-row">
    <label for="s5-pushover-api-key-env">API key env var</label>
    <input type="text" id="s5-pushover-api-key-env" data-field="pushoverApiKeyEnv" value="${escapeHtml(apiKeyEnv)}" pattern="^[A-Z_][A-Z0-9_]*$" />
    ${envVarBadge(state, apiKeyEnv)}
    ${indicatorHtml(apiKeySource, "pushoverApiKeyEnv")}
  </div>

  <div class="field-row">
    <label for="s5-pushover-user-key-env">User key env var</label>
    <input type="text" id="s5-pushover-user-key-env" data-field="pushoverUserKeyEnv" value="${escapeHtml(userKeyEnv)}" pattern="^[A-Z_][A-Z0-9_]*$" />
    ${envVarBadge(state, userKeyEnv)}
    ${indicatorHtml(userKeySource, "pushoverUserKeyEnv")}
  </div>

  <p class="section-info">
    &#9432; These values live in <code>local-overrides.yaml</code> — they are
    NOT shared with collaborators when you push the repo. The env vars themselves
    resolve from your operating-system shell environment, not from any file in the repo.
  </p>

  <div class="field-row">
    <button type="button" id="s5-test-notification" class="secondary">Send a test notification now</button>
  </div>
</div>
`;
  return { html };
}

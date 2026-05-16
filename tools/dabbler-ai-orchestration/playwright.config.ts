// Playwright config for Layer 3 of the orchestrator e2e harness
// (Set 027 Session 4). Scoped to ``src/test/playwright/`` so it does
// not collide with the @vscode/test-electron Mocha suite under
// ``src/test/suite/``. Single worker because each test launches a
// full VS Code Electron instance — running them in parallel hammers
// the host and tends to fight over user-data-dir locks.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./src/test/playwright",
  testMatch: /.*\.spec\.ts$/,
  // Per spec § Session 4: text-only assertions (Option B). The launch
  // itself is the long tail (~30s cold start), so a per-test timeout
  // of 90s gives the test body ~60s after activation.
  timeout: 90_000,
  workers: 1,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    actionTimeout: 15_000,
  },
});

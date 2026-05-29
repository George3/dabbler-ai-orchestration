// Set 050 S4 (Explorer UX revision) — unit tests for the asterisk
// marker + tooltip that replace the old "(needs migration)" row label.

import * as assert from "assert";
import { SessionSet } from "../../types";
import {
  hasSubCurrentSets,
  migrationMarker,
  migrationTooltip,
} from "../../providers/SessionSetsModel";

// Minimal cast factory — the two helpers read only `needsMigration` and
// `schemaVersionOnDisk`.
function set(over: Partial<SessionSet>): SessionSet {
  return over as SessionSet;
}

suite("migrationMarker / migrationTooltip (Set 050 S4)", () => {
  test("current set: no marker, no tooltip", () => {
    const s = set({ needsMigration: false, schemaVersionOnDisk: 4 });
    assert.strictEqual(migrationMarker(s), "");
    assert.strictEqual(migrationTooltip(s), "");
  });

  test("sub-current set: asterisk + 'Ran under schema vN'", () => {
    const s = set({ needsMigration: true, schemaVersionOnDisk: 3 });
    assert.strictEqual(migrationMarker(s), "*");
    assert.strictEqual(migrationTooltip(s), "Ran under schema v3");
  });

  test("v2 set tooltip reports v2", () => {
    const s = set({ needsMigration: true, schemaVersionOnDisk: 2 });
    assert.strictEqual(migrationTooltip(s), "Ran under schema v2");
  });

  test("missing/unknown schema version: generic tooltip", () => {
    const s = set({ needsMigration: true, schemaVersionOnDisk: null });
    assert.strictEqual(migrationMarker(s), "*");
    assert.strictEqual(migrationTooltip(s), "Ran under an older schema");
  });

  test("no '(needs migration)' string is produced anywhere", () => {
    const s = set({ needsMigration: true, schemaVersionOnDisk: 3 });
    assert.ok(!migrationMarker(s).includes("needs migration"));
    assert.ok(!migrationTooltip(s).includes("needs migration"));
  });

  test("hasSubCurrentSets gates the bulk-upgrade title-bar icon", () => {
    // Empty / all-current → icon hidden.
    assert.strictEqual(hasSubCurrentSets([]), false);
    assert.strictEqual(
      hasSubCurrentSets([
        set({ needsMigration: false }),
        set({ needsMigration: false }),
      ]),
      false,
    );
    // Any sub-current set → icon shown.
    assert.strictEqual(
      hasSubCurrentSets([
        set({ needsMigration: false }),
        set({ needsMigration: true }),
      ]),
      true,
    );
  });
});

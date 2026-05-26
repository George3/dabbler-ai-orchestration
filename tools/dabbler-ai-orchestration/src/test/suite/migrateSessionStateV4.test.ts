// Coverage for the in-extension v3 → v4 migrator. Mirrors the Python
// test suite at ai_router/tests/test_migrate_v3_to_v4.py (the Python
// side is the wider authority); these tests exercise the TS port that
// the right-click "Migrate to v4 schema" command calls directly.

import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  BACKUP_FILENAME,
  SESSION_STATE_FILENAME,
  buildV4OnDiskShape,
  migrateOneSetV4,
} from "../../utils/migrateSessionStateV4";
import {
  SCHEMA_VERSION_V3,
  SCHEMA_VERSION_V4,
  normalizeToV4Shape,
} from "../../utils/progress";

function mkTmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "migrate-v4-test-"));
}

function rmTmpDir(dir: string): void {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {
    // ignore
  }
}

function specBody(n: number): string {
  const parts: string[] = ["# Test set", "", "## Sessions", ""];
  for (let i = 1; i <= n; i++) {
    parts.push(`### Session ${i} of ${n}: title-${i}`);
    parts.push("Body...");
    parts.push("");
  }
  return parts.join("\n");
}

function writeFixture(setDir: string, state: unknown, n: number): void {
  fs.writeFileSync(
    path.join(setDir, SESSION_STATE_FILENAME),
    JSON.stringify(state, null, 2),
    "utf-8",
  );
  fs.writeFileSync(path.join(setDir, "spec.md"), specBody(n), "utf-8");
}

function readState(setDir: string): Record<string, unknown> {
  return JSON.parse(
    fs.readFileSync(path.join(setDir, SESSION_STATE_FILENAME), "utf-8"),
  );
}

function readBackup(setDir: string): Record<string, unknown> {
  return JSON.parse(
    fs.readFileSync(path.join(setDir, BACKUP_FILENAME), "utf-8"),
  );
}

function v3State(opts: {
  name?: string;
  total?: number;
  completed?: number;
  inProgress?: number | null;
  topStatus?: string;
  lifecycle?: string | null;
  orchestrator?: Record<string, unknown> | null;
  startedAt?: string | null;
  completedAt?: string | null;
  verdict?: string | null;
  extra?: Record<string, unknown>;
} = {}): Record<string, unknown> {
  const total = opts.total ?? 3;
  const completed = opts.completed ?? 0;
  const inProgress = opts.inProgress === undefined ? null : opts.inProgress;
  const sessions = [];
  for (let n = 1; n <= total; n++) {
    let status: string;
    if (n <= completed) {
      status = "complete";
    } else if (inProgress !== null && n === inProgress) {
      status = "in-progress";
    } else {
      status = "not-started";
    }
    sessions.push({ number: n, title: `title-${n}`, status });
  }
  const out: Record<string, unknown> = {
    schemaVersion: SCHEMA_VERSION_V3,
    sessionSetName: opts.name ?? "set",
    sessions,
    status: opts.topStatus ?? "in-progress",
    lifecycleState: opts.lifecycle ?? "work_in_progress",
    currentSession: inProgress,
    totalSessions: total,
    completedSessions: Array.from({ length: completed }, (_, i) => i + 1),
    startedAt: opts.startedAt ?? null,
    completedAt: opts.completedAt ?? null,
    verificationVerdict: opts.verdict ?? null,
    orchestrator: opts.orchestrator ?? null,
  };
  if (opts.extra) {
    Object.assign(out, opts.extra);
  }
  return out;
}

suite("migrateOneSetV4 — happy path", () => {
  test("in-progress v3 migrates to v4 shape with promoted orchestrator", () => {
    const tmp = mkTmpDir();
    try {
      const orch = {
        engine: "claude",
        provider: "anthropic",
        model: "claude-opus-4-7",
        effort: "high",
      };
      writeFixture(
        tmp,
        v3State({
          name: "in-flight",
          total: 3,
          completed: 1,
          inProgress: 2,
          orchestrator: orch,
          startedAt: "2026-05-26T09:00:00-04:00",
        }),
        3,
      );

      const r = migrateOneSetV4(tmp, { dryRun: true });

      assert.strictEqual(r.action, "migrated");
      const out = r.after as Record<string, unknown>;
      assert.strictEqual(out.schemaVersion, SCHEMA_VERSION_V4);
      assert.strictEqual(out.sessionSetName, "in-flight");
      assert.strictEqual(out.status, "in-progress");

      for (const dropped of [
        "lifecycleState",
        "currentSession",
        "totalSessions",
        "completedSessions",
        "startedAt",
        "completedAt",
        "verificationVerdict",
        "orchestrator",
      ]) {
        assert.ok(
          !(dropped in out),
          `v4 on-disk should not carry ${dropped}`,
        );
      }

      const sessions = out.sessions as Array<Record<string, unknown>>;
      assert.strictEqual(sessions.length, 3);
      const s2 = sessions[1];
      assert.strictEqual(s2.status, "in-progress");
      assert.deepStrictEqual(s2.orchestrator, orch);
      assert.strictEqual(s2.startedAt, "2026-05-26T09:00:00-04:00");
      const s1 = sessions[0];
      assert.strictEqual(s1.status, "complete");
      assert.strictEqual(s1.orchestrator, null);
      assert.strictEqual(s1.startedAt, null);
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("completed v3 migrates with orchestrator on the last-completed session", () => {
    const tmp = mkTmpDir();
    try {
      const orch = {
        engine: "claude",
        provider: "anthropic",
        model: "claude-opus-4-7",
        effort: "high",
      };
      writeFixture(
        tmp,
        v3State({
          name: "all-done",
          total: 3,
          completed: 3,
          topStatus: "complete",
          lifecycle: "closed",
          orchestrator: orch,
          startedAt: "2026-05-25T09:00:00-04:00",
          completedAt: "2026-05-26T17:00:00-04:00",
          verdict: "VERIFIED",
        }),
        3,
      );

      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      const out = r.after as Record<string, unknown>;
      assert.strictEqual(out.status, "complete");
      const sessions = out.sessions as Array<Record<string, unknown>>;
      const s3 = sessions[2];
      assert.strictEqual(s3.status, "complete");
      assert.deepStrictEqual(s3.orchestrator, orch);
      assert.strictEqual(s3.completedAt, "2026-05-26T17:00:00-04:00");
      assert.strictEqual(s3.verificationVerdict, "VERIFIED");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("status alias `completed` canonicalizes to `complete` on the way out", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        v3State({
          name: "alias",
          total: 2,
          completed: 2,
          topStatus: "completed",
          lifecycle: "closed",
        }),
        2,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      const out = r.after as Record<string, unknown>;
      assert.strictEqual(out.status, "complete");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("passthrough fields preserved (preCancelStatus, forceClosed)", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        v3State({
          name: "passthrough",
          total: 2,
          completed: 2,
          topStatus: "complete",
          lifecycle: "closed",
          extra: { preCancelStatus: "in-progress", forceClosed: true },
        }),
        2,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      const out = r.after as Record<string, unknown>;
      assert.strictEqual(out.preCancelStatus, "in-progress");
      assert.strictEqual(out.forceClosed, true);
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("round-trip equivalence: shim's read view over v4 output == over v3 input", () => {
    const tmp = mkTmpDir();
    try {
      const state = v3State({
        name: "round-trip",
        total: 3,
        completed: 2,
        inProgress: 3,
        orchestrator: { engine: "claude", provider: "anthropic", model: "claude-opus-4-7", effort: "high" },
        startedAt: "2026-05-26T10:00:00-04:00",
      });
      writeFixture(tmp, state, 3);
      const specPath = path.join(tmp, "spec.md");

      const before = normalizeToV4Shape(state, specPath) as Record<string, unknown>;
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      const after = normalizeToV4Shape(r.after, specPath) as Record<string, unknown>;

      assert.deepStrictEqual(after.sessions, before.sessions);
      assert.strictEqual(after.currentSession, before.currentSession);
      assert.deepStrictEqual(after.completedSessions, before.completedSessions);
      assert.deepStrictEqual(after.orchestrator, before.orchestrator);
      assert.strictEqual(after.startedAt, before.startedAt);
      assert.strictEqual(after.completedAt, before.completedAt);
      assert.strictEqual(after.verificationVerdict, before.verificationVerdict);
      assert.strictEqual(after.status, before.status);
    } finally {
      rmTmpDir(tmp);
    }
  });
});

suite("migrateOneSetV4 — idempotence", () => {
  test("v4 file is skipped without touching disk", () => {
    const tmp = mkTmpDir();
    try {
      const v4 = {
        schemaVersion: SCHEMA_VERSION_V4,
        sessionSetName: "already-v4",
        status: "complete",
        sessions: [
          {
            number: 1,
            title: "title-1",
            status: "complete",
            startedAt: null,
            completedAt: null,
            orchestrator: null,
            verificationVerdict: null,
          },
        ],
      };
      writeFixture(tmp, v4, 1);
      const r = migrateOneSetV4(tmp, { dryRun: false });
      assert.strictEqual(r.action, "skipped-v4");
      assert.ok(!fs.existsSync(path.join(tmp, BACKUP_FILENAME)));
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("apply-then-skip: second run is a no-op", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        v3State({
          name: "apply-then-skip",
          total: 2,
          completed: 2,
          topStatus: "complete",
          lifecycle: "closed",
        }),
        2,
      );
      const r1 = migrateOneSetV4(tmp, { dryRun: false });
      assert.strictEqual(r1.action, "migrated");
      assert.ok(fs.existsSync(path.join(tmp, BACKUP_FILENAME)));
      const r2 = migrateOneSetV4(tmp, { dryRun: false });
      assert.strictEqual(r2.action, "skipped-v4");
      assert.strictEqual(readBackup(tmp).schemaVersion, SCHEMA_VERSION_V3);
    } finally {
      rmTmpDir(tmp);
    }
  });
});

suite("migrateOneSetV4 — refusals", () => {
  test("v2 file is skipped with not-v3 action", () => {
    const tmp = mkTmpDir();
    try {
      const v2 = {
        schemaVersion: 2,
        sessionSetName: "v2",
        currentSession: 2,
        totalSessions: 3,
        completedSessions: [1],
        status: "in-progress",
      };
      writeFixture(tmp, v2, 3);
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-not-v3");
      assert.ok(/Migrate to v3/.test(r.reason));
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("missing schemaVersion is skipped with not-v3 action", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(tmp, { sessionSetName: "no-schema", status: "not-started" }, 1);
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-not-v3");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("broken v3 (schemaVersion=3, no sessions[]) is skipped with malformed action", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        {
          schemaVersion: 3,
          sessionSetName: "broken",
          status: "in-progress",
        },
        1,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-malformed");
      assert.ok(/sessions\[\]/.test(r.reason));
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("future schemaVersion (> 4) is skipped", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        {
          schemaVersion: 99,
          sessionSetName: "future",
          status: "in-progress",
          sessions: [],
        },
        0,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-future-schema");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("missing state file is skipped with no-state action", () => {
    const tmp = mkTmpDir();
    try {
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-no-state");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("unparseable JSON is skipped with malformed action", () => {
    const tmp = mkTmpDir();
    try {
      fs.writeFileSync(path.join(tmp, SESSION_STATE_FILENAME), "{ not json", "utf-8");
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-malformed");
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("non-object top-level JSON is skipped with malformed action", () => {
    const tmp = mkTmpDir();
    try {
      fs.writeFileSync(path.join(tmp, SESSION_STATE_FILENAME), "[]", "utf-8");
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "skipped-malformed");
      assert.ok(/array/.test(r.reason));
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("invariant violation surfaces would-violate", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        {
          schemaVersion: 3,
          sessionSetName: "violating",
          status: "complete",
          lifecycleState: "closed",
          sessions: [
            { number: 1, title: "title-1", status: "complete" },
            { number: 2, title: "title-2", status: "not-started" },
          ],
          currentSession: null,
          totalSessions: 2,
          completedSessions: [1],
        },
        2,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "would-violate");
    } finally {
      rmTmpDir(tmp);
    }
  });
});

suite("migrateOneSetV4 — backup + apply", () => {
  test("apply writes session-state.v3.bak.json with original content", () => {
    const tmp = mkTmpDir();
    try {
      const original = v3State({
        name: "backup",
        total: 2,
        completed: 2,
        topStatus: "complete",
        lifecycle: "closed",
      });
      writeFixture(tmp, original, 2);
      const r = migrateOneSetV4(tmp, { dryRun: false });
      assert.strictEqual(r.action, "migrated");
      assert.strictEqual(r.backupPath, path.join(tmp, BACKUP_FILENAME));
      const bak = readBackup(tmp);
      assert.strictEqual(bak.schemaVersion, SCHEMA_VERSION_V3);
      assert.strictEqual(bak.sessionSetName, "backup");
      const live = readState(tmp);
      assert.strictEqual(live.schemaVersion, SCHEMA_VERSION_V4);
      // Content equivalence (the .bak re-emits with indent=2).
      assert.deepStrictEqual(bak, original);
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("dry-run does not touch disk", () => {
    const tmp = mkTmpDir();
    try {
      writeFixture(tmp, v3State({ name: "dry", total: 2, completed: 1, inProgress: 2 }), 2);
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      assert.ok(!fs.existsSync(path.join(tmp, BACKUP_FILENAME)));
      assert.strictEqual(readState(tmp).schemaVersion, SCHEMA_VERSION_V3);
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("backup write failure aborts: state file untouched, backupPath undefined", () => {
    // Inject a write failure by making the backup target read-only
    // through a pre-created file with a directory at the same path
    // (Windows-portable trick: a directory cannot be renamed to a
    // file path, so the atomicWriteJson `renameSync` step throws).
    // Mirrors the Python `test_backup_write_failure_aborts` shape.
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        v3State({
          name: "backup-fail",
          total: 2,
          completed: 2,
          topStatus: "complete",
          lifecycle: "closed",
        }),
        2,
      );
      // Block the .bak filename by making it a directory.
      fs.mkdirSync(path.join(tmp, BACKUP_FILENAME));
      const r = migrateOneSetV4(tmp, { dryRun: false });
      assert.strictEqual(r.action, "failed-backup");
      // State file must be untouched.
      assert.strictEqual(readState(tmp).schemaVersion, SCHEMA_VERSION_V3);
      // No .bak landed (it's the directory we created) → backupPath
      // is undefined so callers can distinguish from the
      // rollback-needed subcase.
      assert.strictEqual(r.backupPath, undefined);
    } finally {
      rmTmpDir(tmp);
    }
  });

  test("done alias canonicalizes to complete on the way out", () => {
    // Coverage for the second status alias (the earlier alias test
    // only covered `"completed"`). The S3 verifier flagged the gap.
    const tmp = mkTmpDir();
    try {
      writeFixture(
        tmp,
        v3State({
          name: "done-alias",
          total: 2,
          completed: 2,
          topStatus: "done",
          lifecycle: "closed",
        }),
        2,
      );
      const r = migrateOneSetV4(tmp, { dryRun: true });
      assert.strictEqual(r.action, "migrated");
      const out = r.after as Record<string, unknown>;
      assert.strictEqual(out.status, "complete");
    } finally {
      rmTmpDir(tmp);
    }
  });
});

suite("buildV4OnDiskShape — pure function", () => {
  test("drops every derived top-level key", () => {
    const normalized = {
      schemaVersion: SCHEMA_VERSION_V4,
      sessionSetName: "x",
      status: "in-progress",
      sessions: [{ number: 1, title: "t", status: "in-progress" }],
      currentSession: 1,
      totalSessions: 1,
      completedSessions: [],
      orchestrator: { engine: "claude" },
      startedAt: "2026-05-26T09:00:00-04:00",
      completedAt: null,
      verificationVerdict: null,
      lifecycleState: "work_in_progress",
    };
    const out = buildV4OnDiskShape(normalized, { schemaVersion: SCHEMA_VERSION_V3 });
    assert.deepStrictEqual(
      new Set(Object.keys(out)),
      new Set(["schemaVersion", "sessionSetName", "status", "sessions"]),
    );
  });

  test("passthrough only when present in original", () => {
    const normalized = {
      schemaVersion: SCHEMA_VERSION_V4,
      sessionSetName: "x",
      status: "cancelled",
      sessions: [],
    };
    const out1 = buildV4OnDiskShape(normalized, { schemaVersion: SCHEMA_VERSION_V3 });
    assert.ok(!("forceClosed" in out1));
    const out2 = buildV4OnDiskShape(normalized, {
      schemaVersion: SCHEMA_VERSION_V3,
      forceClosed: true,
    });
    assert.strictEqual(out2.forceClosed, true);
  });

  test("status canonicalized", () => {
    const normalized = {
      schemaVersion: SCHEMA_VERSION_V4,
      sessionSetName: "x",
      status: "completed",
      sessions: [],
    };
    const out = buildV4OnDiskShape(normalized, { schemaVersion: SCHEMA_VERSION_V3 });
    assert.strictEqual(out.status, "complete");
  });
});

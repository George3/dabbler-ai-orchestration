# Session 4 verification prompt — Set 023 reader fix (extension v0.13.13)

## Context

Set 023 Session 4 ships the extension-side fix that closes Sharp Edge
1 from the Set 023 spec: `isMidSetComplete` previously treated the
`session-events.jsonl` ledger as the *only* authoritative
"session N is closed" signal. After Set 022 declared
`completedSessions[]` to be authoritative for whether-closed,
`isMidSetComplete` was the last reader on either tier that hadn't
caught up. A migrated pre-Set-022 set whose operator hand-added
`completedSessions: [1..N]` to the snapshot would still be
downgraded to In Progress in the Session Set Explorer unless the
operator also ran `close_session --repair --apply` to synthesize the
missing final-session ledger event.

The Session 2 cross-provider design audit (GPT 5.4 + Gemini Pro,
both reviewed the design before the writer fix shipped) confirmed
the array-before-ledger ordering and added two refinements that
landed in this implementation:

1. **Observability warn** when the array overrides a missing ledger
   closeout (GPT 5.4 caveat on Question (c)).
2. **Sharpened authoritative phrasing** in the schema doc and
   close-out doc to distinguish whether-closed (array) from
   when-closed (ledger), so future maintainers do not read "both
   are authoritative" as "must agree" (both providers on Question (e)).

Session 3 (system-wide audit) found one Python sharp edge
(`print_session_set_status` — shipped as `ai_router 0.2.5`) and
documented one borderline path (`close_session._is_already_closed`)
that was intentionally deferred. No additional TypeScript sharp
edges were surfaced, so this v0.13.13 release carries only the
reader fix plus its audit-driven test fixtures.

## What changed in this session

1. **`tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`**
   `isMidSetComplete` consults `completedSessions[]` before the
   events-ledger check. When the array satisfies the guard but the
   ledger does not, a one-line `console.warn` surfaces the drift.
   The legacy ledger-only path is preserved for sets without the
   array. The docstring is rewritten to reflect the new
   two-authoritative-signals contract.

2. **`tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts`**
   New suite `fileSystem — isMidSetComplete (Set 023 Session 4)`
   with fixtures F1–F7 plus a migration-shape bonus fixture. F5
   covers `null` / non-array `completedSessions` values (Gemini on
   (e)). F6 covers a stray out-of-range entry (`[1, 2, 99]` —
   audit-driven, both providers on (b) and (e)). F7 documents that
   only `currentSession` is checked; non-final disagreement is
   irrelevant (GPT on (e)).

3. **`docs/session-state-schema.md`** "Parser cheat-sheet" /
   bucketing section now documents the array-before-ledger ordering
   and the sharpened invariant phrasing.

4. **`ai_router/docs/close-out.md`** § 5 drift case 1 gains an
   attestation note: `completedSessions[]` is **operator-attested**
   for migrated sets and **tool-maintained** for sets that ran the
   close-out gate (GPT on (a)).

5. **Version bump** to extension v0.13.13:
   `tools/dabbler-ai-orchestration/package.json`,
   `tools/dabbler-ai-orchestration/package-lock.json`,
   `tools/dabbler-ai-orchestration/CHANGELOG.md`, `CLAUDE.md`.

## Verification questions

Answer in JSON with one key per question. Be specific; cite line
numbers where possible.

1. **Correctness of `isMidSetComplete`.** Does the new ordering
   (currentSession < totalSessions → array check → ledger check)
   match the spec's pseudo-code in `spec.md` § Architecture? Is the
   `Array.isArray` + `.includes(currentSession)` guard correct
   defensive shape against non-array `completedSessions` values?

2. **Observability warn placement.** The warn fires *inside* the
   array-satisfies-guard branch, only when the ledger exists and
   lacks the corresponding closeout. Is this the right moment to
   warn (not too eager, not silenced)? Any concern about warn
   spamming on repeated reads of the same set?

3. **Test coverage.** Do fixtures F1–F7 cover the spec's enumerated
   shapes plus the audit-driven cases? Any missing shape (e.g., the
   `currentSession < totalSessions` early-return path; the
   array-present-but-ledger-absent migration shape)?

4. **Doc edits.** Does the schema doc + close-out doc language hold
   up the sharpened invariant ("array is authoritative for
   whether-closed; ledger is authoritative for when-closed") clearly
   enough that a future maintainer would not "fix" the guard to
   require both signals to agree?

5. **Backward compatibility.** A set carrying `completedSessions[]`
   but stale/incorrect entries would now be classified as Done where
   it would have been In Progress under v0.13.12. The spec's Risks
   section calls this the intended migration story; do you agree, or
   does the change create a regression class we missed?

6. **Anything else (open).** Sharp edges, security concerns, naming,
   error handling, edge cases the test fixtures don't cover.


---

## Inlined: isMidSetComplete (new) + hasCloseoutEventForSession

```typescript
// Detect a stale `status: "complete"` snapshot that doesn't actually
// reflect a finished set. Two authoritative signals govern the guard,
// per the Set 022 + Set 023 sharpened invariant:
// `completedSessions[]` is authoritative for *whether* a session is
// closed; `session-events.jsonl` is authoritative for *when* each
// closeout was recorded. The guard downgrades to in-progress only when
// neither whether-closed signal agrees with the snapshot's
// `status: "complete"`. Two drift shapes still downgrade:
//
//   1. **Count mismatch.** `currentSession < totalSessions`. Pre-0.2.1
//      ai_router flipped to complete after every session, and manual
//      edits / stale consumer snapshots still produce this shape.
//
//   2. **Final-session signal gap.** `currentSession === totalSessions`
//      and the snapshot claims complete, but neither
//      `completedSessions[]` nor the events ledger records the final
//      session as closed. Set 023: `completedSessions[]` is consulted
//      *before* the ledger so a migrated pre-Set-022 set whose
//      operator hand-added the array displays as Done without also
//      needing a synthesized `closeout_succeeded` event. The legacy
//      ledger-only path remains for sets without the array.
//
// Returns false on any read/parse failure — trust the canonical status
// rather than second-guessing on garbled input.
export function isMidSetComplete(statePath: string): boolean {
  if (!fs.existsSync(statePath)) return false;
  try {
    const sd = JSON.parse(fs.readFileSync(statePath, "utf8")) as {
      currentSession?: number;
      totalSessions?: number;
      completedSessions?: unknown;
    };
    if (typeof sd.currentSession !== "number") return false;
    if (typeof sd.totalSessions !== "number") return false;

    if (sd.currentSession < sd.totalSessions) return true;

    // Set 023 Session 4: `completedSessions[]` is an alternative
    // authoritative signal to the events ledger. The array check fires
    // first so a migrated pre-Set-022 set whose snapshot carries
    // `completedSessions: [1..N]` is recognized as Done even when its
    // ledger lacks the corresponding `closeout_succeeded` event. When
    // the array satisfies the guard but the ledger does not, surface
    // the drift via console.warn so the operator can choose to heal
    // the ledger with `--repair --apply` — the override is correct,
    // the warn is observability only.
    if (Array.isArray(sd.completedSessions) &&
        sd.completedSessions.includes(sd.currentSession)) {
      const eventsPath = path.join(path.dirname(statePath), "session-events.jsonl");
      if (fs.existsSync(eventsPath) &&
          !hasCloseoutEventForSession(eventsPath, sd.currentSession)) {
        const slug = path.basename(path.dirname(statePath));
        console.warn(
          `[session-set ${slug}] completedSessions[] overrides missing ledger ` +
          `closeout for session ${sd.currentSession}`
        );
      }
      return false;
    }

    const eventsPath = path.join(path.dirname(statePath), "session-events.jsonl");
    if (fs.existsSync(eventsPath) &&
        !hasCloseoutEventForSession(eventsPath, sd.currentSession)) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

function hasCloseoutEventForSession(
  eventsPath: string,
  sessionNumber: number
): boolean {
  let text: string;
  try {
    text = fs.readFileSync(eventsPath, "utf8");
  } catch {
    return false;
  }
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    try {
      const event = JSON.parse(line) as {
        session_number?: number;
        event_type?: string;
      };
      if (
        event.event_type === "closeout_succeeded" &&
        event.session_number === sessionNumber
      ) {
        return true;
      }
    } catch {
      // skip malformed lines — append-only ledger may carry partial writes
    }
  }
  return false;
}

// Set 022 Session 2: generalization of `hasCloseoutEventForSession` to
// "how many distinct sessions does the ledger record as closed." Used
// as the Full-tier fallback for `sessionsCompleted` when
// `completedSessions[]` is missing from the snapshot (e.g., a set
// that pre-dates Set 022's writer changes and hasn't had its next
// boundary-write heal it yet). Returns 0 on any read/parse failure
// or when the file is absent — the caller treats 0 as "no
// authoritative signal" and falls through to the next derivation
// step rather than asserting "0 sessions done."

```

---

## Inlined: new test suite (F1–F7 plus migration bonus)

```typescript
// Set 023 Session 4: `isMidSetComplete` now consults
// `completedSessions[]` before falling through to the events-ledger
// check. The array is authoritative for *whether* a session is closed;
// the events ledger remains authoritative for *when* each closeout was
// recorded. Fixtures F1-F7 lock in the new ordering and the legacy
// fall-through paths.
suite("fileSystem — isMidSetComplete (Set 023 Session 4)", () => {
  function writeState(setDir: string, state: object): string {
    fs.mkdirSync(setDir, { recursive: true });
    const statePath = path.join(setDir, "session-state.json");
    fs.writeFileSync(statePath, JSON.stringify(state));
    return statePath;
  }

  function writeEvents(setDir: string, sessionsClosed: number[]): void {
    const events =
      sessionsClosed
        .map((n) =>
          JSON.stringify({
            timestamp: `2026-05-15T0${n}:00:00Z`,
            session_number: n,
            event_type: "closeout_succeeded",
          })
        )
        .join("\n") + "\n";
    fs.writeFileSync(path.join(setDir, "session-events.jsonl"), events);
  }

  // F1: array satisfies the guard with no ledger present at all.
  test("F1: completedSessions includes currentSession + no events ledger → not mid-set", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f1");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
      completedSessions: [1, 2, 3],
    });
    assert.strictEqual(isMidSetComplete(statePath), false);
    fs.rmSync(dir, { recursive: true });
  });

  // F2: array disagrees on the final session AND ledger disagrees → downgrade.
  test("F2: array missing currentSession + ledger missing closeout → mid-set", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f2");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
      completedSessions: [1, 2],
    });
    writeEvents(setDir, [1, 2]);
    assert.strictEqual(isMidSetComplete(statePath), true);
    fs.rmSync(dir, { recursive: true });
  });

  // F3: legacy path unchanged — no array, ledger closes the final session.
  test("F3: no completedSessions field + ledger has closeout → not mid-set", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f3");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
    });
    writeEvents(setDir, [1, 2, 3]);
    assert.strictEqual(isMidSetComplete(statePath), false);
    fs.rmSync(dir, { recursive: true });
  });

  // F4: legacy drift case unchanged — no array, ledger lacks final closeout.
  test("F4: no completedSessions field + ledger missing closeout → mid-set", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f4");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
    });
    writeEvents(setDir, [1, 2]);
    assert.strictEqual(isMidSetComplete(statePath), true);
    fs.rmSync(dir, { recursive: true });
  });

  // F5 (audit-driven, Gemini on (e)): non-array completedSessions values
  // are tolerated via Array.isArray; legacy ledger path takes over.
  test("F5: non-array completedSessions falls through to ledger check", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f5");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
      completedSessions: null,
    });
    writeEvents(setDir, [1, 2, 3]);
    assert.strictEqual(isMidSetComplete(statePath), false);

    // Also exercise a non-array object shape — same fall-through behavior.
    const setDir2 = path.join(dir, "f5b");
    const statePath2 = writeState(setDir2, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
      completedSessions: { not: "array" },
    });
    writeEvents(setDir2, [1, 2, 3]);
    assert.strictEqual(isMidSetComplete(statePath2), false);
    fs.rmSync(dir, { recursive: true });
  });

  // F6 (audit-driven, both on (b) and (e)): a stray out-of-range entry
  // (e.g., [1, 2, 99] with totalSessions 4 and currentSession 4) does not
  // accidentally satisfy `.includes(currentSession)`. The array check
  // returns false for `4`, so the guard falls through to the ledger,
  // which also lacks closeout for 4 → mid-set.
  test("F6: stray out-of-range array entry does not satisfy includes(currentSession)", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f6");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 4,
      totalSessions: 4,
      completedSessions: [1, 2, 99],
    });
    writeEvents(setDir, [1, 2]);
    assert.strictEqual(isMidSetComplete(statePath), true);
    fs.rmSync(dir, { recursive: true });
  });

  // F7 (audit-driven, GPT on (e)): the guard checks `currentSession`
  // specifically; disagreement on non-final sessions is irrelevant. An
  // array [1, 2] with currentSession 3 and a ledger that has a closeout
  // for session 1 only still downgrades to mid-set — neither signal
  // closes session 3.
  test("F7: non-final-session disagreement is irrelevant; only currentSession matters", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "f7");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 3,
      totalSessions: 3,
      completedSessions: [1, 2],
    });
    writeEvents(setDir, [1]);
    assert.strictEqual(isMidSetComplete(statePath), true);
    fs.rmSync(dir, { recursive: true });
  });

  // Bonus: array satisfies the guard while the ledger lacks the
  // corresponding closeout — the migration shape Set 023 was authored
  // to fix. Locks in that the override path returns false (Done) and
  // does not throw on the observability warn.
  test("array overrides missing ledger closeout (migration shape) → not mid-set", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "migration");
    const statePath = writeState(setDir, {
      status: "complete",
      currentSession: 4,
      totalSessions: 4,
      completedSessions: [1, 2, 3, 4],
    });
    writeEvents(setDir, [3]);  // synthetic-only ledger, missing session 4
    assert.strictEqual(isMidSetComplete(statePath), false);
    fs.rmSync(dir, { recursive: true });
  });
});

suite("fileSystem — countDistinctCloseoutSessions", () => {
  // Set 022 Session 2: generalization of hasCloseoutEventForSession.
  // Treated as 0 for any read failure (missing file, malformed JSON,
  // permission error) so callers fall through to the next derivation
  // step rather than asserting "no sessions done" on garbled input.
  test("returns 0 when the events file is missing", () => {
    assert.strictEqual(
      countDistinctCloseoutSessions("/nonexistent/session-events.jsonl"),
      0,
    );
  });

  test("counts distinct closeout_succeeded session numbers", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const events = [
      { session_number: 1, event_type: "work_started" },
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 2, event_type: "work_started" },
      { session_number: 2, event_type: "closeout_succeeded" },
      // Non-closeout events with the same session_number must not count.
      { session_number: 3, event_type: "work_started" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(eventsPath, events);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });

  test("dedupes duplicate closeout_succeeded events for the same session", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const events = [
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 2, event_type: "closeout_succeeded" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(eventsPath, events);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });

  test("tolerates malformed lines in the append-only ledger", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const lines = [
      JSON.stringify({ session_number: 1, event_type: "closeout_succeeded" }),
      "not json",
      JSON.stringify({ session_number: 2, event_type: "closeout_succeeded" }),
    ].join("\n") + "\n";
    fs.writeFileSync(eventsPath, lines);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });
});

```

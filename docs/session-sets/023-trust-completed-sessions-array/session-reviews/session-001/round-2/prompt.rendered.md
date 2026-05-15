
> **Round-2 context.** Round 1 (gpt-5-4, $0.140) returned ISSUES_FOUND
> with two findings:
>
> - **Major (Correctness):** the preserved/no-rewrite branch was
>   comparing a sanitized `existing_list` against `merged`, so a
>   snapshot with malformed entries like `[1, -1]` could take the
>   "preserved" branch and leave the malformed value in place.
>   **Fixed** by comparing the raw on-disk `existing_raw_list`
>   against `merged` for the rewrite decision and adding a fourth
>   "normalized" message branch for when the snapshot had malformed
>   / duplicate / unsorted entries that needed cleanup. New test
>   `test_repair_normalizes_malformed_snapshot_completed_sessions`
>   exercises this directly: snapshot `[1, -1, 2]` + ledger
>   `closeout_succeeded(1)` + synthetic `closeout_succeeded(2)`
>   → snapshot becomes `[1, 2]` with the "normalized" message.
>
> - **Minor (Completeness):** the close-out.md Section 5 text said
>   "Two apply outcomes" while listing three. **Fixed** by enumerating
>   four outcomes (backfilled / merged / normalized / preserved) and
>   noting that the union math operates on a sanitized view of the
>   snapshot.
>
> All 702 tests pass (up from 701 with the new test). Please verify
> the round-1 findings are resolved and no new issues introduced.

# Set 023 Session 1 — ai_router writer fix (union-not-overwrite)

You are an independent verifier reviewing Session 1 of session set
`023-trust-completed-sessions-array` in `dabbler-ai-orchestration`.

## Decisions confirmed (do not re-litigate)

Set 022 (shipped 2026-05-15 as `ai_router 0.2.3` + extension v0.13.12)
made `completedSessions[]` the authoritative progress ledger on both
tiers. Migration of two pre-Set-022 sets on this repo (Set 004,
Set 006) surfaced a regression: `close_session --repair --apply`
Case 1 overwrote a hand-authored `completedSessions[]` with the
events-ledger reconstruction, *dropping* sessions the operator had
declared closed.

Set 023's design (decided 2026-05-15):

1. **Repair's `completedSessions[]` backfill is monotone-up only.**
   Take the union of (a) the snapshot's existing array and (b) the
   events-ledger reconstruction. Never drop a session number the
   operator hand-authored.
2. **Three apply outcomes, three message phrasings:**
   - `backfilled completedSessions=[…]` — snapshot's array was empty/absent.
   - `merged completedSessions=[…] (union of snapshot [...] and events [...])` — snapshot's array existed but differed.
   - `repair preserved completedSessions=[…]` (no rewrite) — snapshot's array already a superset.
3. **Idempotency:** a second `--repair --apply` on a clean shape produces no further snapshot writes.

This session implements those decisions. No new drift case added;
this tightens an existing case's apply behavior.

## Session 1 plan

**Goal:** Make `close_session --repair --apply` Case 1 preserve a
hand-authored `completedSessions[]`. Release as `ai_router 0.2.4`.

**Steps:**

1. Modify `_run_repair` Case 1 apply path in
   `ai_router/close_session.py`: replace the events-ledger
   overwrite with a union computation.
2. Distinguish the three message outcomes (backfilled / merged /
   preserved).
3. Add two regression tests + an idempotency assertion to
   `ai_router/tests/test_close_session_session4.py`.
4. Update `ai_router/docs/close-out.md` Section 5 drift-case-1
   description.
5. Bump to `ai_router 0.2.4`.
6. Cross-provider verification (this round).

## Test results

`python -m pytest ai_router/tests/` → **701 passed** (up from 699
before this session; the 2 new tests landed without regressions).

The two new tests:

- `test_repair_preserves_snapshot_completed_sessions_superset` —
  snapshot has `[1, 2, 3, 4]`, ledger has only forced session-3
  closeout. After `--apply`: snapshot's array preserved verbatim;
  message line includes `preserved completedSessions=[1, 2, 3, 4]`.
- `test_repair_merges_snapshot_completed_sessions_with_events` —
  snapshot has `[2]`, ledger has session-1 closeout. After
  `--apply`: snapshot becomes `[1, 2]`; message line reports the
  union framing explicitly. Plus idempotency assertion: second
  `--apply` produces no further snapshot rewrite.

The existing `test_repair_detects_mixed_mode_drift` continues to
pass — its assertion `completedSessions == [1, 2]` is preserved
under the new union code (existing was empty, so union of {} and
{1, 2} is [1, 2], reported as "backfilled" not "merged").

## Files in this session's commit

```diff
warning: in the working copy of 'ai_router/docs/close-out.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/ai_router/__init__.py b/ai_router/__init__.py
index eca5969..9543e2c 100644
--- a/ai_router/__init__.py
+++ b/ai_router/__init__.py
@@ -61,7 +61,7 @@ the SessionLog class:
     log.log_step(session_number=1, step_number=1, ...)
 """
 
-__version__ = "0.2.3"
+__version__ = "0.2.4"
 
 from .config import load_config, resolve_generation_params
 from .models import estimate_complexity, pick_model
diff --git a/ai_router/close_session.py b/ai_router/close_session.py
index 116d611..21727d4 100644
--- a/ai_router/close_session.py
+++ b/ai_router/close_session.py
@@ -887,24 +887,32 @@ def _run_repair(
                     f"for session {target_session}"
                 )
 
-            # Set 022: also backfill completedSessions[] from the
-            # (now-repaired) events ledger. This intentionally reads
-            # ``closeout_succeeded`` events DIRECTLY rather than via
-            # ``compute_effective_completed_sessions()``, because the
-            # helper prefers a non-empty snapshot ``completedSessions[]``
-            # over the events ledger — and a mixed-mode drift snapshot
-            # can carry a stale, partial array. The
-            # unified-master-details-composite incident (2026-05-12)
-            # is the cautionary example: a hand-edited snapshot might
-            # claim ``completedSessions=[1,2,3,4]`` while
-            # ``currentSession=5`` was the session whose closeout
-            # was actually missing; routing through the helper here
-            # would re-write ``[1,2,3,4]`` even though the synthetic
-            # closeout we just appended for session 5 means [1..5]
-            # is the truth. Direct events read avoids that trap and
-            # stays idempotent on the second pass.
+            # Set 022 + 023: backfill completedSessions[] as the UNION
+            # of (a) the snapshot's existing array and (b) the
+            # ``closeout_succeeded`` session numbers in the (now-
+            # repaired) events ledger. The union is monotone-up:
+            # repair adds session numbers to bring the snapshot up to
+            # ledger reality, but never removes a session number the
+            # operator hand-authored.
+            #
+            # We read ``closeout_succeeded`` events directly rather
+            # than going through ``compute_effective_completed_sessions``
+            # because the helper short-circuits on a non-empty snapshot
+            # array and would miss the session we just synthesized.
+            # Direct events read picks up the synthetic closeout; the
+            # union then adds it to whatever the snapshot already had.
+            #
+            # Set 023 motivation: an operator hand-migrating a pre-
+            # Set-022 set adds ``completedSessions=[1..N]`` to a
+            # snapshot whose events ledger only ever recorded the
+            # final session's closeout (or, as on Set 004 of this
+            # repo, only an early session's closeout). The previous
+            # overwrite-with-ledger-view regressed the operator's
+            # count from ``[1..N]`` to a partial subset; the union
+            # preserves the hand-authored intent while still healing
+            # the ledger.
             events_now = read_events(session_set_dir)
-            backfilled = sorted({
+            from_events = sorted({
                 ev.session_number for ev in events_now
                 if ev.event_type == "closeout_succeeded"
                 and isinstance(ev.session_number, int)
@@ -912,12 +920,40 @@ def _run_repair(
                 and ev.session_number > 0
             })
             existing_completed = (state or {}).get("completedSessions")
-            existing_list = (
-                sorted(existing_completed)
+            # ``existing_clean`` is the sanitized view used for the
+            # union math (drops non-int, booleans, non-positive).
+            # ``existing_raw_list`` is the snapshot's literal value,
+            # used to decide whether the *file on disk* needs a
+            # rewrite — a malformed entry in the raw array (e.g.,
+            # ``[1, -1]``) means the file is not already correct
+            # even when ``existing_clean`` happens to equal
+            # ``merged``, so the preserved/no-rewrite branch must
+            # not fire. This is the round-1 verifier finding fix.
+            existing_raw_list = (
+                existing_completed
+                if isinstance(existing_completed, list)
+                else None
+            )
+            existing_clean = (
+                sorted({
+                    c for c in existing_completed
+                    if isinstance(c, int)
+                    and not isinstance(c, bool)
+                    and c > 0
+                })
                 if isinstance(existing_completed, list)
                 else []
             )
-            if backfilled and backfilled != existing_list:
+            merged = sorted(set(existing_clean) | set(from_events))
+            # Rewrite the snapshot whenever the raw on-disk value
+            # does not already equal the canonical merged form.
+            # That covers three apply outcomes: backfilled (no array
+            # before), merged (array existed but differed cleanly),
+            # and normalized (array existed but had malformed /
+            # duplicate / unsorted entries that need cleaning up).
+            # Only the truly-equal case takes the no-rewrite branch.
+            needs_rewrite = bool(merged) and existing_raw_list != merged
+            if needs_rewrite:
                 try:
                     state_path = os.path.join(
                         session_set_dir, "session-state.json"
@@ -931,22 +967,67 @@ def _run_repair(
                     # concurrent writer or external mutation could
                     # break it between then and now — fall back to an
                     # empty dict and write a snapshot that records the
-                    # backfilled completedSessions.
+                    # merged completedSessions.
                     snapshot = read_session_state(session_set_dir) or {}
-                    snapshot["completedSessions"] = backfilled
+                    snapshot["completedSessions"] = merged
                     with open(state_path, "w", encoding="utf-8") as f:
                         json.dump(snapshot, f, indent=2)
                         f.write("\n")
-                    messages.append(
-                        "repair applied: backfilled "
-                        f"completedSessions={backfilled} into "
-                        "session-state.json"
-                    )
+                    # Distinguish three apply outcomes:
+                    #   - "backfilled" — snapshot had no array at all
+                    #   - "merged"     — snapshot had a clean array
+                    #                    that differed cleanly from
+                    #                    the union view
+                    #   - "normalized" — snapshot's array had
+                    #                    malformed / duplicate /
+                    #                    unsorted entries that we
+                    #                    cleaned up while also
+                    #                    applying the union
+                    if existing_raw_list is None or existing_raw_list == []:
+                        messages.append(
+                            "repair applied: backfilled "
+                            f"completedSessions={merged} into "
+                            "session-state.json"
+                        )
+                    elif existing_raw_list == existing_clean:
+                        # Clean input, just augmented by the events
+                        # reconstruction.
+                        messages.append(
+                            "repair applied: merged "
+                            f"completedSessions={merged} into "
+                            "session-state.json (union of snapshot "
+                            f"{existing_clean} and events "
+                            f"{from_events})"
+                        )
+                    else:
+                        # Malformed or unsorted input. Report both
+                        # the raw existing and the cleaned merged so
+                        # the operator sees what was normalized away.
+                        messages.append(
+                            "repair applied: normalized "
+                            f"completedSessions={merged} into "
+                            "session-state.json (raw snapshot "
+                            f"{existing_raw_list} cleaned + unioned "
+                            f"with events {from_events})"
+                        )
                 except Exception as exc:  # pragma: no cover — defensive
                     messages.append(
                         f"repair could not backfill completedSessions[]: "
                         f"{type(exc).__name__}: {exc}"
                     )
+            elif merged and existing_raw_list == merged and from_events:
+                # Snapshot's array already covers everything the
+                # ledger reconstruction would add AND its raw on-disk
+                # form is exactly the canonical merged value — no
+                # rewrite needed. Surface this as a distinct outcome
+                # so an operator who hand-migrated a set sees that
+                # their array was preserved verbatim.
+                messages.append(
+                    "repair preserved completedSessions="
+                    f"{merged} in session-state.json "
+                    "(snapshot already a superset of the events-"
+                    "ledger reconstruction)"
+                )
 
     # Case 2: events say closed, state has not caught up.
     #
diff --git a/ai_router/docs/close-out.md b/ai_router/docs/close-out.md
index 5c30ee5..4976424 100644
--- a/ai_router/docs/close-out.md
+++ b/ai_router/docs/close-out.md
@@ -499,13 +499,42 @@ The drift shapes the walk detects:
    session so the events ledger becomes internally consistent and
    the tree view stops downgrading. **Set 022 extension:** the
    apply path also backfills `completedSessions[]` in
-   `session-state.json` using
-   `compute_effective_completed_sessions` (which now sees the
-   synthesized closeout events). A drifted set with events for
-   sessions 1–4 but a snapshot that claims session 5 done gets
-   `completedSessions: [1, 2, 3, 4]` plus synthetic session-5
-   events (or whatever the helper resolves to), bringing both
-   files into agreement on the same boundary write.
+   `session-state.json` using the events ledger directly (post-
+   synthesis). **Set 023 refinement (`ai_router 0.2.4`):** the
+   backfill is now the **union** of (a) the snapshot's existing
+   `completedSessions[]` (sanitized — non-positive-int entries,
+   booleans, and duplicates are dropped from the union math) and
+   (b) the distinct `closeout_succeeded` session numbers in the
+   now-repaired ledger. The union is **monotone-up only** —
+   repair appends session numbers to bring the snapshot up to
+   ledger reality but never removes a session number the operator
+   hand-authored. Four apply outcomes are distinguished in the
+   `messages` line:
+     - *Backfilled* (snapshot's array was empty, absent, or
+       null): the repair writes the events-ledger reconstruction
+       in full — `repair applied: backfilled completedSessions=[...]`.
+     - *Merged* (snapshot's array is a clean sorted-int list that
+       differs from the union view): the repair writes the union
+       and reports both sources — `repair applied: merged
+       completedSessions=[...] (union of snapshot [...] and
+       events [...])`.
+     - *Normalized* (snapshot's array exists but has malformed,
+       duplicate, or unsorted entries): the repair cleans the
+       array while applying the union — `repair applied:
+       normalized completedSessions=[...] (raw snapshot [...]
+       cleaned + unioned with events [...])`. This branch ensures
+       a typo like `[1, -1, 2]` does not survive a repair pass.
+     - *Preserved* (snapshot's raw on-disk array already equals
+       the canonical merged form): no snapshot rewrite happens;
+       the message line reports `repair preserved
+       completedSessions=[...] (snapshot already a superset of the
+       events-ledger reconstruction)` so the operator sees the
+       no-op explicitly.
+   This eliminates the pre-Set-023 regression where a hand-migrated
+   snapshot with `completedSessions: [1, 2, 3, 4]` would be
+   overwritten back to a partial subset whenever the events ledger
+   only recorded a later session's closeout (Set 004 on this repo
+   hit this on 2026-05-15).
 
 2. **Closeout-succeeded-but-state-not-closed.** The reverse drift:
    events ledger says the session closed but `session-state.json`
diff --git a/ai_router/tests/test_close_session_session4.py b/ai_router/tests/test_close_session_session4.py
index 1c9a467..39145b9 100644
--- a/ai_router/tests/test_close_session_session4.py
+++ b/ai_router/tests/test_close_session_session4.py
@@ -612,6 +612,197 @@ def test_repair_detects_mixed_mode_drift(closeable_set: Path):
     assert any("no drift detected" in m for m in outcome3.messages)
 
 
+def test_repair_preserves_snapshot_completed_sessions_superset(
+    closeable_set: Path,
+):
+    """Set 023: ``--repair --apply`` Case 1 must preserve a snapshot's
+    hand-authored ``completedSessions[]`` when it is a superset of what
+    the events ledger can reconstruct.
+
+    Reproduces the Set 022 migration shape on Set 004 (2026-05-15): a
+    pre-Set-022 set's snapshot was hand-migrated to declare
+    ``status: complete`` with ``completedSessions: [1, 2, 3, 4]`` even
+    though the events ledger only ever recorded one closeout (session
+    3, forced). Under the pre-Set-023 overwrite-from-events behavior,
+    ``--repair --apply`` regressed the array to ``[3, 4]`` (events
+    [3] + synthetic [4]), losing the operator's intent for sessions
+    1 and 2. Under Set 023 the repair takes the union and preserves
+    the snapshot's claim.
+    """
+    # Events ledger: only a single forced session-3 closeout (the
+    # legacy shape).
+    append_event(
+        str(closeable_set),
+        "closeout_succeeded",
+        3,
+        forced=True,
+        method="snapshot_flip",
+        verdict="VERIFIED",
+    )
+
+    # Snapshot: operator hand-migrated to declare the full 4-of-4
+    # completion with completedSessions[] but events ledger never
+    # caught up.
+    state_path = closeable_set / "session-state.json"
+    state = json.loads(state_path.read_text(encoding="utf-8"))
+    state["currentSession"] = 4
+    state["totalSessions"] = 4
+    state["status"] = "complete"
+    state["lifecycleState"] = "closed"
+    state["completedAt"] = "2026-04-30T15:03:35-04:00"
+    state["verificationVerdict"] = "VERIFIED"
+    state["completedSessions"] = [1, 2, 3, 4]
+    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
+
+    # --apply: synthetic closeout trio lands against session 4; the
+    # snapshot's completedSessions=[1, 2, 3, 4] is preserved verbatim
+    # (the union of [1, 2, 3, 4] and ledger view {3, 4} is still
+    # [1, 2, 3, 4]).
+    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
+    outcome = close_session.run(args)
+    assert outcome.result == "succeeded"
+
+    state_after = read_session_state(str(closeable_set)) or {}
+    assert state_after.get("completedSessions") == [1, 2, 3, 4], (
+        f"expected completedSessions=[1, 2, 3, 4] preserved across "
+        f"--apply; got {state_after.get('completedSessions')!r}"
+    )
+
+    # Message distinguishes the "preserved" outcome so the operator
+    # can tell at a glance.
+    assert any(
+        "preserved completedSessions=[1, 2, 3, 4]" in m
+        for m in outcome.messages
+    ), outcome.messages
+
+    # Events ledger now has both the original forced session-3
+    # closeout and the synthetic session-4 closeout.
+    events_after = read_events(str(closeable_set))
+    session4_closeouts = [
+        e for e in events_after
+        if e.event_type == "closeout_succeeded" and e.session_number == 4
+    ]
+    assert len(session4_closeouts) == 1
+    assert session4_closeouts[0].fields.get("repaired") is True
+
+
+def test_repair_merges_snapshot_completed_sessions_with_events(
+    closeable_set: Path,
+):
+    """Set 023: ``--repair --apply`` Case 1 takes the union when the
+    snapshot's ``completedSessions[]`` and the events-ledger
+    reconstruction disagree on different sessions. The union is
+    monotone-up: every session number from either source survives.
+    """
+    # Events ledger: closeout for an earlier session that the
+    # snapshot's hand-authored array does not mention.
+    append_event(
+        str(closeable_set),
+        "closeout_requested",
+        1,
+    )
+    append_event(
+        str(closeable_set),
+        "closeout_succeeded",
+        1,
+        verdict="VERIFIED",
+    )
+
+    # Snapshot: declares session 2 complete with a partial
+    # completedSessions array (only session 2, not session 1) — the
+    # operator hand-edited mid-migration.
+    state_path = closeable_set / "session-state.json"
+    state = json.loads(state_path.read_text(encoding="utf-8"))
+    state["currentSession"] = 2
+    state["status"] = "complete"
+    state["lifecycleState"] = "closed"
+    state["completedAt"] = "2026-05-12T15:20:00.000000-04:00"
+    state["verificationVerdict"] = "VERIFIED"
+    state["completedSessions"] = [2]  # partial; missing session 1
+    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
+
+    # --apply: synthetic session-2 closeout lands; completedSessions[]
+    # becomes the union of snapshot [2], events {1}, and the
+    # synthetic {2} → [1, 2].
+    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
+    outcome = close_session.run(args)
+    assert outcome.result == "succeeded"
+
+    state_after = read_session_state(str(closeable_set)) or {}
+    assert state_after.get("completedSessions") == [1, 2], (
+        f"expected completedSessions=[1, 2] (union of snapshot [2] and "
+        f"events {{1}} ∪ synthetic {{2}}); got "
+        f"{state_after.get('completedSessions')!r}"
+    )
+
+    # Message line explicitly reports the union framing so the
+    # operator sees both sources.
+    assert any(
+        "merged completedSessions=[1, 2]" in m
+        and "union of snapshot [2]" in m
+        and "events [1, 2]" in m
+        for m in outcome.messages
+    ), outcome.messages
+
+    # Idempotent: a second --apply run produces no further snapshot
+    # rewrite (the array is already correct under the new union).
+    outcome2 = close_session.run(args)
+    assert outcome2.result == "succeeded"
+    assert any("no drift detected" in m for m in outcome2.messages), (
+        outcome2.messages
+    )
+
+
+def test_repair_normalizes_malformed_snapshot_completed_sessions(
+    closeable_set: Path,
+):
+    """Set 023 round-1 verifier finding: when the snapshot's
+    ``completedSessions`` contains malformed entries (booleans,
+    negatives, non-ints), ``--repair --apply`` Case 1 must rewrite
+    the snapshot with the canonical merged form rather than taking
+    the no-rewrite "preserved" branch and leaving the malformed
+    array in place.
+    """
+    # Events ledger: a clean session-1 closeout from a prior close.
+    append_event(str(closeable_set), "closeout_requested", 1)
+    append_event(str(closeable_set), "closeout_succeeded", 1, verdict="VERIFIED")
+
+    # Snapshot: hand-migrated by an operator with a typo or two —
+    # the array contains -1 (negative, nonsensical) alongside the
+    # legitimate sessions 1 and 2.
+    state_path = closeable_set / "session-state.json"
+    state = json.loads(state_path.read_text(encoding="utf-8"))
+    state["currentSession"] = 2
+    state["status"] = "complete"
+    state["lifecycleState"] = "closed"
+    state["completedAt"] = "2026-05-15T12:00:00.000000-04:00"
+    state["verificationVerdict"] = "VERIFIED"
+    state["completedSessions"] = [1, -1, 2]
+    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
+
+    # --apply: must normalize the malformed entry away while writing
+    # the union with the events-ledger reconstruction (+ synthetic
+    # session-2 closeout).
+    args = _ns(session_set_dir=str(closeable_set), repair=True, apply=True)
+    outcome = close_session.run(args)
+    assert outcome.result == "succeeded"
+
+    state_after = read_session_state(str(closeable_set)) or {}
+    assert state_after.get("completedSessions") == [1, 2], (
+        f"expected malformed [-1] to be normalized away, leaving "
+        f"completedSessions=[1, 2]; got "
+        f"{state_after.get('completedSessions')!r}"
+    )
+
+    # Message line specifically reports the "normalized" outcome so
+    # an operator can see the malformed entries were dropped.
+    assert any(
+        "normalized completedSessions=[1, 2]" in m
+        and "raw snapshot [1, -1, 2]" in m
+        for m in outcome.messages
+    ), outcome.messages
+
+
 def test_repair_detects_event_says_closed_but_state_lagging(
     closeable_set: Path,
 ):
diff --git a/pyproject.toml b/pyproject.toml
index 32d08f0..7d2123a 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -4,7 +4,7 @@ build-backend = "setuptools.build_meta"
 
 [project]
 name = "dabbler-ai-router"
-version = "0.2.3"
+version = "0.2.4"
 description = "Multi-provider model routing, prompt templates, session state, and metrics for the Dabbler AI-led-workflow."
 readme = "README.md"
 license = "MIT"

```

## Your verification task

Evaluate per the structured verifier instructions:

1. **Correctness.** Does the union computation match the spec's
   "monotone-up only" framing? Are there shapes where it incorrectly
   *adds* a session number that should not be marked closed (e.g.,
   could the ledger after synthesis include a stale event for an
   unrelated session)? Is the idempotency invariant preserved (a
   second apply on a clean shape doesn't rewrite the snapshot)?

2. **Completeness.** Does the implementation cover all three message
   outcomes the spec enumerates? Is the "preserved" no-rewrite branch
   actually a no-op (no snapshot.write happens, mtime stable)?

3. **Defensive handling.** Does the new `existing_list` filter
   handle malformed snapshot arrays (non-int entries, booleans,
   negative numbers) the same way the previous code did? Does
   `read_session_state` being None still get handled by the
   `or {}` fallback?

4. **Doc/code alignment.** Does the close-out.md Section 5 update
   accurately describe what the code now does?

Output JSON only:

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {
      "category": "Correctness | Completeness | False Positive",
      "severity": "Critical | Major | Minor",
      "description": "...",
      "location": "<file path or section>"
    }
  ]
}
```

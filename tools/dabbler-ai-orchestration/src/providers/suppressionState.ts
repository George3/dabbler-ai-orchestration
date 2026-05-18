// Manual-collapse suppression state for the Set 029 Session 4 custom
// tree. Per S4 audit Q2(a) + GPT-5.4 M7: the suppression key is the
// (slug, marker.updatedAt) tuple — naturally aging because the key
// changes on every new SessionStart. Pure reducer functions; the
// caller persists the resulting state via vscode workspaceState.
//
// The state object is `Record<slug, marker.updatedAt>`. A row is
// suppressed iff `state[slug] === currentMarker.updatedAt` for that
// row's marker. Manual re-expand clears state[slug]. Pruning drops
// entries whose slug is no longer in the visible set list.

export type SuppressionState = Record<string, string>;

// Is the row for this (slug, updatedAt) currently suppressed?
export function isSuppressed(
  state: SuppressionState,
  slug: string,
  markerUpdatedAt: string | null,
): boolean {
  if (!markerUpdatedAt) return false;
  return state[slug] === markerUpdatedAt;
}

// Operator manually collapsed the accordion. Suppress auto-expand
// for THIS occurrence (same updatedAt). The next SessionStart writes
// a fresh marker with a new updatedAt — that automatically un-
// suppresses because the key tuple no longer matches.
export function suppress(
  state: SuppressionState,
  slug: string,
  markerUpdatedAt: string,
): SuppressionState {
  return { ...state, [slug]: markerUpdatedAt };
}

// Operator manually expanded the row again (clicked the collapsed
// header). Clear suppression for the slug entirely — the next
// auto-expand signal will fire normally even within the current
// occurrence.
export function clearSuppression(state: SuppressionState, slug: string): SuppressionState {
  if (!(slug in state)) return state;
  const next: SuppressionState = { ...state };
  delete next[slug];
  return next;
}

// Prune entries whose slug is no longer in the visible-set list.
// Prevents workspaceState from accumulating stale keys after sets
// are renamed, deleted, or moved.
export function prune(state: SuppressionState, visibleSlugs: ReadonlySet<string>): SuppressionState {
  let changed = false;
  const next: SuppressionState = {};
  for (const slug of Object.keys(state)) {
    if (visibleSlugs.has(slug)) {
      next[slug] = state[slug];
    } else {
      changed = true;
    }
  }
  return changed ? next : state;
}

// Set 036 Session 4 (Q3): chatSessionId-mismatch takeover modal.
//
// The H4 identity composite (Set 036 Session 1) is
// engine + provider + chatSessionId. When start_session refuses with
// EXIT_CHECKOUT_CONFLICT because the same engine+provider is already
// held by a different chatSessionId — typically a stale Claude chat
// that left the slot claimed — the existing "Poll for release"
// prompt's assumption ("the other holder may release naturally") is
// wrong: the same engine is sitting there. This module surfaces a
// modal with the three Q3-locked actions so the operator can take
// over, observe in read-only mode, or cancel.
//
// Pure helper: the showInformationMessage surface is injectable so
// the Layer-2 test in chatSessionMismatchModal.test.ts can drive
// each branch without booting the VS Code window. The CheckoutPoll
// integration point (CheckoutPollService.handleConflict) constructs
// the live surface from vscode.window.showInformationMessage with
// `{ modal: true }`.

import * as vscode from "vscode";

export type ChatSessionMismatchChoice = "take-over" | "read-only" | "cancel";

// The three button labels surfaced in the modal. Exported so callers
// (and tests) can pattern-match the user's choice without re-deriving
// the label strings. The order in showInformationMessage call sites
// is take-over → read-only → cancel; "Cancel" is also the implicit
// dismiss choice (closing the modal via the X) so undefined collapses
// to "cancel" in resolveChoice().
export const MODAL_TAKE_OVER = "Take Over";
export const MODAL_READ_ONLY = "Open in Read-Only Mode";
export const MODAL_CANCEL = "Cancel";

export interface MismatchCopy {
  // The H4 holder composite text, with chatSessionId truncated to
  // the first 8 characters per the Q3 audit-locked verdict. Rendered
  // in the modal body.
  heldByLabel: string;
  // The would-be holder's composite text (same truncation rule).
  wouldBeLabel: string;
  // The session set slug, used in both the title and the body line.
  sessionSetSlug: string;
}

export type ShowModal = (
  message: string,
  options: { modal: true; detail?: string },
  ...items: string[]
) => Thenable<string | undefined>;

// Truncate a chatSessionId to 8 chars (or render a placeholder when
// the field is missing/null). 8 chars is enough to disambiguate the
// chat for the operator without surfacing the full UUID. Matches the
// `_identity_label` Python helper's contract on the CLI side.
export function truncateChatSessionId(value: string | null | undefined): string {
  if (typeof value !== "string" || value.length === 0) return "<none>";
  if (value.length <= 8) return value;
  return value.slice(0, 8) + "…";
}

export function formatHolderLabel(
  engine: string,
  provider: string,
  chatSessionId: string | null,
): string {
  const cid = truncateChatSessionId(chatSessionId);
  return `${engine} + ${provider} + chat ${cid}`;
}

export function buildModalMessage(copy: MismatchCopy): {
  message: string;
  detail: string;
} {
  return {
    message: `Another chat already checked out "${copy.sessionSetSlug}".`,
    detail:
      `Held by: ${copy.heldByLabel}\n` +
      `This chat: ${copy.wouldBeLabel}\n\n` +
      `Take Over forces the check-out to this chat (audit-logged). ` +
      `Open in Read-Only Mode keeps the other chat's check-out intact ` +
      `and prevents this chat's extension commands from writing state. ` +
      `Cancel aborts the start.`,
  };
}

export function resolveChoice(label: string | undefined): ChatSessionMismatchChoice {
  switch (label) {
    case MODAL_TAKE_OVER:
      return "take-over";
    case MODAL_READ_ONLY:
      return "read-only";
    default:
      return "cancel";
  }
}

// Drive the modal. Default surface is the live vscode one; tests pass
// their own. The promise resolves to the locked choice — never throws.
export async function chatSessionMismatchModal(
  copy: MismatchCopy,
  show?: ShowModal,
): Promise<ChatSessionMismatchChoice> {
  const surface: ShowModal =
    show ??
    ((m, o, ...items) =>
      vscode.window.showInformationMessage(m, o, ...items) as Thenable<string | undefined>);
  const { message, detail } = buildModalMessage(copy);
  const choice = await surface(
    message,
    { modal: true, detail },
    MODAL_TAKE_OVER,
    MODAL_READ_ONLY,
    MODAL_CANCEL,
  );
  return resolveChoice(choice);
}

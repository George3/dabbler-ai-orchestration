/**
 * "Resolve Set by Number" Command-Palette affordance — Set 050 S4
 * (Feature 2), the minimal extension surface for the number->slug handle
 * (verdict Q9). The load-bearing resolver lives in `ai_router` and backs
 * `start_session --session-set-dir <n>`; this is its human-facing twin.
 *
 * Flow: ask for a number via `showInputBox`, resolve it against the
 * scanned session sets entirely in-process (no Python — a Lightweight
 * consumer without the router still gets the handle), then present a
 * QuickPick of actions that reuse the existing copy / open commands.
 *
 * Match / collision / no-match are surfaced with the same posture as the
 * Python resolver: a collision names both offending slugs, a no-match
 * lists the available numbers. No fuzzy "nearest" suggestion.
 */
import * as vscode from "vscode";
import { SessionSet } from "../types";
import { readAllSessionSets } from "../utils/fileSystem";
import {
  parseSetHandle,
  resolveSetNumber,
} from "../utils/resolveSetNumber";

interface CommandDeps {
  // Injectable for tests; defaults to the real scan.
  readSets?: () => SessionSet[];
}

export function registerResolveSetNumberCommand(
  context: vscode.ExtensionContext,
  deps: CommandDeps = {},
): void {
  const readSets = deps.readSets ?? readAllSessionSets;

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabblerSessionSets.resolveSetNumber",
      async () => {
        const raw = await vscode.window.showInputBox({
          title: "Resolve session set by number",
          prompt: "Enter a session-set number (e.g. 50 or 050)",
          placeHolder: "50",
          ignoreFocusOut: true,
          validateInput: (value) =>
            value.trim() === "" || parseSetHandle(value) !== null
              ? undefined
              : "Enter a bare number (e.g. 50). Leading zeros and a 'Set ' prefix are OK.",
        });
        if (raw === undefined) return; // cancelled
        const n = parseSetHandle(raw);
        if (n === null) {
          vscode.window.showErrorMessage(
            `"${raw}" is not a session-set number. Enter a bare integer like 50.`,
          );
          return;
        }

        const sets = readSets();
        const slugs = sets.map((s) => s.name);
        const result = resolveSetNumber(slugs, n);

        if (result.kind === "no-match") {
          const avail =
            result.available.length > 0
              ? result.available.join(", ")
              : "(none)";
          vscode.window.showErrorMessage(
            `No session set numbered ${n}. Available numbers: ${avail}.`,
          );
          return;
        }
        if (result.kind === "collision") {
          vscode.window.showErrorMessage(
            `Number ${n} is ambiguous — it matches ${result.matches.join(
              " and ",
            )}. Two session sets must not share a numeric prefix; rename one.`,
          );
          return;
        }

        const slug = result.slug;
        const set = sets.find((s) => s.name === slug);
        await presentActions(slug, set);
      },
    ),
  );
}

async function presentActions(
  slug: string,
  set: SessionSet | undefined,
): Promise<void> {
  type Action = vscode.QuickPickItem & { run: () => void | Promise<void> };
  const actions: Action[] = [
    {
      label: "$(clippy) Copy slug",
      description: slug,
      run: async () => {
        await vscode.env.clipboard.writeText(slug);
        vscode.window.setStatusBarMessage(`Copied: ${slug}`, 4000);
      },
    },
    {
      label: "$(clippy) Copy “Start the next session” prompt",
      description: `Start the next session of \`${slug}\`.`,
      run: async () => {
        await vscode.env.clipboard.writeText(
          `Start the next session of \`${slug}\`.`,
        );
        vscode.window.setStatusBarMessage("Copied: start next session", 4000);
      },
    },
  ];
  if (set?.specPath) {
    actions.push({
      label: "$(go-to-file) Open spec",
      description: slug,
      run: () =>
        void vscode.commands.executeCommand("dabblerSessionSets.openSpec", {
          set,
        }),
    });
  }

  const pick = await vscode.window.showQuickPick(actions, {
    title: `Set ${slug}`,
    placeHolder: "What would you like to do with this set?",
  });
  if (pick) await pick.run();
}

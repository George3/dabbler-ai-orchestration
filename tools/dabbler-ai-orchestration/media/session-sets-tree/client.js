// Webview-side client for the Set 029 Session 4 custom Session Sets
// view. Owns: ARIA tree rendering (roving tabindex), keyboard nav,
// contextmenu / Shift+F10 / Context Menu key dispatch, manual expand/
// collapse, postMessage protocol with monotonic-version drop per
// S4 audit GPT-5.4 M3.
//
// All dynamic text from the host snapshot is HTML-escaped here on the
// webview side too (defense-in-depth) before any innerHTML
// assignment, per S4 R13 mitigation / GPT-5.4 M5.
//
// TODO: type-ahead search (WAI-ARIA tree pattern). Deferred to v1.1
// per S4 audit Gemini M10 — today's set counts are small enough that
// arrow nav is fine; the affordance ships when set counts grow.

(function () {
  const vscode = acquireVsCodeApi();
  const root = document.getElementById("root");
  let currentVersion = -1;
  let scanState = "loading";
  let lastSnapshot = null;
  let suppressed = {}; // slug -> marker.updatedAt
  // Manually toggled slugs in the current session (added on every
  // user click). Persists across re-renders so a fresh snapshot
  // doesn't snap-back an operator's manual collapse / expand.
  const manualToggles = {};

  // ----- Escape helpers (defense-in-depth) -----
  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escAttr(s) {
    return escHtml(s).replace(/"/g, "&quot;");
  }

  // ----- Message receive (host → webview) -----
  window.addEventListener("message", function (event) {
    const msg = event.data;
    if (!msg || typeof msg !== "object") return;
    if (typeof msg.version === "number" && msg.version < currentVersion) {
      // Stale snapshot — drop. Monotonic version protects against
      // out-of-order watcher / polling races.
      return;
    }
    if (typeof msg.version === "number") {
      currentVersion = msg.version;
    }
    switch (msg.type) {
      case "rowsSnapshot":
        scanState = msg.scanState || "ready";
        lastSnapshot = msg.payload;
        render();
        return;
      case "scanStateChanged":
        scanState = msg.state;
        render();
        return;
      case "suppressionEcho":
        suppressed = msg.suppressed || {};
        render();
        return;
    }
  });

  // ----- Render -----
  function render() {
    if (!root) return;
    if (scanState === "loading") {
      root.innerHTML =
        '<div class="loading-sentinel" role="status" aria-live="polite">' +
          '<div class="loading-title">Setting up your project…</div>' +
          '<div class="loading-subtitle">scanning session sets…</div>' +
        '</div>';
      return;
    }
    if (!lastSnapshot) {
      // Ready but no snapshot yet. Render nothing; host will ship one
      // momentarily.
      root.innerHTML = "";
      return;
    }
    if (!lastSnapshot.hasAnySets) {
      // viewsWelcome equivalent — render the welcome HTML provided
      // by the host (it parses package.json viewsWelcome contents).
      // welcomeHtml is host-escaped via the renderWelcomeMarkdown
      // pipeline, safe to insert.
      root.innerHTML = '<div class="welcome">' + lastSnapshot.welcomeHtml + '</div>';
      return;
    }

    const parts = [];
    // Set 033 Session 2: ambiguity banner retired. Multi-in-progress
    // is the supported case — every in-progress row carries its own
    // accordion below.
    parts.push('<div role="tree" aria-label="Session Sets" class="tree">');
    for (const bucket of lastSnapshot.buckets) {
      parts.push(renderBucket(bucket));
    }
    parts.push('</div>');
    root.innerHTML = parts.join("");

    wireInteraction();
    initRovingFocus();
  }

  function renderBucket(bucket) {
    const labelText = bucket.label + "  (" + bucket.count + ")";
    const groupId = "group-" + bucket.key;
    if (bucket.count === 0) {
      return (
        '<div role="group" aria-labelledby="' + groupId + '" class="bucket bucket-empty">' +
          '<div id="' + groupId + '" class="bucket-header">' + escHtml(labelText) + '</div>' +
        '</div>'
      );
    }
    const rows = bucket.rows.map(function (row) { return renderRow(row); }).join("");
    return (
      '<div role="group" aria-labelledby="' + groupId + '" class="bucket">' +
        '<div id="' + groupId + '" class="bucket-header">' + escHtml(labelText) + '</div>' +
        rows +
      '</div>'
    );
  }

  function renderRow(row) {
    // Set 033 Session 2: every in-progress row is expandable when
    // accordionHtml is non-null (multi-in-progress is the supported
    // case). Non-in-progress rows still skip the accordion entirely.
    const isExpandable = row.accordionHtml !== null;
    // Default expansion: expandable + not currently suppressed for
    // this occurrence. Manual override (current session click) takes
    // precedence.
    let expanded;
    if (Object.prototype.hasOwnProperty.call(manualToggles, row.slug)) {
      expanded = manualToggles[row.slug];
    } else {
      expanded = isExpandable && !isSuppressedForRow(row);
    }
    const ariaExpanded = isExpandable ? ' aria-expanded="' + (expanded ? "true" : "false") + '"' : "";
    const chevron = isExpandable
      ? '<span class="chevron" aria-hidden="true">' + (expanded ? "▾" : "▸") + '</span>'
      : '<span class="chevron-spacer" aria-hidden="true"></span>';
    const accordionAttrs = isExpandable
      ? (' data-expandable="1" data-accordion-updated-at="' +
          (row.accordionUpdatedAt ? escAttr(row.accordionUpdatedAt) : "") + '"')
      : "";

    const bodyHtml = isExpandable && expanded
      ? '<div class="accordion-body" role="region" aria-label="Orchestrator">' +
          // accordionHtml is host-escaped (OrchestratorAccordion.escHtml
          // / escAttr) — safe to inject.
          row.accordionHtml +
        '</div>'
      : "";

    return (
      '<div role="treeitem" tabindex="-1" aria-level="2"' + ariaExpanded +
      ' aria-selected="false" data-slug="' + escAttr(row.slug) + '"' +
      ' data-state="' + escAttr(row.state) + '"' +
      ' data-context-value="' + escAttr(row.contextValue) + '"' +
      accordionAttrs +
      ' class="row row-' + escAttr(row.state) + '">' +
        '<div class="row-header" role="presentation">' +
          chevron +
          '<span class="row-icon" aria-hidden="true" data-icon="' + escAttr(row.iconSlug) + '"></span>' +
          '<span class="row-name">' + escHtml(row.name) + '</span>' +
          '<span class="row-description">' + escHtml(row.description) + '</span>' +
        '</div>' +
        bodyHtml +
      '</div>'
    );
  }

  function isSuppressedForRow(row) {
    // Set 033 Session 2: row payload now carries `accordionUpdatedAt`
    // (orchestrator.lastActivityAt). A row is suppressed iff the
    // host's suppression record for the slug exactly matches the
    // current accordion's updatedAt. New orchestrator activity bumps
    // lastActivityAt, the key mismatches, and the row auto-expands
    // on the next paint without the operator having to intervene.
    if (!row.accordionUpdatedAt) return false;
    return suppressed[row.slug] === row.accordionUpdatedAt;
  }

  // ----- Roving tabindex + kbd nav -----
  function initRovingFocus() {
    const items = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (items.length === 0) return;
    // The first row owns the single tabstop into the tree.
    items.forEach(function (el, idx) {
      el.setAttribute("tabindex", idx === 0 ? "0" : "-1");
    });
  }

  function focusItem(item) {
    if (!item) return;
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    all.forEach(function (el) {
      el.setAttribute("tabindex", "-1");
      el.setAttribute("aria-selected", "false");
    });
    item.setAttribute("tabindex", "0");
    item.setAttribute("aria-selected", "true");
    item.focus();
  }

  function moveFocus(current, delta) {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    const i = all.indexOf(current);
    if (i === -1) return;
    const next = all[Math.min(all.length - 1, Math.max(0, i + delta))];
    focusItem(next);
  }

  function focusFirst() {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (all.length) focusItem(all[0]);
  }
  function focusLast() {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (all.length) focusItem(all[all.length - 1]);
  }

  function toggleRow(item, expand) {
    const slug = item.getAttribute("data-slug");
    const isExpandable = item.getAttribute("data-expandable") === "1";
    if (!slug || !isExpandable) return;
    const desired =
      typeof expand === "boolean"
        ? expand
        : item.getAttribute("aria-expanded") !== "true";
    manualToggles[slug] = desired;
    const accordionUpdatedAt = item.getAttribute("data-accordion-updated-at") || null;
    vscode.postMessage({
      type: "toggleRow",
      slug: slug,
      expanded: desired,
      accordionUpdatedAt: accordionUpdatedAt,
    });
    render();
    // Re-focus the same row after re-render.
    const refreshed = root.querySelector('[data-slug="' + cssEscape(slug) + '"]');
    if (refreshed) focusItem(refreshed);
  }

  // ----- Interaction wiring (after each render) -----
  function wireInteraction() {
    // Click on row header → activate (default = openSpec).
    Array.from(root.querySelectorAll('.row-header')).forEach(function (header) {
      header.addEventListener("click", function (ev) {
        const item = ev.currentTarget.closest('[role="treeitem"]');
        if (!item) return;
        // Click on the chevron toggles expand/collapse; click
        // elsewhere on the header activates.
        if (ev.target && ev.target.classList && ev.target.classList.contains("chevron")) {
          toggleRow(item);
          ev.stopPropagation();
          return;
        }
        focusItem(item);
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "activateRow", slug: slug });
        }
      });
    });

    // Right-click → context menu.
    Array.from(root.querySelectorAll('[role="treeitem"]')).forEach(function (item) {
      item.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        focusItem(item);
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "showRowContextMenu", slug: slug });
        }
      });
    });

    // Buttons inside accordion / banner with data-command. Optional
    // data-command-args is a JSON-encoded array of args appended to
    // the executeCommand call (Session 5 — used by the smart CTA to
    // pass `prefillProvider` to dabbler.checkOutOrchestrator).
    Array.from(root.querySelectorAll('[data-command]')).forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const commandId = btn.getAttribute("data-command");
        if (!commandId) return;
        const argsAttr = btn.getAttribute("data-command-args");
        let args;
        if (argsAttr) {
          try {
            const parsed = JSON.parse(argsAttr);
            args = Array.isArray(parsed) ? parsed : undefined;
          } catch (_e) {
            args = undefined;
          }
        }
        vscode.postMessage({
          type: "executeCommand",
          commandId: commandId,
          args: args,
        });
      });
    });
  }

  // Root-level keydown — captures keys regardless of which row has
  // focus. Implements WAI-ARIA single-select tree pattern.
  document.addEventListener("keydown", function (ev) {
    const item = ev.target.closest && ev.target.closest('[role="treeitem"]');
    if (!item) return;
    switch (ev.key) {
      case "ArrowDown":
        ev.preventDefault();
        moveFocus(item, 1);
        return;
      case "ArrowUp":
        ev.preventDefault();
        moveFocus(item, -1);
        return;
      case "Home":
        ev.preventDefault();
        focusFirst();
        return;
      case "End":
        ev.preventDefault();
        focusLast();
        return;
      case "ArrowRight":
        ev.preventDefault();
        if (item.getAttribute("data-expandable") === "1") {
          if (item.getAttribute("aria-expanded") !== "true") {
            toggleRow(item, true);
          }
        }
        return;
      case "ArrowLeft":
        ev.preventDefault();
        if (item.getAttribute("data-expandable") === "1" && item.getAttribute("aria-expanded") === "true") {
          toggleRow(item, false);
        }
        return;
      case "Enter":
      case " ":
        ev.preventDefault();
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "activateRow", slug: slug });
        }
        return;
      case "F10":
        if (ev.shiftKey) {
          ev.preventDefault();
          const s = item.getAttribute("data-slug");
          if (s) vscode.postMessage({ type: "showRowContextMenu", slug: s });
        }
        return;
      case "ContextMenu":
        ev.preventDefault();
        const slugCm = item.getAttribute("data-slug");
        if (slugCm) vscode.postMessage({ type: "showRowContextMenu", slug: slugCm });
        return;
    }
  });

  // Minimal CSS.escape polyfill for attribute-selector use.
  function cssEscape(s) {
    if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, function (c) {
      return "\\" + c.charCodeAt(0).toString(16) + " ";
    });
  }

  // Handshake: tell host we're ready for the first snapshot.
  vscode.postMessage({ type: "ready" });
})();

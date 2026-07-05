(() => {
  "use strict";

  let BOOT = null;
  let currentHistoryPage = 0;
  let currentHistoryPageSize = 50;
  let lastPolishOriginal = "";
  let lastTranslateOriginal = "";

  function fmt(template, values) {
    return template.replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : `{${key}}`));
  }

  function $(id) {
    return document.getElementById(id);
  }

  const ICONS = {
    use: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3 3 7-7"/></svg>',
    copy: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 10V4.5A1.5 1.5 0 0 1 4.5 3H10"/></svg>',
    check: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3 3 7-7"/></svg>',
  };

  function makeIconButton(iconKey, label, extraClass) {
    const btn = document.createElement("button");
    btn.className = "icon-btn" + (extraClass ? " " + extraClass : "");
    btn.innerHTML = ICONS[iconKey];
    btn.title = label;
    btn.setAttribute("aria-label", label);
    return btn;
  }

  function setIconButtonState(btn, iconKey, label) {
    btn.innerHTML = ICONS[iconKey];
    btn.title = label;
    btn.setAttribute("aria-label", label);
  }

  function setStatus(el, text, color) {
    el.textContent = text || "";
    el.className = "status" + (color ? " " + color : "");
  }

  // ------------------------------------------------------------------ i18n

  function applyStrings() {
    const s = BOOT.strings;
    const map = {
      "tab-btn[data-tab=polish]": s.POLISH,
      "tab-btn[data-tab=translate]": s.TRANSLATE,
      "tab-btn[data-tab=history]": s.HISTORY,
      "#lbl-original-text": s.ORIGINAL_TEXT,
      "#lbl-tone": s.TONE_LABEL,
      "#lbl-translate-original": s.ORIGINAL_TEXT,
      "#lbl-translated-text": s.TRANSLATED_TEXT + ": " + BOOT.translateLanguage,
      "#lbl-page-size": s.PAGE_SIZE,
      "#th-used-at": s.USED_AT,
      "#th-tone": s.TONE,
      "#th-goal": s.GOAL,
      "#th-polished-text": s.POLISHED_TEXT,
      "#settings-title": s.SETTINGS,
      "#lbl-base-url": s.BASE_URL,
      "#lbl-model": s.MODEL,
      "#lbl-api-key": s.API_KEY,
      "#lbl-polish-language": s.POLISH_LANGUAGE,
      "#lbl-translate-language": s.TRANSLATE_LANGUAGE,
      "#lbl-interface-language": s.INTERFACE_LANGUAGE,
      "#lbl-run-at-startup": s.RUN_AT_STARTUP,
      "#lbl-goals-to-generate": s.GOALS_TO_GENERATE,
      "#lbl-more-goals-disclaimer": s.MORE_GOALS_DISCLAIMER,
      "#lbl-context": s.CONTEXT,
      "#lbl-history-entry": s.HISTORY_ENTRY,
      "#lbl-tone-meta": s.TONE + ":",
      "#lbl-goal-meta": s.GOAL + ":",
      "#lbl-used-at-meta": s.USED_AT + ":",
      "#lbl-detail-original": s.ORIGINAL_TEXT,
      "#lbl-detail-polished": s.POLISHED_TEXT,
      "#lbl-llm-error": s.LLM_ERROR,
      "#lbl-llm-error-body": s.LLM_ERROR_BODY,
      "#lbl-polished-versions": s.POLISHED_VERSIONS + ": " + BOOT.config.output_language,
    };
    for (const [selector, text] of Object.entries(map)) {
      const el = selector.startsWith("#") ? $(selector.slice(1)) : document.querySelector(`.${selector}`);
      if (el) el.textContent = text;
    }

    $("polish-trigger-btn").textContent = fmt(s.TRIGGER, { hotkey: BOOT.polishHotkey });
    $("translate-trigger-btn").textContent = s.TRANSLATE + " (" + BOOT.translateHotkey + ")";
    setIconButtonState($("translate-copy-btn"), "copy", s.COPY);
    $("history-refresh-btn").textContent = s.REFRESH;
    $("history-clear-btn").textContent = s.CLEAR;
    $("history-prev-btn").title = s.PREV;
    $("history-next-btn").title = s.NEXT;
    $("test-connection-btn").textContent = s.TEST_CONNECTION;
    $("settings-save-btn").textContent = s.SAVE;
    $("settings-cancel-btn").textContent = s.CANCEL;
    $("goal-preset-min").textContent = s.MINIMUM;
    $("goal-preset-default").textContent = s.DEFAULT;
    $("goal-preset-all").textContent = s.ALL;
    $("detail-close-btn").textContent = s.CLOSE;
    $("error-open-log-btn").textContent = s.OPEN_LOG;
    $("error-close-btn").textContent = s.CLOSE;
    $("clear-btn").title = s.CLEAR;
    $("settings-btn").title = s.SETTINGS;
    $("set-output-language").title = s.OUTPUT_LANGUAGE_TOOLTIP;
    $("set-context").title = s.CONTEXT_TOOLTIP;
    document.title = BOOT.appName;
    $("titlebar-title").textContent = BOOT.appName;
  }

  // ------------------------------------------------------------------ tabs

  function initTabs() {
    $("window-close-btn").addEventListener("click", () => pywebview.api.close_window());
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => selectTab(btn.dataset.tab));
    });
    $("clear-btn").addEventListener("click", () => {
      const active = document.querySelector(".tab-btn.active").dataset.tab;
      if (active === "polish") clearPolish();
      else if (active === "translate") clearTranslate();
    });
  }

  function selectTab(name) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
    $("clear-btn").disabled = name === "history";
    if (name === "history") refreshHistory();
  }

  // Alt+1..Alt+9,Alt+0 triggers "Use" on the Nth polished result card, while
  // the Polish tab is active and focus isn't in any input/textarea/select.
  function initResultShortcuts() {
    document.addEventListener("keydown", (e) => {
      if (!e.altKey) return;
      // Digit detection uses e.code (the physical key) rather than e.key, which
      // can vary with keyboard layout under Alt.
      const m = /^Digit([0-9])$/.exec(e.code);
      if (!m) return;
      if (document.querySelector(".tab-btn.active")?.dataset.tab !== "polish") return;
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      const n = m[1] === "0" ? 10 : Number(m[1]);
      const useBtn = document.querySelectorAll("#polish-results .result-card")[n - 1]?.querySelector(".use-btn");
      if (useBtn) {
        e.preventDefault();
        useBtn.click();
      }
    });
  }

  // ------------------------------------------------------------------ polish

  function initPolish() {
    const toneSelect = $("tone-select");
    BOOT.tones.forEach((tone) => {
      const opt = document.createElement("option");
      opt.value = tone.value;
      opt.textContent = tone.label;
      if (tone.value === BOOT.selectedTone) opt.selected = true;
      toneSelect.appendChild(opt);
    });
    toneSelect.addEventListener("change", () => {
      pywebview.api.set_selected_tone(toneSelect.value);
    });

    $("polish-trigger-btn").addEventListener("click", () => {
      const text = $("polish-original").value.trim();
      if (!text) {
        showAlert(BOOT.strings.EMPTY + "\n\n" + BOOT.strings.ENTER_OR_PASTE);
        return;
      }
      runPolish(text);
    });
  }

  function runPolish(text) {
    if (!BOOT.config.api_key) {
      showAlert(BOOT.strings.NO_API_KEY + "\n\n" + BOOT.strings.CONFIGURE_API_KEY);
      return;
    }
    lastPolishOriginal = text;
    $("polish-results").innerHTML = "";
    window._polishReceived = 0;
    setStatus($("polish-status"), BOOT.strings.POLISHING, "blue");
    $("polish-trigger-btn").disabled = true;
    pywebview.api.polish(text, $("tone-select").value);
  }

  window.onHotkeyCapture = (kind, text) => {
    if (kind === "polish") {
      selectTab("polish");
      $("polish-original").value = text;
      runPolish(text);
    } else if (kind === "translate") {
      selectTab("translate");
      $("translate-original").value = text;
      runTranslate(text);
    }
  };

  window.onPolishResult = (originalText, result) => {
    if (originalText !== lastPolishOriginal) return;
    window._polishReceived = (window._polishReceived || 0) + 1;
    setStatus(
      $("polish-status"),
      fmt(BOOT.strings.POLISHING_PROGRESS, {
        received: window._polishReceived,
        total: BOOT.selectedGoals.length,
      }),
      "blue"
    );
    addResultCard(originalText, result);
  };

  window.onPolishDone = (originalText) => {
    if (originalText !== lastPolishOriginal) return;
    setStatus($("polish-status"), BOOT.strings.POLISHED_READY, "green");
    $("polish-trigger-btn").disabled = false;
  };

  window.onPolishError = (originalText, error) => {
    if (originalText !== lastPolishOriginal) return;
    setStatus($("polish-status"), BOOT.strings.ERROR, "red");
    $("polish-trigger-btn").disabled = false;
    showError(error);
  };

  function addResultCard(original, result) {
    const goalMeta = BOOT.goals.find((g) => g.value === result.goal);
    const myIndex = BOOT_GOAL_ORDER.indexOf(result.goal);
    const card = document.createElement("div");
    card.className = "result-card";
    card.dataset.goal = result.goal;

    const header = document.createElement("div");
    header.className = "result-header";
    const badge = document.createElement("span");
    badge.className = "goal-badge";
    badge.textContent = goalMeta ? goalMeta.label : result.goal;
    header.appendChild(badge);

    const shortcutHint = document.createElement("span");
    shortcutHint.className = "shortcut-hint hidden";
    header.appendChild(shortcutHint);

    const spacer = document.createElement("span");
    spacer.className = "spacer";
    header.appendChild(spacer);

    const useBtn = makeIconButton("use", BOOT.strings.USE, "use-btn");
    const copyBtn = makeIconButton("copy", BOOT.strings.COPY);

    header.appendChild(useBtn);
    header.appendChild(copyBtn);

    const textarea = document.createElement("textarea");
    textarea.rows = 3;
    textarea.value = result.text;

    card.appendChild(header);
    card.appendChild(textarea);

    useBtn.addEventListener("click", async () => {
      const text = textarea.value;
      const res = await pywebview.api.use_polished(original, result.tone, result.goal, text);
      const label = fmt(res.pasted ? BOOT.strings.PASTED : BOOT.strings.COPIED, {
        tone: BOOT.tones.find((t) => t.value === result.tone)?.label || result.tone,
        goal: goalMeta ? goalMeta.label : result.goal,
      });
      setStatus($("polish-status"), label, res.pasted ? "green" : "gray");
      setTimeout(() => pywebview.api.hide_to_tray(), 400);
    });

    copyBtn.addEventListener("click", async () => {
      await pywebview.api.copy_text(textarea.value);
      const label = fmt(BOOT.strings.COPIED_TO_CLIPBOARD, {
        tone: BOOT.tones.find((t) => t.value === result.tone)?.label || result.tone,
        goal: goalMeta ? goalMeta.label : result.goal,
      });
      setStatus($("polish-status"), label, "green");
      setIconButtonState(copyBtn, "check", BOOT.strings.COPIED_EXCL);
      setTimeout(() => setIconButtonState(copyBtn, "copy", BOOT.strings.COPY), 1500);
    });

    // Keep result cards ordered the same way GOALS is ordered.
    const container = $("polish-results");
    const existing = Array.from(container.children);
    const before = existing.find((c) => BOOT_GOAL_ORDER.indexOf(c.dataset.goal) > myIndex);
    if (before) container.insertBefore(card, before);
    else container.appendChild(card);

    renumberShortcutHints();
  }

  // The Alt+1..Alt+9,Alt+0 shortcut (initResultShortcuts) indexes cards by
  // their actual DOM position, not by goal-list order, so the hint badges must be
  // recomputed for every card each time one is inserted (an earlier-goal card can
  // land before an already-displayed later-goal card, shifting everyone's position).
  function renumberShortcutHints() {
    const cards = document.querySelectorAll("#polish-results .result-card");
    cards.forEach((c, i) => {
      const hint = c.querySelector(".shortcut-hint");
      if (!hint) return;
      if (i < 10) {
        const n = i === 9 ? "0" : String(i + 1);
        hint.textContent = "Alt" + n;
        hint.title = "Shift+" + n;
        hint.classList.remove("hidden");
      } else {
        hint.classList.add("hidden");
      }
    });
  }

  function clearPolish() {
    $("polish-original").value = "";
    $("polish-results").innerHTML = "";
    setStatus($("polish-status"), "", "gray");
    lastPolishOriginal = "";
  }

  // ------------------------------------------------------------------ translate

  function initTranslate() {
    $("translate-trigger-btn").addEventListener("click", () => {
      const text = $("translate-original").value.trim();
      if (!text) {
        showAlert(BOOT.strings.EMPTY + "\n\n" + BOOT.strings.ENTER_TEXT_TO_TRANSLATE);
        return;
      }
      runTranslate(text);
    });
    $("translate-copy-btn").addEventListener("click", async () => {
      const text = $("translate-output").value;
      if (!text) return;
      await pywebview.api.copy_text(text);
      const btn = $("translate-copy-btn");
      setIconButtonState(btn, "check", BOOT.strings.COPIED_EXCL);
      setTimeout(() => setIconButtonState(btn, "copy", BOOT.strings.COPY), 1500);
    });
  }

  function runTranslate(text) {
    if (!BOOT.config.api_key) {
      showAlert(BOOT.strings.NO_API_KEY + "\n\n" + BOOT.strings.CONFIGURE_API_KEY);
      return;
    }
    lastTranslateOriginal = text;
    $("translate-trigger-btn").disabled = true;
    $("translate-copy-btn").disabled = true;
    $("translate-output").value = "";
    setStatus($("translate-status"), BOOT.strings.TRANSLATING, "blue");
    pywebview.api.translate(text);
  }

  window.onTranslateDone = (result) => {
    $("translate-output").value = result;
    setStatus($("translate-status"), BOOT.strings.TRANSLATION_READY, "green");
    $("translate-trigger-btn").disabled = false;
    $("translate-copy-btn").disabled = false;
  };

  window.onTranslateError = (error) => {
    setStatus($("translate-status"), BOOT.strings.ERROR, "red");
    $("translate-trigger-btn").disabled = false;
    showError(error);
  };

  function clearTranslate() {
    $("translate-original").value = "";
    $("translate-output").value = "";
    $("translate-copy-btn").disabled = true;
    setStatus($("translate-status"), "", "gray");
  }

  // ------------------------------------------------------------------ history

  async function refreshHistory() {
    const res = await pywebview.api.get_history(currentHistoryPage, currentHistoryPageSize);
    const body = $("history-body");
    body.innerHTML = "";
    res.entries.forEach((e) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtml(e.usedAt)}</td><td>${escapeHtml(e.tone)}</td><td>${escapeHtml(
        e.goal
      )}</td><td>${escapeHtml(e.polishedText.split("\n")[0].slice(0, 120))}</td>`;
      tr.addEventListener("click", () => showHistoryDetail(e));
      body.appendChild(tr);
    });
    const totalPages = Math.max(1, Math.ceil(res.totalCount / currentHistoryPageSize));
    $("history-page-label").textContent = fmt(BOOT.strings.PAGE_X_OF_Y, {
      cur: currentHistoryPage + 1,
      total: totalPages,
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function showHistoryDetail(entry) {
    $("detail-tone").textContent = entry.tone;
    $("detail-goal").textContent = entry.goal;
    $("detail-used-at").textContent = entry.usedAt;
    $("detail-original").value = entry.originalText;
    $("detail-polished").value = entry.polishedText;
    $("history-detail-modal").classList.remove("hidden");
  }

  function initHistory() {
    $("history-refresh-btn").addEventListener("click", refreshHistory);
    $("history-clear-btn").addEventListener("click", async () => {
      await pywebview.api.clear_history_action();
      currentHistoryPage = 0;
      refreshHistory();
    });
    $("history-page-size").addEventListener("change", (e) => {
      currentHistoryPageSize = parseInt(e.target.value, 10);
      currentHistoryPage = 0;
      refreshHistory();
    });
    $("history-prev-btn").addEventListener("click", () => {
      if (currentHistoryPage > 0) {
        currentHistoryPage -= 1;
        refreshHistory();
      }
    });
    $("history-next-btn").addEventListener("click", () => {
      currentHistoryPage += 1;
      refreshHistory();
    });
    $("detail-close-btn").addEventListener("click", () => {
      $("history-detail-modal").classList.add("hidden");
    });
  }

  // ------------------------------------------------------------------ settings

  function initSettings() {
    $("settings-btn").addEventListener("click", openSettings);
    $("settings-cancel-btn").addEventListener("click", closeSettings);
    $("settings-save-btn").addEventListener("click", saveSettings);
    $("test-connection-btn").addEventListener("click", testConnection);

    const dl = $("output-lang-list");
    BOOT.outputLanguages.forEach((label) => {
      const opt = document.createElement("option");
      opt.value = label;
      dl.appendChild(opt);
    });

    const translateSelect = $("set-translate-language");
    BOOT.outputLanguages.forEach((label) => {
      const opt = document.createElement("option");
      opt.value = label;
      opt.textContent = label;
      translateSelect.appendChild(opt);
    });

    const uiSelect = $("set-ui-language");
    BOOT.uiLanguages.forEach((label) => {
      const opt = document.createElement("option");
      opt.value = label;
      opt.textContent = label;
      uiSelect.appendChild(opt);
    });

    const goalBox = $("goal-checkboxes");
    BOOT.goals.forEach((g) => {
      const label = document.createElement("label");
      label.title = g.description || "";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = g.value;
      cb.checked = BOOT.selectedGoals.includes(g.value);
      label.appendChild(cb);
      label.appendChild(document.createTextNode(g.label));
      goalBox.appendChild(label);
    });

    $("goal-preset-min").addEventListener("click", () => setGoalPreset(BOOT.goalPresets.minimum));
    $("goal-preset-default").addEventListener("click", () => setGoalPreset(BOOT.goalPresets.default));
    $("goal-preset-all").addEventListener("click", () => setGoalPreset(BOOT.goalPresets.all));

    $("error-close-btn").addEventListener("click", () => $("error-modal").classList.add("hidden"));
    $("error-open-log-btn").addEventListener("click", () => pywebview.api.open_log());
  }

  function setGoalPreset(values) {
    document.querySelectorAll("#goal-checkboxes input[type=checkbox]").forEach((cb) => {
      cb.checked = values.includes(cb.value);
    });
  }

  function openSettings() {
    // outputLanguageMap is {friendly label -> model value}; reverse it to show the
    // friendly label for the currently saved value (mirrors the old Tkinter dialog).
    const outLabel = Object.keys(BOOT.outputLanguageMap).find(
      (k) => BOOT.outputLanguageMap[k] === BOOT.config.output_language
    );
    const uiLabel = Object.keys(BOOT.uiLanguageMap).find(
      (k) => BOOT.uiLanguageMap[k] === BOOT.uiLanguageCode
    );
    $("set-base-url").value = BOOT.config.base_url;
    $("set-model").value = BOOT.config.model;
    $("set-api-key").value = BOOT.config.api_key;
    $("set-output-language").value = outLabel || BOOT.config.output_language;
    $("set-translate-language").value = BOOT.translateLanguage;
    $("set-ui-language").value = uiLabel || "English";
    $("set-autorun").checked = BOOT.autorun;
    $("set-context").value = BOOT.config.context || "";
    setStatus($("settings-status"), "", "gray");
    $("settings-modal").classList.remove("hidden");
  }

  function closeSettings() {
    $("settings-modal").classList.add("hidden");
  }

  function collectSettingsPayload() {
    const goals = Array.from(document.querySelectorAll("#goal-checkboxes input:checked")).map((cb) => cb.value);
    return {
      baseUrl: $("set-base-url").value,
      model: $("set-model").value,
      apiKey: $("set-api-key").value,
      outputLanguage: $("set-output-language").value,
      translateLanguage: $("set-translate-language").value,
      uiLanguage: $("set-ui-language").value,
      autorun: $("set-autorun").checked,
      context: $("set-context").value,
      goals,
    };
  }

  async function testConnection() {
    const btn = $("test-connection-btn");
    btn.disabled = true;
    setStatus($("settings-status"), BOOT.strings.TESTING, "gray");
    const payload = collectSettingsPayload();
    const res = await pywebview.api.test_connection(payload);
    setStatus($("settings-status"), res.message, res.ok ? "green" : "red");
    btn.disabled = false;
  }

  async function saveSettings() {
    const payload = collectSettingsPayload();
    const res = await pywebview.api.save_settings(payload);
    if (!res.ok) {
      showAlert(res.error);
      return;
    }
    BOOT.config.base_url = payload.baseUrl;
    BOOT.config.model = payload.model;
    BOOT.config.api_key = payload.apiKey;
    BOOT.translateLanguage = payload.translateLanguage;
    BOOT.autorun = payload.autorun;
    BOOT.selectedGoals = payload.goals;
    applyStrings();
    closeSettings();
    if (res.restartRequired && (await showConfirm(BOOT.strings.RESTART_TO_APPLY_LANGUAGE, BOOT.strings.RESTART_NOW, BOOT.strings.RESTART_LATER))) {
      pywebview.api.restart_app();
    }
  }

  // ------------------------------------------------------------------ update banner

  window.onUpdateAvailable = (version, url) => {
    $("update-text").textContent = fmt(BOOT.strings.UPDATE_AVAILABLE, { version });
    $("update-now-btn").textContent = BOOT.strings.UPDATE_NOW;
    $("update-now-btn").onclick = () => pywebview.api.open_url(url);
    $("update-dismiss-btn").onclick = () => $("update-bar").classList.add("hidden");
    $("update-bar").classList.remove("hidden");
  };

  // ------------------------------------------------------------------ dialogs

  function showAlert(message) {
    return showGenericDialog(message, { okLabel: BOOT.strings.CLOSE, showCancel: false });
  }

  function showConfirm(message, okLabel, cancelLabel) {
    return showGenericDialog(message, {
      okLabel: okLabel || BOOT.strings.CLOSE,
      cancelLabel: cancelLabel || BOOT.strings.CANCEL,
      showCancel: true,
    });
  }

  function showGenericDialog(message, { okLabel, cancelLabel, showCancel }) {
    return new Promise((resolve) => {
      const modal = $("generic-dialog-modal");
      const okBtn = $("generic-dialog-ok-btn");
      const cancelBtn = $("generic-dialog-cancel-btn");

      $("generic-dialog-message").textContent = message;
      okBtn.textContent = okLabel;
      cancelBtn.textContent = cancelLabel || "";
      cancelBtn.classList.toggle("hidden", !showCancel);
      modal.classList.remove("hidden");

      const cleanup = () => {
        modal.classList.add("hidden");
        okBtn.removeEventListener("click", onOk);
        cancelBtn.removeEventListener("click", onCancel);
      };
      const onOk = () => {
        cleanup();
        resolve(true);
      };
      const onCancel = () => {
        cleanup();
        resolve(false);
      };
      okBtn.addEventListener("click", onOk);
      cancelBtn.addEventListener("click", onCancel);
    });
  }

  // ------------------------------------------------------------------ errors

  function showError(message) {
    $("error-body").value = message;
    $("error-modal").classList.remove("hidden");
  }

  // ------------------------------------------------------------------ boot

  let BOOT_GOAL_ORDER = [];

  async function boot() {
    BOOT = await pywebview.api.get_bootstrap();
    BOOT_GOAL_ORDER = BOOT.goals.map((g) => g.value);
    applyStrings();
    initTabs();
    initPolish();
    initTranslate();
    initHistory();
    initSettings();
    initResultShortcuts();
  }

  window.addEventListener("pywebviewready", boot);
})();

// Typed bridge to the Python `pywebview.api` object (see app/ui/webview/api.py).
// Every method here is a straight passthrough to Api's methods of the same name -
// keep this in sync with api.py when adding/removing/renaming a bridge method.

export interface GoalInfo {
  value: string;
  label: string;
  description: string;
}

export interface ToneInfo {
  value: string;
  label: string;
}

export interface AppConfig {
  base_url: string;
  model: string;
  api_key: string;
  output_language: string;
  context: string;
}

export interface Bootstrap {
  version: string;
  appName: string;
  strings: Record<string, string>;
  tones: ToneInfo[];
  goals: GoalInfo[];
  goalPresets: {
    minimum: string[];
    default: string[];
    all: string[];
  };
  outputLanguages: string[];
  outputLanguageMap: Record<string, string>;
  uiLanguages: string[];
  uiLanguageMap: Record<string, string>;
  config: AppConfig;
  selectedTone: string;
  selectedGoals: string[];
  translateLanguage: string;
  uiLanguageCode: string;
  autorun: boolean;
  theme: string | null;
  polishHotkey: string;
  translateHotkey: string;
}

export interface SettingsPayload {
  baseUrl: string;
  model: string;
  apiKey: string;
  outputLanguage: string;
  translateLanguage: string;
  uiLanguage: string;
  autorun: boolean;
  context: string;
  goals: string[];
}

export interface SaveSettingsResult {
  ok: boolean;
  error?: string;
  restartRequired?: boolean;
}

export interface TestConnectionResult {
  ok: boolean;
  message: string;
}

export interface PolishResult {
  goal: string;
  text: string;
  tone: string;
}

export interface UsePolishedResult {
  ok: boolean;
  pasted?: boolean;
}

export interface HistoryEntry {
  id: number;
  originalText: string;
  polishedText: string;
  tone: string;
  goal: string;
  usedAt: string;
}

export interface GetHistoryResult {
  entries: HistoryEntry[];
  totalCount: number;
}

export interface PywebviewApi {
  get_bootstrap(): Promise<Bootstrap>;
  save_settings(payload: SettingsPayload): Promise<SaveSettingsResult>;
  save_theme_setting(theme: string): Promise<{ ok: boolean; error?: string }>;
  test_connection(payload: SettingsPayload): Promise<TestConnectionResult>;
  restart_app(): Promise<void>;
  set_selected_tone(toneValue: string): Promise<void>;
  polish(text: string, toneValue: string): Promise<{ ok: boolean; error?: string }>;
  use_polished(
    original: string,
    toneValue: string,
    goalValue: string,
    text: string
  ): Promise<UsePolishedResult>;
  copy_text(text: string): Promise<{ ok: boolean }>;
  translate(text: string): Promise<{ ok: boolean; error?: string }>;
  get_history(page: number, pageSize: number): Promise<GetHistoryResult>;
  clear_history_action(): Promise<{ ok: boolean }>;
  open_url(url: string): Promise<void>;
  open_log(): Promise<{ ok: boolean; error?: string }>;
  close_window(): Promise<void>;
  hide_to_tray(): Promise<void>;
  quit_app(): Promise<void>;
  open_installer_and_quit(): Promise<{ ok: boolean }>;
}

declare global {
  interface Window {
    // Injected by pywebview only after the `pywebviewready` event fires - optional so
    // call sites must guard, matching the real runtime lifecycle.
    pywebview?: {
      api: PywebviewApi;
    };
    // Pushed from Python via `Api._eval()` (window.evaluate_js(...)) - see
    // app/ui/webview/api.py. Assigned by usePywebviewPush().
    onHotkeyCapture?: (kind: "polish" | "translate", text: string) => void;
    onPolishResult?: (originalText: string, result: PolishResult) => void;
    onPolishDone?: (originalText: string) => void;
    onPolishError?: (originalText: string, error: string) => void;
    onTranslateDone?: (result: string) => void;
    onTranslateError?: (error: string) => void;
    onUpdateAvailable?: (version: string) => void;
  }
}

export function api(): PywebviewApi {
  if (!window.pywebview?.api) {
    throw new Error("pywebview.api not available yet (called before pywebviewready)");
  }
  return window.pywebview.api;
}

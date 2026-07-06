import { useEffect, useRef, useState } from "react";
import { Titlebar } from "@/components/Titlebar";
import { UpdateBar, type UpdateInfo } from "@/components/UpdateBar";
import { PolishTab, type PolishTabHandle } from "@/components/PolishTab";
import { TranslateTab, type TranslateTabHandle } from "@/components/TranslateTab";
import { HistoryTab } from "@/components/HistoryTab";
import { SettingsDialog } from "@/components/SettingsDialog";
import { ErrorDialog } from "@/components/ErrorDialog";
import { useBootstrap } from "@/hooks/useBootstrap";
import { cn } from "@/lib/utils";

type TabName = "polish" | "translate" | "history";

export function App() {
  const { boot } = useBootstrap();
  const [tab, setTab] = useState<TabName>("polish");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [update, setUpdate] = useState<UpdateInfo | null>(null);

  const polishRef = useRef<PolishTabHandle>(null);
  const translateRef = useRef<TranslateTabHandle>(null);

  // Hotkey capture (pushed from Python: window.onHotkeyCapture, app.js:203-213) and the
  // update banner (window.onUpdateAvailable, app.js:578-584). Polish/Translate run handlers
  // are reached through the tab refs so the capture switches tabs and kicks off a run.
  useEffect(() => {
    window.onHotkeyCapture = (kind, text) => {
      if (kind === "polish") {
        setTab("polish");
        polishRef.current?.run(text);
      } else if (kind === "translate") {
        setTab("translate");
        translateRef.current?.run(text);
      }
    };
    window.onUpdateAvailable = (version) => setUpdate({ version });
    return () => {
      delete window.onHotkeyCapture;
      delete window.onUpdateAvailable;
    };
  }, []);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Titlebar appName={boot.appName} version={boot.version} onSettingsOpen={() => setSettingsOpen(true)} />
      <UpdateBar update={update} onDismiss={() => setUpdate(null)} />

      <nav className="flex items-center gap-0.5 border-b border-border px-1 pt-1">
        <TabButton label={boot.strings.POLISH} active={tab === "polish"} onClick={() => setTab("polish")} />
        <TabButton
          label={boot.strings.TRANSLATE}
          active={tab === "translate"}
          onClick={() => setTab("translate")}
        />
        <TabButton
          label={boot.strings.HISTORY}
          active={tab === "history"}
          onClick={() => setTab("history")}
        />
        <span className="flex-1" />
      </nav>

      <main className="flex-1 overflow-y-auto p-2">
        <PolishTab ref={polishRef} active={tab === "polish"} onError={setErrorMessage} />
        <TranslateTab ref={translateRef} active={tab === "translate"} onError={setErrorMessage} />
        <HistoryTab active={tab === "history"} />
      </main>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ErrorDialog message={errorMessage} onOpenChange={(open) => !open && setErrorMessage(null)} />
    </div>
  );
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "border-b-2 border-transparent px-2.5 py-1.5 text-sm text-muted-foreground",
        active && "border-primary font-semibold text-primary"
      )}
    >
      {label}
    </button>
  );
}

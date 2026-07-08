import { KeyboardIcon, MoonIcon, SettingsIcon, SunIcon, XIcon } from "lucide-react";
import { api } from "@/lib/pywebview";
import { useTheme } from "@/hooks/useTheme";

export function Titlebar({
  appName,
  version,
  onSettingsOpen,
  onHotkeysOpen,
}: {
  appName: string;
  version: string;
  onSettingsOpen: () => void;
  onHotkeysOpen: () => void;
}) {
  const { theme, toggle } = useTheme();

  return (
    <div className="pywebview-drag-region flex h-10 flex-none items-center gap-1 border-b border-border bg-card px-1">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <span className="truncate text-sm font-semibold text-foreground pl-2">{appName}</span>
        {version ? <span className="shrink-0 text-sm text-muted-foreground">v{version}</span> : null}
      </div>
      <button
        type="button"
        title="Hotkeys"
        aria-label="Hotkeys"
        onClick={onHotkeysOpen}
        className="flex h-8 w-8 items-center justify-center rounded text-foreground hover:bg-border"
      >
        <KeyboardIcon className="size-4" />
      </button>
      <button
        type="button"
        title="Settings"
        aria-label="Settings"
        onClick={onSettingsOpen}
        className="flex h-8 w-8 items-center justify-center rounded text-foreground hover:bg-border"
      >
        <SettingsIcon className="size-4" />
      </button>
      <button
        type="button"
        title="Toggle theme"
        aria-label="Toggle theme"
        onClick={toggle}
        className="flex h-8 w-8 items-center justify-center rounded text-foreground hover:bg-border"
      >
        {theme === "dark" ? <SunIcon className="size-4" /> : <MoonIcon className="size-4" />}
      </button>
      <button
        type="button"
        title="Close (Esc)"
        aria-label="Close"
        onClick={() => api().close_window()}
        className="flex h-8 w-12 items-center justify-center rounded text-base text-foreground hover:bg-destructive hover:text-white"
      >
        <XIcon className="size-4" />
      </button>
    </div>
  );
}

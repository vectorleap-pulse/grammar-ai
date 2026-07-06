import { api } from "@/lib/pywebview";
import { fmt } from "@/lib/format";
import { useBootstrap } from "@/hooks/useBootstrap";

export interface UpdateInfo {
  version: string;
}

export function UpdateBar({ update, onDismiss }: { update: UpdateInfo | null; onDismiss: () => void }) {
  const { boot } = useBootstrap();
  if (!update) return null;

  return (
    <div className="flex items-center gap-2 border-b border-border bg-primary/10 px-2 py-1 text-sm text-foreground">
      <span className="font-medium">{fmt(boot.strings.UPDATE_AVAILABLE, { version: update.version })}</span>
      <span className="flex-1" />
      <button
        type="button"
        className="rounded border border-primary/30 bg-primary px-2 py-1 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        onClick={() => void api().open_installer_and_quit()}
      >
        {boot.strings.UPDATE_NOW}
      </button>
      <button
        type="button"
        className="rounded px-1.5 py-0.5 text-sm text-foreground/80 transition-colors hover:bg-background/70 hover:text-foreground"
        onClick={onDismiss}
      >
        &times;
      </button>
    </div>
  );
}

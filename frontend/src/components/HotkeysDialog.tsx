import { Dialog, DialogClose, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useBootstrap } from "@/hooks/useBootstrap";

export function HotkeysDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { boot } = useBootstrap();

  const rows: { label: string; keys: string }[] = [
    { label: boot.strings.POLISH, keys: boot.polishHotkey },
    { label: boot.strings.TRANSLATE, keys: boot.translateHotkey },
    { label: `${boot.strings.USE} result (Polish tab)`, keys: "Alt+1 … Alt+9, Alt+0" },
    { label: "Close window", keys: "Esc" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Hotkeys</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-1.5 text-sm">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">{row.label}</span>
              <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-sm">
                {row.keys}
              </kbd>
            </div>
          ))}
        </div>
        <div className="flex justify-end">
          <DialogClose render={<Button variant="outline" />}>{boot.strings.CLOSE}</DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}

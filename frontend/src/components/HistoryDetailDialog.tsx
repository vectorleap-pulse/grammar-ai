import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { DialogClose } from "@/components/ui/dialog";
import { useBootstrap } from "@/hooks/useBootstrap";
import type { HistoryEntry } from "@/lib/pywebview";

// Mirrors app.js's showHistoryDetail() + the #history-detail-modal (app.js:417-424, index.html:158-176).
export function HistoryDetailDialog({
  entry,
  onOpenChange,
}: {
  entry: HistoryEntry | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { boot } = useBootstrap();

  return (
    <Dialog open={entry !== null} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>{boot.strings.HISTORY_ENTRY}</DialogTitle>
        </DialogHeader>

        {entry && (
          <div className="flex min-h-0 flex-col gap-2 overflow-y-auto text-sm">
            <div className="flex flex-col gap-0.5 text-muted-foreground">
              <div>
                <strong>{boot.strings.TONE}:</strong> {entry.tone}
              </div>
              <div>
                <strong>{boot.strings.GOAL}:</strong> {entry.goal}
              </div>
              <div>
                <strong>{boot.strings.USED_AT}:</strong> {entry.usedAt}
              </div>
            </div>
            <hr className="border-border" />
            <label className="text-sm font-semibold text-muted-foreground">
              {boot.strings.ORIGINAL_TEXT}
            </label>
            <Textarea readOnly rows={4} value={entry.originalText} />
            <label className="text-sm font-semibold text-muted-foreground">
              {boot.strings.POLISHED_TEXT}
            </label>
            <Textarea readOnly rows={4} value={entry.polishedText} />
          </div>
        )}

        <div className="flex justify-end">
          <DialogClose render={<Button variant="outline" />}>{boot.strings.CLOSE}</DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}

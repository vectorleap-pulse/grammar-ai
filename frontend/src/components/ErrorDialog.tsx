import { Dialog, DialogClose, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/pywebview";
import { useBootstrap } from "@/hooks/useBootstrap";

// Mirrors app.js's showError() + #error-modal (app.js:632-635, index.html:178-189).
export function ErrorDialog({
  message,
  onOpenChange,
}: {
  message: string | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { boot } = useBootstrap();

  return (
    <Dialog open={message !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{boot.strings.LLM_ERROR}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">{boot.strings.LLM_ERROR_BODY}</p>
        <Textarea readOnly rows={6} value={message ?? ""} className="text-sm" />
        <div className="flex justify-end gap-1.5">
          <Button type="button" variant="outline" onClick={() => void api().open_log()}>
            {boot.strings.OPEN_LOG}
          </Button>
          <DialogClose render={<Button variant="outline" />}>{boot.strings.CLOSE}</DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}

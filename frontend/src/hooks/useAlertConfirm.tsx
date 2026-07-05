import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useBootstrap } from "@/hooks/useBootstrap";

interface DialogState {
  message: string;
  okLabel: string;
  cancelLabel?: string;
  showCancel: boolean;
  resolve: (value: boolean) => void;
}

interface AlertConfirmContextValue {
  alert: (message: string) => Promise<boolean>;
  confirm: (message: string, okLabel?: string, cancelLabel?: string) => Promise<boolean>;
}

const AlertConfirmContext = createContext<AlertConfirmContextValue | null>(null);

// Replaces app.js's showAlert/showConfirm Promise-based singleton dialog (app.js:588-628)
// with one shared shadcn AlertDialog mounted at the app root.
export function AlertConfirmProvider({ children }: { children: ReactNode }) {
  const { boot } = useBootstrap();
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const show = useCallback(
    (message: string, opts: { okLabel: string; cancelLabel?: string; showCancel: boolean }) => {
      return new Promise<boolean>((resolve) => {
        setDialog({ message, resolve, ...opts });
      });
    },
    []
  );

  const alert = useCallback(
    (message: string) => show(message, { okLabel: boot.strings.CLOSE, showCancel: false }),
    [show, boot.strings.CLOSE]
  );

  const confirm = useCallback(
    (message: string, okLabel?: string, cancelLabel?: string) =>
      show(message, {
        okLabel: okLabel || boot.strings.CLOSE,
        cancelLabel: cancelLabel || boot.strings.CANCEL,
        showCancel: true,
      }),
    [show, boot.strings.CLOSE, boot.strings.CANCEL]
  );

  const settle = (result: boolean) => {
    setDialog((current) => {
      current?.resolve(result);
      return null;
    });
  };

  return (
    <AlertConfirmContext.Provider value={{ alert, confirm }}>
      {children}
      <AlertDialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) settle(false);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="sr-only">Notice</AlertDialogTitle>
            <AlertDialogDescription className="whitespace-pre-line text-foreground">
              {dialog?.message}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            {dialog?.showCancel && (
              <AlertDialogCancel onClick={() => settle(false)}>{dialog.cancelLabel}</AlertDialogCancel>
            )}
            <AlertDialogAction onClick={() => settle(true)}>{dialog?.okLabel}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AlertConfirmContext.Provider>
  );
}

export function useAlertConfirm(): AlertConfirmContextValue {
  const ctx = useContext(AlertConfirmContext);
  if (!ctx) throw new Error("useAlertConfirm must be used within AlertConfirmProvider");
  return ctx;
}

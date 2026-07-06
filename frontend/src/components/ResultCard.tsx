import { forwardRef, useImperativeHandle, useState } from "react";
import { CheckCheckIcon, CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type GoalInfo, type PolishResult, type ToneInfo } from "@/lib/pywebview";
import { fmt } from "@/lib/format";
import { useBootstrap } from "@/hooks/useBootstrap";

export interface ResultCardHandle {
  triggerUse: () => void;
}

interface ResultCardProps {
  original: string;
  result: PolishResult;
  goalMeta?: GoalInfo;
  toneMeta?: ToneInfo;
  shortcutHint: string | null;
  onStatus: (text: string, color: string) => void;
}

// Mirrors app.js's addResultCard() (app.js:242-307): an editable result textarea with
// Use (paste back to the originating control) and Copy actions. `text` is local, editable
// state seeded from the LLM result - the user can tweak it before Use/Copy reads it.
export const ResultCard = forwardRef<ResultCardHandle, ResultCardProps>(function ResultCard(
  { original, result, goalMeta, toneMeta, shortcutHint, onStatus },
  ref
) {
  const { boot } = useBootstrap();
  const [text, setText] = useState(result.text);
  const [justCopied, setJustCopied] = useState(false);

  const triggerUse = async () => {
    const res = await api().use_polished(original, result.tone, result.goal, text);
    const label = fmt(res.pasted ? boot.strings.PASTED : boot.strings.COPIED, {
      tone: toneMeta?.label || result.tone,
      goal: goalMeta?.label || result.goal,
    });
    onStatus(label, res.pasted ? "green" : "gray");
    setTimeout(() => api().hide_to_tray(), 400);
  };

  useImperativeHandle(ref, () => ({ triggerUse }));

  const doCopy = async () => {
    await api().copy_text(text);
    const label = fmt(boot.strings.COPIED_TO_CLIPBOARD, {
      tone: toneMeta?.label || result.tone,
      goal: goalMeta?.label || result.goal,
    });
    onStatus(label, "green");
    setJustCopied(true);
    setTimeout(() => setJustCopied(false), 1500);
  };

  return (
    <div className="rounded-md border border-border bg-card p-1.5">
      <div className="mb-1 flex items-center gap-1.5">
        <span className="text-sm font-semibold text-muted-foreground">{goalMeta?.label || result.goal}</span>
        <span className="flex-1" />
        {shortcutHint && (
          <span className="rounded border border-border px-1.5 text-sm leading-snug text-muted-foreground">
            {shortcutHint}
          </span>
        )}
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          title={boot.strings.USE}
          aria-label={boot.strings.USE}
          onClick={triggerUse}
        >
          <CheckIcon />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          title={justCopied ? boot.strings.COPIED_EXCL : boot.strings.COPY}
          aria-label={boot.strings.COPY}
          onClick={doCopy}
        >
          {justCopied ? <CheckCheckIcon /> : <CopyIcon />}
        </Button>
      </div>
      <Textarea
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="min-h-0 border-none p-0 shadow-none"
      />
    </div>
  );
});

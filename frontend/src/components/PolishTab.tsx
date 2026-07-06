import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from "react";
import { Loader2Icon, Trash2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ResultCard, type ResultCardHandle } from "@/components/ResultCard";
import { useBootstrap } from "@/hooks/useBootstrap";
import { useAlertConfirm } from "@/hooks/useAlertConfirm";
import { usePolish } from "@/hooks/usePolish";
import { cn } from "@/lib/utils";

export interface PolishTabHandle {
  run: (text: string) => void;
}

interface PolishTabProps {
  active: boolean;
  onError: (message: string) => void;
}

// Digit hint text for the Nth card, matching app.js's renumberShortcutHints() (app.js:313-327).
function shortcutHintFor(index: number): string | null {
  if (index >= 10) return null;
  return "Shift+" + (index === 9 ? "0" : String(index + 1));
}

export const PolishTab = forwardRef<PolishTabHandle, PolishTabProps>(function PolishTab(
  { active, onError },
  ref
) {
  const { boot, outputLanguageLabel } = useBootstrap();
  const { alert } = useAlertConfirm();
  const polish = usePolish(onError);
  const cardRefs = useRef<Array<ResultCardHandle | null>>([]);

  useImperativeHandle(ref, () => ({ run: polish.run }));

  const triggerFromButton = () => {
    const text = polish.original.trim();
    if (!text) {
      void alert(boot.strings.EMPTY + "\n\n" + boot.strings.ENTER_OR_PASTE);
      return;
    }
    polish.run(text);
  };

  const goalMetaByValue = useMemo(() => new Map(boot.goals.map((g) => [g.value, g])), [boot.goals]);
  const toneMetaByValue = useMemo(() => new Map(boot.tones.map((t) => [t.value, t])), [boot.tones]);

  // Shift+1..Shift+9,Shift+0 triggers "Use" on the Nth result card, while this tab is active
  // and focus isn't in an input/textarea/select - mirrors app.js:143-163.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!active || !e.shiftKey) return;
      const match = /^Digit([0-9])$/.exec(e.code);
      if (!match) return;
      const tag = (document.activeElement as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      const n = match[1] === "0" ? 10 : Number(match[1]);
      const card = cardRefs.current[n - 1];
      if (card) {
        e.preventDefault();
        card.triggerUse();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [active]);

  return (
    <div className={cn("flex flex-col gap-2", !active && "hidden")}>
      <div className="flex items-center gap-1.5">
        <label className="whitespace-nowrap text-xs text-muted-foreground">{boot.strings.TONE_LABEL}</label>
        <Select value={polish.tone} onValueChange={(v) => v !== null && polish.onToneChange(v)}>
          <SelectTrigger size="sm" className="w-30">
            {/* base-ui's Select.Value shows the raw value (tone.value, e.g. "professional")
                unless told how to render it - it doesn't look up the matching SelectItem's
                label on its own like Radix does. */}
            <SelectValue>
              {(value: string | null) => (value ? toneMetaByValue.get(value)?.label : null)}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {boot.tones.map((tone) => (
              <SelectItem key={tone.value} value={tone.value}>
                {tone.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button type="button" size="sm" variant="outline" disabled={polish.busy} onClick={triggerFromButton}>
          {polish.busy ? <Loader2Icon className="mr-2 size-3.5 animate-spin" /> : null}
          {boot.strings.POLISH} ({boot.polishHotkey})
        </Button>
        <span className="flex-1" />
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          title={boot.strings.CLEAR}
          aria-label={boot.strings.CLEAR}
          onClick={polish.clear}
        >
          <Trash2Icon />
        </Button>
      </div>

      <div>
        <label className="mb-1 block text-[11px] font-semibold text-muted-foreground">
          {boot.strings.ORIGINAL_TEXT}
        </label>
        <Textarea rows={4} value={polish.original} onChange={(e) => polish.setOriginal(e.target.value)} />
      </div>

      <div className="mt-1 flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
        <span>
          {boot.strings.POLISHED_VERSIONS}: {outputLanguageLabel()}
        </span>
        {polish.busy ? <Loader2Icon className="size-3.5 animate-spin" /> : null}
      </div>

      <div className="flex flex-col gap-1.5">
        {polish.results.map((result, index) => (
          <ResultCard
            key={result.goal}
            ref={(el) => {
              cardRefs.current[index] = el;
            }}
            original={polish.submittedOriginal}
            result={result}
            goalMeta={goalMetaByValue.get(result.goal)}
            toneMeta={toneMetaByValue.get(result.tone)}
            shortcutHint={shortcutHintFor(index)}
            onStatus={polish.setStatus}
          />
        ))}
      </div>
    </div>
  );
});

import { useCallback, useEffect, useState } from "react";
import { ChevronLeftIcon, ChevronRightIcon, RotateCcwIcon, Trash2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { HistoryDetailDialog } from "@/components/HistoryDetailDialog";
import { api, type HistoryEntry } from "@/lib/pywebview";
import { fmt } from "@/lib/format";
import { useBootstrap } from "@/hooks/useBootstrap";
import { cn } from "@/lib/utils";

const PAGE_SIZES = [10, 50, 100];

// Mirrors app.js's History-tab logic (app.js:392-451) + #tab-history (index.html:69-97).
export function HistoryTab({ active }: { active: boolean }) {
  const { boot } = useBootstrap();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [detail, setDetail] = useState<HistoryEntry | null>(null);

  const refresh = useCallback(async (targetPage: number, size: number) => {
    const res = await api().get_history(targetPage, size);
    setEntries(res.entries);
    setTotalCount(res.totalCount);
  }, []);

  // Load whenever the tab becomes active, or paging/size changes while active
  // (app.js refreshes on tab-select and after every pager/size/clear action).
  useEffect(() => {
    if (active) void refresh(page, pageSize);
  }, [active, page, pageSize, refresh]);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const onClear = async () => {
    await api().clear_history_action();
    setPage(0);
    void refresh(0, pageSize);
  };

  return (
    <div className={cn("flex flex-col gap-2", !active && "hidden")}>
      <div className="flex items-center gap-1.5">
        <Button
          type="button"
          size="sm"
          variant="outline"
          title={boot.strings.REFRESH}
          onClick={() => void refresh(page, pageSize)}
        >
          <RotateCcwIcon className="size-3.5" />
          {boot.strings.REFRESH}
        </Button>
        <Button type="button" size="sm" variant="outline" title={boot.strings.CLEAR} onClick={onClear}>
          <Trash2Icon className="size-3.5" />
          {boot.strings.CLEAR}
        </Button>
      </div>

      <div className="flex items-center gap-1.5">
        <label className="whitespace-nowrap text-xs text-muted-foreground">{boot.strings.PAGE_SIZE}</label>
        <Select
          value={String(pageSize)}
          onValueChange={(v) => {
            setPageSize(Number(v));
            setPage(0);
          }}
        >
          <SelectTrigger size="sm" className="w-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          size="icon-sm"
          variant="outline"
          title={boot.strings.PREV}
          disabled={page <= 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          <ChevronLeftIcon />
        </Button>
        <span className="text-xs text-muted-foreground">
          {fmt(boot.strings.PAGE_X_OF_Y, { cur: page + 1, total: totalPages })}
        </span>
        <Button
          type="button"
          size="icon-sm"
          variant="outline"
          title={boot.strings.NEXT}
          disabled={page + 1 >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          <ChevronRightIcon />
        </Button>
      </div>

      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr>
            <th className="border-b border-border px-1.5 py-1 text-left">{boot.strings.USED_AT}</th>
            <th className="border-b border-border px-1.5 py-1 text-left">{boot.strings.TONE}</th>
            <th className="border-b border-border px-1.5 py-1 text-left">{boot.strings.GOAL}</th>
            <th className="border-b border-border px-1.5 py-1 text-left">{boot.strings.POLISHED_TEXT}</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id} className="cursor-pointer hover:bg-muted" onClick={() => setDetail(entry)}>
              <td className="max-w-35 truncate border-b border-border px-1.5 py-1">{entry.usedAt}</td>
              <td className="max-w-35 truncate border-b border-border px-1.5 py-1">{entry.tone}</td>
              <td className="max-w-35 truncate border-b border-border px-1.5 py-1">{entry.goal}</td>
              <td className="max-w-35 truncate border-b border-border px-1.5 py-1">
                {entry.polishedText.split("\n")[0].slice(0, 120)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <HistoryDetailDialog entry={detail} onOpenChange={(open) => !open && setDetail(null)} />
    </div>
  );
}

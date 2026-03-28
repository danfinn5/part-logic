import { useState } from "react";
import { SourceStatus } from "../lib/types";

interface SourceStatusBarProps {
  sources: SourceStatus[];
}

export default function SourceStatusBar({ sources }: SourceStatusBarProps) {
  const [open, setOpen] = useState(false);

  const okCount = sources.filter((s) => s.status === "ok").length;
  const cachedCount = sources.filter((s) => s.status === "cached").length;
  const errorCount = sources.filter((s) => s.status === "error").length;
  const totalResults = sources.reduce((sum, s) => sum + s.result_count, 0);
  const avgTime =
    sources.filter((s) => s.response_time_ms != null).length > 0
      ? Math.round(
          sources
            .filter((s) => s.response_time_ms != null)
            .reduce((sum, s) => sum + (s.response_time_ms ?? 0), 0) /
            sources.filter((s) => s.response_time_ms != null).length,
        )
      : null;

  // Sort: errors first, then by response time desc
  const sorted = [...sources].sort((a, b) => {
    if (a.status === "error" && b.status !== "error") return -1;
    if (a.status !== "error" && b.status === "error") return 1;
    return (b.response_time_ms ?? 0) - (a.response_time_ms ?? 0);
  });

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="text-xs text-slate-400 dark:text-zinc-500 mt-2"
    >
      <summary className="cursor-pointer select-none hover:text-slate-600 dark:hover:text-zinc-300 transition-colors">
        {sources.length} sources queried &middot; {totalResults} results
        {okCount > 0 && (
          <span className="text-green-600 dark:text-green-400 ml-1.5">
            {okCount} ok
          </span>
        )}
        {cachedCount > 0 && (
          <span className="text-blue-600 dark:text-blue-400 ml-1.5">
            {cachedCount} cached
          </span>
        )}
        {errorCount > 0 && (
          <span className="text-red-500 dark:text-red-400 ml-1.5">
            {errorCount} failed
          </span>
        )}
        {avgTime != null && (
          <span className="text-slate-400 dark:text-zinc-500 ml-1.5">
            avg {avgTime}ms
          </span>
        )}
      </summary>
      <div className="mt-3 pb-2 space-y-1">
        {sorted.map((s) => (
          <div
            key={`${s.source}-${s.status}-${s.result_count}`}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${
              s.status === "ok"
                ? "bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300"
                : s.status === "cached"
                  ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300"
                  : "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                s.status === "ok"
                  ? "bg-green-500"
                  : s.status === "cached"
                    ? "bg-blue-500"
                    : "bg-red-500"
              }`}
            />
            <span className="font-medium min-w-[90px]">{s.source}</span>
            <span className="text-slate-500 dark:text-zinc-400">
              {s.result_count} result{s.result_count !== 1 ? "s" : ""}
            </span>
            {s.response_time_ms != null && (
              <span className="text-slate-400 dark:text-zinc-500 tabular-nums">
                {s.response_time_ms}ms
              </span>
            )}
            {s.status === "error" && s.details && s.details !== "Success" && (
              <span className="ml-auto text-red-500 dark:text-red-400 truncate max-w-[300px]">
                {s.details}
              </span>
            )}
          </div>
        ))}
      </div>
    </details>
  );
}

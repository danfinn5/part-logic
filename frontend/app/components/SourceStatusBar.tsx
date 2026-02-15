import { useState } from 'react';
import { SourceStatus } from '../lib/types';

interface SourceStatusBarProps {
  sources: SourceStatus[];
}

export default function SourceStatusBar({ sources }: SourceStatusBarProps) {
  const [open, setOpen] = useState(false);

  const okCount = sources.filter((s) => s.status === 'ok').length;
  const errorCount = sources.filter((s) => s.status === 'error').length;

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="text-xs text-slate-400 mt-2"
    >
      <summary className="cursor-pointer select-none hover:text-slate-600 transition-colors">
        {sources.length} sources queried
        {okCount > 0 && <span className="text-green-600 ml-1">{okCount} ok</span>}
        {errorCount > 0 && <span className="text-red-500 ml-1">{errorCount} errors</span>}
      </summary>
      <div className="flex flex-wrap gap-1.5 mt-3 pb-2">
        {sources.map((s) => (
          <span
            key={s.source}
            title={s.details || ''}
            className={`px-2.5 py-1 rounded-full text-xs ${
              s.status === 'ok'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : s.status === 'cached'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {s.source} &middot; {s.result_count}
          </span>
        ))}
      </div>
    </details>
  );
}

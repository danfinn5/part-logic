import { useState } from 'react';
import { SourceStatus } from '../lib/types';

interface SourceStatusBarProps {
  sources: SourceStatus[];
}

export default function SourceStatusBar({ sources }: SourceStatusBarProps) {
  const [open, setOpen] = useState(false);

  return (
    <details open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} className="mt-4 text-xs text-gray-500">
      <summary className="cursor-pointer select-none">
        Sources queried ({sources.length})
      </summary>
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        {sources.map((s) => (
          <span
            key={s.source}
            title={s.details || ''}
            className={`px-2.5 py-1 rounded-full text-xs ${
              s.status === 'ok'
                ? 'bg-green-100 text-green-800'
                : s.status === 'cached'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {s.source}
            {s.status === 'cached' ? ' (cached)' : s.status === 'error' ? ' (error)' : ''}
            {' '}&middot; {s.result_count}
          </span>
        ))}
      </div>
    </details>
  );
}

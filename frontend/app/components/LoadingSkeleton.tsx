'use client';

export default function LoadingSkeleton() {
  return (
    <div className="pb-12 space-y-8 animate-pulse">
      {/* AI Summary skeleton */}
      <div className="card border-blue-100 bg-gradient-to-br from-slate-50 to-blue-50/30 p-5">
        <div className="flex gap-2 mb-3">
          <div className="h-4 bg-slate-200 rounded w-32" />
          <div className="h-4 bg-slate-200 rounded w-24" />
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-slate-200 rounded w-full" />
          <div className="h-3 bg-slate-200 rounded w-3/4" />
        </div>
      </div>

      {/* Recommendations skeleton */}
      <div>
        <div className="h-5 bg-slate-200 rounded w-48 mb-4" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card border border-slate-200 overflow-hidden">
              <div className="px-5 py-3 bg-slate-50/50 border-b border-slate-100 flex gap-3">
                <div className="h-5 bg-slate-200 rounded w-24" />
                <div className="h-5 bg-slate-200 rounded w-16" />
                <div className="ml-auto h-5 bg-slate-200 rounded w-20" />
              </div>
              <div className="px-5 py-4 space-y-3">
                <div className="flex justify-between">
                  <div>
                    <div className="h-4 bg-slate-200 rounded w-28 mb-1" />
                    <div className="h-3 bg-slate-200 rounded w-20" />
                  </div>
                  <div className="h-3 bg-slate-200 rounded w-24" />
                </div>
                <div className="h-3 bg-slate-200 rounded w-full" />
                <div className="h-3 bg-slate-200 rounded w-2/3" />
                <div className="flex gap-2">
                  <div className="h-7 bg-slate-200 rounded-lg w-24" />
                  <div className="h-7 bg-slate-200 rounded-lg w-20" />
                  <div className="h-7 bg-slate-200 rounded-lg w-16" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Listings skeleton */}
      <div>
        <div className="h-5 bg-slate-200 rounded w-32 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="border border-slate-200 rounded-lg p-4 flex gap-3">
              <div className="w-20 h-16 bg-slate-200 rounded" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-slate-200 rounded w-3/4" />
                <div className="h-3 bg-slate-200 rounded w-1/4" />
                <div className="h-3 bg-slate-200 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

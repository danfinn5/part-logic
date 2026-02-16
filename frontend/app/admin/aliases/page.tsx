'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface VehicleAlias {
  alias_id: number;
  alias_text: string;
  alias_norm: string;
  year: number | null;
  make_raw: string | null;
  model_raw: string | null;
  trim_raw: string | null;
  vehicle_id: number | null;
  config_id: number | null;
  source_domain: string | null;
  confidence: number;
  created_at: string;
}

export default function VehicleAliasesPage() {
  const [aliases, setAliases] = useState<VehicleAlias[]>([]);
  const [loading, setLoading] = useState(true);
  const [unlinkedOnly, setUnlinkedOnly] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '100' });
    if (unlinkedOnly) params.set('unlinked_only', 'true');
    fetch(`/api/canonical/aliases?${params}`)
      .then((res) => res.json())
      .then((data) => setAliases(data.aliases || []))
      .finally(() => setLoading(false));
  }, [unlinkedOnly]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/admin" className="text-slate-500 hover:text-slate-800 text-sm">← Sources</Link>
        <h1 className="text-2xl font-bold text-slate-900">Vehicle Aliases</h1>
      </div>
      <p className="text-sm text-slate-500 mb-4">
        Raw vehicle strings from ingestion; link to canonical vehicles for fitment. Run <code className="bg-slate-100 px-1 rounded">reconcile_aliases.py</code> to auto-link.
      </p>
      <label className="flex items-center gap-2 text-sm text-slate-600 mb-4">
        <input
          type="checkbox"
          checked={unlinkedOnly}
          onChange={(e) => setUnlinkedOnly(e.target.checked)}
        />
        Unlinked only
      </label>
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-600">alias_text</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">alias_norm</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">year / make / model</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">vehicle_id</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">confidence</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {aliases.map((a) => (
                <tr key={a.alias_id} className="hover:bg-slate-50">
                  <td className="px-3 py-2 font-mono text-xs max-w-xs truncate" title={a.alias_text}>{a.alias_text}</td>
                  <td className="px-3 py-2 font-mono text-xs max-w-xs truncate">{a.alias_norm}</td>
                  <td className="px-3 py-2 text-slate-600">{a.year ?? '—'} {a.make_raw ?? ''} {a.model_raw ?? ''}</td>
                  <td className="px-3 py-2">{a.vehicle_id ?? <span className="text-amber-600">unlinked</span>}</td>
                  <td className="px-3 py-2">{a.confidence}</td>
                  <td className="px-3 py-2 text-slate-500">{a.source_domain ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!loading && aliases.length === 0 && (
        <p className="text-slate-500 mt-4">No aliases found. Import via <code className="bg-slate-100 px-1 rounded">import_aliases.py --file data/templates/aliases_template.csv</code></p>
      )}
    </div>
  );
}

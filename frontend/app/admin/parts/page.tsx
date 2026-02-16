'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface PartNumberRow {
  pn_id: number;
  part_id: number;
  namespace: string;
  value: string;
  value_norm: string;
  source_domain: string | null;
  part_type: string;
  brand: string | null;
  name: string | null;
}

export default function PartNumbersPage() {
  const [rows, setRows] = useState<PartNumberRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [namespace, setNamespace] = useState('');
  const [valueNorm, setValueNorm] = useState('');

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '100' });
    if (namespace) params.set('namespace', namespace);
    if (valueNorm) params.set('value_norm', valueNorm);
    fetch(`/api/canonical/part_numbers?${params}`)
      .then((res) => res.json())
      .then((data) => setRows(data.part_numbers || []))
      .finally(() => setLoading(false));
  }, [namespace, valueNorm]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/admin" className="text-slate-500 hover:text-slate-800 text-sm">← Sources</Link>
        <h1 className="text-2xl font-bold text-slate-900">Part Numbers</h1>
      </div>
      <p className="text-sm text-slate-500 mb-4">
        Search by namespace and/or value_norm. Supersession chain and interchange group (when implemented) will appear here.
      </p>
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Namespace (e.g. oem, manufacturer_mpn)"
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          className="input-field max-w-xs"
        />
        <input
          type="text"
          placeholder="Value / value_norm"
          value={valueNorm}
          onChange={(e) => setValueNorm(e.target.value)}
          className="input-field max-w-xs"
        />
      </div>
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-600">pn_id</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">part_id</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">namespace</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">value</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">value_norm</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">part (type / brand / name)</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.pn_id} className="hover:bg-slate-50">
                  <td className="px-3 py-2">{r.pn_id}</td>
                  <td className="px-3 py-2">{r.part_id}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.namespace}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.value}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.value_norm}</td>
                  <td className="px-3 py-2 text-slate-600">{r.part_type} {r.brand ?? ''} {r.name ?? ''}</td>
                  <td className="px-3 py-2 text-slate-500">{r.source_domain ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!loading && rows.length === 0 && (
        <p className="text-slate-500 mt-4">No part numbers found. Import parts and part_numbers via import scripts.</p>
      )}
    </div>
  );
}

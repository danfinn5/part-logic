'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface FitmentRow {
  fitment_id: number;
  part_id: number;
  vehicle_id: number | null;
  config_id: number | null;
  position: string | null;
  qualifiers_json: string | null;
  qualifiers?: Record<string, unknown> | null;
  vin_range_start: string | null;
  vin_range_end: string | null;
  build_date_start: string | null;
  build_date_end: string | null;
  confidence: number;
  source_domain: string | null;
  year: number | null;
  make: string | null;
  model: string | null;
  generation: string | null;
  part_type: string;
  brand: string | null;
  name: string | null;
}

export default function FitmentInspectorPage() {
  const [fitments, setFitments] = useState<FitmentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [year, setYear] = useState('');
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [partId, setPartId] = useState('');

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '50' });
    if (year) params.set('year', year);
    if (make) params.set('make', make);
    if (model) params.set('model', model);
    if (partId) params.set('part_id', partId);
    fetch(`/api/canonical/fitments?${params}`)
      .then((res) => res.json())
      .then((data) => setFitments(data.fitments || []))
      .finally(() => setLoading(false));
  }, [year, make, model, partId]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/admin" className="text-slate-500 hover:text-slate-800 text-sm">← Sources</Link>
        <h1 className="text-2xl font-bold text-slate-900">Fitment Inspector</h1>
      </div>
      <p className="text-sm text-slate-500 mb-4">
        Given year/make/model (or part_id), see which parts match and why (qualifiers + provenance).
      </p>
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Year"
          value={year}
          onChange={(e) => setYear(e.target.value)}
          className="input-field w-20"
        />
        <input
          type="text"
          placeholder="Make"
          value={make}
          onChange={(e) => setMake(e.target.value)}
          className="input-field max-w-[120px]"
        />
        <input
          type="text"
          placeholder="Model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="input-field max-w-[120px]"
        />
        <input
          type="text"
          placeholder="Part ID"
          value={partId}
          onChange={(e) => setPartId(e.target.value)}
          className="input-field w-24"
        />
      </div>
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Vehicle (year make model)</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">Part (brand name)</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">position</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">qualifiers</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">confidence</th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {fitments.map((f) => (
                <tr key={f.fitment_id} className="hover:bg-slate-50">
                  <td className="px-3 py-2">{f.year ?? '—'} {f.make ?? ''} {f.model ?? ''} {f.generation ?? ''}</td>
                  <td className="px-3 py-2">{f.brand ?? ''} {f.name ?? ''} (part_id={f.part_id})</td>
                  <td className="px-3 py-2 text-slate-600">{f.position ?? '—'}</td>
                  <td className="px-3 py-2 font-mono text-xs max-w-xs truncate" title={f.qualifiers_json ?? ''}>
                    {f.qualifiers ? JSON.stringify(f.qualifiers) : (f.qualifiers_json ?? '—')}
                  </td>
                  <td className="px-3 py-2">{f.confidence}</td>
                  <td className="px-3 py-2 text-slate-500">{f.source_domain ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!loading && fitments.length === 0 && (
        <p className="text-slate-500 mt-4">No fitments found. Import vehicles, parts, and fitments via import scripts.</p>
      )}
    </div>
  );
}

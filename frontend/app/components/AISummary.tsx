'use client';

import { AIAnalysis } from '../lib/types';

interface AISummaryProps {
  analysis: AIAnalysis;
}

export default function AISummary({ analysis }: AISummaryProps) {
  const vehicleStr = [
    analysis.vehicle_years,
    analysis.vehicle_make,
    analysis.vehicle_model,
    analysis.vehicle_generation ? `(${analysis.vehicle_generation})` : null,
  ]
    .filter(Boolean)
    .join(' ');
  const oem = analysis.oem_part_numbers || [];
  const hasContext = vehicleStr || analysis.part_type || oem.length > 0;
  const hasNotes = analysis.notes && analysis.notes.trim().length > 0;

  if (!hasContext && !hasNotes) return null;

  return (
    <section className="mb-8">
      <div className="card border-blue-100 bg-gradient-to-br from-slate-50 to-blue-50/30 p-5">
        {/* One-line context */}
        {(vehicleStr || analysis.part_type) && (
          <div className="flex flex-wrap items-center gap-2 mb-3">
            {vehicleStr && (
              <span className="text-sm font-semibold text-slate-800">{vehicleStr}</span>
            )}
            {vehicleStr && analysis.part_type && (
              <span className="text-slate-400" aria-hidden>·</span>
            )}
            {analysis.part_type && (
              <span className="text-sm font-medium text-slate-600">{analysis.part_type}</span>
            )}
            {oem.length > 0 && (
              <span className="text-xs text-slate-500 ml-2">
                OEM: {oem.map((pn) => (
                  <code key={pn} className="px-1.5 py-0.5 bg-white/80 rounded font-mono border border-slate-200 ml-1">
                    {pn}
                  </code>
                ))}
              </span>
            )}
          </div>
        )}

        {/* Expert summary — the “little summary” from Gemini */}
        {hasNotes && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-1.5">Summary</h2>
            <p className="text-sm text-slate-700 leading-relaxed">{analysis.notes}</p>
          </div>
        )}
      </div>
    </section>
  );
}

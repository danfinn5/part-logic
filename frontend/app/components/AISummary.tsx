'use client';

import { AIAnalysis, PartIntelligence } from '../lib/types';

const TIER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  oem: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'OEM' },
  premium_aftermarket: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Premium' },
  economy: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Economy' },
  budget: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Budget' },
  unknown: { bg: 'bg-gray-50', text: 'text-gray-500', label: '' },
};

interface AISummaryProps {
  analysis: AIAnalysis;
  intelligence?: PartIntelligence | null;
  onSearchPartNumber?: (pn: string) => void;
}

function QualityDots({ score }: { score: number }) {
  const filled = Math.round(score / 2);
  return (
    <div className="flex gap-0.5 items-center" title={`Quality: ${score}/10`}>
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            i < filled ? 'bg-green-500' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  );
}

export default function AISummary({ analysis, intelligence, onSearchPartNumber }: AISummaryProps) {
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
  const hasInterchange = intelligence?.interchange && intelligence.interchange.interchange_numbers.length > 0;
  const hasBrandComparison = intelligence?.brand_comparison && intelligence.brand_comparison.length > 0;
  const hasCommunity = intelligence?.community_sources && intelligence.community_sources.length > 0;

  if (!hasContext && !hasNotes && !hasInterchange && !hasBrandComparison && !hasCommunity) return null;

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

        {/* Expert summary */}
        {hasNotes && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-1.5">Summary</h2>
            <p className="text-sm text-slate-700 leading-relaxed">{analysis.notes}</p>
          </div>
        )}

        {/* Interchange Part Numbers */}
        {hasInterchange && intelligence?.interchange && (
          <div className={hasNotes || hasContext ? 'mt-4 pt-4 border-t border-slate-200/60' : ''}>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Interchange Part Numbers</h3>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <code className="px-2.5 py-1 bg-blue-100 text-blue-800 rounded-md font-mono text-sm font-semibold border border-blue-200">
                {intelligence.interchange.primary_part_number}
              </code>
              <span className="text-xs text-slate-400">primary</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {intelligence.interchange.interchange_numbers.map((pn) => (
                <button
                  key={pn}
                  onClick={() => onSearchPartNumber?.(pn)}
                  className="px-2 py-1 bg-white border border-slate-200 rounded-md font-mono text-xs text-slate-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors cursor-pointer"
                  title={`Search for ${pn}`}
                >
                  {pn}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded border border-green-200">
                {Math.round(intelligence.interchange.confidence * 100)}% confidence
              </span>
              {intelligence.interchange.sources_consulted.map((src) => (
                <span key={src} className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">
                  {src}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Brand Breakdown */}
        {hasBrandComparison && intelligence?.brand_comparison && (
          <div className={hasNotes || hasContext || hasInterchange ? 'mt-4 pt-4 border-t border-slate-200/60' : ''}>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Brand Breakdown</h3>
            <div className="space-y-1.5">
              {[...intelligence.brand_comparison]
                .sort((a, b) => b.quality_score - a.quality_score)
                .map((brand) => {
                  const tier = TIER_STYLES[brand.tier] || TIER_STYLES.unknown;
                  return (
                    <div
                      key={brand.brand}
                      className="flex items-center gap-3 px-3 py-2 bg-white rounded-md border border-slate-100 text-sm"
                    >
                      <span className="font-medium text-slate-800 w-28 sm:w-36 truncate flex-shrink-0">
                        {brand.brand}
                      </span>
                      {tier.label && (
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${tier.bg} ${tier.text}`}>
                          {tier.label}
                        </span>
                      )}
                      {brand.quality_score > 0 && <QualityDots score={brand.quality_score} />}
                      {brand.avg_price != null && (
                        <span className="text-xs text-slate-500 flex-shrink-0">
                          ~${brand.avg_price.toFixed(0)}
                        </span>
                      )}
                      <span className="text-xs text-slate-400 flex-shrink-0">
                        {brand.listing_count} listing{brand.listing_count !== 1 ? 's' : ''}
                      </span>
                      {brand.recommendation_note && (
                        <span className="text-xs text-slate-500 italic hidden sm:inline truncate ml-auto">
                          {brand.recommendation_note}
                        </span>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Community Discussions */}
        {hasCommunity && intelligence?.community_sources && (
          <div className="mt-4 pt-4 border-t border-slate-200/60">
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Community Discussions</h3>
            <div className="space-y-1.5">
              {intelligence.community_sources.slice(0, 5).map((thread, i) => (
                <a
                  key={i}
                  href={thread.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 bg-white rounded-md border border-slate-100 hover:border-orange-200 hover:bg-orange-50/30 transition-colors no-underline group"
                >
                  <span className="text-xs text-slate-700 group-hover:text-orange-800 flex-1 min-w-0 truncate">
                    {thread.title}
                  </span>
                  <span className="px-1.5 py-0.5 bg-orange-50 text-orange-600 rounded text-[10px] font-medium flex-shrink-0">
                    r/{thread.source === 'reddit' ? thread.url.split('/r/')[1]?.split('/')[0] || 'reddit' : thread.source}
                  </span>
                  {thread.score > 0 && (
                    <span className="text-[10px] text-slate-400 flex-shrink-0">
                      {thread.score} pts
                    </span>
                  )}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

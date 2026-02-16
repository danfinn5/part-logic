'use client';

import { AIAnalysis, AIRecommendation } from '../lib/types';

interface AIRecommendationsProps {
  analysis: AIAnalysis;
}

const GRADE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  best_overall: { label: 'Best Overall', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  also_great: { label: 'Also Great', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  budget_pick: { label: 'Budget Pick', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  performance: { label: 'Performance', color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
  value_pick: { label: 'Best Value', color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
};

const TIER_BADGE: Record<string, { label: string; color: string }> = {
  oem: { label: 'OEM', color: 'bg-purple-100 text-purple-800' },
  premium_aftermarket: { label: 'Premium', color: 'bg-blue-100 text-blue-800' },
  economy: { label: 'Economy', color: 'bg-amber-100 text-amber-800' },
  budget: { label: 'Budget', color: 'bg-slate-100 text-slate-600' },
};

function QualityBar({ score }: { score: number }) {
  const pct = (score / 10) * 100;
  const color = score >= 9 ? 'bg-green-500' : score >= 7 ? 'bg-blue-500' : score >= 5 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-500">{score}/10</span>
    </div>
  );
}

function RecommendationCard({ rec }: { rec: AIRecommendation }) {
  const grade = GRADE_CONFIG[rec.grade] || GRADE_CONFIG.also_great;
  const tier = TIER_BADGE[rec.quality_tier] || TIER_BADGE.economy;

  return (
    <div className={`card border ${rec.rank === 1 ? 'border-green-300 shadow-md ring-1 ring-green-200' : 'border-slate-200'} overflow-hidden`}>
      {/* Header */}
      <div className={`px-5 py-3 flex items-center gap-3 ${rec.rank === 1 ? 'bg-green-50/60' : 'bg-slate-50/50'} border-b border-slate-100`}>
        <span className={`badge ${grade.bg} border ${grade.color} font-semibold`}>
          {grade.label}
        </span>
        <span className={`badge ${tier.color}`}>
          {tier.label}
        </span>
        <span className="ml-auto text-sm font-bold text-slate-900">
          ${rec.estimated_price_low.toFixed(0)}&ndash;${rec.estimated_price_high.toFixed(0)}
        </span>
      </div>

      {/* Body */}
      <div className="px-5 py-4">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900">{rec.brand}</h3>
            <p className="text-sm text-slate-500 font-mono">{rec.part_number}</p>
          </div>
          <QualityBar score={rec.quality_score} />
        </div>

        <p className="text-sm text-slate-600 leading-relaxed mb-4">{rec.why}</p>

        {/* Buy links */}
        <div className="flex flex-wrap gap-2">
          {rec.buy_links.map((link, i) => (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 hover:border-blue-300 transition-all no-underline"
            >
              <img
                src={`https://www.google.com/s2/favicons?domain=${_storeDomain(link.store)}&sz=16`}
                alt=""
                width={12}
                height={12}
                className="rounded-sm"
              />
              {link.store}
              <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

const STORE_DOMAINS: Record<string, string> = {
  'FCP Euro': 'fcpeuro.com',
  'ECS Tuning': 'ecstuning.com',
  'RockAuto': 'rockauto.com',
  'Amazon': 'amazon.com',
  'eBay': 'ebay.com',
  'AutoZone': 'autozone.com',
  "O'Reilly": 'oreillyauto.com',
  'Advance Auto': 'advanceautoparts.com',
  'NAPA': 'napaonline.com',
  'Parts Geek': 'partsgeek.com',
  'Pelican Parts': 'pelicanparts.com',
  'Turner Motorsport': 'turnermotorsport.com',
  'BimmerWorld': 'bimmerworld.com',
  'Summit Racing': 'summitracing.com',
  'JEGS': 'jegs.com',
  'CarParts.com': 'carparts.com',
  '1A Auto': '1aauto.com',
};

function _storeDomain(store: string): string {
  return STORE_DOMAINS[store] || store.toLowerCase().replace(/[^a-z0-9]/g, '') + '.com';
}

export default function AIRecommendations({ analysis }: AIRecommendationsProps) {
  const recs = analysis.recommendations || [];
  const avoid = analysis.avoid || [];
  const oem = analysis.oem_part_numbers || [];

  if (recs.length === 0 && !analysis.error) return null;

  const vehicleStr = [
    analysis.vehicle_years,
    analysis.vehicle_make,
    analysis.vehicle_model,
    analysis.vehicle_generation ? `(${analysis.vehicle_generation})` : null,
  ].filter(Boolean).join(' ');

  return (
    <section className="mb-8">
      {/* Context bar */}
      {(vehicleStr || analysis.part_type) && (
        <div className="flex flex-wrap items-center gap-3 mb-4 text-sm">
          {vehicleStr && (
            <span className="badge bg-slate-100 text-slate-700 border border-slate-200">
              {vehicleStr}
            </span>
          )}
          {analysis.part_type && (
            <span className="badge bg-slate-100 text-slate-700 border border-slate-200">
              {analysis.part_type}
            </span>
          )}
          {oem.length > 0 && (
            <span className="text-xs text-slate-500">
              OEM: {oem.map((pn) => (
                <code key={pn} className="px-1.5 py-0.5 bg-slate-100 rounded text-xs font-mono ml-1">{pn}</code>
              ))}
            </span>
          )}
        </div>
      )}

      {/* Recommendations header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-title">
          Recommended Parts
          <span className="text-sm font-normal text-slate-400 ml-2">
            {recs.length} options ranked by quality &amp; value
          </span>
        </h2>
      </div>

      {/* Error fallback */}
      {analysis.error && recs.length === 0 && (
        <div className="card p-4 border-amber-200 bg-amber-50 text-sm text-amber-800 mb-4">
          AI analysis unavailable: {analysis.error}
        </div>
      )}

      {/* Recommendation cards */}
      <div className="space-y-4">
        {recs.map((rec) => (
          <RecommendationCard key={`${rec.brand}-${rec.part_number}`} rec={rec} />
        ))}
      </div>

      {/* Avoid section */}
      {avoid.length > 0 && (
        <div className="mt-4 card border-red-200 bg-red-50/50 p-4">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Brands to Avoid</h3>
          <div className="space-y-1.5">
            {avoid.map((item, i) => (
              <div key={i} className="text-sm">
                <span className="font-medium text-red-700">{item.brand}</span>
                <span className="text-red-600 ml-1.5">&mdash; {item.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

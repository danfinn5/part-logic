import { BrandSummary } from '../lib/types';

interface BrandComparisonProps {
  brands: BrandSummary[];
}

const TIER_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  oem: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'OEM' },
  premium_aftermarket: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Premium' },
  economy: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Economy' },
  budget: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Budget' },
  unknown: { bg: 'bg-gray-50', text: 'text-gray-500', label: 'Unknown' },
};

function QualityBar({ score }: { score: number }) {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? 'bg-green-500' : score >= 6 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] text-gray-500">{score}/10</span>
    </div>
  );
}

export default function BrandComparison({ brands }: BrandComparisonProps) {
  if (brands.length === 0) return null;

  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold mb-3 pb-2 border-b-2 border-gray-200">
        Brand Comparison
        <span className="text-sm font-normal text-gray-500 ml-2">
          ({brands.length} brands)
        </span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {brands.map((brand) => {
          const tier = TIER_COLORS[brand.tier] || TIER_COLORS.unknown;
          return (
            <div
              key={brand.brand}
              className="p-3 border border-gray-200 rounded-lg bg-white hover:border-blue-300 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-medium text-sm">{brand.brand}</div>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${tier.bg} ${tier.text}`}>
                  {tier.label}
                </span>
              </div>
              {brand.quality_score > 0 && (
                <div className="mb-1.5">
                  <QualityBar score={brand.quality_score} />
                </div>
              )}
              <div className="flex items-center gap-3 text-xs text-gray-600">
                {brand.avg_price != null && (
                  <span className="font-semibold text-gray-900">
                    ${brand.avg_price.toFixed(2)} avg
                  </span>
                )}
                {brand.listing_count > 0 && (
                  <span>{brand.listing_count} listing{brand.listing_count !== 1 ? 's' : ''}</span>
                )}
              </div>
              {brand.recommendation_note && (
                <div className="mt-2 text-[11px] text-gray-500 leading-tight">
                  {brand.recommendation_note}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

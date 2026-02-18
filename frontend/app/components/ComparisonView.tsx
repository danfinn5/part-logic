import { ListingGroup } from '../lib/types';

interface ComparisonViewProps {
  groups: ListingGroup[];
}

const TIER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  oem: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'OEM' },
  premium_aftermarket: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Premium' },
  economy: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Economy' },
  budget: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Budget' },
  unknown: { bg: 'bg-gray-50', text: 'text-gray-500', label: '' },
};

const SOURCE_ICONS: Record<string, string> = {
  ebay: 'ebay.com',
  rockauto: 'rockauto.com',
  partsouq: 'partsouq.com',
  ecstuning: 'ecstuning.com',
  fcpeuro: 'fcpeuro.com',
  amazon: 'amazon.com',
  partsgeek: 'partsgeek.com',
  row52: 'row52.com',
  carpart: 'car-part.com',
};

function QualityDots({ score }: { score: number }) {
  const filled = Math.round(score / 2); // 0-5 dots from 0-10 score
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
      <span className="text-[10px] text-gray-400 ml-1">{score}/10</span>
    </div>
  );
}

export default function ComparisonView({ groups }: ComparisonViewProps) {
  if (groups.length === 0) return null;

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-1 pb-2 border-b-2 border-gray-200">
        Price Comparison
        <span className="text-sm font-normal text-gray-500 ml-2">
          ({groups.length} product{groups.length !== 1 ? 's' : ''}, {groups.reduce((a, g) => a + g.offer_count, 0)} offers)
        </span>
      </h2>
      <p className="text-xs text-gray-400 mb-4">Same part grouped across retailers. Sorted by best value (quality vs price).</p>

      <div className="space-y-4">
        {groups.map((group, gi) => {
          const tier = TIER_STYLES[group.tier] || TIER_STYLES.unknown;
          const bestOffer = group.offers[0]; // already sorted by total_cost
          const hasMultipleOffers = group.offers.length > 1;
          const savings = hasMultipleOffers
            ? group.price_range.high - group.price_range.low
            : 0;

          return (
            <div key={`${group.brand}-${group.part_number}-${gi}`} className="border border-gray-200 rounded-lg bg-white overflow-hidden">
              {/* Group header */}
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex flex-wrap items-center gap-x-3 gap-y-1">
                <div className="font-semibold text-sm text-gray-900">
                  {group.brand}
                  {group.part_number && (
                    <span className="font-mono text-gray-500 ml-1.5">{group.part_number}</span>
                  )}
                </div>
                {tier.label && (
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${tier.bg} ${tier.text}`}>
                    {tier.label}
                  </span>
                )}
                {group.quality_score > 0 && <QualityDots score={group.quality_score} />}
                <div className="ml-auto flex items-center gap-3 text-xs text-gray-500">
                  {hasMultipleOffers && (
                    <span className="font-medium text-green-700">
                      ${group.best_price.toFixed(2)} best price
                    </span>
                  )}
                  {savings > 1 && (
                    <span className="text-green-600">
                      Save ${savings.toFixed(2)}
                    </span>
                  )}
                  <span>{group.offer_count} offer{group.offer_count !== 1 ? 's' : ''}</span>
                </div>
              </div>

              {/* Offers */}
              <div className="divide-y divide-gray-50">
                {group.offers.map((offer, oi) => {
                  const isBest = oi === 0 && hasMultipleOffers;
                  return (
                    <div
                      key={`${offer.source}-${offer.url}-${oi}`}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
                        isBest ? 'bg-green-50/50' : 'hover:bg-gray-50'
                      } transition-colors`}
                    >
                      {/* Source icon + name */}
                      <div className="flex items-center gap-2 w-20 sm:w-28 flex-shrink-0">
                        <img
                          src={`https://www.google.com/s2/favicons?domain=${SOURCE_ICONS[offer.source] || offer.source}&sz=16`}
                          alt=""
                          width={14}
                          height={14}
                          className="flex-shrink-0 opacity-80"
                        />
                        <span className="text-xs text-gray-600 capitalize truncate">{offer.source}</span>
                        {offer.fitment_status === 'confirmed_fit' && (
                          <span className="px-1 py-0.5 bg-green-100 text-green-700 rounded text-[9px] font-medium flex-shrink-0" title="Fits your vehicle">Fits</span>
                        )}
                        {offer.fitment_status === 'likely_fit' && (
                          <span className="px-1 py-0.5 bg-amber-100 text-amber-700 rounded text-[9px] font-medium flex-shrink-0" title="Likely fits your vehicle">Likely</span>
                        )}
                      </div>

                      {/* Title (truncated) */}
                      <a
                        href={offer.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 min-w-0 text-[11px] sm:text-xs text-blue-600 hover:text-blue-800 truncate no-underline"
                        title={offer.title}
                      >
                        {offer.title}
                      </a>

                      {/* Condition */}
                      {offer.condition && (
                        <span className="text-[11px] text-gray-400 w-16 text-center flex-shrink-0 hidden sm:block">
                          {offer.condition}
                        </span>
                      )}

                      {/* Price */}
                      <div className="text-right flex-shrink-0 w-auto sm:w-32">
                        <span className={`font-semibold ${isBest ? 'text-green-700' : 'text-gray-900'}`}>
                          ${offer.price.toFixed(2)}
                        </span>
                        {offer.shipping_cost != null && offer.shipping_cost > 0 && (
                          <span className="text-[11px] text-gray-400 ml-1">
                            +${offer.shipping_cost.toFixed(2)}
                          </span>
                        )}
                        {offer.shipping_cost === 0 && (
                          <span className="text-[11px] text-green-600 ml-1">free ship</span>
                        )}
                        {isBest && (
                          <span className="ml-1.5 px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium">
                            BEST
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

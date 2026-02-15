import { PartIntelligence } from '../lib/types';

interface IntelligencePanelProps {
  intelligence: PartIntelligence;
  onSearchPartNumber: (pn: string) => void;
}

export default function IntelligencePanel({ intelligence, onSearchPartNumber }: IntelligencePanelProps) {
  const hasContent = intelligence.query_type === 'part_number' && (
    intelligence.part_description ||
    intelligence.vehicle_hint ||
    intelligence.cross_references.length > 0 ||
    intelligence.interchange
  );

  if (!hasContent) return null;

  const interchange = intelligence.interchange;

  return (
    <div className="p-4 bg-green-50 border border-green-200 rounded-lg mb-5">
      {/* Part identification */}
      {(intelligence.part_description || intelligence.vehicle_hint) && (
        <div className="text-sm font-semibold text-green-800 mb-1.5">
          Part identified as: {intelligence.part_description || ''}
          {intelligence.part_description && intelligence.vehicle_hint ? ' for ' : ''}
          {intelligence.vehicle_hint || ''}
        </div>
      )}

      {/* Brands found */}
      {intelligence.brands_found.length > 0 && (
        <div className="text-xs text-green-700 mb-1">
          Brands: {intelligence.brands_found.join(', ')}
        </div>
      )}

      {/* Interchange group (Phase 5) */}
      {interchange && interchange.interchange_numbers.length > 0 && (
        <div className="mt-3 pt-3 border-t border-green-200">
          <div className="text-xs font-semibold text-green-800 mb-2">
            Interchange Parts
            {interchange.confidence > 0 && (
              <span className="ml-2 px-1.5 py-0.5 bg-green-100 rounded text-[11px] font-normal">
                {Math.round(interchange.confidence * 100)}% confidence
              </span>
            )}
          </div>

          {/* Group by brand */}
          {Object.keys(interchange.brands_by_number).length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {Object.entries(interchange.brands_by_number).map(([brand, pns]) => (
                <div key={brand} className="px-2.5 py-1.5 bg-white border border-green-200 rounded-md">
                  <div className="text-[11px] font-semibold text-gray-600 mb-0.5">{brand}</div>
                  <div className="flex flex-wrap gap-1">
                    {pns.map((pn) => (
                      <button
                        key={pn}
                        onClick={() => onSearchPartNumber(pn)}
                        className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer bg-transparent border-none p-0"
                      >
                        {pn}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-green-700">
              Cross-references:{' '}
              {interchange.interchange_numbers.map((xref, i) => (
                <span key={xref}>
                  {i > 0 && ', '}
                  <button
                    onClick={() => onSearchPartNumber(xref)}
                    className="text-blue-600 hover:text-blue-800 underline cursor-pointer bg-transparent border-none p-0 text-xs"
                  >
                    {xref}
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Sources consulted */}
          {interchange.sources_consulted.length > 0 && (
            <div className="text-[10px] text-green-600 mt-1.5">
              Sources: {interchange.sources_consulted.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Legacy cross-references (when interchange is not available) */}
      {!interchange && intelligence.cross_references.length > 0 && (
        <div className="text-xs text-green-700">
          Cross-references:{' '}
          {intelligence.cross_references.map((xref, i) => (
            <span key={xref}>
              {i > 0 && ', '}
              <button
                onClick={() => onSearchPartNumber(xref)}
                className="text-blue-600 hover:text-blue-800 underline cursor-pointer bg-transparent border-none p-0 text-xs"
              >
                {xref}
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

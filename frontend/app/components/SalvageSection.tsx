import { SalvageHit } from '../lib/types';

interface SalvageSectionProps {
  hits: SalvageHit[];
}

export default function SalvageSection({ hits }: SalvageSectionProps) {
  if (hits.length === 0) return null;

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-3 pb-2 border-b-2 border-gray-200">
        Salvage Yard Inventory
        <span className="text-sm font-normal text-gray-500 ml-2">({hits.length})</span>
      </h2>
      <div className="grid gap-3">
        {hits.map((hit, i) => (
          <div key={i} className="p-3.5 border border-gray-200 rounded-lg bg-white">
            <a
              href={hit.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-blue-600 hover:text-blue-800 no-underline"
            >
              {hit.yard_name}
            </a>
            <div className="mt-1.5 text-sm text-gray-600">
              {hit.yard_location} &middot; {hit.vehicle}
              {hit.part_description && <span> &middot; {hit.part_description}</span>}
            </div>
            {hit.last_seen && (
              <div className="text-xs text-gray-400 mt-1">Last seen: {hit.last_seen}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

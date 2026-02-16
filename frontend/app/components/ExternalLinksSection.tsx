import { ExternalLink } from '../lib/types';

interface ExternalLinksSectionProps {
  links: ExternalLink[];
}

const CATEGORY_LABELS: Record<string, string> = {
  new_parts: 'New & Aftermarket Parts',
  used_salvage: 'Used & Salvage Parts',
  repair_resources: 'Repair Resources',
};

const CATEGORY_ORDER = ['new_parts', 'used_salvage', 'repair_resources'];

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
  youtube: 'youtube.com',
  charmli: 'charm.li',
};

function groupLinksByCategory(links: ExternalLink[]): Record<string, ExternalLink[]> {
  const grouped: Record<string, ExternalLink[]> = {};
  for (const link of links) {
    const cat = link.category || 'new_parts';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(link);
  }
  return grouped;
}

export default function ExternalLinksSection({ links }: ExternalLinksSectionProps) {
  if (links.length === 0) return null;

  const grouped = groupLinksByCategory(links);

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-4 pb-2 border-b-2 border-gray-200">
        Search Other Sources
        <span className="text-sm font-normal text-gray-500 ml-2">({links.length} links)</span>
      </h2>
      {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length).map((cat) => (
        <div key={cat} className="mb-5">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">
            {CATEGORY_LABELS[cat] || cat}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {grouped[cat].map((link, i) => (
              <a
                key={i}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 px-3.5 py-2.5 border border-gray-200 rounded-md bg-white text-blue-600 no-underline text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                <img
                  src={`https://www.google.com/s2/favicons?domain=${SOURCE_ICONS[link.source] || link.source}&sz=16`}
                  alt=""
                  width={16}
                  height={16}
                  className="flex-shrink-0"
                />
                <span className="overflow-hidden text-ellipsis whitespace-nowrap">{link.label}</span>
                <span className="ml-auto text-gray-400 text-base flex-shrink-0">&rarr;</span>
              </a>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

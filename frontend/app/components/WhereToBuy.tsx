'use client';

import { useState } from 'react';
import { ExternalLink } from '../lib/types';

interface WhereToBuySectionProps {
  links: ExternalLink[];
}

/* ── Category configuration ──────────────────────────────────────── */

const CATEGORIES: {
  key: string;
  label: string;
  description: string;
  icon: string;
  apiCategories: string[];
}[] = [
  {
    key: 'retailers',
    label: 'Retailers',
    description: 'Major auto parts retailers with pricing and availability',
    icon: '🏪',
    apiCategories: ['new_parts'],
  },
  {
    key: 'oem',
    label: 'OEM & Dealer Parts',
    description: 'Factory original parts from authorized dealer storefronts',
    icon: '🏭',
    apiCategories: ['oem_parts'],
  },
  {
    key: 'marketplace',
    label: 'Marketplaces',
    description: 'eBay, Amazon, and other major marketplaces',
    icon: '🛒',
    apiCategories: ['marketplace'],
  },
  {
    key: 'used',
    label: 'Used & Salvage',
    description: 'Recycled OEM and salvage yard inventory',
    icon: '♻️',
    apiCategories: ['used_parts', 'used_salvage'],
  },
  {
    key: 'reference',
    label: 'Reference & Diagrams',
    description: 'Parts catalogs, interchange databases, and EPC diagrams',
    icon: '📖',
    apiCategories: ['reference'],
  },
  {
    key: 'industrial',
    label: 'Industrial & Specialty',
    description: 'Fasteners, bearings, electrical, and industrial supply',
    icon: '🔧',
    apiCategories: ['industrial'],
  },
  {
    key: 'repair',
    label: 'Repair Resources',
    description: 'How-to videos and repair guides',
    icon: '🎥',
    apiCategories: ['repair_resources'],
  },
];

/* ── Source display name overrides ───────────────────────────────── */

const SOURCE_DISPLAY: Record<string, string> = {
  rockauto_com: 'RockAuto',
  autozone_com: 'AutoZone',
  oreillyauto_com: "O'Reilly Auto Parts",
  advanceautoparts_com: 'Advance Auto Parts',
  napaonline_com: 'NAPA',
  carparts_com: 'CarParts.com',
  '1aauto_com': '1A Auto',
  partsgeek_com: 'Parts Geek',
  summitracing_com: 'Summit Racing',
  jegs_com: 'JEGS',
  amazon_com: 'Amazon',
  ebay_com: 'eBay',
  fcpeuro_com: 'FCP Euro',
  ecstuning_com: 'ECS Tuning',
  car_part_com: 'Car-Part.com',
  lkqonline_com: 'LKQ Online',
  row52_com: 'Row52',
  partsouq_com: 'Partsouq',
  realoem_com: 'RealOEM',
  youtube: 'YouTube',
  charmli: 'Charm.li',
};

function getDisplayName(link: ExternalLink): string {
  if (SOURCE_DISPLAY[link.source]) return SOURCE_DISPLAY[link.source];
  // Fall back to extracting domain from label or source
  const label = link.label.split(':')[0].trim();
  if (label.length < 40) return label;
  return link.source.replace(/_/g, '.');
}

function getFaviconDomain(link: ExternalLink): string {
  try {
    const url = new URL(link.url);
    return url.hostname;
  } catch {
    return link.source.replace(/_/g, '.');
  }
}

function groupByCategory(links: ExternalLink[]) {
  const groups: Record<string, ExternalLink[]> = {};
  for (const cat of CATEGORIES) {
    groups[cat.key] = [];
  }
  groups['other'] = [];

  for (const link of links) {
    const linkCat = link.category || 'new_parts';
    let placed = false;
    for (const cat of CATEGORIES) {
      if (cat.apiCategories.includes(linkCat)) {
        groups[cat.key].push(link);
        placed = true;
        break;
      }
    }
    if (!placed) {
      groups['other'].push(link);
    }
  }
  return groups;
}

/* ── Deduplicate by display name ─────────────────────────────────── */
function dedupeLinks(links: ExternalLink[]): ExternalLink[] {
  const seen = new Set<string>();
  return links.filter((link) => {
    const name = getDisplayName(link);
    if (seen.has(name)) return false;
    seen.add(name);
    return true;
  });
}

/* ── Component ───────────────────────────────────────────────────── */

export default function WhereToBySection({ links }: WhereToBuySectionProps) {
  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  if (links.length === 0) return null;

  const grouped = groupByCategory(links);

  // Count non-empty categories
  const activeCats = CATEGORIES.filter((cat) => grouped[cat.key]?.length > 0);

  return (
    <section>
      <h2 className="section-title mb-1">
        Where to Buy
      </h2>
      <p className="text-sm text-slate-400 mb-5">
        Search {links.length} sources directly — click any retailer to search their site.
      </p>

      <div className="space-y-3">
        {activeCats.map((cat) => {
          const catLinks = dedupeLinks(grouped[cat.key]);
          if (catLinks.length === 0) return null;

          const isExpanded = expandedCat === cat.key;
          const showAll = isExpanded || catLinks.length <= 6;
          const visibleLinks = showAll ? catLinks : catLinks.slice(0, 6);

          return (
            <div key={cat.key} className="card overflow-hidden">
              {/* Category header */}
              <div className="px-4 py-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="text-base">{cat.icon}</span>
                  <div>
                    <span className="text-sm font-semibold text-slate-800">{cat.label}</span>
                    <span className="text-xs text-slate-400 ml-2">{catLinks.length} source{catLinks.length !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              </div>

              {/* Retailer cards */}
              <div className="p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {visibleLinks.map((link, i) => (
                  <a
                    key={`${link.source}-${i}`}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg border border-transparent hover:border-slate-200 hover:bg-slate-50 transition-all duration-150 no-underline group"
                  >
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${getFaviconDomain(link)}&sz=32`}
                      alt=""
                      width={20}
                      height={20}
                      className="flex-shrink-0 rounded"
                    />
                    <span className="text-sm font-medium text-slate-700 group-hover:text-blue-600 truncate transition-colors">
                      {getDisplayName(link)}
                    </span>
                    <svg className="w-4 h-4 text-slate-300 group-hover:text-blue-500 ml-auto flex-shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ))}
              </div>

              {/* Show more / less */}
              {catLinks.length > 6 && (
                <div className="px-4 py-2 border-t border-slate-100 text-center">
                  <button
                    onClick={() => setExpandedCat(isExpanded ? null : cat.key)}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium bg-transparent border-none cursor-pointer"
                  >
                    {isExpanded ? 'Show fewer' : `Show all ${catLinks.length} sources`}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

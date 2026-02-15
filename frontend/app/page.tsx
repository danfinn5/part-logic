'use client';

import { useState } from 'react';

interface MarketListing {
  source: string;
  title: string;
  price: number;
  currency: string;
  condition?: string;
  url: string;
  part_numbers: string[];
  vendor?: string;
  image_url?: string;
  brand?: string;
  shipping_cost?: number | null;
  listing_type?: string | null;
}

interface SalvageHit {
  source: string;
  yard_name: string;
  yard_location: string;
  vehicle: string;
  url: string;
  last_seen?: string;
  part_description?: string;
}

interface ExternalLink {
  label: string;
  url: string;
  source: string;
  category?: string;
}

interface SourceStatus {
  source: string;
  status: 'ok' | 'error' | 'cached';
  details?: string;
  result_count: number;
}

interface PartIntelligence {
  query_type: string;
  vehicle_hint?: string | null;
  part_description?: string | null;
  cross_references: string[];
  brands_found: string[];
}

interface SearchResponse {
  query: string;
  extracted_part_numbers: string[];
  results: {
    market_listings: MarketListing[];
    salvage_hits: SalvageHit[];
    external_links: ExternalLink[];
  };
  sources_queried: SourceStatus[];
  warnings: string[];
  cached: boolean;
  intelligence?: PartIntelligence | null;
}

type SortOption = 'relevance' | 'price_asc' | 'price_desc';

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

export default function Home() {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortOption>('relevance');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [showSources, setShowSources] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        sort,
      });
      const response = await fetch(`/api/search?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result: SearchResponse = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const groupedLinks = data ? groupLinksByCategory(data.results.external_links) : {};

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      {/* Header */}
      <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '24px' }}>
        PartLogic
        <span style={{ fontSize: '14px', fontWeight: 400, color: '#666', marginLeft: '12px' }}>
          Search 10 sources at once
        </span>
      </h1>

      {/* Search bar */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Part number, keywords, or OEM number..."
          style={{
            flex: '1 1 300px',
            padding: '10px 14px',
            fontSize: '15px',
            border: '2px solid #ddd',
            borderRadius: '6px',
            outline: 'none',
          }}
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          style={{
            padding: '10px 12px',
            fontSize: '14px',
            border: '2px solid #ddd',
            borderRadius: '6px',
            backgroundColor: '#fff',
            cursor: 'pointer',
          }}
        >
          <option value="relevance">Sort: Relevance</option>
          <option value="price_asc">Sort: Price Low→High</option>
          <option value="price_desc">Sort: Price High→Low</option>
        </select>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          style={{
            padding: '10px 28px',
            fontSize: '15px',
            fontWeight: 600,
            backgroundColor: loading ? '#94a3b8' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', marginBottom: '20px', color: '#991b1b' }}>
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Meta bar: part numbers + cache */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', marginBottom: '20px', fontSize: '14px', color: '#555' }}>
            {data.cached && (
              <span style={{ padding: '2px 10px', backgroundColor: '#dbeafe', borderRadius: '12px', fontSize: '12px' }}>
                cached
              </span>
            )}
            {data.extracted_part_numbers.length > 0 && (
              <span>
                Part numbers: {data.extracted_part_numbers.map((pn) => (
                  <code key={pn} style={{ padding: '1px 6px', backgroundColor: '#f1f5f9', borderRadius: '3px', fontSize: '13px', marginLeft: '4px' }}>{pn}</code>
                ))}
              </span>
            )}
          </div>

          {/* Part Intelligence */}
          {data.intelligence && data.intelligence.query_type === 'part_number' && (
            data.intelligence.part_description || data.intelligence.vehicle_hint || data.intelligence.cross_references.length > 0
          ) && (
            <div style={{ padding: '14px 18px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', marginBottom: '20px' }}>
              {(data.intelligence.part_description || data.intelligence.vehicle_hint) && (
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#166534', marginBottom: '6px' }}>
                  Part identified as: {data.intelligence.part_description || ''}
                  {data.intelligence.part_description && data.intelligence.vehicle_hint ? ' for ' : ''}
                  {data.intelligence.vehicle_hint || ''}
                </div>
              )}
              {data.intelligence.brands_found.length > 0 && (
                <div style={{ fontSize: '13px', color: '#15803d', marginBottom: '4px' }}>
                  Brands: {data.intelligence.brands_found.join(', ')}
                </div>
              )}
              {data.intelligence.cross_references.length > 0 && (
                <div style={{ fontSize: '13px', color: '#15803d' }}>
                  Cross-references:{' '}
                  {data.intelligence.cross_references.map((xref, i) => (
                    <span key={xref}>
                      {i > 0 && ', '}
                      <button
                        onClick={() => { setQuery(xref); }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#2563eb',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          fontSize: '13px',
                          padding: 0,
                        }}
                      >
                        {xref}
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <details style={{ marginBottom: '20px' }}>
              <summary style={{ cursor: 'pointer', fontSize: '13px', color: '#92400e' }}>
                {data.warnings.length} warning{data.warnings.length > 1 ? 's' : ''}
              </summary>
              <ul style={{ margin: '8px 0 0', paddingLeft: '20px', fontSize: '13px', color: '#92400e' }}>
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          {/* Market Listings (eBay API results) */}
          {data.results.market_listings.length > 0 && (
            <section style={{ marginBottom: '32px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px' }}>
                Market Listings
                <span style={{ fontSize: '14px', fontWeight: 400, color: '#666', marginLeft: '8px' }}>
                  ({data.results.market_listings.length})
                </span>
              </h2>
              <div style={{ display: 'grid', gap: '12px' }}>
                {data.results.market_listings.map((listing, i) => (
                  <div key={i} style={{ display: 'flex', gap: '14px', padding: '14px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#fff' }}>
                    {listing.image_url && (
                      <img
                        src={listing.image_url}
                        alt=""
                        style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '6px', flexShrink: 0 }}
                      />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <a
                        href={listing.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: '15px', fontWeight: 500, color: '#2563eb', textDecoration: 'none', lineHeight: 1.3 }}
                      >
                        {listing.title}
                      </a>
                      <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px 16px', fontSize: '14px', color: '#444' }}>
                        <span style={{ fontWeight: 700, color: '#111' }}>
                          ${listing.price.toFixed(2)}
                        </span>
                        {listing.shipping_cost != null && listing.shipping_cost > 0 && (
                          <span style={{ color: '#666' }}>+${listing.shipping_cost.toFixed(2)} ship</span>
                        )}
                        {listing.shipping_cost === 0 && (
                          <span style={{ color: '#16a34a' }}>Free shipping</span>
                        )}
                        {listing.condition && <span>{listing.condition}</span>}
                        {listing.listing_type === 'auction' && (
                          <span style={{ padding: '0 6px', backgroundColor: '#fef3c7', borderRadius: '3px', fontSize: '12px', fontWeight: 500 }}>Auction</span>
                        )}
                        {listing.listing_type === 'buy_it_now' && (
                          <span style={{ padding: '0 6px', backgroundColor: '#dcfce7', borderRadius: '3px', fontSize: '12px', fontWeight: 500 }}>Buy It Now</span>
                        )}
                      </div>
                      <div style={{ marginTop: '4px', fontSize: '12px', color: '#888', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        <span>{listing.source}</span>
                        {listing.brand && <span>{listing.brand}</span>}
                        {listing.vendor && <span>Seller: {listing.vendor}</span>}
                        {listing.part_numbers.length > 0 && (
                          <span>Part #: {listing.part_numbers.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Salvage Hits */}
          {data.results.salvage_hits.length > 0 && (
            <section style={{ marginBottom: '32px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '12px', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px' }}>
                Salvage Yard Inventory
                <span style={{ fontSize: '14px', fontWeight: 400, color: '#666', marginLeft: '8px' }}>
                  ({data.results.salvage_hits.length})
                </span>
              </h2>
              <div style={{ display: 'grid', gap: '12px' }}>
                {data.results.salvage_hits.map((hit, i) => (
                  <div key={i} style={{ padding: '14px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#fff' }}>
                    <a href={hit.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '15px', fontWeight: 500, color: '#2563eb', textDecoration: 'none' }}>
                      {hit.yard_name}
                    </a>
                    <div style={{ marginTop: '6px', fontSize: '14px', color: '#555' }}>
                      {hit.yard_location} &middot; {hit.vehicle}
                      {hit.part_description && <span> &middot; {hit.part_description}</span>}
                    </div>
                    {hit.last_seen && (
                      <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>Last seen: {hit.last_seen}</div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* External Links grouped by category */}
          {data.results.external_links.length > 0 && (
            <section style={{ marginBottom: '32px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px' }}>
                Search Other Sources
                <span style={{ fontSize: '14px', fontWeight: 400, color: '#666', marginLeft: '8px' }}>
                  ({data.results.external_links.length} links)
                </span>
              </h2>
              {CATEGORY_ORDER.filter((cat) => groupedLinks[cat]?.length).map((cat) => (
                <div key={cat} style={{ marginBottom: '20px' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>
                    {CATEGORY_LABELS[cat] || cat}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px' }}>
                    {groupedLinks[cat].map((link, i) => (
                      <a
                        key={i}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '10px 14px',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          backgroundColor: '#fff',
                          color: '#2563eb',
                          textDecoration: 'none',
                          fontSize: '14px',
                          fontWeight: 500,
                          transition: 'background-color 0.15s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f8fafc')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#fff')}
                      >
                        <img
                          src={`https://www.google.com/s2/favicons?domain=${SOURCE_ICONS[link.source] || link.source}&sz=16`}
                          alt=""
                          width={16}
                          height={16}
                          style={{ flexShrink: 0 }}
                        />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {link.label}
                        </span>
                        <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: '16px', flexShrink: 0 }}>&rarr;</span>
                      </a>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* No results at all */}
          {data.results.market_listings.length === 0 &&
           data.results.salvage_hits.length === 0 &&
           data.results.external_links.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
              No results found. Try a different search query.
            </div>
          )}

          {/* Source status (collapsible) */}
          <details open={showSources} onToggle={(e) => setShowSources((e.target as HTMLDetailsElement).open)} style={{ marginTop: '16px', fontSize: '13px', color: '#666' }}>
            <summary style={{ cursor: 'pointer', userSelect: 'none' }}>
              Sources queried ({data.sources_queried.length})
            </summary>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
              {data.sources_queried.map((s) => (
                <span
                  key={s.source}
                  title={s.details || ''}
                  style={{
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    backgroundColor:
                      s.status === 'ok' ? '#dcfce7' :
                      s.status === 'cached' ? '#dbeafe' : '#fee2e2',
                    color:
                      s.status === 'ok' ? '#166534' :
                      s.status === 'cached' ? '#1e40af' : '#991b1b',
                  }}
                >
                  {s.source} {s.status === 'cached' ? '(cached)' : s.status === 'error' ? '(error)' : ''} &middot; {s.result_count}
                </span>
              ))}
            </div>
          </details>
        </>
      )}
    </div>
  );
}

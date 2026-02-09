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
}

interface SourceStatus {
  source: string;
  status: 'ok' | 'error' | 'cached';
  details?: string;
  result_count: number;
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
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ marginBottom: '30px', color: '#333' }}>PartLogic Search</h1>

      <div style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter part number or keywords..."
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '16px',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: loading ? '#ccc' : '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: '#fee',
          border: '1px solid #fcc',
          borderRadius: '4px',
          marginBottom: '20px',
          color: '#c00',
        }}>
          Error: {error}
        </div>
      )}

      {data && (
        <div>
          {data.cached && (
            <div style={{
              padding: '8px',
              backgroundColor: '#e3f2fd',
              border: '1px solid #90caf9',
              borderRadius: '4px',
              marginBottom: '20px',
              fontSize: '14px',
            }}>
              Results served from cache
            </div>
          )}

          {data.extracted_part_numbers.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <strong>Extracted Part Numbers:</strong>{' '}
              {data.extracted_part_numbers.join(', ')}
            </div>
          )}

          {data.warnings.length > 0 && (
            <div style={{
              padding: '12px',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '4px',
              marginBottom: '20px',
            }}>
              <strong>Warnings:</strong>
              <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                {data.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginBottom: '30px' }}>
            <h3>Source Status</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
              {data.sources_queried.map((source) => (
                <div
                  key={source.source}
                  style={{
                    padding: '10px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    backgroundColor: source.status === 'ok' ? '#e8f5e9' : source.status === 'cached' ? '#e3f2fd' : '#ffebee',
                  }}
                >
                  <strong>{source.source}</strong>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    Status: {source.status} ({source.result_count} results)
                  </div>
                  {source.details && (
                    <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                      {source.details}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {data.results.market_listings.length > 0 && (
            <div style={{ marginBottom: '30px' }}>
              <h2>Market Listings ({data.results.market_listings.length})</h2>
              <div style={{ display: 'grid', gap: '15px' }}>
                {data.results.market_listings.map((listing, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '15px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      backgroundColor: '#f9f9f9',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                      <div style={{ flex: 1 }}>
                        <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>
                          <a href={listing.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3', textDecoration: 'none' }}>
                            {listing.title}
                          </a>
                        </h3>
                        <div style={{ fontSize: '14px', color: '#666' }}>
                          <span style={{ fontWeight: 'bold', color: '#333' }}>
                            {listing.currency} ${listing.price.toFixed(2)}
                          </span>
                          {listing.condition && <span> • {listing.condition}</span>}
                          {listing.vendor && <span> • {listing.vendor}</span>}
                        </div>
                        <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
                          Source: {listing.source}
                          {listing.part_numbers.length > 0 && (
                            <span> • Part #: {listing.part_numbers.join(', ')}</span>
                          )}
                        </div>
                      </div>
                      {listing.image_url && (
                        <img
                          src={listing.image_url}
                          alt={listing.title}
                          style={{ width: '100px', height: '100px', objectFit: 'cover', borderRadius: '4px', marginLeft: '15px' }}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.results.salvage_hits.length > 0 && (
            <div style={{ marginBottom: '30px' }}>
              <h2>Salvage Yard Inventory ({data.results.salvage_hits.length})</h2>
              <div style={{ display: 'grid', gap: '15px' }}>
                {data.results.salvage_hits.map((hit, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '15px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      backgroundColor: '#f9f9f9',
                    }}
                  >
                    <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>
                      <a href={hit.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3', textDecoration: 'none' }}>
                        {hit.yard_name}
                      </a>
                    </h3>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      <div><strong>Location:</strong> {hit.yard_location}</div>
                      <div><strong>Vehicle:</strong> {hit.vehicle}</div>
                      {hit.part_description && <div><strong>Part:</strong> {hit.part_description}</div>}
                      {hit.last_seen && <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>Last seen: {hit.last_seen}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.results.external_links.length > 0 && (
            <div style={{ marginBottom: '30px' }}>
              <h2>External Links ({data.results.external_links.length})</h2>
              <div style={{ display: 'grid', gap: '10px' }}>
                {data.results.external_links.map((link, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '12px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      backgroundColor: '#f0f0f0',
                    }}
                  >
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#0070f3', textDecoration: 'none', fontWeight: '500' }}
                    >
                      {link.label} →
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.results.market_listings.length === 0 &&
           data.results.salvage_hits.length === 0 &&
           data.results.external_links.length === 0 && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
              No results found. Try a different search query.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

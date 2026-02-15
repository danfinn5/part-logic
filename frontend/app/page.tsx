'use client';

import { useState } from 'react';
import { SearchResponse, SortOption, ViewMode } from './lib/types';
import { searchParts } from './lib/api';
import IntelligencePanel from './components/IntelligencePanel';
import BrandComparison from './components/BrandComparison';
import ComparisonView from './components/ComparisonView';
import ListingGrid from './components/ListingGrid';
import SalvageSection from './components/SalvageSection';
import WhereToBySection from './components/WhereToBuy';
import SourceStatusBar from './components/SourceStatusBar';

export default function Home() {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortOption>('value');
  const [viewMode, setViewMode] = useState<ViewMode>('comparison');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await searchParts(query, sort);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchPartNumber = (pn: string) => {
    setQuery(pn);
    setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await searchParts(pn, sort);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }, 0);
  };

  const intel = data?.intelligence;
  const hasListings = data && data.results.market_listings.length > 0;
  const hasSalvage = data && data.results.salvage_hits.length > 0;
  const hasLinks = data && data.results.external_links.length > 0;
  const hasResults = hasListings || hasSalvage || hasLinks;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6">
      {/* Hero search area */}
      {!data && (
        <div className="pt-20 pb-16 text-center">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight mb-3">
            Find any part. <span className="text-blue-600">Best price.</span>
          </h1>
          <p className="text-lg text-slate-500 mb-10 max-w-xl mx-auto">
            Search 80+ retailers, OEM dealers, salvage yards, and specialty shops
            at once. Compare prices and track trends over time.
          </p>
          <div className="max-w-2xl mx-auto flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Part number, description, or OEM number..."
              className="input-field flex-1 !py-3.5 !text-base !rounded-xl shadow-sm"
              autoFocus
            />
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="btn-primary !px-8 !py-3.5 !text-base !rounded-xl shadow-sm"
            >
              {loading ? (
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : 'Search'}
            </button>
          </div>
          <div className="flex items-center justify-center gap-4 mt-6 text-sm text-slate-400">
            <span>Try:</span>
            {['11427566327', 'BMW E46 oil filter', 'Porsche 997 brake pads'].map((ex) => (
              <button
                key={ex}
                onClick={() => { setQuery(ex); }}
                className="text-slate-500 hover:text-blue-600 transition-colors bg-transparent border-none cursor-pointer underline decoration-slate-300 hover:decoration-blue-400"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Compact search bar after results */}
      {data && (
        <div className="pt-6 pb-4">
          <div className="flex gap-3 items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Part number, description, or OEM number..."
              className="input-field flex-1"
            />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortOption)}
              className="input-field !w-auto"
            >
              <option value="value">Best Value</option>
              <option value="relevance">Relevance</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="btn-primary"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card border-red-200 bg-red-50 px-4 py-3 mb-6">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {data && (
        <div className="pb-12 space-y-8">
          {/* Query metadata */}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {data.cached && (
              <span className="badge bg-blue-100 text-blue-700">Cached result</span>
            )}
            {data.extracted_part_numbers.length > 0 && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <span>Detected:</span>
                {data.extracted_part_numbers.map((pn) => (
                  <code key={pn} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-mono">
                    {pn}
                  </code>
                ))}
              </div>
            )}
          </div>

          {/* Intelligence */}
          {intel && (
            <IntelligencePanel
              intelligence={intel}
              onSearchPartNumber={handleSearchPartNumber}
            />
          )}

          {/* Warnings (collapsed) */}
          {data.warnings.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-amber-600 font-medium">
                {data.warnings.length} source warning{data.warnings.length > 1 ? 's' : ''}
              </summary>
              <ul className="mt-2 ml-4 space-y-1 text-slate-500 text-xs list-disc">
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          {/* Brand comparison */}
          {intel && intel.brand_comparison.length > 0 && (
            <BrandComparison brands={intel.brand_comparison} />
          )}

          {/* Results section */}
          {hasListings && (
            <section>
              {/* View toggle */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="section-title">
                  Price Comparison
                  <span className="text-sm font-normal text-slate-400 ml-2">
                    {data.results.market_listings.length} listings from {new Set(data.results.market_listings.map(l => l.source)).size} sources
                  </span>
                </h2>
                <div className="flex rounded-lg border border-slate-200 overflow-hidden">
                  <button
                    onClick={() => setViewMode('comparison')}
                    className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                      viewMode === 'comparison'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Grouped
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-slate-200 ${
                      viewMode === 'list'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    All
                  </button>
                </div>
              </div>

              {viewMode === 'comparison' && data.grouped_listings.length > 0 && (
                <ComparisonView groups={data.grouped_listings} />
              )}
              {viewMode === 'list' && (
                <ListingGrid listings={data.results.market_listings} />
              )}
            </section>
          )}

          {/* Salvage */}
          {hasSalvage && <SalvageSection hits={data.results.salvage_hits} />}

          {/* Where to Buy — redesigned external links */}
          {hasLinks && <WhereToBySection links={data.results.external_links} />}

          {/* No results */}
          {!hasResults && (
            <div className="card py-16 text-center">
              <div className="text-4xl mb-3">&#128269;</div>
              <p className="text-slate-500">No results found for &ldquo;{data.query}&rdquo;</p>
              <p className="text-sm text-slate-400 mt-1">Try a different part number or description.</p>
            </div>
          )}

          {/* Source status */}
          <SourceStatusBar sources={data.sources_queried} />
        </div>
      )}
    </div>
  );
}

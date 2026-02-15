'use client';

import { useState } from 'react';
import { SearchResponse, SortOption, ViewMode } from './lib/types';
import { searchParts } from './lib/api';
import SearchBar from './components/SearchBar';
import IntelligencePanel from './components/IntelligencePanel';
import BrandComparison from './components/BrandComparison';
import RecommendationCard from './components/RecommendationCard';
import ComparisonView from './components/ComparisonView';
import ListingGrid from './components/ListingGrid';
import SalvageSection from './components/SalvageSection';
import ExternalLinksSection from './components/ExternalLinksSection';
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
    // Trigger search with new query after state update
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
  const hasResults = data && (
    data.results.market_listings.length > 0 ||
    data.results.salvage_hits.length > 0 ||
    data.results.external_links.length > 0
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 font-sans text-gray-900">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          PartLogic
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Search 10 sources at once. Compare prices. Find the best value.
        </p>
      </div>

      {/* Search */}
      <SearchBar
        query={query}
        sort={sort}
        loading={loading}
        onQueryChange={setQuery}
        onSortChange={setSort}
        onSearch={handleSearch}
      />

      {/* Error */}
      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-md mb-5 text-red-800 text-sm">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Meta bar */}
          <div className="flex flex-wrap items-center gap-2 mb-4 text-sm text-gray-500">
            {data.cached && (
              <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
                cached
              </span>
            )}
            {data.extracted_part_numbers.length > 0 && (
              <span>
                Part numbers:{' '}
                {data.extracted_part_numbers.map((pn) => (
                  <code key={pn} className="px-1.5 py-0.5 bg-gray-100 rounded text-xs ml-1">
                    {pn}
                  </code>
                ))}
              </span>
            )}
          </div>

          {/* Intelligence Panel */}
          {intel && (
            <IntelligencePanel
              intelligence={intel}
              onSearchPartNumber={handleSearchPartNumber}
            />
          )}

          {/* Recommendation */}
          {intel?.recommendation && (
            <RecommendationCard
              recommendation={intel.recommendation}
              communitySources={intel.community_sources || []}
            />
          )}

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <details className="mb-4">
              <summary className="cursor-pointer text-xs text-amber-700">
                {data.warnings.length} warning{data.warnings.length > 1 ? 's' : ''}
              </summary>
              <ul className="mt-2 pl-5 text-xs text-amber-700 space-y-0.5">
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          {/* Brand Comparison */}
          {intel && intel.brand_comparison.length > 0 && (
            <BrandComparison brands={intel.brand_comparison} />
          )}

          {/* View mode toggle */}
          {data.results.market_listings.length > 0 && (
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xs text-gray-500">View:</span>
              <button
                onClick={() => setViewMode('comparison')}
                className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                  viewMode === 'comparison'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                }`}
              >
                Price Comparison
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                  viewMode === 'list'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                }`}
              >
                All Listings
              </button>
            </div>
          )}

          {/* Comparison View (grouped by brand+part) */}
          {viewMode === 'comparison' && data.grouped_listings.length > 0 && (
            <ComparisonView groups={data.grouped_listings} />
          )}

          {/* Traditional flat listing view */}
          {viewMode === 'list' && (
            <ListingGrid listings={data.results.market_listings} />
          )}

          {/* Salvage Hits */}
          <SalvageSection hits={data.results.salvage_hits} />

          {/* External Links */}
          <ExternalLinksSection links={data.results.external_links} />

          {/* No results */}
          {!hasResults && (
            <div className="py-12 text-center text-gray-500">
              No results found. Try a different search query.
            </div>
          )}

          {/* Source Status */}
          <SourceStatusBar sources={data.sources_queried} />
        </>
      )}
    </div>
  );
}

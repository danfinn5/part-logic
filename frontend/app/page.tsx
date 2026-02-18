'use client';

import { useState, useEffect } from 'react';
import { SearchResponse, SortOption, ViewMode, PriceTrend } from './lib/types';
import { searchParts, getPriceTrends, decodeVin } from './lib/api';
import AISummary from './components/AISummary';
import AIRecommendations from './components/AIRecommendations';
import ComparisonView from './components/ComparisonView';
import ListingGrid from './components/ListingGrid';
import SalvageSection from './components/SalvageSection';
import ExternalLinksSection from './components/ExternalLinksSection';
import SourceStatusBar from './components/SourceStatusBar';
import LoadingSkeleton from './components/LoadingSkeleton';
import PriceChart from './components/PriceChart';
import SavedSearches from './components/SavedSearches';
import { saveSearch as saveSearchApi } from './lib/api';

function getPrimaryPartNumber(data: SearchResponse | null): string | null {
  if (!data) return null;
  const ai = data.ai_analysis;
  if (ai?.oem_part_numbers?.length) return ai.oem_part_numbers[0];
  if (ai?.recommendations?.length) return ai.recommendations[0].part_number;
  if (data.extracted_part_numbers?.length) return data.extracted_part_numbers[0];
  return null;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortOption>('value');
  const [viewMode, setViewMode] = useState<ViewMode>('comparison');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [priceTrends, setPriceTrends] = useState<PriceTrend[]>([]);
  const [priceChartLoading, setPriceChartLoading] = useState(false);
  const [vehicleMake, setVehicleMake] = useState('');
  const [vehicleModel, setVehicleModel] = useState('');
  const [vehicleYear, setVehicleYear] = useState('');
  const [vin, setVin] = useState('');
  const [vinDecoding, setVinDecoding] = useState(false);
  const [saved, setSaved] = useState(false);

  const vehicleContext =
    vehicleMake || vehicleModel || vehicleYear
      ? { make: vehicleMake.trim() || undefined, model: vehicleModel.trim() || undefined, year: vehicleYear.trim() || undefined }
      : undefined;

  const handleSaveSearch = async () => {
    if (!query.trim()) return;
    await saveSearchApi({
      query: query.trim(),
      vehicle_make: vehicleMake || undefined,
      vehicle_model: vehicleModel || undefined,
      vehicle_year: vehicleYear || undefined,
      vin: vin.length === 17 ? vin : undefined,
      sort,
    });
    setSaved(true);
  };

  const handleRunSavedSearch = (q: string, vehicle?: { make?: string; model?: string; year?: string }) => {
    setQuery(q);
    if (vehicle?.make) setVehicleMake(vehicle.make);
    if (vehicle?.model) setVehicleModel(vehicle.model);
    if (vehicle?.year) setVehicleYear(vehicle.year);
    setTimeout(async () => {
      setLoading(true);
      setError(null);
      setSaved(false);
      try {
        const result = await searchParts(q, sort, vehicle);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }, 0);
  };

  const handleVinChange = async (value: string) => {
    setVin(value);
    if (value.length === 17 && /^[A-HJ-NPR-Z0-9]{17}$/i.test(value)) {
      setVinDecoding(true);
      try {
        const result = await decodeVin(value);
        if (!result.error) {
          if (result.year) setVehicleYear(String(result.year));
          if (result.make) setVehicleMake(result.make);
          if (result.model) setVehicleModel(result.model);
        }
      } catch {
        // Silently fail — VIN decode is optional
      } finally {
        setVinDecoding(false);
      }
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setSaved(false);
    try {
      const result = await searchParts(query, sort, vehicleContext, vin.length === 17 ? vin : undefined);
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
        const result = await searchParts(pn, sort, vehicleContext, vin.length === 17 ? vin : undefined);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }, 0);
  };

  // Fetch price history for the primary part number when results change
  useEffect(() => {
    const primary = data ? getPrimaryPartNumber(data) : null;
    if (!primary) {
      setPriceTrends([]);
      return;
    }
    setPriceChartLoading(true);
    getPriceTrends(primary, 90)
      .then((trends) => setPriceTrends(trends || []))
      .catch(() => setPriceTrends([]))
      .finally(() => setPriceChartLoading(false));
  }, [data]);

  const intel = data?.intelligence;
  const ai = data?.ai_analysis;
  const hasAI = ai && (ai.recommendations?.length ?? 0) > 0;
  const hasListings = data && data.results.market_listings.length > 0;
  const hasSalvage = data && data.results.salvage_hits.length > 0;
  const hasSummary = ai && (ai.notes || ai.vehicle_make || ai.part_type || (ai.oem_part_numbers?.length ?? 0) > 0);
  const hasResults = hasAI || hasListings || hasSalvage;
  const primaryPartNumber = data ? getPrimaryPartNumber(data) : null;

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
          <details className="mt-6 text-left max-w-2xl mx-auto">
            <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-700">
              My vehicle (optional — improves recommendations)
            </summary>
            <div className="mt-3 flex flex-wrap gap-3">
              <input
                type="text"
                value={vin}
                onChange={(e) => handleVinChange(e.target.value.toUpperCase())}
                placeholder="VIN (17 chars — auto-fills below)"
                className="input-field w-full font-mono text-xs"
                maxLength={17}
              />
              {vinDecoding && (
                <span className="text-xs text-blue-500 w-full">Decoding VIN...</span>
              )}
              <input
                type="text"
                value={vehicleYear}
                onChange={(e) => setVehicleYear(e.target.value)}
                placeholder="Year"
                className="input-field !w-20"
                maxLength={4}
              />
              <input
                type="text"
                value={vehicleMake}
                onChange={(e) => setVehicleMake(e.target.value)}
                placeholder="Make (e.g. Volvo, BMW)"
                className="input-field flex-1 min-w-[120px]"
              />
              <input
                type="text"
                value={vehicleModel}
                onChange={(e) => setVehicleModel(e.target.value)}
                placeholder="Model (e.g. 940, E46)"
                className="input-field flex-1 min-w-[120px]"
              />
            </div>
          </details>
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
          <div className="flex flex-wrap gap-3 items-end">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Part number, description, or OEM number..."
              className="input-field w-full sm:w-auto sm:flex-1 min-w-[200px]"
            />
            <span className="text-slate-400 text-sm hidden sm:inline">Vehicle:</span>
            <input
              type="text"
              value={vin}
              onChange={(e) => handleVinChange(e.target.value.toUpperCase())}
              placeholder="VIN"
              className="input-field !w-20 sm:!w-44 !py-2 font-mono text-[10px]"
              maxLength={17}
              title="17-character VIN"
            />
            <input
              type="text"
              value={vehicleYear}
              onChange={(e) => setVehicleYear(e.target.value)}
              placeholder="Year"
              className="input-field !w-16 !py-2"
              maxLength={4}
              title="Vehicle year"
            />
            <input
              type="text"
              value={vehicleMake}
              onChange={(e) => setVehicleMake(e.target.value)}
              placeholder="Make"
              className="input-field !w-20 sm:!w-24 !py-2"
              title="Vehicle make"
            />
            <input
              type="text"
              value={vehicleModel}
              onChange={(e) => setVehicleModel(e.target.value)}
              placeholder="Model"
              className="input-field !w-20 sm:!w-24 !py-2"
              title="Vehicle model"
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

      {/* Loading skeleton while searching */}
      {loading && !data && <LoadingSkeleton />}

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
            <div className="ml-auto flex items-center gap-3">
              <button
                onClick={handleSaveSearch}
                disabled={saved}
                className={`text-xs flex items-center gap-1 px-2 py-1 rounded border cursor-pointer transition-colors ${
                  saved
                    ? 'bg-green-50 text-green-600 border-green-200'
                    : 'bg-white text-slate-500 border-slate-200 hover:text-blue-600 hover:border-blue-200'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill={saved ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                {saved ? 'Saved' : 'Save'}
              </button>
              <SavedSearches onRunSearch={handleRunSavedSearch} currentQuery={query} />
            </div>
          </div>

          {/* 1. Summary at top — vehicle, part, expert notes, interchange, brand breakdown */}
          {hasSummary && ai && (
            <AISummary analysis={ai} intelligence={intel} onSearchPartNumber={handleSearchPartNumber} />
          )}

          {/* 2. AI Recommendations */}
          {hasAI && ai && (
            <AIRecommendations analysis={ai} />
          )}

          {/* 3. Price history for the part(s) found */}
          {primaryPartNumber != null && (
            <section>
              <h2 className="section-title mb-4">
                Price history
                <span className="text-sm font-normal text-slate-400 ml-2 font-mono">
                  {primaryPartNumber}
                </span>
              </h2>
              {priceChartLoading && (
                <div className="card p-8 text-center text-slate-500 text-sm">
                  Loading price history…
                </div>
              )}
              {!priceChartLoading && priceTrends.length > 0 && (
                <PriceChart trends={priceTrends} />
              )}
              {!priceChartLoading && priceTrends.length === 0 && (
                <div className="card p-6 text-center text-slate-500 text-sm">
                  <p>No price history yet for this part.</p>
                  <p className="mt-1">
                    There isn’t a CamelCamelCamel-style tracker for car parts; our chart fills in as you and others run searches.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* 4. Part listings only — real product links, no generic “search here” links */}
          {hasListings && (
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="section-title">
                  Part listings
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

          {/* Salvage (when relevant, e.g. not consumables) */}
          {hasSalvage && <SalvageSection hits={data.results.salvage_hits} />}

          {/* External links to other sources */}
          {data.results.external_links.length > 0 && (
            <ExternalLinksSection links={data.results.external_links} />
          )}

          {/* Warnings (collapsed) */}
          {data.warnings.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-600 transition-colors">
                {data.warnings.length} source note{data.warnings.length > 1 ? 's' : ''}
              </summary>
              <ul className="mt-2 ml-4 space-y-1 text-slate-400 text-xs list-disc">
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          {/* No results */}
          {!hasResults && (
            <div className="card py-16 text-center">
              <div className="text-4xl mb-3">&#128269;</div>
              <p className="text-slate-500">No results found for &ldquo;{data.query}&rdquo;</p>
              <p className="text-sm text-slate-400 mt-1">Try a different part number or description.</p>
            </div>
          )}

          <SourceStatusBar sources={data.sources_queried} />
        </div>
      )}
    </div>
  );
}

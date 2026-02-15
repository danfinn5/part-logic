'use client';

import { useState, useEffect } from 'react';
import {
  SearchStats,
  PopularSearch,
  SearchHistoryEntry,
  PriceSnapshot,
  PriceTrend,
} from '../lib/types';
import {
  getSearchStats,
  getPopularSearches,
  getRecentSearches,
  getPriceHistory,
  getPriceTrends,
} from '../lib/api';
import PriceChart from '../components/PriceChart';

export default function PricesPage() {
  const [stats, setStats] = useState<SearchStats | null>(null);
  const [popular, setPopular] = useState<PopularSearch[]>([]);
  const [recent, setRecent] = useState<SearchHistoryEntry[]>([]);
  const [priceQuery, setPriceQuery] = useState('');
  const [priceData, setPriceData] = useState<PriceSnapshot[]>([]);
  const [trends, setTrends] = useState<PriceTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [priceLoading, setPriceLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      getSearchStats().then(setStats),
      getPopularSearches(10, 30).then(setPopular),
      getRecentSearches(15).then(setRecent),
    ]).finally(() => setLoading(false));
  }, []);

  const lookupPrices = async () => {
    if (!priceQuery.trim()) return;
    setPriceLoading(true);
    try {
      const [prices, trendData] = await Promise.all([
        getPriceHistory({ part_number: priceQuery.trim().toUpperCase(), limit: 100 }),
        getPriceTrends(priceQuery.trim().toUpperCase(), 90),
      ]);
      setPriceData(prices);
      setTrends(trendData);
    } finally {
      setPriceLoading(false);
    }
  };

  // Price summary stats
  const uniqueSources = new Set(priceData.map((p) => p.source));
  const allPrices = priceData.map((p) => p.price).filter((p) => p > 0);
  const minPrice = allPrices.length > 0 ? Math.min(...allPrices) : null;
  const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : null;
  const avgPrice = allPrices.length > 0 ? allPrices.reduce((a, b) => a + b, 0) / allPrices.length : null;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Price Tracker</h1>
        <p className="text-slate-500 mt-1">
          Track prices over time across all sources. Every search automatically records price data.
        </p>
      </div>

      {/* Stats overview */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Searches" value={stats.total_searches.toLocaleString()} />
          <StatCard label="Unique Queries" value={stats.unique_queries.toLocaleString()} />
          <StatCard label="Avg Listings/Search" value={stats.avg_listings_per_search.toFixed(1)} />
          <StatCard label="Avg Response" value={`${Math.round(stats.avg_response_ms)}ms`} />
        </div>
      )}

      {/* Price lookup */}
      <div className="card p-6 mb-8">
        <h2 className="section-title mb-4">Look Up Price History</h2>
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={priceQuery}
            onChange={(e) => setPriceQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && lookupPrices()}
            placeholder="Enter a part number (e.g., 11427566327)"
            className="input-field flex-1"
          />
          <button
            onClick={lookupPrices}
            disabled={priceLoading || !priceQuery.trim()}
            className="btn-primary"
          >
            {priceLoading ? 'Loading...' : 'Look Up'}
          </button>
        </div>

        {/* Price results */}
        {priceData.length > 0 && (
          <div>
            {/* Summary cards */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
              <MiniStat
                label="Lowest Seen"
                value={minPrice ? `$${minPrice.toFixed(2)}` : '—'}
                highlight
              />
              <MiniStat
                label="Highest Seen"
                value={maxPrice ? `$${maxPrice.toFixed(2)}` : '—'}
              />
              <MiniStat
                label="Average"
                value={avgPrice ? `$${avgPrice.toFixed(2)}` : '—'}
              />
              <MiniStat
                label="Sources"
                value={String(uniqueSources.size)}
              />
              <MiniStat
                label="Observations"
                value={String(priceData.length)}
              />
            </div>

            {/* Price trend chart */}
            {trends.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Price Trend (90 days)</h3>
                <PriceChart trends={trends} />
              </div>
            )}

            {/* Recent observations table */}
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Recent Observations</h3>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium text-slate-600">Source</th>
                    <th className="text-left px-3 py-2 font-medium text-slate-600">Brand</th>
                    <th className="text-left px-3 py-2 font-medium text-slate-600">Title</th>
                    <th className="text-right px-3 py-2 font-medium text-slate-600">Price</th>
                    <th className="text-left px-3 py-2 font-medium text-slate-600">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {priceData.slice(0, 25).map((snap) => (
                    <tr key={snap.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2">
                        <span className="badge bg-slate-100 text-slate-700">{snap.source}</span>
                      </td>
                      <td className="px-3 py-2 text-slate-600">{snap.brand || '—'}</td>
                      <td className="px-3 py-2 text-slate-700 max-w-xs truncate">
                        {snap.url ? (
                          <a href={snap.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-600 no-underline">
                            {snap.title}
                          </a>
                        ) : snap.title}
                      </td>
                      <td className="px-3 py-2 text-right font-semibold text-slate-900">
                        ${snap.price.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-slate-400 text-xs">
                        {new Date(snap.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {priceData.length === 0 && priceQuery && !priceLoading && (
          <div className="text-center py-8 text-slate-400">
            <p>No price data found for &ldquo;{priceQuery}&rdquo;</p>
            <p className="text-sm mt-1">Price data is recorded automatically when you search. Try searching for this part first.</p>
          </div>
        )}
      </div>

      {/* Two-column: popular + recent */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Popular searches */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Popular Searches (30 days)</h2>
          {popular.length === 0 ? (
            <p className="text-sm text-slate-400">No searches recorded yet. Start searching to see trends.</p>
          ) : (
            <div className="space-y-2">
              {popular.map((item) => (
                <div key={item.normalized_query} className="flex items-center justify-between py-1.5">
                  <button
                    onClick={() => { setPriceQuery(item.normalized_query); }}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium bg-transparent border-none cursor-pointer text-left truncate"
                  >
                    {item.normalized_query}
                  </button>
                  <div className="flex items-center gap-3 text-xs text-slate-400 flex-shrink-0">
                    <span>{item.count} searches</span>
                    <span>{Math.round(item.avg_listings)} avg results</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent searches */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Recent Searches</h2>
          {recent.length === 0 ? (
            <p className="text-sm text-slate-400">No searches recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {recent.map((item) => (
                <div key={item.id} className="flex items-center justify-between py-1.5">
                  <button
                    onClick={() => { setPriceQuery(item.normalized_query); }}
                    className="text-sm text-slate-700 font-medium bg-transparent border-none cursor-pointer text-left truncate"
                  >
                    {item.query}
                  </button>
                  <div className="flex items-center gap-3 text-xs text-slate-400 flex-shrink-0">
                    <span>{item.market_listing_count} listings</span>
                    {item.response_time_ms && <span>{item.response_time_ms}ms</span>}
                    <span>{new Date(item.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-slate-900 mt-1">{value}</div>
    </div>
  );
}

function MiniStat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg px-3 py-2.5 ${highlight ? 'bg-green-50 border border-green-200' : 'bg-slate-50 border border-slate-200'}`}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-lg font-bold ${highlight ? 'text-green-700' : 'text-slate-900'}`}>{value}</div>
    </div>
  );
}

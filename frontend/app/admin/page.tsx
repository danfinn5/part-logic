'use client';
import { useState, useEffect, useCallback } from 'react';

interface Source {
  id: string;
  domain: string;
  name: string;
  category: string;
  tags: string[];
  notes: string;
  source_type: string;
  status: string;
  priority: number;
  supports_vin: boolean;
  supports_part_number_search: boolean;
  robots_policy: string;
  sitemap_url: string | null;
  created_at: string;
  updated_at: string;
}

interface RegistryStats {
  total: number;
  active: number;
  disabled: number;
  by_source_type: Record<string, number>;
  by_category: Record<string, number>;
}

const CATEGORY_COLORS: Record<string, string> = {
  retailer: 'bg-blue-100 text-blue-800',
  marketplace: 'bg-purple-100 text-purple-800',
  used_aggregator: 'bg-amber-100 text-amber-800',
  salvage_yard: 'bg-orange-100 text-orange-800',
  oe_dealer: 'bg-green-100 text-green-800',
  industrial: 'bg-gray-100 text-gray-800',
  electronics: 'bg-cyan-100 text-cyan-800',
  interchange: 'bg-rose-100 text-rose-800',
  epc: 'bg-indigo-100 text-indigo-800',
  epc_retail: 'bg-violet-100 text-violet-800',
  oem_catalog: 'bg-emerald-100 text-emerald-800',
};

export default function AdminPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<RegistryStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const fetchSources = useCallback(async () => {
    const params = new URLSearchParams();
    if (filterType) params.set('source_type', filterType);
    if (filterCategory) params.set('category', filterCategory);
    if (filterTag) params.set('tag', filterTag);
    if (filterStatus) params.set('status', filterStatus);
    if (searchQuery) params.set('search', searchQuery);

    const res = await fetch(`/api/sources?${params}`);
    const data = await res.json();
    setSources(data.sources || []);
  }, [filterType, filterCategory, filterTag, filterStatus, searchQuery]);

  const fetchStats = useCallback(async () => {
    const res = await fetch('/api/sources/stats');
    const data = await res.json();
    setStats(data);
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchSources(), fetchStats()]).finally(() => setLoading(false));
  }, [fetchSources, fetchStats]);

  const toggleStatus = async (domain: string) => {
    await fetch(`/api/sources/${domain}/toggle`, { method: 'POST' });
    fetchSources();
    fetchStats();
  };

  const allCategories = stats ? Object.keys(stats.by_category).sort() : [];
  const allTags = Array.from(new Set(sources.flatMap((s) => s.tags))).sort();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Source Registry</h1>
            <p className="text-sm text-gray-500">
              Manage parts sources for search and link generation
            </p>
          </div>
          <a
            href="/"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            &larr; Back to Search
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Sources" value={stats.total} />
            <StatCard label="Active" value={stats.active} color="text-green-600" />
            <StatCard label="Disabled" value={stats.disabled} color="text-red-600" />
            <StatCard label="Categories" value={Object.keys(stats.by_category).length} />
          </div>
        )}

        {/* Category Breakdown */}
        {stats && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Sources by Category</h2>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([cat, count]) => (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(filterCategory === cat ? '' : cat)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                      filterCategory === cat
                        ? 'ring-2 ring-blue-500 ring-offset-1'
                        : ''
                    } ${CATEGORY_COLORS[cat] || 'bg-gray-100 text-gray-700'}`}
                  >
                    {cat.replace(/_/g, ' ')}
                    <span className="bg-white/50 rounded-full px-1.5 py-0.5 text-[10px]">
                      {count}
                    </span>
                  </button>
                ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <input
              type="text"
              placeholder="Search by domain or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm px-3 py-2 border"
            />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm px-3 py-2 border"
            >
              <option value="">All Types</option>
              <option value="buyable">Buyable</option>
              <option value="reference">Reference</option>
            </select>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm px-3 py-2 border"
            >
              <option value="">All Categories</option>
              {allCategories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <select
              value={filterTag}
              onChange={(e) => setFilterTag(e.target.value)}
              className="rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm px-3 py-2 border"
            >
              <option value="">All Tags</option>
              {allTags.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm px-3 py-2 border"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        </div>

        {/* Sources Table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading sources...</div>
          ) : sources.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No sources match filters</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Source</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Tags</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Priority</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {sources.map((source) => (
                    <tr key={source.domain} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleStatus(source.domain)}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                            source.status === 'active'
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-red-100 text-red-700 hover:bg-red-200'
                          }`}
                          title={`Click to ${source.status === 'active' ? 'disable' : 'enable'}`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              source.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                            }`}
                          />
                          {source.status}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{source.name}</div>
                        <div className="text-gray-500 text-xs">{source.domain}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            CATEGORY_COLORS[source.category] || 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {source.category.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-gray-600">{source.source_type}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {source.tags.slice(0, 4).map((tag) => (
                            <span
                              key={tag}
                              className="inline-block px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[10px]"
                            >
                              {tag}
                            </span>
                          ))}
                          {source.tags.length > 4 && (
                            <span className="text-[10px] text-gray-400">
                              +{source.tags.length - 4}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-mono text-gray-600">{source.priority}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-gray-500 max-w-[200px] truncate block">
                          {source.notes}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!loading && sources.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
              Showing {sources.length} source{sources.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  color = 'text-gray-900',
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-xs text-gray-500 font-medium">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}

import {
  SearchResponse,
  SortOption,
  SearchHistoryEntry,
  PriceSnapshot,
  PriceTrend,
  SearchStats,
  PopularSearch,
} from './types';

const API_BASE = '/api';

export async function searchParts(
  query: string,
  sort: SortOption = 'value',
): Promise<SearchResponse> {
  const params = new URLSearchParams({ query: query.trim(), sort });
  const response = await fetch(`${API_BASE}/search?${params}`);
  if (!response.ok) {
    throw new Error(`Search failed (HTTP ${response.status})`);
  }
  return response.json();
}

/* ── History & Price Tracking ────────────────────────────────────── */

export async function getRecentSearches(limit = 20): Promise<SearchHistoryEntry[]> {
  const res = await fetch(`${API_BASE}/history/searches?limit=${limit}`);
  const data = await res.json();
  return data.searches || [];
}

export async function getPopularSearches(limit = 20, days = 7): Promise<PopularSearch[]> {
  const res = await fetch(`${API_BASE}/history/searches/popular?limit=${limit}&days=${days}`);
  const data = await res.json();
  return data.searches || [];
}

export async function getSearchStats(): Promise<SearchStats> {
  const res = await fetch(`${API_BASE}/history/searches/stats`);
  return res.json();
}

export async function getPriceHistory(params: {
  part_number?: string;
  brand?: string;
  source?: string;
  limit?: number;
}): Promise<PriceSnapshot[]> {
  const searchParams = new URLSearchParams();
  if (params.part_number) searchParams.set('part_number', params.part_number);
  if (params.brand) searchParams.set('brand', params.brand);
  if (params.source) searchParams.set('source', params.source);
  if (params.limit) searchParams.set('limit', String(params.limit));
  const res = await fetch(`${API_BASE}/history/prices?${searchParams}`);
  const data = await res.json();
  return data.prices || [];
}

export async function getPriceTrends(partNumber: string, days = 30): Promise<PriceTrend[]> {
  const res = await fetch(`${API_BASE}/history/prices/trends?part_number=${encodeURIComponent(partNumber)}&days=${days}`);
  const data = await res.json();
  return data.trends || [];
}

import {
  SearchResponse,
  SortOption,
  SearchHistoryEntry,
  PriceSnapshot,
  PriceTrend,
  SearchStats,
  PopularSearch,
  VINDecodeResult,
  SavedSearch,
  PriceAlert,
} from './types';

const API_BASE = '/api';

export async function searchParts(
  query: string,
  sort: SortOption = 'value',
  vehicle?: { make?: string; model?: string; year?: string },
  vin?: string,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ query: query.trim(), sort });
  if (vehicle?.make) params.set('vehicle_make', vehicle.make);
  if (vehicle?.model) params.set('vehicle_model', vehicle.model);
  if (vehicle?.year) params.set('vehicle_year', vehicle.year);
  if (vin) params.set('vin', vin);
  const response = await fetch(`${API_BASE}/search?${params}`);
  if (!response.ok) {
    throw new Error(`Search failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function decodeVin(vin: string): Promise<VINDecodeResult> {
  const response = await fetch(`${API_BASE}/vin/decode?vin=${encodeURIComponent(vin)}`);
  if (!response.ok) {
    throw new Error(`VIN decode failed (HTTP ${response.status})`);
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

/* ── Saved Searches & Price Alerts ─────────────────────────────────── */

export async function saveSearch(params: {
  query: string;
  vehicle_make?: string;
  vehicle_model?: string;
  vehicle_year?: string;
  vin?: string;
  sort?: string;
  price_threshold?: number;
}): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/saved/searches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getSavedSearches(): Promise<SavedSearch[]> {
  const res = await fetch(`${API_BASE}/saved/searches`);
  const data = await res.json();
  return data.searches || [];
}

export async function deleteSavedSearch(id: number): Promise<void> {
  await fetch(`${API_BASE}/saved/searches/${id}`, { method: 'DELETE' });
}

export async function createPriceAlert(params: {
  saved_search_id: number;
  target_price: number;
  part_number?: string;
  brand?: string;
}): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/saved/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getAlerts(): Promise<PriceAlert[]> {
  const res = await fetch(`${API_BASE}/saved/alerts`);
  const data = await res.json();
  return data.alerts || [];
}

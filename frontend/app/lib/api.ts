import { SearchResponse, SortOption } from './types';

export async function searchParts(
  query: string,
  sort: SortOption = 'value',
): Promise<SearchResponse> {
  const params = new URLSearchParams({ query: query.trim(), sort });
  const response = await fetch(`/api/search?${params}`);
  if (!response.ok) {
    throw new Error(`Search failed (HTTP ${response.status})`);
  }
  return response.json();
}

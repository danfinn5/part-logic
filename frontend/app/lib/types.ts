export interface MarketListing {
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
  matched_interchange?: string | null;
}

export interface SalvageHit {
  source: string;
  yard_name: string;
  yard_location: string;
  vehicle: string;
  url: string;
  last_seen?: string;
  part_description?: string;
}

export interface ExternalLink {
  label: string;
  url: string;
  source: string;
  category?: string;
}

export interface SourceStatus {
  source: string;
  status: 'ok' | 'error' | 'cached';
  details?: string;
  result_count: number;
}

export interface InterchangeInfo {
  primary_part_number: string;
  interchange_numbers: string[];
  brands_by_number: Record<string, string[]>;
  confidence: number;
  sources_consulted: string[];
}

export interface BrandSummary {
  brand: string;
  tier: string;
  quality_score: number;
  avg_price?: number | null;
  listing_count: number;
  recommendation_note?: string | null;
}

export interface CommunitySource {
  title: string;
  url: string;
  source: string;
  score: number;
}

export interface PartIntelligence {
  query_type: string;
  vehicle_hint?: string | null;
  part_description?: string | null;
  cross_references: string[];
  brands_found: string[];
  interchange?: InterchangeInfo | null;
  brand_comparison: BrandSummary[];
  recommendation?: string | null;
  community_sources: CommunitySource[];
}

export interface Offer {
  source: string;
  price: number;
  shipping_cost?: number | null;
  total_cost: number;
  condition?: string | null;
  url: string;
  title: string;
  image_url?: string | null;
  value_score: number;
}

export interface ListingGroup {
  brand: string;
  part_number: string;
  tier: string;
  quality_score: number;
  offers: Offer[];
  best_price: number;
  price_range: { low: number; high: number };
  offer_count: number;
  best_value_score: number;
}

export interface SearchResponse {
  query: string;
  extracted_part_numbers: string[];
  results: {
    market_listings: MarketListing[];
    salvage_hits: SalvageHit[];
    external_links: ExternalLink[];
  };
  grouped_listings: ListingGroup[];
  sources_queried: SourceStatus[];
  warnings: string[];
  cached: boolean;
  intelligence?: PartIntelligence | null;
}

export type SortOption = 'relevance' | 'price_asc' | 'price_desc' | 'value';

export type ViewMode = 'comparison' | 'list';

/* ── Price Tracking Types ────────────────────────────────────────── */

export interface SearchHistoryEntry {
  id: number;
  query: string;
  normalized_query: string;
  query_type: string | null;
  vehicle_hint: string | null;
  part_description: string | null;
  sort: string;
  market_listing_count: number;
  salvage_hit_count: number;
  external_link_count: number;
  source_count: number;
  has_interchange: number;
  cached: number;
  response_time_ms: number | null;
  created_at: string;
}

export interface PriceSnapshot {
  id: number;
  query: string;
  source: string;
  part_number: string | null;
  brand: string | null;
  title: string;
  price: number;
  shipping_cost: number;
  condition: string | null;
  url: string | null;
  created_at: string;
}

export interface PriceTrend {
  date: string;
  source: string;
  avg_price: number;
  min_price: number;
  max_price: number;
  observations: number;
}

export interface SearchStats {
  total_searches: number;
  unique_queries: number;
  avg_listings_per_search: number;
  avg_response_ms: number;
  by_query_type: { query_type: string; count: number }[];
}

export interface PopularSearch {
  normalized_query: string;
  count: number;
  avg_listings: number;
  last_searched: string;
}

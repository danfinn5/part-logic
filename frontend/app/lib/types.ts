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

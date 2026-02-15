import { useState } from 'react';
import { MarketListing } from '../lib/types';
import ListingCard from './ListingCard';

interface ListingGridProps {
  listings: MarketListing[];
}

const PAGE_SIZE = 20;

export default function ListingGrid({ listings }: ListingGridProps) {
  const [page, setPage] = useState(0);
  const [brandFilter, setBrandFilter] = useState<string | null>(null);
  const [conditionFilter, setConditionFilter] = useState<string | null>(null);

  if (listings.length === 0) return null;

  // Get unique brands and conditions for filters
  const brands = Array.from(new Set(listings.map((l) => l.brand).filter((b): b is string => !!b)));
  const conditions = Array.from(new Set(listings.map((l) => l.condition).filter((c): c is string => !!c)));

  // Apply filters
  let filtered = listings;
  if (brandFilter) {
    filtered = filtered.filter((l) => l.brand === brandFilter);
  }
  if (conditionFilter) {
    filtered = filtered.filter((l) => l.condition === conditionFilter);
  }

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-3 pb-2 border-b-2 border-gray-200">
        Market Listings
        <span className="text-sm font-normal text-gray-500 ml-2">
          ({filtered.length}{filtered.length !== listings.length ? ` of ${listings.length}` : ''})
        </span>
      </h2>

      {/* Filters */}
      {(brands.length > 1 || conditions.length > 1) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {brands.length > 1 && (
            <select
              value={brandFilter || ''}
              onChange={(e) => { setBrandFilter(e.target.value || null); setPage(0); }}
              className="text-xs px-2 py-1 border border-gray-200 rounded bg-white"
            >
              <option value="">All brands</option>
              {brands.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          )}
          {conditions.length > 1 && (
            <select
              value={conditionFilter || ''}
              onChange={(e) => { setConditionFilter(e.target.value || null); setPage(0); }}
              className="text-xs px-2 py-1 border border-gray-200 rounded bg-white"
            >
              <option value="">All conditions</option>
              {conditions.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          )}
          {(brandFilter || conditionFilter) && (
            <button
              onClick={() => { setBrandFilter(null); setConditionFilter(null); setPage(0); }}
              className="text-xs text-blue-600 hover:text-blue-800 bg-transparent border-none cursor-pointer"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      <div className="grid gap-3">
        {paged.map((listing, i) => (
          <ListingCard key={`${listing.source}-${listing.url}-${i}`} listing={listing} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1 text-xs border border-gray-200 rounded bg-white disabled:opacity-50 cursor-pointer disabled:cursor-default"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 text-xs border border-gray-200 rounded bg-white disabled:opacity-50 cursor-pointer disabled:cursor-default"
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}

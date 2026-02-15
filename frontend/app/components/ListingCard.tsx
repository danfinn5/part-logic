import { MarketListing } from '../lib/types';

interface ListingCardProps {
  listing: MarketListing;
}

export default function ListingCard({ listing }: ListingCardProps) {
  return (
    <div className="flex gap-3.5 p-3.5 border border-gray-200 rounded-lg bg-white hover:border-blue-200 transition-colors">
      {listing.image_url && (
        <img
          src={listing.image_url}
          alt=""
          className="w-20 h-20 object-cover rounded-md flex-shrink-0"
        />
      )}
      <div className="flex-1 min-w-0">
        <a
          href={listing.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-blue-600 hover:text-blue-800 no-underline leading-tight block"
        >
          {listing.title}
        </a>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
          <span className="font-bold text-gray-900">${listing.price.toFixed(2)}</span>
          {listing.shipping_cost != null && listing.shipping_cost > 0 && (
            <span className="text-gray-500">+${listing.shipping_cost.toFixed(2)} ship</span>
          )}
          {listing.shipping_cost === 0 && (
            <span className="text-green-600">Free shipping</span>
          )}
          {listing.condition && <span>{listing.condition}</span>}
          {listing.listing_type === 'auction' && (
            <span className="px-1.5 bg-amber-100 rounded text-xs font-medium">Auction</span>
          )}
          {listing.listing_type === 'buy_it_now' && (
            <span className="px-1.5 bg-green-100 rounded text-xs font-medium">Buy It Now</span>
          )}
        </div>
        <div className="mt-1 text-xs text-gray-400 flex flex-wrap gap-2">
          <span>{listing.source}</span>
          {listing.brand && <span>{listing.brand}</span>}
          {listing.vendor && <span>Seller: {listing.vendor}</span>}
          {listing.part_numbers.length > 0 && (
            <span>Part #: {listing.part_numbers.join(', ')}</span>
          )}
          {listing.matched_interchange && (
            <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded text-[10px]">
              via {listing.matched_interchange}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

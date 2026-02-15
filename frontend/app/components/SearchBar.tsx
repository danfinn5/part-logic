import { SortOption } from '../lib/types';

interface SearchBarProps {
  query: string;
  sort: SortOption;
  loading: boolean;
  onQueryChange: (query: string) => void;
  onSortChange: (sort: SortOption) => void;
  onSearch: () => void;
}

export default function SearchBar({
  query, sort, loading, onQueryChange, onSortChange, onSearch,
}: SearchBarProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') onSearch();
  };

  return (
    <div className="flex gap-2 mb-6 flex-wrap">
      <input
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Part number, keywords, or OEM number..."
        className="flex-1 min-w-[300px] px-3.5 py-2.5 text-sm border-2 border-gray-200 rounded-md outline-none focus:border-blue-500 transition-colors"
      />
      <select
        value={sort}
        onChange={(e) => onSortChange(e.target.value as SortOption)}
        className="px-3 py-2.5 text-sm border-2 border-gray-200 rounded-md bg-white cursor-pointer"
      >
        <option value="value">Sort: Best Value</option>
          <option value="relevance">Sort: Relevance</option>
          <option value="price_asc">Sort: Price Low→High</option>
          <option value="price_desc">Sort: Price High→Low</option>
      </select>
      <button
        onClick={onSearch}
        disabled={loading || !query.trim()}
        className={`px-7 py-2.5 text-sm font-semibold text-white border-none rounded-md cursor-pointer transition-colors ${
          loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {loading ? 'Searching...' : 'Search'}
      </button>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { SavedSearch } from '../lib/types';
import { getSavedSearches, deleteSavedSearch, createPriceAlert } from '../lib/api';

interface SavedSearchesProps {
  onRunSearch: (query: string, vehicle?: { make?: string; model?: string; year?: string }) => void;
  currentQuery?: string;
}

export default function SavedSearches({ onRunSearch, currentQuery }: SavedSearchesProps) {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [open, setOpen] = useState(false);
  const [alertSearchId, setAlertSearchId] = useState<number | null>(null);
  const [alertPrice, setAlertPrice] = useState('');
  const [alertPartNumber, setAlertPartNumber] = useState('');

  useEffect(() => {
    if (open) {
      getSavedSearches().then(setSearches).catch(() => setSearches([]));
    }
  }, [open]);

  const handleDelete = async (id: number) => {
    await deleteSavedSearch(id);
    setSearches(searches.filter((s) => s.id !== id));
  };

  const handleCreateAlert = async (searchId: number) => {
    const price = parseFloat(alertPrice);
    if (isNaN(price) || price <= 0) return;
    await createPriceAlert({
      saved_search_id: searchId,
      target_price: price,
      part_number: alertPartNumber || undefined,
    });
    setAlertSearchId(null);
    setAlertPrice('');
    setAlertPartNumber('');
  };

  if (searches.length === 0 && !open) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-slate-500 hover:text-blue-600 transition-colors bg-transparent border-none cursor-pointer flex items-center gap-1"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        Saved ({searches.length})
      </button>

      {open && (
        <div className="absolute right-0 top-8 z-50 w-80 bg-white border border-slate-200 rounded-lg shadow-lg p-3 space-y-2">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Saved Searches</h3>
          {searches.length === 0 && (
            <p className="text-xs text-slate-400">No saved searches yet.</p>
          )}
          {searches.map((s) => (
            <div key={s.id} className="border border-slate-100 rounded-md p-2">
              <div className="flex items-center justify-between gap-2">
                <button
                  onClick={() => {
                    onRunSearch(s.query, {
                      make: s.vehicle_make || undefined,
                      model: s.vehicle_model || undefined,
                      year: s.vehicle_year || undefined,
                    });
                    setOpen(false);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800 bg-transparent border-none cursor-pointer text-left truncate flex-1"
                >
                  {s.query}
                </button>
                <div className="flex gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => setAlertSearchId(alertSearchId === s.id ? null : s.id)}
                    className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-600 border border-amber-200 rounded cursor-pointer hover:bg-amber-100"
                    title="Set price alert"
                  >
                    Alert
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="text-[10px] px-1.5 py-0.5 bg-red-50 text-red-500 border border-red-200 rounded cursor-pointer hover:bg-red-100"
                    title="Delete"
                  >
                    Del
                  </button>
                </div>
              </div>
              {s.vehicle_make && (
                <span className="text-[10px] text-slate-400">
                  {[s.vehicle_year, s.vehicle_make, s.vehicle_model].filter(Boolean).join(' ')}
                </span>
              )}

              {/* Alert creation form */}
              {alertSearchId === s.id && (
                <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-1.5">
                  <input
                    type="number"
                    value={alertPrice}
                    onChange={(e) => setAlertPrice(e.target.value)}
                    placeholder="Target price"
                    className="text-xs px-2 py-1 border border-slate-200 rounded w-24"
                    step="0.01"
                    min="0"
                  />
                  <input
                    type="text"
                    value={alertPartNumber}
                    onChange={(e) => setAlertPartNumber(e.target.value)}
                    placeholder="Part # (opt)"
                    className="text-xs px-2 py-1 border border-slate-200 rounded w-24"
                  />
                  <button
                    onClick={() => handleCreateAlert(s.id)}
                    className="text-xs px-2 py-1 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700"
                  >
                    Set
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PartLogic — Smart Auto Parts Search',
  description: 'Search 80+ auto parts retailers at once. Compare prices, track trends, find the best value.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="font-[Inter,system-ui,sans-serif]">
        {/* Top navigation */}
        <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200/80">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2 no-underline">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.3-4.3" />
                </svg>
              </div>
              <span className="text-lg font-bold text-slate-900 tracking-tight">
                Part<span className="text-blue-600">Logic</span>
              </span>
            </a>
            <nav className="flex items-center gap-1">
              <a href="/" className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 rounded-md hover:bg-slate-100 transition-colors no-underline">
                Search
              </a>
              <a href="/prices" className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 rounded-md hover:bg-slate-100 transition-colors no-underline">
                Price Tracker
              </a>
              <a href="/admin" className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 rounded-md hover:bg-slate-100 transition-colors no-underline">
                Sources
              </a>
            </nav>
          </div>
        </header>

        <main className="min-h-[calc(100vh-3.5rem)]">
          {children}
        </main>
      </body>
    </html>
  );
}

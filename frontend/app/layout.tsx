import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PartLogic - Parts Search',
  description: 'Search for auto parts across multiple sources — compare prices, quality, and value',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}

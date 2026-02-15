'use client';

import { PriceTrend } from '../lib/types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface PriceChartProps {
  trends: PriceTrend[];
}

// Colors for different sources
const SOURCE_COLORS: Record<string, string> = {
  rockauto: '#e11d48',
  fcpeuro: '#2563eb',
  autozone: '#f97316',
  amazon: '#059669',
  ebay: '#7c3aed',
  partsgeek: '#0891b2',
  ecstuning: '#dc2626',
  napa: '#ca8a04',
  oreilly: '#16a34a',
  lkq: '#9333ea',
  advanceauto: '#ea580c',
  partsouq: '#0d9488',
};

const DEFAULT_COLOR = '#64748b';

function getSourceColor(source: string): string {
  return SOURCE_COLORS[source] || DEFAULT_COLOR;
}

export default function PriceChart({ trends }: PriceChartProps) {
  if (trends.length === 0) return null;

  // Pivot data: group by date, with one column per source
  const sources = Array.from(new Set(trends.map((t) => t.source)));
  const dateMap: Record<string, Record<string, number>> = {};

  for (const t of trends) {
    if (!dateMap[t.date]) dateMap[t.date] = {};
    dateMap[t.date][t.source] = t.avg_price;
  }

  const chartData = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, prices]) => ({
      date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      ...prices,
    }));

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number | undefined) => value != null ? [`$${value.toFixed(2)}`, ''] : ['—', '']}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
          />
          {sources.map((source) => (
            <Line
              key={source}
              type="monotone"
              dataKey={source}
              name={source}
              stroke={getSourceColor(source)}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

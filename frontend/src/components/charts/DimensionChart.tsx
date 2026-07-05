import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { DimensionAverages } from '../../types/dashboard';
import { SCORE_DIMENSIONS } from '../../constants/dimensions';

interface DimensionChartProps {
  averages: DimensionAverages | null | undefined;
}

export default function DimensionChart({ averages }: DimensionChartProps) {
  if (!averages) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-neutral-400 font-medium">
        No dimension scores available
      </div>
    );
  }

  // Build chart-friendly data array
  const data = SCORE_DIMENSIONS.map((dim) => {
    const val = averages[dim.key];
    return {
      name: dim.label,
      score: val !== null && val !== undefined ? Math.round(val) : null,
    };
  }).filter((d) => d.score !== null);

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-neutral-400 font-medium">
        No dimension score records exist for this scope
      </div>
    );
  }

  // Get color based on score value
  const getBarColor = (score: number) => {
    if (score >= 75) return '#10b981'; // emerald-500
    if (score >= 50) return '#f59e0b'; // amber-500
    return '#ef4444'; // red-500
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const val = payload[0].value;
      return (
        <div className="bg-white p-2.5 border border-neutral-200 shadow-sm rounded text-xs font-semibold">
          <p className="text-neutral-500">{payload[0].payload.name}</p>
          <p className="text-neutral-900 mt-0.5">Average Score: {val}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f5f5f5" />
          <XAxis 
            type="number" 
            domain={[0, 100]} 
            tick={{ fontSize: 11, fill: '#888' }}
            stroke="#e5e5e5"
          />
          <YAxis 
            dataKey="name" 
            type="category" 
            tick={{ fontSize: 11, fill: '#555' }}
            width={120}
            stroke="#e5e5e5"
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(245, 243, 236, 0.4)' }} />
          <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={16}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.score || 0)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

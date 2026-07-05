import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TeamPerformanceSummary } from '../../types/dashboard';

interface TeamScoreChartProps {
  performance: TeamPerformanceSummary[] | null | undefined;
}

export default function TeamScoreChart({ performance }: TeamScoreChartProps) {
  if (!performance || performance.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-neutral-400 font-medium">
        No team performance records available
      </div>
    );
  }

  // Filter out teams with no score
  const data = performance
    .map((team) => ({
      name: team.team_name,
      score: team.average_score !== null && team.average_score !== undefined ? Math.round(team.average_score) : null,
      calls: team.completed_calls,
    }))
    .filter((d) => d.score !== null);

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-neutral-400 font-medium">
        No completed scores found for any team
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-white p-2.5 border border-neutral-200 shadow-sm rounded text-xs font-semibold">
          <p className="text-neutral-500">{p.name}</p>
          <p className="text-brand-600 mt-1 font-bold">Average Score: {p.score}%</p>
          <p className="text-neutral-400 font-normal mt-0.5">Completed Calls: {p.calls}</p>
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
          margin={{ top: 15, right: 10, left: -10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f5f5f5" />
          <XAxis 
            dataKey="name" 
            tick={{ fontSize: 11, fill: '#666' }}
            stroke="#e5e5e5"
          />
          <YAxis 
            domain={[0, 100]} 
            tick={{ fontSize: 11, fill: '#888' }}
            stroke="#e5e5e5"
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(124, 58, 237, 0.05)' }} />
          <Bar dataKey="score" fill="#7c3aed" radius={[4, 4, 0, 0]} barSize={28} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

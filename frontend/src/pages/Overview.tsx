import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  TrendingUp, 
  Phone, 
  CheckCircle2, 
  Users2, 
  XCircle, 
  RefreshCw,
  Building,
  Calendar
} from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { getOrgDashboard } from '../api/dashboard';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import MetricCard from '../components/common/MetricCard';
import ScoreBadge from '../components/common/ScoreBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import DimensionChart from '../components/charts/DimensionChart';
import TeamScoreChart from '../components/charts/TeamScoreChart';
import IssueDistribution from '../components/charts/IssueDistribution';
import { formatScore } from '../utils/formatters';

export default function Overview() {
  const navigate = useNavigate();
  const { selectedOrgId, organizations, selectedTeamId, isLoadingContext } = useAppGlobalContext();
  
  // Date filter state (default to all-time or last 30 days)
  const [datePreset, setDatePreset] = useState<string>('all');
  const [customStart, setCustomStart] = useState<string>('');
  const [customEnd, setCustomEnd] = useState<string>('');

  // Calculate actual query params
  const getDates = () => {
    if (datePreset === 'all') return { start: undefined, end: undefined };
    
    const today = new Date();
    if (datePreset === '7d') {
      const past = new Date(today);
      past.setDate(today.getDate() - 7);
      return { start: past.toISOString().split('T')[0], end: today.toISOString().split('T')[0] };
    }
    if (datePreset === '30d') {
      const past = new Date(today);
      past.setDate(today.getDate() - 30);
      return { start: past.toISOString().split('T')[0], end: today.toISOString().split('T')[0] };
    }
    return {
      start: customStart || undefined,
      end: customEnd || undefined
    };
  };

  const { start, end } = getDates();

  const org = organizations.find((o) => o.id === selectedOrgId);

  const {
    data,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: QUERY_KEYS.orgDashboard(selectedOrgId, start, end, selectedTeamId || undefined),
    queryFn: () => getOrgDashboard(selectedOrgId, start, end, selectedTeamId || undefined),
    enabled: !!selectedOrgId,
  });

  if (isLoadingContext) {
    return <LoadingSkeleton variant="dashboard" />;
  }

  if (!selectedOrgId || organizations.length === 0) {
    return (
      <EmptyState
        title="No Organization Context Selected"
        description="Select or create an organization to view operational overview analytics."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={org ? `${org.name} Overview` : 'Organization Overview'}
        subtitle={org?.industry ? `Industry: ${org.industry}` : ''}
        action={
          <div className="flex flex-wrap items-center gap-3 bg-white p-2 border border-neutral-200 rounded-lg shadow-sm">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-500 mr-2 shrink-0">
              <Calendar className="w-4 h-4" />
              <span>Timeframe:</span>
            </div>
            
            {/* Presets */}
            <div className="flex items-center gap-1">
              {['all', '7d', '30d', 'custom'].map((preset) => (
                <button
                  key={preset}
                  onClick={() => setDatePreset(preset)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
                    datePreset === preset
                      ? 'bg-brand-600 text-white'
                      : 'text-neutral-600 hover:bg-neutral-50'
                  }`}
                >
                  {preset === 'all' && 'All Time'}
                  {preset === '7d' && '7 Days'}
                  {preset === '30d' && '30 Days'}
                  {preset === 'custom' && 'Custom'}
                </button>
              ))}
            </div>

            {/* Custom Inputs */}
            {datePreset === 'custom' && (
              <div className="flex items-center gap-1.5 border-l border-neutral-200 pl-3">
                <input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="text-xs border-neutral-200 rounded px-1.5 py-0.5"
                />
                <span className="text-neutral-400 text-xs">to</span>
                <input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="text-xs border-neutral-200 rounded px-1.5 py-0.5"
                />
              </div>
            )}

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-1 rounded text-neutral-400 hover:text-neutral-600 border border-transparent hover:border-neutral-100 disabled:opacity-50 shrink-0"
              title="Refresh dashboard"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
        }
      />

      {/* States */}
      {isLoading ? (
        <LoadingSkeleton variant="dashboard" />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : !data ? (
        <EmptyState />
      ) : (
        <>
          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Quality Score"
              value={data.average_quality_score ? `${formatScore(data.average_quality_score)}%` : '--'}
              icon={TrendingUp}
              supportingText="Avg score across completed calls"
            />
            <MetricCard
              label="Total Calls"
              value={data.total_calls}
              icon={Phone}
              supportingText={`${data.completed_calls} Completed, ${data.failed_calls} Failed`}
            />
            <MetricCard
              label="Completed Calls"
              value={data.completed_calls}
              icon={CheckCircle2}
              supportingText={`${data.processing_calls} actively processing`}
            />
            <MetricCard
              label="Active Advisors"
              value={data.total_advisors}
              icon={Users2}
              supportingText={`Distributed across ${data.total_teams} teams`}
            />
          </div>

          {/* Warning banner for failing/processing calls */}
          {(data.failed_calls > 0 || data.processing_calls > 0) && (
            <div className="bg-white border border-neutral-200 rounded-lg px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-sm text-xs text-neutral-600">
              <div className="flex items-center gap-1.5">
                <XCircle className="w-4 h-4 text-red-500" />
                <span>
                  Attention: <strong>{data.failed_calls}</strong> calls failed to complete processing pipeline.
                </span>
                {data.processing_calls > 0 && (
                  <span className="border-l border-neutral-200 pl-2">
                    <strong>{data.processing_calls}</strong> calls currently in progress.
                  </span>
                )}
              </div>
              <button 
                onClick={() => navigate('/calls?processing_status=Failed')}
                className="text-brand-600 font-semibold hover:text-brand-700 hover:underline"
              >
                View Failures
              </button>
            </div>
          )}

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Dimension Breakdown */}
            <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm lg:col-span-2">
              <h3 className="text-sm font-semibold text-neutral-900 mb-4 uppercase tracking-wider">
                Dimension Performance Breakdown
              </h3>
              <DimensionChart averages={data.average_dimension_scores} />
            </div>

            {/* Top Issue Tags */}
            <div className="lg:col-span-1">
              <IssueDistribution issues={data.top_issue_tags} />
            </div>
          </div>

          {/* Team Performance charts & list */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Team Chart */}
            <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm lg:col-span-1">
              <h3 className="text-sm font-semibold text-neutral-900 mb-4 uppercase tracking-wider">
                Team Comparison
              </h3>
              <TeamScoreChart performance={data.team_performance} />
            </div>

            {/* Team Table */}
            <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm lg:col-span-2">
              <div className="bg-neutral-50 px-5 py-4 border-b border-neutral-200 flex justify-between items-center">
                <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
                  Team Performance Index
                </h3>
                <button
                  onClick={() => navigate('/teams')}
                  className="text-xs text-brand-600 hover:text-brand-700 font-semibold hover:underline"
                >
                  View All Teams
                </button>
              </div>

              <div className="overflow-x-auto">
                {data.team_performance.length === 0 ? (
                  <div className="p-8 text-center text-xs text-neutral-400">
                    No teams recorded under this organization
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-neutral-200 text-left">
                    <thead>
                      <tr className="bg-neutral-50 text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                        <th className="px-6 py-3">Team Name</th>
                        <th className="px-6 py-3 text-center">Completed Calls</th>
                        <th className="px-6 py-3 text-center">Average Score</th>
                        <th className="px-6 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-200 text-xs">
                      {data.team_performance.map((team) => (
                        <tr key={team.team_id} className="hover:bg-neutral-50 transition-colors">
                          <td className="px-6 py-4 font-medium text-neutral-900">
                            {team.team_name}
                          </td>
                          <td className="px-6 py-4 text-center text-neutral-600">
                            {team.completed_calls}
                          </td>
                          <td className="px-6 py-4 text-center">
                            <ScoreBadge score={team.average_score} size="sm" />
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => navigate(`/teams/${team.team_id}`)}
                              className="text-xs text-brand-600 hover:text-brand-700 font-semibold hover:underline"
                            >
                              View Team
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

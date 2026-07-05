import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  TrendingUp, 
  Phone, 
  CheckCircle2, 
  AlertOctagon, 
  ChevronLeft,
  ArrowRight,
  TrendingDown,
  Info
} from 'lucide-react';

import { getAdvisorDashboard } from '../api/dashboard';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import MetricCard from '../components/common/MetricCard';
import ScoreBadge from '../components/common/ScoreBadge';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import DimensionChart from '../components/charts/DimensionChart';
import IssueDistribution from '../components/charts/IssueDistribution';
import { formatScore, formatDuration, formatDate, formatCategoryLabel } from '../utils/formatters';

export default function AdvisorDetail() {
  const { advisorId } = useParams<{ advisorId: string }>();
  const navigate = useNavigate();

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.advisorDashboard(advisorId || ''),
    queryFn: () => getAdvisorDashboard(advisorId || ''),
    enabled: !!advisorId,
  });

  if (isLoading) {
    return <LoadingSkeleton variant="detail" />;
  }

  // Handle 404
  const is404 = isError && (error as any)?.status === 404;

  if (is404 || !advisorId) {
    return (
      <EmptyState
        title="Advisor Not Found"
        description="The advisor ID specified does not exist or has been removed."
        action={
          <button
            onClick={() => navigate('/advisors')}
            className="inline-flex items-center text-xs font-semibold text-brand-600 hover:text-brand-700"
          >
            <ChevronLeft className="w-4 h-4 mr-1" /> Back to Advisors Directory
          </button>
        }
      />
    );
  }

  if (isError) {
    return <ErrorState onRetry={refetch} message={(error as any)?.message} />;
  }

  if (!data) {
    return <EmptyState />;
  }

  const breadcrumbs = [
    { label: 'Overview', to: '/overview' },
    { label: 'Advisors', to: '/advisors' },
    { label: data.advisor_name },
  ];

  // Get name of top issue category if exists
  const topIssueText = data.top_issue_tags.length > 0
    ? formatCategoryLabel(data.top_issue_tags[0].category)
    : 'None';

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title={data.advisor_name}
        subtitle={`Team: ${data.team_name} | Email: ${data.advisor_email} | Status: ${data.advisor_status}`}
        breadcrumbs={breadcrumbs}
        action={
          <button
            onClick={() => navigate('/advisors')}
            className="inline-flex items-center justify-center px-3 py-1.5 border border-neutral-200 text-xs font-medium rounded-md text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm focus:outline-none"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back to Directory
          </button>
        }
      />

      {/* KPI stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Average Score"
          value={data.average_quality_score ? `${formatScore(data.average_quality_score)}%` : '--'}
          icon={TrendingUp}
          supportingText="Overall performance index"
        />
        <MetricCard
          label="Completed Calls"
          value={data.completed_calls}
          icon={CheckCircle2}
          supportingText={`${data.processing_calls} actively processing`}
        />
        <MetricCard
          label="Total Uploads"
          value={data.total_calls}
          icon={Phone}
          supportingText={`${data.failed_calls} uploads failed`}
        />
        <MetricCard
          label="Top Issue Category"
          value={topIssueText}
          icon={AlertOctagon}
          supportingText="Most frequently flagged issue"
        />
      </div>

      {/* Performance Dimension Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm lg:col-span-2">
          <h3 className="text-sm font-semibold text-neutral-900 mb-4 uppercase tracking-wider">
            Dimension Averages
          </h3>
          <DimensionChart averages={data.average_dimension_scores} />
        </div>

        {/* Top Issues list */}
        <div className="lg:col-span-1">
          <IssueDistribution issues={data.top_issue_tags} />
        </div>
      </div>

      {/* Lower Areas & Recent Calls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Improvement Areas */}
        <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm lg:col-span-1 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-2 uppercase tracking-wider flex items-center gap-1.5">
              <TrendingDown className="w-4 h-4 text-red-500" /> Focus Improvement Areas
            </h3>
            <p className="text-xs text-neutral-500 mb-4">
              Lowest performing dimensions computed by the AI analysis scorecard.
            </p>

            {data.improvement_areas.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-xs text-neutral-400 bg-neutral-50 rounded-lg border border-dashed border-neutral-200 p-4">
                <Info className="w-5 h-5 text-neutral-300 mb-1" />
                <span>No improvement areas identified</span>
              </div>
            ) : (
              <div className="space-y-3.5">
                {data.improvement_areas.map((area, index) => (
                  <div key={area.dimension} className="border border-neutral-100 rounded-lg p-3 hover:bg-neutral-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-neutral-700">
                        {index + 1}. {area.dimension}
                      </span>
                      <ScoreBadge score={area.average_score} size="sm" />
                    </div>
                    {/* Performance bar */}
                    {area.average_score !== null && (
                      <div className="w-full bg-neutral-100 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            area.average_score >= 75 ? 'bg-emerald-500' : area.average_score >= 50 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${area.average_score}%` }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Calls */}
        <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm lg:col-span-2">
          <div className="bg-neutral-50 px-5 py-4 border-b border-neutral-200">
            <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
              Recent Call Ingests
            </h3>
          </div>

          {data.recent_calls.length === 0 ? (
            <div className="p-8 text-center text-xs text-neutral-400">
              No recent call records exist for this advisor
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200 text-left">
                <thead>
                  <tr className="bg-neutral-50 text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                    <th className="px-5 py-3">Upload Date</th>
                    <th className="px-5 py-3 text-center">Duration</th>
                    <th className="px-5 py-3 text-center">Score</th>
                    <th className="px-5 py-3 text-center">Issues</th>
                    <th className="px-5 py-3 text-center">Status</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 text-xs">
                  {data.recent_calls.map((call) => (
                    <tr key={call.call_id} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-5 py-4 text-neutral-900 font-medium whitespace-nowrap">
                        {formatDate(call.upload_time)}
                      </td>
                      <td className="px-5 py-4 text-center text-neutral-600">
                        {formatDuration(call.duration)}
                      </td>
                      <td className="px-5 py-4 text-center">
                        <ScoreBadge score={call.overall_score} size="sm" />
                      </td>
                      <td className="px-5 py-4 text-center">
                        {call.issue_count > 0 ? (
                          <span className="text-xs font-semibold text-red-600 px-2 py-0.5 bg-red-50 border border-red-200 rounded-full">
                            {call.issue_count}
                          </span>
                        ) : (
                          <span className="text-neutral-400">0</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-center whitespace-nowrap">
                        <StatusBadge status={call.processing_status} />
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => navigate(`/calls/${call.call_id}`)}
                          className="text-xs text-brand-600 hover:text-brand-700 font-semibold hover:underline flex items-center justify-end ml-auto"
                        >
                          Review <ArrowRight className="w-3.5 h-3.5 ml-1" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  TrendingUp, 
  Phone, 
  CheckCircle2, 
  Users, 
  Calendar,
  ChevronLeft,
  AlertTriangle,
  ArrowRight,
  Award
} from 'lucide-react';

import { getTeamDashboard } from '../api/dashboard';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import MetricCard from '../components/common/MetricCard';
import ScoreBadge from '../components/common/ScoreBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import DimensionChart from '../components/charts/DimensionChart';
import IssueDistribution from '../components/charts/IssueDistribution';
import { formatScore } from '../utils/formatters';

export default function TeamDetail() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.teamDashboard(teamId || ''),
    queryFn: () => getTeamDashboard(teamId || ''),
    enabled: !!teamId,
  });

  if (isLoading) {
    return <LoadingSkeleton variant="detail" />;
  }

  // Handle 404 or bad team ID
  const is404 = isError && (error as any)?.status === 404;

  if (is404 || !teamId) {
    return (
      <EmptyState
        title="Team Not Found"
        description="The team ID specified does not exist in the active records or has been removed."
        action={
          <button
            onClick={() => navigate('/teams')}
            className="inline-flex items-center text-xs font-semibold text-brand-600 hover:text-brand-700"
          >
            <ChevronLeft className="w-4 h-4 mr-1" /> Back to Teams Index
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

  // Breadcrumbs configuration
  const breadcrumbs = [
    { label: 'Overview', to: '/overview' },
    { label: 'Teams', to: '/teams' },
    { label: data.team_name },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title={`${data.team_name} Dashboard`}
        subtitle={`Organization: ${data.organization_name}`}
        breadcrumbs={breadcrumbs}
        action={
          <button
            onClick={() => navigate('/teams')}
            className="inline-flex items-center justify-center px-3 py-1.5 border border-neutral-200 text-xs font-medium rounded-md text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm focus:outline-none"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back to Teams
          </button>
        }
      />

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Team Score"
          value={data.average_quality_score ? `${formatScore(data.average_quality_score)}%` : '--'}
          icon={TrendingUp}
          supportingText="Average score of calls"
        />
        <MetricCard
          label="Total Calls"
          value={data.total_calls}
          icon={Phone}
          supportingText={`${data.completed_calls} completed, ${data.failed_calls} failed`}
        />
        <MetricCard
          label="Completed Calls"
          value={data.completed_calls}
          icon={CheckCircle2}
          supportingText={`${data.processing_calls} actively processing`}
        />
        <MetricCard
          label="Team Advisors"
          value={data.total_advisors}
          icon={Users}
          supportingText="Assigned advisors in this team"
        />
      </div>

      {/* Leaderboard and breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dimension averages */}
        <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm lg:col-span-2">
          <h3 className="text-sm font-semibold text-neutral-900 mb-4 uppercase tracking-wider">
            Dimension Averages
          </h3>
          <DimensionChart averages={data.average_dimension_scores} />
        </div>

        {/* Issue Tag Distributions */}
        <div className="lg:col-span-1">
          <IssueDistribution issues={data.top_issue_tags} />
        </div>
      </div>

      {/* Leaderboard Section */}
      <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
        <div className="bg-neutral-50 px-5 py-4 border-b border-neutral-200">
          <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
            Advisor Performance Leaderboard
          </h3>
        </div>

        {data.advisor_leaderboard.length === 0 ? (
          <div className="p-8 text-center text-xs text-neutral-400">
            No advisors record calls under this team
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-neutral-200 text-left">
              <thead>
                <tr className="bg-neutral-50 text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                  <th className="px-6 py-3 text-center w-20">Rank</th>
                  <th className="px-6 py-3">Advisor</th>
                  <th className="px-6 py-3 text-center">Completed Calls</th>
                  <th className="px-6 py-3 text-center">Average Score</th>
                  <th className="px-6 py-3 text-center">Critical Issues</th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 text-xs">
                {data.advisor_leaderboard.map((adv, index) => {
                  const rank = index + 1;
                  const isTop3 = rank <= 3;
                  const score = adv.average_score;
                  
                  // Highlight coaching warning if score < 60 or critical issues exist
                  const isCoachingRisk = (score !== null && score < 60) || adv.critical_issue_count > 0;

                  return (
                    <tr 
                      key={adv.advisor_id} 
                      className={`hover:bg-neutral-50 transition-colors ${
                        isCoachingRisk ? 'border-l-4 border-l-red-500' : ''
                      }`}
                    >
                      <td className="px-6 py-4 text-center font-semibold text-neutral-600">
                        {isTop3 ? (
                          <div className="inline-flex items-center gap-0.5 justify-center text-amber-500">
                            <Award className="w-4 h-4 shrink-0" />
                            <span>{rank}</span>
                          </div>
                        ) : (
                          rank
                        )}
                      </td>
                      <td className="px-6 py-4 font-medium text-neutral-900">
                        <div className="flex flex-col">
                          <span>{adv.advisor_name}</span>
                          {isCoachingRisk && (
                            <span className="text-[10px] text-red-500 font-semibold flex items-center mt-0.5">
                              <AlertTriangle className="w-3 h-3 mr-0.5 shrink-0" /> Coaching Attention Needed
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center text-neutral-600">
                        {adv.completed_calls}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <ScoreBadge score={score} size="sm" />
                      </td>
                      <td className="px-6 py-4 text-center font-medium">
                        {adv.critical_issue_count > 0 ? (
                          <span className="text-red-600 font-bold bg-red-50 px-2 py-0.5 rounded border border-red-200">
                            {adv.critical_issue_count} Critical
                          </span>
                        ) : (
                          <span className="text-neutral-400">0</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => navigate(`/advisors/${adv.advisor_id}`)}
                          className="text-xs text-brand-600 hover:text-brand-700 font-semibold hover:underline flex items-center justify-end ml-auto"
                        >
                          Profile <ArrowRight className="w-3.5 h-3.5 ml-1" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

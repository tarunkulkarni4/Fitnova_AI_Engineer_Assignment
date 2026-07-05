import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, PlusCircle, ArrowRight, ShieldAlert } from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { getOrgDashboard } from '../api/dashboard';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import ScoreBadge from '../components/common/ScoreBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';

export default function Teams() {
  const navigate = useNavigate();
  const { selectedOrgId, organizations, selectedTeamId, isLoadingContext } = useAppGlobalContext();
  const [searchTerm, setSearchTerm] = useState('');

  const org = organizations.find((o) => o.id === selectedOrgId);

  // Fetch organization dashboard to get the team performance list
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.orgDashboard(selectedOrgId, undefined, undefined, selectedTeamId || undefined),
    queryFn: () => getOrgDashboard(selectedOrgId, undefined, undefined, selectedTeamId || undefined),
    enabled: !!selectedOrgId,
  });

  if (isLoadingContext) {
    return <LoadingSkeleton variant="cards" />;
  }

  if (!selectedOrgId || organizations.length === 0) {
    return (
      <EmptyState
        title="No Organization Context selected"
        description="Select an organization to load team metrics."
      />
    );
  }

  const performanceList = data?.team_performance || [];

  // Filter list locally based on search
  const filteredTeams = performanceList.filter((team) =>
    team.team_name.toLowerCase().includes(searchTerm.toLowerCase().trim())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Teams Index"
        subtitle={org ? `Showing teams registered under ${org.name}` : ''}
        action={
          <div className="relative">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search teams by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="text-xs border-neutral-200 rounded-md pl-9 pr-4 py-2 w-64 bg-white shadow-sm focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
        }
      />

      {isLoading ? (
        <LoadingSkeleton variant="cards" />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : performanceList.length === 0 ? (
        <EmptyState
          title="No Teams Configured"
          description="There are no teams recorded for the selected organization."
        />
      ) : filteredTeams.length === 0 ? (
        <EmptyState
          title="No Match Found"
          description={`No teams matching name filter "${searchTerm}"`}
          action={
            <button
              onClick={() => setSearchTerm('')}
              className="text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              Clear Search Filter
            </button>
          }
        />
      ) : (
        /* Cards Grid */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTeams.map((team) => {
            const hasData = team.average_score !== null && team.average_score !== undefined;
            return (
              <div
                key={team.team_id}
                onClick={() => navigate(`/teams/${team.team_id}`)}
                className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm hover:shadow-md hover:border-neutral-300 transition-all cursor-pointer flex flex-col justify-between h-44 group"
              >
                <div className="space-y-1">
                  <div className="flex items-start justify-between">
                    <h3 className="text-base font-semibold text-neutral-900 group-hover:text-brand-600 transition-colors">
                      {team.team_name}
                    </h3>
                    <ScoreBadge score={team.average_score} size="sm" />
                  </div>
                  <p className="text-xs text-neutral-500">
                    {team.completed_calls} call records analyzed
                  </p>
                </div>

                <div className="border-t border-neutral-100 pt-3 mt-4 flex items-center justify-between text-xs font-medium text-neutral-500">
                  <span className="text-neutral-400">
                    {hasData 
                      ? team.average_score! >= 75 ? 'Healthy Score' : team.average_score! >= 50 ? 'Needs Attention' : 'Coaching Required'
                      : 'No analytical data'
                    }
                  </span>
                  <span className="inline-flex items-center text-brand-600 font-semibold group-hover:translate-x-1 transition-transform">
                    View Team <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

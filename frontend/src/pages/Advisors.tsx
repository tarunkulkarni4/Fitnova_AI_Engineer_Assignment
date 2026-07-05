import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Users, ChevronLeft, ArrowRight, UserCheck2, UserMinus2 } from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { getAdvisorList } from '../api/dashboard';
import { listTeams } from '../api/lookups';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import ScoreBadge from '../components/common/ScoreBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import Pagination from '../components/common/Pagination';

export default function Advisors() {
  const navigate = useNavigate();
  const { selectedOrgId, organizations, selectedTeamId, setSelectedTeamId, isLoadingContext } = useAppGlobalContext();

  const org = organizations.find((o) => o.id === selectedOrgId);

  // Filters state
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1); // reset to page 1
    }, 400);

    return () => clearTimeout(handler);
  }, [searchInput]);

  // Reset other filters to page 1
  const handleTeamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedTeamId(e.target.value);
    setPage(1);
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setPage(1);
  };

  // Fetch teams for filter dropdown
  const { data: teamsList = [] } = useQuery({
    queryKey: QUERY_KEYS.teamsLookup(selectedOrgId),
    queryFn: () => listTeams(selectedOrgId),
    enabled: !!selectedOrgId,
  });

  // Fetch paginated list
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.advisorList({
      orgId: selectedOrgId,
      teamId: selectedTeamId || undefined,
      search: debouncedSearch || undefined,
      status: statusFilter || undefined,
      page,
      pageSize,
    }),
    queryFn: () =>
      getAdvisorList({
        organization_id: selectedOrgId,
        team_id: selectedTeamId || undefined,
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      }),
    enabled: !!selectedOrgId,
  });

  if (isLoadingContext) {
    return <LoadingSkeleton variant="table" />;
  }

  if (!selectedOrgId || organizations.length === 0) {
    return (
      <EmptyState
        title="No Organization Context Selected"
        description="Select an organization context to view advisor listings."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Advisors Directory"
        subtitle={org ? `Listing active advisors under ${org.name}` : ''}
      />

      {/* Filter Bar */}
      <div className="bg-white border border-neutral-200 rounded-lg p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          {/* Name Search */}
          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by advisor name..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="text-xs border-neutral-200 rounded-md pl-9 pr-4 py-2 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* Team Filter */}
          <div className="flex items-center gap-1.5">
            <Users className="w-4 h-4 text-neutral-400 shrink-0" />
            <select
              value={selectedTeamId}
              onChange={handleTeamChange}
              className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 shadow-sm hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 min-w-[140px]"
            >
              <option value="">All Teams</option>
              {teamsList.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={handleStatusChange}
            className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 shadow-sm hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 min-w-[120px]"
          >
            <option value="">All Statuses</option>
            <option value="Active">Active Only</option>
            <option value="Inactive">Inactive Only</option>
          </select>
        </div>

        {/* Clear Filters Button */}
        {(selectedTeamId || searchInput || statusFilter) && (
          <button
            onClick={() => {
              setSelectedTeamId('');
              setSearchInput('');
              setStatusFilter('');
              setPage(1);
            }}
            className="text-xs font-semibold text-neutral-500 hover:text-neutral-700 transition-colors shrink-0"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Main List */}
      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No Advisors Found"
          description="Try broadening your filters or check that advisor records exist."
        />
      ) : (
        <div className="space-y-4">
          <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200 text-left">
                <thead>
                  <tr className="bg-neutral-50 text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                    <th className="px-6 py-3">Advisor</th>
                    <th className="px-6 py-3">Team</th>
                    <th className="px-6 py-3 text-center">Status</th>
                    <th className="px-6 py-3 text-center">Completed Calls</th>
                    <th className="px-6 py-3 text-center">Avg score</th>
                    <th className="px-6 py-3 text-center">Critical Issues</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 text-xs">
                  {data.items.map((adv) => {
                    const isActive = adv.advisor_status === 'Active';
                    return (
                      <tr key={adv.advisor_id} className="hover:bg-neutral-50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-semibold text-neutral-900">{adv.advisor_name}</span>
                            <span className="text-[10px] text-neutral-400 mt-0.5">{adv.advisor_email}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-neutral-600 font-medium">
                          {adv.team_name}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            isActive
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-neutral-100 text-neutral-500 border-neutral-200'
                          }`}>
                            {isActive ? (
                              <>
                                <UserCheck2 className="w-3 h-3 shrink-0" />
                                <span>Active</span>
                              </>
                            ) : (
                              <>
                                <UserMinus2 className="w-3 h-3 shrink-0" />
                                <span>Inactive</span>
                              </>
                            )}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center text-neutral-600">
                          {adv.completed_calls}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <ScoreBadge score={adv.average_score} size="sm" />
                        </td>
                        <td className="px-6 py-4 text-center">
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
                            View Scorecard <ArrowRight className="w-3.5 h-3.5 ml-1" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls */}
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Search, 
  Phone, 
  Calendar, 
  Clock, 
  TrendingUp, 
  AlertTriangle,
  Filter,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight
} from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { getCallList } from '../api/dashboard';
import { listTeams, listAdvisors, getIssueTaxonomy } from '../api/lookups';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import ScoreBadge from '../components/common/ScoreBadge';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';
import Pagination from '../components/common/Pagination';
import { formatDate, formatDuration, formatScore } from '../utils/formatters';

export default function CallList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedOrgId, organizations, selectedTeamId, setSelectedTeamId } = useAppGlobalContext();

  const org = organizations.find((o) => o.id === selectedOrgId);

  // Parse filters from URL
  const page = Number(searchParams.get('page')) || 1;
  const pageSize = Number(searchParams.get('page_size')) || 20;
  const teamId = selectedTeamId;
  const advisorId = searchParams.get('advisor_id') || '';
  const processingStatus = searchParams.get('processing_status') || '';
  const severity = searchParams.get('severity') || '';
  const issueCategory = searchParams.get('issue_category') || '';
  const minScoreRaw = searchParams.get('min_score');
  const maxScoreRaw = searchParams.get('max_score');
  const minScore = minScoreRaw ? Number(minScoreRaw) : undefined;
  const maxScore = maxScoreRaw ? Number(maxScoreRaw) : undefined;
  const startDate = searchParams.get('start_date') || '';
  const endDate = searchParams.get('end_date') || '';
  const sort = searchParams.get('sort') || 'newest';

  // Helper to update search params
  const updateParams = (newParams: Record<string, string | number | undefined | null>) => {
    const nextParams = new URLSearchParams(searchParams);
    
    // Always reset page to 1 when other filters change, unless page is explicitly updated
    if (!('page' in newParams)) {
      nextParams.set('page', '1');
    }

    Object.entries(newParams).forEach(([key, val]) => {
      if (val === undefined || val === null || val === '') {
        nextParams.delete(key);
      } else {
        nextParams.set(key, String(val));
      }
    });

    setSearchParams(nextParams);
  };

  const prevOrgId = useRef(selectedOrgId);
  // Reset page when context organization changes
  useEffect(() => {
    if (prevOrgId.current && prevOrgId.current !== selectedOrgId) {
      updateParams({
        team_id: '',
        advisor_id: '',
        page: 1,
      });
    }
    prevOrgId.current = selectedOrgId;
  }, [selectedOrgId]);

  // Fetch contextual teams
  const { data: teamsList = [] } = useQuery({
    queryKey: QUERY_KEYS.teamsLookup(selectedOrgId),
    queryFn: () => listTeams(selectedOrgId),
    enabled: !!selectedOrgId,
  });

  // Fetch contextual advisors
  const { data: advisorsList = [] } = useQuery({
    queryKey: QUERY_KEYS.advisorsLookup(teamId || undefined, selectedOrgId),
    queryFn: () => listAdvisors({
      organization_id: selectedOrgId,
      team_id: teamId || undefined,
    }),
    enabled: !!selectedOrgId,
  });

  // Fetch taxonomy categories for filter
  const { data: taxonomy = [] } = useQuery({
    queryKey: [QUERY_KEYS.taxonomy],
    queryFn: getIssueTaxonomy,
  });

  // Fetch call registry
  const {
    data,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: QUERY_KEYS.callList({
      orgId: selectedOrgId,
      teamId: teamId || undefined,
      advisorId: advisorId || undefined,
      status: processingStatus || undefined,
      severity: severity || undefined,
      category: issueCategory || undefined,
      minScore,
      maxScore,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      sort,
      page,
      pageSize,
    }),
    queryFn: () => getCallList({
      organization_id: selectedOrgId,
      team_id: teamId || undefined,
      advisor_id: advisorId || undefined,
      processing_status: processingStatus || undefined,
      severity: severity || undefined,
      issue_category: issueCategory || undefined,
      min_score: minScore,
      max_score: maxScore,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      sort,
      page,
      page_size: pageSize,
    }),
    enabled: !!selectedOrgId,
  });

  const handleResetFilters = () => {
    setSearchParams(new URLSearchParams({
      page: '1',
      page_size: String(pageSize),
      sort: 'newest'
    }));
  };

  if (!selectedOrgId || organizations.length === 0) {
    return (
      <EmptyState
        title="No Organization Selected"
        description="Please select an organization context using the selector in the top bar to view calls."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Call Registry"
        subtitle={org ? `Listing ingested audio calls for ${org.name}` : ''}
        action={
          <div className="flex items-center gap-3">
            <select
              value={sort}
              onChange={(e) => updateParams({ sort: e.target.value })}
              className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 shadow-sm hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 font-semibold"
            >
              <option value="newest">Sort: Newest Uploaded</option>
              <option value="oldest">Sort: Oldest Uploaded</option>
              <option value="highest_score">Sort: Highest Quality Score</option>
              <option value="lowest_score">Sort: Lowest Quality Score</option>
            </select>

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 border border-neutral-200 rounded-md text-neutral-500 hover:text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shrink-0 disabled:opacity-50"
              title="Refresh calls list"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
        }
      />

      {/* Filter Panels */}
      <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold text-neutral-700 uppercase tracking-wider">
          <SlidersHorizontal className="w-4 h-4 text-brand-600" />
          <span>Search and Analysis Filters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {/* Team Filter */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Team</label>
            <select
              value={teamId}
              onChange={(e) => {
                setSelectedTeamId(e.target.value);
                updateParams({ advisor_id: '' });
              }}
              className="text-xs border-neutral-200 rounded-md bg-white py-1.5 px-2.5 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Teams</option>
              {teamsList.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Advisor Filter */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Advisor</label>
            <select
              value={advisorId}
              onChange={(e) => updateParams({ advisor_id: e.target.value })}
              className="text-xs border-neutral-200 rounded-md bg-white py-1.5 px-2.5 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Advisors</option>
              {advisorsList.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Processing Status */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Status</label>
            <select
              value={processingStatus}
              onChange={(e) => updateParams({ processing_status: e.target.value })}
              className="text-xs border-neutral-200 rounded-md bg-white py-1.5 px-2.5 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Statuses</option>
              <option value="Uploaded">Uploaded</option>
              <option value="Processing">Processing</option>
              <option value="Completed">Completed</option>
              <option value="Failed">Failed</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </div>

          {/* Quality Score Range */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Score Range</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                placeholder="Min"
                min="0"
                max="100"
                value={minScoreRaw || ''}
                onChange={(e) => updateParams({ min_score: e.target.value })}
                className="text-xs border-neutral-200 rounded-md py-1 px-2 w-full text-center"
              />
              <span className="text-neutral-400 text-xs">-</span>
              <input
                type="number"
                placeholder="Max"
                min="0"
                max="100"
                value={maxScoreRaw || ''}
                onChange={(e) => updateParams({ max_score: e.target.value })}
                className="text-xs border-neutral-200 rounded-md py-1 px-2 w-full text-center"
              />
            </div>
          </div>

          {/* Severity */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Severity</label>
            <select
              value={severity}
              onChange={(e) => updateParams({ severity: e.target.value })}
              className="text-xs border-neutral-200 rounded-md bg-white py-1.5 px-2.5 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>

          {/* Issue Category */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Issue Category</label>
            <select
              value={issueCategory}
              onChange={(e) => updateParams({ issue_category: e.target.value })}
              className="text-xs border-neutral-200 rounded-md bg-white py-1.5 px-2.5 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 truncate"
            >
              <option value="">All Categories</option>
              {taxonomy.map((item) => (
                <option key={item.category} value={item.category}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range Start */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => updateParams({ start_date: e.target.value })}
              className="text-xs border-neutral-200 rounded-md py-1.5 px-2 w-full"
            />
          </div>

          {/* Date Range End */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-neutral-500 uppercase">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => updateParams({ end_date: e.target.value })}
              className="text-xs border-neutral-200 rounded-md py-1.5 px-2 w-full"
            />
          </div>
        </div>

        {/* Clear Trigger */}
        {(teamId || advisorId || processingStatus || severity || issueCategory || minScoreRaw || maxScoreRaw || startDate || endDate) && (
          <div className="pt-2 border-t border-neutral-100 flex justify-end">
            <button
              onClick={handleResetFilters}
              className="text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* Table Results */}
      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No calls match criteria"
          description="Try relaxing your filters or check that call audio has been uploaded successfully."
        />
      ) : (
        <div className="space-y-4">
          <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200 text-left">
                <thead>
                  <tr className="bg-neutral-50 text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                    <th className="px-6 py-3">Call Registry Details</th>
                    <th className="px-6 py-3">Advisor</th>
                    <th className="px-6 py-3">Team</th>
                    <th className="px-6 py-3 text-center">Status</th>
                    <th className="px-6 py-3 text-center">Score</th>
                    <th className="px-6 py-3 text-center">Detected Issues</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 text-xs">
                  {data.items.map((call) => (
                    <tr
                      key={call.call_id}
                      onClick={() => navigate(`/calls/${call.call_id}`)}
                      className="hover:bg-neutral-50 transition-colors cursor-pointer"
                    >
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-1">
                          <span className="font-semibold text-neutral-900 flex items-center gap-1.5 font-mono">
                            <Phone className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
                            {call.call_id.substring(0, 8)}...
                            {call.is_sales_call === false && (
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase whitespace-nowrap">
                                {call.call_type?.replace('_', ' ')}
                              </span>
                            )}
                          </span>
                          <div className="flex items-center gap-3 text-[10px] text-neutral-400">
                            <span className="flex items-center gap-0.5 whitespace-nowrap">
                              <Calendar className="w-3 h-3 shrink-0" /> {formatDate(call.upload_time)}
                            </span>
                            <span className="flex items-center gap-0.5 whitespace-nowrap">
                              <Clock className="w-3 h-3 shrink-0" /> {formatDuration(call.duration)}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-neutral-800 font-medium whitespace-nowrap">
                        {call.advisor_name}
                      </td>
                      <td className="px-6 py-4 text-neutral-600 whitespace-nowrap">
                        {call.team_name}
                      </td>
                      <td className="px-6 py-4 text-center whitespace-nowrap">
                        <StatusBadge status={call.processing_status} />
                      </td>
                      <td className="px-6 py-4 text-center">
                        {call.is_sales_call === false ? (
                          <span className="text-[9px] font-bold text-neutral-400 uppercase bg-neutral-100 px-1.5 py-0.5 rounded border border-neutral-200">Non-Sales</span>
                        ) : (
                          <ScoreBadge score={call.overall_score} size="sm" />
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {call.is_sales_call === false ? (
                          <span className="text-neutral-400">-</span>
                        ) : call.issue_count > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-red-50 text-red-700 border border-red-150">
                            <AlertTriangle className="w-3 h-3 shrink-0" />
                            {call.issue_count}
                          </span>
                        ) : (
                          <span className="text-neutral-400">0</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline inline-flex items-center justify-end ml-auto">
                          Review <ChevronRight className="w-4 h-4 ml-0.5 shrink-0" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={(p) => updateParams({ page: p })}
            onPageSizeChange={(sz) => updateParams({ page_size: sz, page: 1 })}
          />
        </div>
      )}
    </div>
  );
}


import React, { useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAppGlobalContext } from '../contexts/AppContext';
import { exportFeedbackDataset } from '../api/feedback';
import { ExportRecordItem } from '../types/feedback';
import { QUERY_KEYS } from '../constants/queryKeys';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import PageHeader from '../components/common/PageHeader';

function formatFeedbackMessage(item: ExportRecordItem): React.ReactNode {
  const { feedback_type, original_value, corrected_value } = item;
  try {
    if (feedback_type === 'Score') {
      const dim = corrected_value?.dimension || original_value?.dimension || 'Unknown dimension';
      const origScore = original_value?.score;
      const corrScore = corrected_value?.score;
      return (
        <span>
          <span className="font-semibold text-gray-900 dark:text-white capitalize">{dim.replace('_', ' ')}</span> score corrected from{' '}
          <span className="line-through text-red-500">{origScore}</span> to{' '}
          <span className="text-emerald-500 font-medium">{corrScore}</span>
        </span>
      );
    }
    if (feedback_type === 'Tag') {
      const action = original_value?.action;
      if (action === 'reject') {
        return <span>AI issue tag <span className="font-semibold text-gray-900 dark:text-white">rejected</span></span>;
      }
      if (action === 'add') {
        const cat = corrected_value?.tag?.category || 'Unknown category';
        return <span>Missed issue added: <span className="font-semibold text-gray-900 dark:text-white">{cat}</span></span>;
      }
      if (action === 'correct') {
        const cat = corrected_value?.tag?.category || 'Unknown category';
        return <span>Issue tag corrected to <span className="font-semibold text-gray-900 dark:text-white">{cat}</span></span>;
      }
      return <span>Issue tag modified</span>;
    }
    if (feedback_type === 'Summary') {
      const field = corrected_value?.field || original_value?.field || 'Unknown field';
      return (
        <span>
          <span className="font-semibold text-gray-900 dark:text-white capitalize">{field.replace('_', ' ')}</span> corrected
        </span>
      );
    }
    if (feedback_type === 'Transcript') {
      const segIndex = corrected_value?.segment_index ?? original_value?.segment_index;
      return <span>Transcript segment <span className="font-semibold text-gray-900 dark:text-white">#{segIndex}</span> corrected</span>;
    }
  } catch (e) {
    return <span>Feedback record modified</span>;
  }
  return <span>Feedback record modified</span>;
}

export default function FeedbackActivity() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedTeamId } = useAppGlobalContext();

  const feedbackType = searchParams.get('type') || '';
  const startDate = searchParams.get('startDate') || '';
  const endDate = searchParams.get('endDate') || '';

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: QUERY_KEYS.feedbackExport({ type: feedbackType, teamId: selectedTeamId || undefined, startDate, endDate }),
    queryFn: () => exportFeedbackDataset({
      feedback_type: feedbackType || undefined,
      team_id: selectedTeamId || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
  });

  const updateFilters = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  };

  const clearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  const metrics = useMemo(() => {
    if (!data) return null;
    return {
      total: data.length,
      score: data.filter(d => d.feedback_type === 'Score').length,
      tag: data.filter(d => d.feedback_type === 'Tag').length,
      summary: data.filter(d => d.feedback_type === 'Summary').length,
      transcript: data.filter(d => d.feedback_type === 'Transcript').length,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feedback Activity"
        subtitle="Review and export all human-in-the-loop corrections across the organization."
      />

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" htmlFor="feedback-type-filter">Feedback Type</label>
          <select
            id="feedback-type-filter"
            value={feedbackType}
            onChange={(e) => updateFilters('type', e.target.value)}
            className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">All Types</option>
            <option value="Score">Score</option>
            <option value="Tag">Issue Tag</option>
            <option value="Summary">Summary</option>
            <option value="Transcript">Transcript</option>
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" htmlFor="start-date-filter">Start Date</label>
          <input
            id="start-date-filter"
            type="date"
            value={startDate}
            onChange={(e) => updateFilters('startDate', e.target.value)}
            className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" htmlFor="end-date-filter">End Date</label>
          <input
            id="end-date-filter"
            type="date"
            value={endDate}
            onChange={(e) => updateFilters('endDate', e.target.value)}
            className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>
        {(feedbackType || startDate || endDate) && (
          <button
            onClick={clearFilters}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Clear Filters
          </button>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" />
      ) : isError ? (
        <ErrorState
          title="Failed to load feedback"
          message="An error occurred while fetching feedback activity."
          onRetry={() => refetch()}
        />
      ) : data && data.length === 0 ? (
        <EmptyState
          title="No feedback found"
          description="There are no feedback corrections matching your filters."
          action={
            <button
              onClick={clearFilters}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Clear Filters
            </button>
          }
        />
      ) : (
        <>
          {/* Summary Cards */}
          {metrics && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {[
                { label: 'Total', value: metrics.total },
                { label: 'Score', value: metrics.score },
                { label: 'Tag', value: metrics.tag },
                { label: 'Summary', value: metrics.summary },
                { label: 'Transcript', value: metrics.transcript },
              ].map(m => (
                <div key={m.label} className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="text-sm text-gray-500 dark:text-gray-400">{m.label}</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{m.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* Table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Call</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Type</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Correction Summary</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Comments</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {data?.map((item, i) => (
                    <tr 
                      key={i} 
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/calls/${item.call_id}`)}
                      role="link"
                      tabIndex={0}
                      aria-label={`View call ${item.call_id}`}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          navigate(`/calls/${item.call_id}`);
                        }
                      }}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(item.reviewed_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-indigo-600 dark:text-indigo-400">
                        {item.call_id.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                          {item.feedback_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-md break-words">
                        {formatFeedbackMessage(item)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-sm truncate">
                        {item.comments || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

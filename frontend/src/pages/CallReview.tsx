import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ChevronLeft, Eye, EyeOff, FileText, BarChart3, AlertTriangle,
  MessageSquare, History, User, Calendar, Clock, Globe, Shield,
  Loader2, AlertCircle
} from 'lucide-react';

import { getCallReview } from '../api/dashboard';
import { getFeedbackReviewed, getFeedbackHistory } from '../api/feedback';
import { QUERY_KEYS } from '../constants/queryKeys';
import { formatDate, formatDuration } from '../utils/formatters';

import StatusBadge from '../components/common/StatusBadge';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ErrorState from '../components/common/ErrorState';

import TranscriptViewer from '../components/callreview/TranscriptViewer';
import Scorecard from '../components/callreview/Scorecard';
import IssueList from '../components/callreview/IssueList';
import SummaryPanel from '../components/callreview/SummaryPanel';
import FeedbackHistory from '../components/callreview/FeedbackHistory';

import ScoreCorrectionModal from '../components/review/ScoreCorrectionModal';
import TagRejectModal from '../components/review/TagRejectModal';
import TagCorrectModal from '../components/review/TagCorrectModal';
import TagAddModal from '../components/review/TagAddModal';
import SummaryCorrectionModal from '../components/review/SummaryCorrectionModal';
import TranscriptCorrectionModal from '../components/review/TranscriptCorrectionModal';

import { IssueTagDetail, TranscriptSegment, SummaryCorrectionInput } from '../types/feedback';

type TabKey = 'transcript' | 'scorecard' | 'issues' | 'summary' | 'history';

const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'transcript', label: 'Transcript', icon: <FileText className="w-3.5 h-3.5" /> },
  { key: 'scorecard', label: 'Scorecard', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { key: 'issues', label: 'Issues', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  { key: 'summary', label: 'Summary', icon: <MessageSquare className="w-3.5 h-3.5" /> },
  { key: 'history', label: 'Review History', icon: <History className="w-3.5 h-3.5" /> },
];

export default function CallReview() {
  const { callId } = useParams<{ callId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<TabKey>('transcript');
  const [reviewMode, setReviewMode] = useState(false);

  // Transcript evidence link
  const [highlightedSegmentIndex, setHighlightedSegmentIndex] = useState<number | null>(null);

  // Modal state
  const [scoreModal, setScoreModal] = useState<{ open: boolean; dimension: string; currentValue: number | null }>({
    open: false, dimension: '', currentValue: null
  });
  const [rejectModal, setRejectModal] = useState<{ open: boolean; tagId: string; categoryLabel: string }>({
    open: false, tagId: '', categoryLabel: ''
  });
  const [correctTagModal, setCorrectTagModal] = useState<{ open: boolean; tag: IssueTagDetail | null }>({
    open: false, tag: null
  });
  const [addTagModal, setAddTagModal] = useState(false);
  const [summaryModal, setSummaryModal] = useState<{
    open: boolean; field: SummaryCorrectionInput['field']; currentValue: string
  }>({ open: false, field: 'executive_summary', currentValue: '' });
  const [transcriptModal, setTranscriptModal] = useState<{
    open: boolean; segment: TranscriptSegment | null; index: number
  }>({ open: false, segment: null, index: 0 });

  if (!callId) {
    return <div className="text-xs text-red-600">Invalid call ID.</div>;
  }

  // Query: base call metadata + AI output
  const {
    data: callData,
    isLoading: callLoading,
    isError: callError,
    refetch: refetchCall,
  } = useQuery({
    queryKey: QUERY_KEYS.callReview(callId),
    queryFn: () => getCallReview(callId),
  });

  // Query: feedback reviewed (effective composite view)
  const {
    data: reviewedData,
    isLoading: reviewedLoading,
    refetch: refetchReviewed,
  } = useQuery({
    queryKey: QUERY_KEYS.feedbackReviewed(callId),
    queryFn: () => getFeedbackReviewed(callId),
  });

  // Query: feedback history
  const {
    data: historyData = [],
    refetch: refetchHistory,
  } = useQuery({
    queryKey: QUERY_KEYS.feedbackHistory(callId),
    queryFn: () => getFeedbackHistory(callId),
  });

  // Centralized invalidation after any mutation
  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.feedbackReviewed(callId) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.feedbackHistory(callId) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.callReview(callId) });
  }, [callId, queryClient]);

  // Handle evidence click: switch to transcript tab and highlight segment
  const handleEvidenceClick = useCallback((timestamp: number) => {
    if (!reviewedData) return;
    const segments = reviewedData.effective_transcript;
    // Find segment closest to the timestamp
    let bestIdx = -1;
    let bestDiff = Infinity;
    segments.forEach((seg, idx) => {
      if (timestamp >= seg.start_time && timestamp <= seg.end_time) {
        bestIdx = idx;
        bestDiff = 0;
      } else {
        const diff = Math.min(Math.abs(timestamp - seg.start_time), Math.abs(timestamp - seg.end_time));
        if (diff < bestDiff) {
          bestDiff = diff;
          bestIdx = idx;
        }
      }
    });
    if (bestIdx >= 0) {
      setActiveTab('transcript');
      setHighlightedSegmentIndex(bestIdx);
    }
  }, [reviewedData]);

  const isLoading = callLoading || reviewedLoading;

  if (isLoading) return <LoadingSkeleton variant="detail" />;
  if (callError || !callData) return <ErrorState onRetry={refetchCall} />;

  const meta = callData.metadata;

  // Collect all unique speaker labels from effective transcript (for TranscriptCorrectionModal)
  const existingSpeakers = Array.from(
    new Set((reviewedData?.effective_transcript || []).map(s => s.speaker))
  );

  // Taxonomy labels map built from reviewed data (IssueTagDetail has category)
  const taxonomyLabels: Record<string, string> = {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-3">
            <button
              onClick={() => navigate('/calls')}
              className="inline-flex items-center text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Back to Call Registry
            </button>

            <div className="space-y-1">
              <h1 className="text-lg font-bold text-neutral-900">Call Review</h1>
              <p className="text-xs text-neutral-400 font-mono">{meta.call_id}</p>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-600">
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-neutral-400" />
                <strong>{meta.advisor_name}</strong> · {meta.team_name}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-neutral-400" />
                {formatDate(meta.upload_time)}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-neutral-400" />
                {formatDuration(meta.duration)}
              </span>
              {meta.language && (
                <span className="flex items-center gap-1.5" title="Detected Language">
                  <Globe className="w-3.5 h-3.5 text-neutral-400" />
                  <span className="capitalize">
                    {meta.language.toLowerCase() === 'en' ? 'English' :
                     meta.language.toLowerCase() === 'hi' ? 'Hindi' :
                     meta.language.toLowerCase() === 'kn' ? 'Kannada' :
                     meta.language}
                  </span>
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-neutral-400" />
                {meta.source_type}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <StatusBadge status={meta.processing_status} />
            <button
              onClick={() => setReviewMode(m => !m)}
              className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md border transition-colors ${
                reviewMode
                  ? 'bg-brand-600 text-white border-brand-600 hover:bg-brand-700'
                  : 'bg-white text-neutral-700 border-neutral-200 hover:border-brand-500 hover:text-brand-600'
              }`}
            >
              {reviewMode ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {reviewMode ? 'Exit Review Mode' : 'Enter Review Mode'}
            </button>
          </div>
        </div>
      </div>

      {/* Review Mode Banner */}
      {reviewMode && (
        <div className="bg-brand-50 border border-brand-200 rounded-lg px-5 py-3 text-xs font-semibold text-brand-700 flex items-center gap-2">
          <Eye className="w-4 h-4 shrink-0" />
          Review Mode Active — Correction actions are now visible. Corrections only take effect after form submission.
        </div>
      )}

      {/* Non-Sales Warning Banner */}
      {meta.is_sales_call === false && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-5 shadow-sm space-y-2">
          <h2 className="text-sm font-bold text-amber-800 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            Non-Sales Call Detected ({meta.call_type?.replace('_', ' ')})
          </h2>
          <p className="text-xs text-amber-700">
            <strong>Reason:</strong> {meta.non_sales_reason || 'No reason provided.'}
          </p>
          <p className="text-[11px] text-amber-600">
            This call was automatically classified as a non-sales interaction. Quality scoring and sales issue flags are disabled for this call.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white border border-neutral-200 rounded-lg shadow-sm overflow-hidden">
        <div className="flex border-b border-neutral-200 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-5 py-3.5 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-brand-600 text-brand-600 bg-brand-50/30'
                  : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:bg-neutral-50'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.key === 'issues' && reviewedData && reviewedData.effective_issue_tags.length > 0 && (
                <span className="ml-1 bg-red-100 text-red-700 text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                  {reviewedData.effective_issue_tags.length}
                </span>
              )}
              {tab.key === 'history' && historyData.length > 0 && (
                <span className="ml-1 bg-neutral-100 text-neutral-600 text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                  {historyData.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* TRANSCRIPT TAB */}
          {activeTab === 'transcript' && (
            <TranscriptViewer
              transcript={reviewedData?.effective_transcript || callData.transcript}
              transcriptAvailable={callData.transcript_available}
              reviewMode={reviewMode}
              highlightedIndex={highlightedSegmentIndex}
              onCorrectSegment={(seg, idx) => {
                setTranscriptModal({ open: true, segment: seg, index: idx });
              }}
            />
          )}

          {/* SCORECARD TAB */}
          {activeTab === 'scorecard' && (
            meta.is_sales_call === false ? (
              <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8 text-center text-neutral-500">
                <BarChart3 className="w-8 h-8 text-neutral-455 mx-auto mb-2" />
                <h3 className="text-sm font-bold text-neutral-700">No Scorecard Available</h3>
                <p className="text-xs text-neutral-400 mt-1 max-w-md mx-auto">
                  Sales quality dimensions and performance metrics are not tracked for non-sales calls.
                </p>
              </div>
            ) : (
              <Scorecard
                originalScore={reviewedData?.original_score || callData.score}
                effectiveScore={reviewedData?.effective_score || callData.score}
                reviewMode={reviewMode}
                onCorrectScore={(dimension, currentValue) => {
                  setScoreModal({ open: true, dimension, currentValue });
                }}
              />
            )
          )}

          {/* ISSUES TAB */}
          {activeTab === 'issues' && (
            meta.is_sales_call === false ? (
              <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8 text-center text-neutral-500">
                <AlertTriangle className="w-8 h-8 text-neutral-455 mx-auto mb-2" />
                <h3 className="text-sm font-bold text-neutral-700">No Issues Tracked</h3>
                <p className="text-xs text-neutral-400 mt-1 max-w-md mx-auto">
                  Absence-based sales issues and compliance flags are disabled for non-sales calls.
                </p>
              </div>
            ) : (
              <IssueList
                issues={reviewedData?.effective_issue_tags || callData.issue_tags}
                reviewMode={reviewMode}
                taxonomyLabels={taxonomyLabels}
                onReject={(tagId) => {
                  const tag = (reviewedData?.effective_issue_tags || callData.issue_tags).find(t => t.id === tagId);
                  setRejectModal({ open: true, tagId, categoryLabel: tag?.category || tagId });
                }}
                onCorrect={(tag) => setCorrectTagModal({ open: true, tag })}
                onAddMissedTag={() => setAddTagModal(true)}
                onSelectEvidence={(timestamp) => handleEvidenceClick(timestamp)}
              />
            )
          )}

          {/* SUMMARY TAB */}
          {activeTab === 'summary' && (
            <SummaryPanel
              originalSummary={reviewedData?.original_summary || callData.summary}
              effectiveSummary={reviewedData?.effective_summary || callData.summary}
              reviewMode={reviewMode}
              onCorrectSummary={(field, currentValue) => {
                setSummaryModal({ open: true, field, currentValue });
              }}
            />
          )}

          {/* HISTORY TAB */}
          {activeTab === 'history' && (
            <FeedbackHistory history={historyData} />
          )}
        </div>
      </div>

      {/* === MODALS === */}

      {/* Score Correction */}
      <ScoreCorrectionModal
        isOpen={scoreModal.open}
        onClose={() => setScoreModal(s => ({ ...s, open: false }))}
        callId={callId}
        dimension={scoreModal.dimension}
        currentValue={scoreModal.currentValue}
        onSuccess={invalidateAll}
      />

      {/* Tag Rejection */}
      <TagRejectModal
        isOpen={rejectModal.open}
        onClose={() => setRejectModal(s => ({ ...s, open: false }))}
        callId={callId}
        tagId={rejectModal.tagId}
        categoryLabel={rejectModal.categoryLabel}
        onSuccess={invalidateAll}
      />

      {/* Tag Correction */}
      {correctTagModal.tag && (
        <TagCorrectModal
          isOpen={correctTagModal.open}
          onClose={() => setCorrectTagModal(s => ({ ...s, open: false }))}
          callId={callId}
          tag={correctTagModal.tag}
          onSuccess={invalidateAll}
        />
      )}

      {/* Add Missed Tag */}
      <TagAddModal
        isOpen={addTagModal}
        onClose={() => setAddTagModal(false)}
        callId={callId}
        onSuccess={invalidateAll}
      />

      {/* Summary Correction */}
      <SummaryCorrectionModal
        isOpen={summaryModal.open}
        onClose={() => setSummaryModal(s => ({ ...s, open: false }))}
        callId={callId}
        field={summaryModal.field}
        currentValue={summaryModal.currentValue}
        onSuccess={invalidateAll}
      />

      {/* Transcript Correction */}
      {transcriptModal.segment && (
        <TranscriptCorrectionModal
          isOpen={transcriptModal.open}
          onClose={() => setTranscriptModal(s => ({ ...s, open: false }))}
          callId={callId}
          segment={transcriptModal.segment}
          segmentIndex={transcriptModal.index}
          existingSpeakers={existingSpeakers}
          onSuccess={invalidateAll}
        />
      )}
    </div>
  );
}

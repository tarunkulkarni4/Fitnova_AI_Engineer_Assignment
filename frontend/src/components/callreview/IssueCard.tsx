import React from 'react';
import { Trash2, Edit3, MessageSquare, AlertOctagon, HelpCircle } from 'lucide-react';
import { IssueTagDetail } from '../../types/feedback';
import SeverityBadge from '../common/SeverityBadge';
import { formatTimestamp, formatCategoryLabel } from '../../utils/formatters';

interface IssueCardProps {
  issue: IssueTagDetail;
  reviewMode: boolean;
  onReject?: (tagId: string) => void;
  onCorrect?: (tag: IssueTagDetail) => void;
  onSelectEvidence?: (timestamp: number) => void;
  taxonomyLabels?: Record<string, string>;
}

export default function IssueCard({
  issue,
  reviewMode,
  onReject,
  onCorrect,
  onSelectEvidence,
  taxonomyLabels = {},
}: IssueCardProps) {
  const isAbsence = !issue.quote && !issue.timestamp;
  const tagId = issue.id;

  const displayCategory = taxonomyLabels[issue.category] || formatCategoryLabel(issue.category);

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm space-y-4 hover:shadow-md transition-shadow relative">
      {/* Category & Severity Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-neutral-900 leading-tight">
            {displayCategory}
          </h4>
          <SeverityBadge severity={issue.severity} />
        </div>

        {/* Action Controls in Review Mode */}
        {reviewMode && tagId && (
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={() => onCorrect && onCorrect(issue)}
              className="p-1.5 rounded-md border border-neutral-200 hover:border-brand-500 text-neutral-400 hover:text-brand-600 bg-white hover:bg-brand-50 transition-colors shadow-sm"
              title="Correct issue tag"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onReject && onReject(tagId)}
              className="p-1.5 rounded-md border border-red-100 hover:border-red-500 text-neutral-400 hover:text-red-600 bg-white hover:bg-red-50 transition-colors shadow-sm"
              title="Reject issue tag"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Reason Description */}
      <div className="text-xs text-neutral-600 space-y-1 leading-relaxed select-text">
        <span className="font-semibold text-neutral-800">Reasoning:</span>
        <p className="mt-0.5">{issue.reason || 'No reasoning provided.'}</p>
      </div>

      {/* Evidence Quote / Timestamp Section */}
      {isAbsence ? (
        <div className="bg-neutral-50 rounded-md border border-neutral-100 p-2.5 flex items-center gap-2 text-xs font-semibold text-neutral-500">
          <AlertOctagon className="w-4 h-4 text-neutral-400 shrink-0" />
          <span>Whole-call finding (Absence-based compliance tag)</span>
        </div>
      ) : (
        <div 
          onClick={() => issue.timestamp !== null && issue.timestamp !== undefined && onSelectEvidence && onSelectEvidence(issue.timestamp)}
          className={`border border-neutral-100 rounded-md p-3 text-xs space-y-2 select-text transition-colors ${
            onSelectEvidence && issue.timestamp !== null && issue.timestamp !== undefined
              ? 'bg-neutral-50 hover:bg-brand-50/20 cursor-pointer border-neutral-200' 
              : 'bg-neutral-50'
          }`}
          title={onSelectEvidence && issue.timestamp !== null && issue.timestamp !== undefined ? 'Click to jump to transcript evidence' : undefined}
        >
          <div className="flex items-center justify-between text-[10px] text-neutral-400 font-medium">
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
              <span>Evidence segment at {formatTimestamp(issue.timestamp)}</span>
            </span>
            {issue.speaker && (
              <span className="font-semibold text-neutral-600 uppercase bg-neutral-200 px-1.5 py-0.2 rounded scale-90">
                Speaker: {issue.speaker}
              </span>
            )}
          </div>
          <blockquote className="italic border-l-2 border-brand-500 pl-2 text-neutral-700 font-sans break-words select-text">
            "{issue.quote}"
          </blockquote>
          {issue.confidence !== null && issue.confidence !== undefined && (
            <div className="text-[9px] text-neutral-400 pt-1 text-right">
              Confidence: {Math.round(issue.confidence * 100)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { History, User, Calendar, MessageSquare, ArrowRight } from 'lucide-react';
import { FeedbackResponseItem } from '../../types/feedback';
import { formatDate } from '../../utils/formatters';

interface FeedbackHistoryProps {
  history: FeedbackResponseItem[];
}

export default function FeedbackHistory({ history }: FeedbackHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center text-xs text-neutral-400 font-medium">
        No correction history records found for this call
      </div>
    );
  }

  // Format type labels
  const getActionLabel = (type: string, _original: any, corrected: any) => {
    switch (type) {
      case 'score_correction':
        const dim = corrected?.dimension || 'Score';
        const formattedDim = dim.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
        return `${formattedDim} score changed`;
      case 'tag_rejection':
        return 'AI compliance issue tag rejected';
      case 'tag_correction':
        return 'Compliance issue tag details corrected';
      case 'tag_addition':
        return 'Missed compliance issue tag manually added';
      case 'summary_correction':
        const field = corrected?.field || 'Summary';
        const formattedField = field.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
        return `${formattedField} value corrected`;
      case 'transcript_correction':
        return `Transcript segment #${corrected?.segment_index} corrected`;
      default:
        return type.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
    }
  };

  // Helper to format values safely
  const formatHistoryValue = (val: any) => {
    if (val === null || val === undefined) return 'None';
    if (typeof val === 'object') {
      if ('score' in val) return `${val.score}%`;
      if ('category' in val) return val.category;
      if ('text' in val) return `"${val.text}"`;
      if ('corrected_value' in val) return `"${val.corrected_value}"`;
      return JSON.stringify(val);
    }
    return String(val);
  };

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm space-y-6">
      <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
        <History className="w-5 h-5 text-brand-600" />
        <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
          Manager Feedback and Audit Log
        </h3>
      </div>

      <div className="relative border-l border-neutral-200 ml-3 pl-6 space-y-6 text-xs">
        {history.map((item) => (
          <div key={item.feedback_id} className="relative">
            {/* Timeline bullet */}
            <span className="absolute -left-[30px] top-1 bg-white border border-neutral-300 rounded-full w-4 h-4 flex items-center justify-center">
              <span className="bg-brand-600 rounded-full w-2 h-2" />
            </span>

            <div className="space-y-2 bg-neutral-50/50 p-4 rounded-lg border border-neutral-150">
              {/* Reviewer / Date */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 pb-2">
                <div className="flex items-center gap-1 text-neutral-700 font-semibold">
                  <User className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
                  <span>{item.reviewer_name}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-neutral-400 font-mono">
                  <Calendar className="w-3 h-3 shrink-0" />
                  <span>{formatDate(item.reviewed_at)}</span>
                </div>
              </div>

              {/* Action type */}
              <div>
                <p className="font-bold text-neutral-900">
                  {getActionLabel(item.feedback_type, item.original_value, item.corrected_value)}
                </p>
              </div>

              {/* Original vs corrected details */}
              <div className="flex flex-wrap items-center gap-3 text-neutral-600 mt-1">
                <div className="bg-white px-2.5 py-1 rounded border border-neutral-200">
                  <span className="text-[10px] uppercase font-bold text-neutral-400 block">Before</span>
                  <span className="font-mono mt-0.5 block truncate max-w-xs">{formatHistoryValue(item.original_value)}</span>
                </div>
                <ArrowRight className="w-4 h-4 text-neutral-400 shrink-0" />
                <div className="bg-brand-50/40 border border-brand-100 px-2.5 py-1 rounded">
                  <span className="text-[10px] uppercase font-bold text-brand-500 block">After</span>
                  <span className="font-mono font-semibold text-brand-700 mt-0.5 block truncate max-w-xs">{formatHistoryValue(item.corrected_value)}</span>
                </div>
              </div>

              {/* Comments */}
              {item.comments && (
                <div className="flex items-start gap-1.5 text-neutral-500 bg-white border border-neutral-150 p-2 rounded-md mt-2">
                  <MessageSquare className="w-3.5 h-3.5 text-neutral-400 shrink-0 mt-0.5" />
                  <p className="leading-relaxed italic">"{item.comments}"</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

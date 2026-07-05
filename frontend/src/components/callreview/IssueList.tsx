import React from 'react';
import { PlusCircle, Info, ShieldAlert } from 'lucide-react';
import { IssueTagDetail } from '../../types/feedback';
import IssueCard from './IssueCard';

interface IssueListProps {
  issues: IssueTagDetail[];
  reviewMode: boolean;
  onReject?: (tagId: string) => void;
  onCorrect?: (tag: IssueTagDetail) => void;
  onAddMissedTag?: () => void;
  onSelectEvidence?: (timestamp: number) => void;
  taxonomyLabels?: Record<string, string>;
}

export default function IssueList({
  issues,
  reviewMode,
  onReject,
  onCorrect,
  onAddMissedTag,
  onSelectEvidence,
  taxonomyLabels,
}: IssueListProps) {
  return (
    <div className="space-y-6">
      {/* Top Counter Bar */}
      <div className="bg-neutral-50 border border-neutral-200 rounded-lg px-5 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2">
          <ShieldAlert className={`w-5 h-5 ${issues.length > 0 ? 'text-red-500' : 'text-neutral-400'}`} />
          <div>
            <h4 className="text-xs font-bold text-neutral-900 uppercase tracking-wider">
              Compliance Issue Tags ({issues.length})
            </h4>
            <p className="text-[10px] text-neutral-400">
              {issues.length > 0
                ? 'Review compliance violations and coaching risks identified in analysis.'
                : 'No compliance violations detected.'}
            </p>
          </div>
        </div>

        {/* Add Missed Tag action in Review Mode */}
        {reviewMode && onAddMissedTag && (
          <button
            onClick={onAddMissedTag}
            className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md shadow-sm transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5 mr-1" />
            Add Missed Issue
          </button>
        )}
      </div>

      {/* Grid List */}
      {issues.length === 0 ? (
        <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center flex flex-col items-center justify-center space-y-3">
          <div className="p-3 bg-neutral-50 rounded-full text-neutral-300">
            <Info className="w-6 h-6" />
          </div>
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold text-neutral-900">No issues flagged</h3>
            <p className="text-[10px] text-neutral-400">The advisor followed all compliance rules on this recording.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {issues.map((issue, idx) => (
            <IssueCard
              key={idx}
              issue={issue}
              reviewMode={reviewMode}
              onReject={onReject}
              onCorrect={onCorrect}
              onSelectEvidence={onSelectEvidence}
              taxonomyLabels={taxonomyLabels}
            />
          ))}
        </div>
      )}
    </div>
  );
}

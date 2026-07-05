import React, { useState } from 'react';
import { Edit3, CheckSquare, ChevronDown, ChevronUp, MessageCircle } from 'lucide-react';
import { SummaryDetail } from '../../types/feedback';

interface SummaryPanelProps {
  originalSummary: SummaryDetail | null;
  effectiveSummary: SummaryDetail | null;
  reviewMode: boolean;
  onCorrectSummary?: (field: 'executive_summary' | 'customer_goal' | 'objections' | 'recommended_next_step' | 'sentiment', currentValue: string) => void;
}

export default function SummaryPanel({
  originalSummary,
  effectiveSummary,
  reviewMode,
  onCorrectSummary,
}: SummaryPanelProps) {
  const [expandedFields, setExpandedFields] = useState<Record<string, boolean>>({});

  if (!effectiveSummary) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center text-xs text-neutral-400 font-medium">
        Executive summary details unavailable for this call
      </div>
    );
  }

  const fields = [
    { key: 'executive_summary', label: 'Executive Summary' },
    { key: 'customer_goal', label: 'Customer Goal' },
    { key: 'objections', label: 'Objections Encountered' },
    { key: 'recommended_next_step', label: 'Recommended Next Step' },
    { key: 'sentiment', label: 'Customer Sentiment' }
  ] as const;

  const isCorrected = (key: string) => {
    if (!originalSummary) return false;
    const orig = originalSummary[key as keyof SummaryDetail];
    const eff = effectiveSummary[key as keyof SummaryDetail];
    return orig !== null && eff !== null && orig !== eff;
  };

  const getOriginalVal = (key: string) => {
    return originalSummary ? originalSummary[key as keyof SummaryDetail] : null;
  };

  const toggleExpand = (key: string) => {
    setExpandedFields(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm space-y-6">
      <div className="flex items-center gap-2 border-b border-neutral-100 pb-3">
        <MessageCircle className="w-5 h-5 text-brand-600" />
        <h3 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
          AI-Generated Executive Call Analysis
        </h3>
      </div>

      <div className="space-y-6">
        {fields.map((field) => {
          const effValue = effectiveSummary[field.key] || '--';
          const origValue = getOriginalVal(field.key);
          const hasChanged = isCorrected(field.key);
          const isExpanded = !!expandedFields[field.key];

          return (
            <div key={field.key} className="space-y-2 border-b border-neutral-100 pb-5 last:border-b-0 last:pb-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-neutral-500 uppercase tracking-wider">
                    {field.label}
                  </span>
                  
                  {hasChanged && (
                    <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-brand-600 bg-brand-50 border border-brand-200 px-1.5 py-0.2 rounded">
                      <CheckSquare className="w-2.5 h-2.5 shrink-0" /> Reviewed
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {/* Toggle Comparison if changed */}
                  {hasChanged && (
                    <button
                      onClick={() => toggleExpand(field.key)}
                      className="text-[10px] font-semibold text-neutral-500 hover:text-neutral-700 flex items-center gap-0.5"
                    >
                      {isExpanded ? (
                        <>Hide Original <ChevronUp className="w-3 h-3" /></>
                      ) : (
                        <>Compare AI <ChevronDown className="w-3 h-3" /></>
                      )}
                    </button>
                  )}

                  {/* Correct Action in Review Mode */}
                  {reviewMode && onCorrectSummary && (
                    <button
                      onClick={() => onCorrectSummary(field.key, String(effectiveSummary[field.key] || ''))}
                      className="p-1 rounded border border-neutral-200 hover:border-brand-500 text-neutral-400 hover:text-brand-600 bg-white shadow-sm transition-colors hover:bg-brand-50"
                      title={`Correct ${field.label}`}
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* Collapsible original AI block */}
              {hasChanged && isExpanded && (
                <div className="bg-neutral-50 border border-neutral-200 rounded p-3 text-xs text-neutral-500 space-y-1">
                  <p className="font-bold text-[9px] uppercase tracking-wider text-neutral-400">Original AI Value:</p>
                  <p className="italic leading-relaxed font-sans">"{origValue || '--'}"</p>
                </div>
              )}

              {/* Effective Value */}
              <div className="text-xs font-sans text-neutral-800 leading-relaxed font-medium pl-1 break-words select-text">
                {effValue}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

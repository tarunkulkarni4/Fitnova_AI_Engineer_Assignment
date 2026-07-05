import React from 'react';
import { Edit3, CheckSquare, Info } from 'lucide-react';
import { ScoreDetail } from '../../types/feedback';
import { SCORE_DIMENSIONS } from '../../constants/dimensions';
import ScoreBadge from '../common/ScoreBadge';

interface ScorecardProps {
  originalScore: ScoreDetail | null;
  effectiveScore: ScoreDetail | null;
  reviewMode: boolean;
  onCorrectScore?: (dimension: string, currentValue: number | null) => void;
}

export default function Scorecard({
  originalScore,
  effectiveScore,
  reviewMode,
  onCorrectScore,
}: ScorecardProps) {
  if (!effectiveScore) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center text-xs text-neutral-400 font-medium">
        Scorecard analytics unavailable for this call
      </div>
    );
  }

  // Helper to determine if dimension score has been corrected
  const isCorrected = (key: string) => {
    if (!originalScore) return false;
    const orig = originalScore[key as keyof ScoreDetail];
    const eff = effectiveScore[key as keyof ScoreDetail];
    return orig !== null && eff !== null && orig !== eff;
  };

  const getOriginalVal = (key: string) => {
    return originalScore ? originalScore[key as keyof ScoreDetail] : null;
  };

  return (
    <div className="space-y-6">
      {/* Overall Score Header */}
      <div className="bg-neutral-50 border border-neutral-250 rounded-lg p-5 flex items-center justify-between shadow-sm">
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-neutral-900 uppercase tracking-wider">
            Overall Quality Score
          </h3>
          <p className="text-xs text-neutral-500">
            Weighted quality score derived from analysis dimensions.
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* If overall is corrected */}
          {isCorrected('overall') && (
            <div className="text-right">
              <span className="text-[10px] text-neutral-400 line-through mr-2 font-medium">
                {getOriginalVal('overall')}%
              </span>
              <span className="text-[10px] font-bold text-brand-600 bg-brand-50 border border-brand-200 px-2 py-0.5 rounded mr-1">
                Reviewed
              </span>
            </div>
          )}
          <ScoreBadge score={effectiveScore.overall} size="lg" />
        </div>
      </div>

      {/* Dimensions Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCORE_DIMENSIONS.map((dim) => {
          const effVal = effectiveScore[dim.key as keyof ScoreDetail];
          const origVal = getOriginalVal(dim.key);
          const hasChanged = isCorrected(dim.key);

          return (
            <div
              key={dim.key}
              className={`bg-white border rounded-lg p-4 flex items-center justify-between shadow-sm hover:border-neutral-300 transition-colors ${
                hasChanged ? 'border-brand-200 bg-brand-50/10' : 'border-neutral-200'
              }`}
            >
              <div className="space-y-1.5 min-w-0">
                <span className="text-xs font-semibold text-neutral-800 block truncate">
                  {dim.label}
                </span>
                
                {/* Original comparison if changed */}
                <div className="flex items-center gap-2">
                  {hasChanged && (
                    <span className="text-[10px] text-neutral-400 line-through font-medium">
                      AI: {origVal}%
                    </span>
                  )}
                  {hasChanged && (
                    <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-brand-600 bg-brand-50 border border-brand-200 px-1.5 py-0.2 rounded">
                      <CheckSquare className="w-2.5 h-2.5 shrink-0" /> Reviewed
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <ScoreBadge score={effVal} size="sm" />
                
                {/* Edit Score in Review Mode */}
                {reviewMode && onCorrectScore && (
                  <button
                    onClick={() => onCorrectScore(dim.key, effVal)}
                    className="p-1.5 rounded-md border border-neutral-200 hover:border-brand-500 text-neutral-400 hover:text-brand-600 bg-white shadow-sm transition-colors hover:bg-brand-50"
                    title={`Correct ${dim.label} score`}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

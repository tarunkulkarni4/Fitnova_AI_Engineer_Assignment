import React, { useEffect, useRef, useState } from 'react';
import { Edit3, Check, User } from 'lucide-react';
import { TranscriptSegment } from '../../types/feedback';
import { formatTimestamp } from '../../utils/formatters';

interface TranscriptViewerProps {
  transcript: TranscriptSegment[];
  transcriptAvailable: boolean;
  reviewMode: boolean;
  onCorrectSegment?: (segment: TranscriptSegment, idx: number) => void;
  highlightedIndex?: number | null;
}

export default function TranscriptViewer({
  transcript,
  transcriptAvailable,
  reviewMode,
  onCorrectSegment,
  highlightedIndex: externalHighlightIndex,
}: TranscriptViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [highlightedIdx, setHighlightedIdx] = useState<number | null>(null);

  // Sync external highlight index and scroll into view
  useEffect(() => {
    if (externalHighlightIndex !== null && externalHighlightIndex !== undefined && externalHighlightIndex >= 0) {
      setHighlightedIdx(externalHighlightIndex);
      
      // Scroll to segment element
      const element = document.getElementById(`segment-${externalHighlightIndex}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      // Remove highlight after 2.5s
      const timer = setTimeout(() => {
        setHighlightedIdx(null);
      }, 2500);

      return () => clearTimeout(timer);
    }
  }, [externalHighlightIndex]);

  if (!transcriptAvailable || transcript.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center text-xs text-neutral-400 font-medium">
        Transcript data is unavailable for this call recording
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-4 max-h-[600px] overflow-y-auto pr-2 border border-neutral-100 rounded-lg p-4 bg-neutral-50/50">
      {transcript.map((seg, idx) => {
        const isAdvisor = seg.speaker.toLowerCase() === 'advisor';
        const isCustomer = seg.speaker.toLowerCase() === 'customer';
        const isHighlighted = highlightedIdx === idx;

        let speakerStyles = 'bg-neutral-100 text-neutral-600 border-neutral-200';
        if (isAdvisor) {
          speakerStyles = 'bg-brand-50 text-brand-700 border-brand-200 font-semibold';
        } else if (isCustomer) {
          speakerStyles = 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold';
        }

        return (
          <div
            key={idx}
            id={`segment-${idx}`}
            className={`flex gap-3 p-3 rounded-lg border transition-all duration-300 ${
              isHighlighted
                ? 'bg-brand-100 border-brand-300 ring-2 ring-brand-500 shadow-md'
                : 'bg-white border-neutral-200 hover:border-neutral-350'
            }`}
          >
            {/* Speaker icon / label */}
            <div className="shrink-0 flex flex-col items-center gap-1.5 w-20">
              <span className={`px-2 py-0.5 rounded text-[10px] text-center w-full truncate border ${speakerStyles}`}>
                {seg.speaker}
              </span>
              <span className="text-[9px] font-mono text-neutral-400">
                {formatTimestamp(seg.start_time)}
              </span>
            </div>

            {/* Content text */}
            <div className="flex-1 space-y-1 min-w-0">
              <p className="text-xs text-neutral-800 leading-relaxed font-sans select-text">
                {seg.text}
              </p>
              {seg.confidence !== null && seg.confidence !== undefined && (
                <span className="text-[9px] text-neutral-400">
                  Confidence: {Math.round(seg.confidence * 100)}%
                </span>
              )}
            </div>

            {/* Correction Action in Review Mode */}
            {reviewMode && onCorrectSegment && (
              <button
                onClick={() => onCorrectSegment(seg, idx)}
                className="shrink-0 p-1.5 rounded-md border border-neutral-200 hover:border-brand-500 text-neutral-400 hover:text-brand-600 bg-white shadow-sm transition-colors hover:bg-brand-50 h-8 w-8 flex items-center justify-center"
                title="Correct transcript segment"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

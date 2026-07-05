import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2, AlertCircle, Info } from 'lucide-react';
import Modal from '../common/Modal';
import { correctTranscript } from '../../api/feedback';
import { TranscriptSegment } from '../../types/feedback';
import { formatTimestamp } from '../../utils/formatters';

// Backend-supported speaker values
const FIXED_SPEAKERS = ['Advisor', 'Customer', 'Unknown'];

interface TranscriptCorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  segment: TranscriptSegment;
  segmentIndex: number;
  existingSpeakers: string[]; // neutral SPEAKER_* labels already in transcript
  onSuccess: () => void;
}

export default function TranscriptCorrectionModal({
  isOpen,
  onClose,
  callId,
  segment,
  segmentIndex,
  existingSpeakers,
  onSuccess,
}: TranscriptCorrectionModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [correctedSpeaker, setCorrectedSpeaker] = useState(segment.speaker);
  const [correctedText, setCorrectedText] = useState(segment.text);
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setCorrectedSpeaker(segment.speaker);
    setCorrectedText(segment.text);
  }, [segment]);

  // Build speaker options: fixed + any existing SPEAKER_* labels from this call
  const neutralLabels = existingSpeakers.filter(
    s => s.startsWith('SPEAKER_') && !FIXED_SPEAKERS.includes(s)
  );
  const speakerOptions = [...FIXED_SPEAKERS, ...neutralLabels];

  const mutation = useMutation({
    mutationFn: () => correctTranscript(callId, {
      reviewer_name: reviewerName.trim(),
      segment_index: segmentIndex,
      corrected_speaker: correctedSpeaker,
      corrected_text: correctedText.trim(),
      comments: comments.trim() || null,
    }),
    onSuccess: () => {
      onSuccess();
      onClose();
      setReviewerName(''); setComments(''); setErrorMsg('');
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to submit correction.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    if (!reviewerName.trim()) { setErrorMsg('Reviewer name is required.'); return; }
    if (!correctedText.trim()) { setErrorMsg('Corrected text cannot be empty.'); return; }
    if (!correctedSpeaker) { setErrorMsg('Speaker label is required.'); return; }
    mutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Correct Transcript Segment #${segmentIndex}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Segment context */}
        <div className="bg-neutral-50 border border-neutral-200 rounded-md p-3 space-y-1 text-xs">
          <p className="text-[10px] text-neutral-400 uppercase font-bold">Original Segment at {formatTimestamp(segment.start_time)}</p>
          <p className="text-neutral-500 italic">"{segment.text}"</p>
          <p className="text-[10px] text-neutral-400">Speaker: <span className="font-semibold">{segment.speaker}</span></p>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-md p-3 text-xs flex items-start gap-2">
          <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-amber-700">
            The backend will automatically redact any PII from corrected text before saving. Never enter raw personal data.
          </p>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Reviewer Name *</label>
          <input type="text" required placeholder="E.g., Team Leader Sarah"
            value={reviewerName} onChange={(e) => setReviewerName(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Speaker Label *</label>
          <select value={correctedSpeaker} onChange={(e) => setCorrectedSpeaker(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white focus:ring-1 focus:ring-brand-500">
            {speakerOptions.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <p className="text-[10px] text-neutral-400">
            Only Advisor, Customer, Unknown, or existing neutral SPEAKER_* labels are accepted.
          </p>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Corrected Text *</label>
          <textarea rows={4} placeholder="Corrected redacted transcript text..."
            value={correctedText} onChange={(e) => setCorrectedText(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Comments</label>
          <textarea rows={2} placeholder="Optional context for this correction..."
            value={comments} onChange={(e) => setComments(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
        </div>

        {errorMsg && (
          <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 border-t border-neutral-100 pt-3">
          <button type="button" onClick={onClose} disabled={mutation.isPending}
            className="px-4 py-2 border border-neutral-200 rounded-md text-neutral-700 hover:bg-neutral-50 font-semibold text-xs">
            Cancel
          </button>
          <button type="submit" disabled={mutation.isPending}
            className="px-4 py-2 text-white bg-brand-600 hover:bg-brand-700 rounded-md font-semibold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50">
            {mutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Save Transcript Correction
          </button>
        </div>
      </form>
    </Modal>
  );
}

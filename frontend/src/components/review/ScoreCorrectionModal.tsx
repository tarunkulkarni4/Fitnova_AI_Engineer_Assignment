import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import Modal from '../common/Modal';
import { correctScore } from '../../api/feedback';
import { DIMENSION_LABELS } from '../../constants/dimensions';
import { Loader2, AlertCircle } from 'lucide-react';

interface ScoreCorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  dimension: string;
  currentValue: number | null;
  onSuccess: () => void;
}

export default function ScoreCorrectionModal({
  isOpen,
  onClose,
  callId,
  dimension,
  currentValue,
  onSuccess,
}: ScoreCorrectionModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [scoreInput, setScoreInput] = useState(currentValue !== null ? String(currentValue) : '');
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const mutation = useMutation({
    mutationFn: (input: any) => correctScore(callId, input),
    onSuccess: () => {
      onSuccess();
      onClose();
      setReviewerName('');
      setComments('');
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to submit score correction.');
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!reviewerName.trim()) {
      setErrorMsg('Reviewer name is required.');
      return;
    }

    const val = Number(scoreInput);
    if (isNaN(val) || val < 0 || val > 100) {
      setErrorMsg('Score must be an integer between 0 and 100.');
      return;
    }

    mutation.mutate({
      reviewer_name: reviewerName.trim(),
      dimension: dimension as any,
      corrected_score: Math.round(val),
      comments: comments.trim() || null,
    });
  };

  const label = DIMENSION_LABELS[dimension] || dimension;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Correct ${label} Score`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Reviewer Name */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Reviewer Name *</label>
          <input
            type="text"
            required
            placeholder="E.g., Team Leader Sarah"
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Dimension Label (Read Only) */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Dimension</label>
          <input
            type="text"
            readOnly
            value={label}
            className="text-xs border border-neutral-100 bg-neutral-50 rounded-md py-2 px-3 w-full text-neutral-500 focus:outline-none"
          />
        </div>

        {/* Corrected Score */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Corrected Score (0-100) *</label>
          <input
            type="number"
            required
            min="0"
            max="100"
            value={scoreInput}
            onChange={(e) => setScoreInput(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Comments */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Comments / Notes</label>
          <textarea
            placeholder="Provide context for score adjustment..."
            rows={3}
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {errorMsg && (
          <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 border-t border-neutral-100 pt-3">
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="px-4 py-2 border border-neutral-200 rounded-md text-neutral-700 hover:bg-neutral-50 font-semibold"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 text-white bg-brand-600 hover:bg-brand-700 rounded-md font-semibold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {mutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Submit Score Correction
          </button>
        </div>
      </form>
    </Modal>
  );
}

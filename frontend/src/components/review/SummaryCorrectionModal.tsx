import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2, AlertCircle } from 'lucide-react';
import Modal from '../common/Modal';
import { correctSummary } from '../../api/feedback';
import { SummaryCorrectionInput } from '../../types/feedback';

const SENTIMENT_OPTIONS = ['Positive', 'Neutral', 'Negative', 'Mixed'];

const FIELD_LABELS: Record<string, string> = {
  executive_summary: 'Executive Summary',
  customer_goal: 'Customer Goal',
  objections: 'Objections Encountered',
  recommended_next_step: 'Recommended Next Step',
  sentiment: 'Customer Sentiment',
};

interface SummaryCorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  field: SummaryCorrectionInput['field'];
  currentValue: string;
  onSuccess: () => void;
}

export default function SummaryCorrectionModal({
  isOpen,
  onClose,
  callId,
  field,
  currentValue,
  onSuccess,
}: SummaryCorrectionModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [correctedValue, setCorrectedValue] = useState(currentValue);
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const isSentiment = field === 'sentiment';

  const mutation = useMutation({
    mutationFn: () => correctSummary(callId, {
      reviewer_name: reviewerName.trim(),
      field,
      corrected_value: correctedValue.trim(),
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
    if (!correctedValue.trim()) { setErrorMsg('Corrected value cannot be empty.'); return; }
    mutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Correct ${FIELD_LABELS[field] || field}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Reviewer Name *</label>
          <input type="text" required placeholder="E.g., Team Leader Sarah"
            value={reviewerName} onChange={(e) => setReviewerName(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">
            Corrected Value *
          </label>
          {isSentiment ? (
            <>
              <select value={correctedValue} onChange={(e) => setCorrectedValue(e.target.value)}
                disabled={mutation.isPending}
                className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white focus:ring-1 focus:ring-brand-500">
                <option value="">Select sentiment...</option>
                {SENTIMENT_OPTIONS.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <p className="text-[10px] text-neutral-400">Only backend-supported sentiment values are accepted.</p>
            </>
          ) : (
            <textarea rows={4} placeholder={`Corrected ${FIELD_LABELS[field]}...`}
              value={correctedValue} onChange={(e) => setCorrectedValue(e.target.value)}
              disabled={mutation.isPending}
              className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
          )}
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
            Save Correction
          </button>
        </div>
      </form>
    </Modal>
  );
}

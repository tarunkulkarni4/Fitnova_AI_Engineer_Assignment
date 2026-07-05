import React, { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle } from 'lucide-react';
import Modal from '../common/Modal';
import { correctTag } from '../../api/feedback';
import { getIssueTaxonomy } from '../../api/lookups';
import { IssueTagDetail } from '../../types/feedback';
import { QUERY_KEYS } from '../../constants/queryKeys';

interface TagCorrectModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  tag: IssueTagDetail;
  onSuccess: () => void;
}

export default function TagCorrectModal({
  isOpen,
  onClose,
  callId,
  tag,
  onSuccess,
}: TagCorrectModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [category, setCategory] = useState(tag.category);
  const [timestamp, setTimestamp] = useState(tag.timestamp !== null ? String(tag.timestamp) : '');
  const [quote, setQuote] = useState(tag.quote || '');
  const [reason, setReason] = useState(tag.reason || '');
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Re-initialize when tag changes
  useEffect(() => {
    setCategory(tag.category);
    setTimestamp(tag.timestamp !== null ? String(tag.timestamp) : '');
    setQuote(tag.quote || '');
    setReason(tag.reason || '');
  }, [tag]);

  const { data: taxonomy = [] } = useQuery({
    queryKey: [QUERY_KEYS.taxonomy],
    queryFn: getIssueTaxonomy,
  });

  const selectedTaxItem = taxonomy.find(t => t.category === category);
  const isAbsence = selectedTaxItem?.absence_based ?? false;

  const mutation = useMutation({
    mutationFn: () => correctTag(callId, tag.id!, {
      reviewer_name: reviewerName.trim(),
      category,
      timestamp: isAbsence ? null : (timestamp ? Number(timestamp) : null),
      quote: isAbsence ? null : (quote.trim() || null),
      reason: reason.trim() || null,
      comments: comments.trim() || null,
    }),
    onSuccess: () => {
      onSuccess();
      onClose();
      setReviewerName('');
      setComments('');
      setErrorMsg('');
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to correct tag.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    if (!reviewerName.trim()) {
      setErrorMsg('Reviewer name is required.');
      return;
    }
    if (!category) {
      setErrorMsg('Category is required.');
      return;
    }
    mutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Correct Compliance Issue Tag">
      <form onSubmit={handleSubmit} className="space-y-4">
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

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Category *</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white focus:ring-1 focus:ring-brand-500"
          >
            {taxonomy.map(t => (
              <option key={t.category} value={t.category}>{t.label}</option>
            ))}
          </select>
          <p className="text-[10px] text-neutral-400">Severity is derived from the server-side taxonomy — do not specify it.</p>
        </div>

        {!isAbsence && (
          <>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-600 block">Timestamp (seconds)</label>
              <input
                type="number"
                min="0"
                step="0.1"
                placeholder="e.g., 45.2"
                value={timestamp}
                onChange={(e) => setTimestamp(e.target.value)}
                disabled={mutation.isPending}
                className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-600 block">Evidence Quote</label>
              <textarea
                placeholder="Exact quote from the transcript..."
                rows={2}
                value={quote}
                onChange={(e) => setQuote(e.target.value)}
                disabled={mutation.isPending}
                className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </>
        )}

        {isAbsence && (
          <div className="bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-500">
            This is an absence-based tag — quote and timestamp fields do not apply.
          </div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Correction Reason</label>
          <textarea
            placeholder="Explain the corrected finding..."
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Comments</label>
          <textarea
            placeholder="Optional context for this correction..."
            rows={2}
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

        <div className="flex items-center justify-end gap-2 border-t border-neutral-100 pt-3">
          <button type="button" onClick={onClose} disabled={mutation.isPending}
            className="px-4 py-2 border border-neutral-200 rounded-md text-neutral-700 hover:bg-neutral-50 font-semibold text-xs">
            Cancel
          </button>
          <button type="submit" disabled={mutation.isPending}
            className="px-4 py-2 text-white bg-brand-600 hover:bg-brand-700 rounded-md font-semibold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50">
            {mutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Submit Correction
          </button>
        </div>
      </form>
    </Modal>
  );
}

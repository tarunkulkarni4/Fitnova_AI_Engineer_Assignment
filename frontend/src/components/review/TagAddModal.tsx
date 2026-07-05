import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle, PlusCircle } from 'lucide-react';
import Modal from '../common/Modal';
import { addTag } from '../../api/feedback';
import { getIssueTaxonomy } from '../../api/lookups';
import { QUERY_KEYS } from '../../constants/queryKeys';

interface TagAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  onSuccess: () => void;
}

export default function TagAddModal({ isOpen, onClose, callId, onSuccess }: TagAddModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [category, setCategory] = useState('');
  const [timestamp, setTimestamp] = useState('');
  const [quote, setQuote] = useState('');
  const [reason, setReason] = useState('');
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { data: taxonomy = [] } = useQuery({
    queryKey: [QUERY_KEYS.taxonomy],
    queryFn: getIssueTaxonomy,
  });

  // Determine if selected category is absence-based
  const selectedItem = taxonomy.find(t => t.category === category);
  const isAbsence = selectedItem?.absence_based ?? false;

  const mutation = useMutation({
    mutationFn: () => addTag(callId, {
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
      setReviewerName(''); setCategory(''); setTimestamp('');
      setQuote(''); setReason(''); setComments(''); setErrorMsg('');
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to add tag.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    if (!reviewerName.trim()) { setErrorMsg('Reviewer name is required.'); return; }
    if (!category) { setErrorMsg('Please select an issue category.'); return; }
    mutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Missed Compliance Issue Tag">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-brand-50 border border-brand-200 rounded-md p-3 text-xs flex items-start gap-2">
          <PlusCircle className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
          <p className="text-brand-700">
            Use this to record a compliance issue that the AI analysis missed. Severity is derived server-side from the taxonomy — do not specify it.
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
          <label className="text-xs font-semibold text-neutral-600 block">Issue Category *</label>
          <select value={category} onChange={(e) => { setCategory(e.target.value); setQuote(''); setTimestamp(''); }}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white focus:ring-1 focus:ring-brand-500">
            <option value="">Select a category...</option>
            {taxonomy.map(t => (
              <option key={t.category} value={t.category}>
                {t.label} ({t.severity})
              </option>
            ))}
          </select>
        </div>

        {category && isAbsence && (
          <div className="bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-500">
            <strong>Absence-based tag:</strong> Quote and timestamp fields do not apply — this is a whole-call finding.
          </div>
        )}

        {category && !isAbsence && (
          <>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-600 block">Timestamp (seconds)</label>
              <input type="number" min="0" step="0.1" placeholder="e.g., 45.2"
                value={timestamp} onChange={(e) => setTimestamp(e.target.value)}
                disabled={mutation.isPending}
                className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-600 block">Evidence Quote</label>
              <textarea placeholder="Exact quote from the redacted transcript..." rows={2}
                value={quote} onChange={(e) => setQuote(e.target.value)}
                disabled={mutation.isPending}
                className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
              <p className="text-[10px] text-neutral-400">The backend will verify this quote against the redacted transcript.</p>
            </div>
          </>
        )}

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Reason / Finding</label>
          <textarea placeholder="Describe the compliance concern..." rows={2}
            value={reason} onChange={(e) => setReason(e.target.value)}
            disabled={mutation.isPending}
            className="text-xs border border-neutral-200 rounded-md py-2 px-3 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500" />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-neutral-600 block">Comments</label>
          <textarea placeholder="Optional additional context..." rows={2}
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
          <button type="submit" disabled={mutation.isPending || !category}
            className="px-4 py-2 text-white bg-brand-600 hover:bg-brand-700 rounded-md font-semibold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50">
            {mutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Add Issue Tag
          </button>
        </div>
      </form>
    </Modal>
  );
}

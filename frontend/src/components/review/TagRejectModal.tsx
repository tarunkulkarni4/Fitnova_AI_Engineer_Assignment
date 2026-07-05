import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Loader2, AlertCircle, Trash2 } from 'lucide-react';
import Modal from '../common/Modal';
import { rejectTag } from '../../api/feedback';

interface TagRejectModalProps {
  isOpen: boolean;
  onClose: () => void;
  callId: string;
  tagId: string;
  categoryLabel: string;
  onSuccess: () => void;
}

export default function TagRejectModal({
  isOpen,
  onClose,
  callId,
  tagId,
  categoryLabel,
  onSuccess,
}: TagRejectModalProps) {
  const [reviewerName, setReviewerName] = useState('');
  const [comments, setComments] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const mutation = useMutation({
    mutationFn: () => rejectTag(callId, tagId, {
      reviewer_name: reviewerName.trim(),
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
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to reject tag.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    if (!reviewerName.trim()) {
      setErrorMsg('Reviewer name is required.');
      return;
    }
    mutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Reject Compliance Issue Tag">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-red-50 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
          <Trash2 className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800">Rejecting: "{categoryLabel}"</p>
            <p className="text-red-600 mt-0.5">This tag will be excluded from the effective reviewed view.</p>
          </div>
        </div>

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
          <label className="text-xs font-semibold text-neutral-600 block">Comments / Reason for Rejection</label>
          <textarea
            placeholder="Why is this tag incorrect? (Optional)"
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

        <div className="flex items-center justify-end gap-2 border-t border-neutral-100 pt-3">
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="px-4 py-2 border border-neutral-200 rounded-md text-neutral-700 hover:bg-neutral-50 font-semibold text-xs"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-md font-semibold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {mutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Confirm Rejection
          </button>
        </div>
      </form>
    </Modal>
  );
}

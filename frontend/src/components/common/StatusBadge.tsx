import React from 'react';
import { formatProcessingStatus } from '../../utils/formatters';

interface StatusBadgeProps {
  status: string | null | undefined;
  className?: string;
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  if (!status) {
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-neutral-100 text-neutral-500 border border-neutral-200 ${className}`}>
        Unknown
      </span>
    );
  }

  const label = formatProcessingStatus(status);
  const normalized = status.toLowerCase().replace(/[\s_]+/g, '');

  let badgeStyle = 'bg-neutral-100 text-neutral-600 border-neutral-200';

  if (normalized === 'completed') {
    badgeStyle = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (normalized === 'failed') {
    badgeStyle = 'bg-red-50 text-red-700 border-red-200';
  } else if (normalized === 'cancelled') {
    badgeStyle = 'bg-neutral-100 text-neutral-500 border-neutral-300';
  } else if (normalized === 'uploaded') {
    badgeStyle = 'bg-blue-50 text-blue-700 border-blue-200';
  } else {
    // intermediate processing states
    badgeStyle = 'bg-indigo-50 text-indigo-700 border-indigo-200 animate-pulse';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${badgeStyle} ${className}`}>
      {label}
    </span>
  );
}

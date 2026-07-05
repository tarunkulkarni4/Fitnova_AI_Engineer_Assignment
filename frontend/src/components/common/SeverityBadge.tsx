import React from 'react';

interface SeverityBadgeProps {
  severity: string | null | undefined;
  className?: string;
}

export default function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  if (!severity) return null;

  const normalized = severity.toLowerCase().trim();

  let styles = 'bg-neutral-100 text-neutral-600 border-neutral-200';

  if (normalized === 'critical') {
    styles = 'bg-red-100 text-red-800 border-red-300 font-semibold';
  } else if (normalized === 'high') {
    styles = 'bg-orange-50 text-orange-700 border-orange-200';
  } else if (normalized === 'medium') {
    styles = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (normalized === 'low') {
    styles = 'bg-blue-50 text-blue-700 border-blue-200';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles} ${className}`}>
      {severity}
    </span>
  );
}

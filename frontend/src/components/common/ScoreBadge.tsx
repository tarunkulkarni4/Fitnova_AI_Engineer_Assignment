import React from 'react';

interface ScoreBadgeProps {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function ScoreBadge({
  score,
  size = 'md',
  className = '',
}: ScoreBadgeProps) {
  if (score === null || score === undefined) {
    const sizeClasses = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-sm font-medium',
      lg: 'px-4 py-2 text-base font-bold',
    };
    return (
      <span className={`inline-flex items-center rounded bg-neutral-100 text-neutral-500 border border-neutral-200 ${sizeClasses[size]} ${className}`}>
        No data
      </span>
    );
  }

  const roundedScore = Math.round(score * 100) / 100;
  
  let styles = 'bg-red-50 text-red-700 border-red-200';
  if (roundedScore >= 75) {
    styles = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (roundedScore >= 50) {
    styles = 'bg-amber-50 text-amber-700 border-amber-200';
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs border',
    md: 'px-2.5 py-1 text-sm font-semibold border',
    lg: 'px-4 py-2 text-lg font-bold border-2',
  };

  return (
    <span className={`inline-flex items-center rounded ${styles} ${sizeClasses[size]} ${className}`}>
      {roundedScore}%
    </span>
  );
}

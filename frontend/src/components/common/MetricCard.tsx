import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  icon?: LucideIcon;
  supportingText?: string;
  className?: string;
}

export default function MetricCard({
  label,
  value,
  icon: Icon,
  supportingText,
  className = '',
}: MetricCardProps) {
  const displayValue = value === null || value === undefined ? '--' : value;

  return (
    <div className={`bg-white border border-neutral-200 rounded-lg p-5 shadow-sm flex items-start justify-between ${className}`}>
      <div className="space-y-1 min-w-0">
        <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider block">
          {label}
        </span>
        <span className="text-2xl font-bold text-neutral-900 block truncate">
          {displayValue}
        </span>
        {supportingText && (
          <span className="text-xs text-neutral-500 block truncate">
            {supportingText}
          </span>
        )}
      </div>
      {Icon && (
        <div className="p-2 bg-brand-50 rounded-lg text-brand-600 shrink-0">
          <Icon className="w-5 h-5" />
        </div>
      )}
    </div>
  );
}

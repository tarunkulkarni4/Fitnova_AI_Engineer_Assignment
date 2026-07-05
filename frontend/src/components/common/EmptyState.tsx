import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({
  title = 'No data available',
  description = 'There are no records matching your criteria or scope.',
  action,
}: EmptyStateProps) {
  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-10 text-center flex flex-col items-center justify-center space-y-4">
      <div className="p-3 bg-neutral-50 rounded-full text-neutral-400">
        <Inbox className="w-8 h-8" />
      </div>
      <div className="space-y-1 max-w-sm">
        <h3 className="text-sm font-semibold text-neutral-900">{title}</h3>
        <p className="text-xs text-neutral-500">{description}</p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}

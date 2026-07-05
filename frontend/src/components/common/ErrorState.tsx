import React from 'react';
import { AlertCircle, RefreshCcw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  title = 'Failed to load content',
  message = 'An error occurred while fetching data from the server.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="bg-white border border-red-100 rounded-lg p-8 text-center flex flex-col items-center justify-center space-y-4">
      <div className="p-3 bg-red-50 rounded-full text-red-500">
        <AlertCircle className="w-8 h-8" />
      </div>
      <div className="space-y-1 max-w-md">
        <h3 className="text-sm font-semibold text-neutral-900">{title}</h3>
        <p className="text-xs text-neutral-500">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center justify-center px-3.5 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors shadow-sm focus:ring-1 focus:ring-brand-500"
        >
          <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
          Retry Request
        </button>
      )}
    </div>
  );
}

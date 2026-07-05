import React from 'react';

interface LoadingSkeletonProps {
  variant?: 'dashboard' | 'table' | 'cards' | 'detail';
  rows?: number;
}

export default function LoadingSkeleton({
  variant = 'dashboard',
  rows = 5,
}: LoadingSkeletonProps) {
  const shimmer = 'animate-pulse bg-neutral-200 rounded';

  if (variant === 'dashboard') {
    return (
      <div className="space-y-6 w-full">
        {/* KPI Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white border border-neutral-200 rounded-lg p-5 h-24 flex flex-col justify-between">
              <div className={`h-3 w-20 ${shimmer}`} />
              <div className={`h-6 w-16 ${shimmer}`} />
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white border border-neutral-200 rounded-lg p-5 h-80 flex flex-col justify-between">
            <div className={`h-4 w-32 ${shimmer}`} />
            <div className="flex-1 mt-4 space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className={`h-3 w-16 ${shimmer}`} />
                  <div className={`h-5 flex-1 ${shimmer}`} />
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white border border-neutral-200 rounded-lg p-5 h-80 flex flex-col justify-between">
            <div className={`h-4 w-32 ${shimmer}`} />
            <div className="flex-1 mt-4 flex items-end justify-between gap-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className={`w-12 ${shimmer}`} style={{ height: `${20 + i * 15}%` }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden w-full">
        <div className="p-4 border-b border-neutral-200 flex justify-between">
          <div className={`h-6 w-48 ${shimmer}`} />
          <div className={`h-6 w-24 ${shimmer}`} />
        </div>
        <div className="divide-y divide-neutral-200">
          {[...Array(rows)].map((_, i) => (
            <div key={i} className="p-4 flex items-center justify-between gap-4">
              <div className="space-y-1 flex-1">
                <div className={`h-4 w-1/4 ${shimmer}`} />
                <div className={`h-3 w-1/3 ${shimmer}`} />
              </div>
              <div className={`h-5 w-16 ${shimmer}`} />
              <div className={`h-5 w-24 ${shimmer}`} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (variant === 'cards') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white border border-neutral-200 rounded-lg p-5 h-44 flex flex-col justify-between">
            <div className="space-y-2">
              <div className={`h-4 w-2/3 ${shimmer}`} />
              <div className={`h-3 w-1/2 ${shimmer}`} />
            </div>
            <div className="border-t border-neutral-100 pt-3 flex justify-between">
              <div className={`h-3.5 w-16 ${shimmer}`} />
              <div className={`h-3.5 w-12 ${shimmer}`} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'detail') {
    return (
      <div className="space-y-6 w-full">
        {/* Header summary */}
        <div className="bg-white border border-neutral-200 rounded-lg p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-2">
            <div className={`h-6 w-48 ${shimmer}`} />
            <div className={`h-3 w-32 ${shimmer}`} />
          </div>
          <div className={`h-10 w-24 ${shimmer}`} />
        </div>

        {/* Info grids */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white border border-neutral-200 rounded-lg p-5 h-72" />
            <div className="bg-white border border-neutral-200 rounded-lg p-5 h-96" />
          </div>
          <div className="bg-white border border-neutral-200 rounded-lg p-5 h-[500px]" />
        </div>
      </div>
    );
  }

  return null;
}

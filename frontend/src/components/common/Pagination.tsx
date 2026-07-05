import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
}

export default function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  if (total === 0 || totalPages <= 1) return null;

  const startIdx = (page - 1) * pageSize + 1;
  const endIdx = Math.min(page * pageSize, total);

  return (
    <div className="bg-white px-4 py-3 flex items-center justify-between border border-neutral-200 rounded-lg shadow-sm sm:px-6">
      {/* Mobile view */}
      <div className="flex-1 flex justify-between sm:hidden">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="relative inline-flex items-center px-4 py-2 border border-neutral-200 text-xs font-semibold rounded-md text-neutral-700 bg-white hover:bg-neutral-50 disabled:opacity-50 transition-colors"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="ml-3 relative inline-flex items-center px-4 py-2 border border-neutral-200 text-xs font-semibold rounded-md text-neutral-700 bg-white hover:bg-neutral-50 disabled:opacity-50 transition-colors"
        >
          Next
        </button>
      </div>

      {/* Desktop view */}
      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <p className="text-xs text-neutral-700">
            Showing <span className="font-semibold">{startIdx}</span> to{' '}
            <span className="font-semibold">{endIdx}</span> of{' '}
            <span className="font-semibold">{total}</span> results
          </p>

          {onPageSizeChange && (
            <div className="flex items-center gap-1.5 text-xs text-neutral-700">
              <span>Show</span>
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="border-neutral-200 rounded py-0.5 px-2 bg-white font-semibold text-neutral-700 focus:ring-1 focus:ring-brand-500"
              >
                {[10, 20, 50, 100].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
              <span>per page</span>
            </div>
          )}
        </div>

        <div>
          <nav
            className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
            aria-label="Pagination"
          >
            {/* Prev */}
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-neutral-200 bg-white text-xs font-medium text-neutral-500 hover:bg-neutral-50 disabled:opacity-50 transition-colors"
            >
              <span className="sr-only">Previous</span>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>

            {/* Page numbers */}
            {Array.from({ length: totalPages }, (_, idx) => {
              const p = idx + 1;
              const isCurrent = p === page;
              return (
                <button
                  key={p}
                  onClick={() => onPageChange(p)}
                  aria-current={isCurrent ? 'page' : undefined}
                  className={`relative inline-flex items-center px-4 py-2 border text-xs font-semibold transition-colors ${
                    isCurrent
                      ? 'z-10 bg-brand-600 border-brand-600 text-white'
                      : 'bg-white border-neutral-200 text-neutral-500 hover:bg-neutral-50'
                  }`}
                >
                  {p}
                </button>
              );
            })}

            {/* Next */}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-neutral-200 bg-white text-xs font-medium text-neutral-500 hover:bg-neutral-50 disabled:opacity-50 transition-colors"
            >
              <span className="sr-only">Next</span>
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
}

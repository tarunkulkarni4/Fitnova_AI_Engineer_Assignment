import React from 'react';
import SeverityBadge from '../common/SeverityBadge';
import { formatCategoryLabel } from '../../utils/formatters';
import { IssueTagCount } from '../../types/dashboard';

interface IssueDistributionProps {
  issues: IssueTagCount[] | null | undefined;
}

export default function IssueDistribution({ issues }: IssueDistributionProps) {
  if (!issues || issues.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-neutral-400 font-medium bg-neutral-50 rounded-lg border border-dashed border-neutral-200">
        No issue tags detected in this scope
      </div>
    );
  }

  return (
    <div className="overflow-hidden border border-neutral-200 rounded-lg bg-white shadow-sm">
      <div className="bg-neutral-50 px-4 py-3 border-b border-neutral-200">
        <h3 className="text-xs font-semibold text-neutral-700 uppercase tracking-wider">
          Top Detected Issues
        </h3>
      </div>
      <ul className="divide-y divide-neutral-200 max-h-[300px] overflow-y-auto">
        {issues.map((issue) => (
          <li
            key={issue.category}
            className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50 transition-colors"
          >
            <div className="min-w-0 flex-1 pr-4">
              <span className="text-sm font-medium text-neutral-900 block truncate">
                {formatCategoryLabel(issue.category)}
              </span>
              <SeverityBadge severity={issue.severity} className="mt-1" />
            </div>
            <div className="shrink-0 flex items-center justify-center px-2.5 py-1 bg-neutral-100 rounded-full border border-neutral-200 min-w-8">
              <span className="text-xs font-semibold text-neutral-700">{issue.count}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
}

export default function PageHeader({
  title,
  subtitle,
  action,
  breadcrumbs,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col space-y-2 md:flex-row md:items-center md:justify-between md:space-y-0 pb-2 border-b border-neutral-100">
      <div className="space-y-1.5 min-w-0">
        {/* Breadcrumbs */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center space-x-1.5 text-xs text-neutral-500 font-medium overflow-x-auto whitespace-nowrap pb-1">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight className="w-3 h-3 text-neutral-400 shrink-0" />}
                {crumb.to ? (
                  <Link to={crumb.to} className="hover:text-brand-600 transition-colors">
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-neutral-700 font-semibold truncate">{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        <h2 className="text-xl font-bold text-neutral-900 leading-7 tracking-tight">
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-neutral-500 max-w-2xl truncate">
            {subtitle}
          </p>
        )}
      </div>
      {action && (
        <div className="flex items-center shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}

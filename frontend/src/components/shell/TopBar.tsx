import React from 'react';
import { useLocation } from 'react-router-dom';
import { Building2, Users } from 'lucide-react';
import { useAppGlobalContext } from '../../contexts/AppContext';

export default function TopBar() {
  const location = useLocation();
  const {
    selectedOrgId,
    setSelectedOrgId,
    selectedTeamId,
    setSelectedTeamId,
    organizations,
    teams,
    isLoadingContext,
  } = useAppGlobalContext();

  // Determine current page details
  const getPageMeta = () => {
    const path = location.pathname;
    if (path.startsWith('/overview')) {
      return { title: 'Organization Overview', subtitle: 'Global performance, team metrics, and key issue distributions' };
    }
    if (path.startsWith('/teams')) {
      if (path.match(/\/teams\/.+/)) {
        return { title: 'Team Performance', subtitle: 'Detailed advisor leaderboard, dimensions, and coaching risks' };
      }
      return { title: 'Teams Overview', subtitle: 'Compare team metrics and completed calls' };
    }
    if (path.startsWith('/advisors')) {
      if (path.match(/\/advisors\/.+/)) {
        return { title: 'Advisor Scorecard', subtitle: 'Recent call history, improvement areas, and issue trends' };
      }
      return { title: 'Advisors Directory', subtitle: 'Search and filter advisors across teams' };
    }
    if (path.startsWith('/calls')) {
      if (path.match(/\/calls\/.+/)) {
        return { title: 'Call Intelligence Review', subtitle: 'Deep dive call review, scorecard metrics, transcript, and human corrections' };
      }
      return { title: 'Call Registry', subtitle: 'Advanced search, paginated listing, and processing statuses' };
    }
    if (path.startsWith('/upload')) {
      return { title: 'Ingest Call Ingestion', subtitle: 'Direct browser upload and synchronous call analysis pipeline execution' };
    }
    if (path.startsWith('/feedback')) {
      return { title: 'Review & Feedback Activity', subtitle: 'Chronological manager-led corrections dataset export' };
    }
    return { title: 'FitNova Platform', subtitle: 'AI Sales Intelligence & Quality Assurance' };
  };

  const meta = getPageMeta();

  return (
    <header className="h-16 bg-white border-b border-neutral-200 flex items-center justify-between px-6 sticky top-0 z-30">
      {/* Title & Subtitle */}
      <div className="flex flex-col min-w-0">
        <h1 className="text-lg font-semibold text-neutral-900 truncate">
          {meta.title}
        </h1>
        <p className="text-xs text-neutral-500 truncate hidden sm:block">
          {meta.subtitle}
        </p>
      </div>

      {/* Dev Context Selector */}
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-xs font-semibold text-brand-600 bg-brand-50 px-2 py-1 rounded hidden md:inline">
          DEV CONTEXT
        </span>

        {/* Org Selector */}
        <div className="flex items-center gap-1.5">
          <Building2 className="w-4 h-4 text-neutral-400" />
          <select
            value={selectedOrgId}
            onChange={(e) => setSelectedOrgId(e.target.value)}
            disabled={isLoadingContext}
            className="text-sm font-medium border-neutral-200 rounded-md bg-white py-1 px-2.5 shadow-sm hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 max-w-[160px]"
          >
            {organizations.length === 0 ? (
              <option value="">No Organizations</option>
            ) : (
              organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Team Selector */}
        <div className="flex items-center gap-1.5">
          <Users className="w-4 h-4 text-neutral-400" />
          <select
            value={selectedTeamId}
            onChange={(e) => setSelectedTeamId(e.target.value)}
            disabled={isLoadingContext}
            className="text-sm font-medium border-neutral-200 rounded-md bg-white py-1 px-2.5 shadow-sm hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 max-w-[160px]"
          >
            <option value="">All Teams</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}

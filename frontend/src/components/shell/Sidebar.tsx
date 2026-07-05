import React from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  BarChart3, 
  Users2, 
  UserSquare2, 
  PhoneCall, 
  UploadCloud, 
  History,
  Activity,
  Flame,
  Menu,
  ChevronLeft,
  Webhook
} from 'lucide-react';
import { useAppGlobalContext } from '../../contexts/AppContext';
import { apiClient } from '../../api/client';

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useAppGlobalContext();

  // Periodically check api connection status
  const { data: apiConnected, isError } = useQuery({
    queryKey: ['api-health'],
    queryFn: async () => {
      try {
        await apiClient.get('/health');
        return true;
      } catch {
        return false;
      }
    },
    refetchInterval: 10000,
    initialData: true,
  });

  const links = [
    { to: '/overview', label: 'Overview', icon: BarChart3 },
    { to: '/teams', label: 'Teams', icon: Users2 },
    { to: '/advisors', label: 'Advisors', icon: UserSquare2 },
    { to: '/calls', label: 'Calls', icon: PhoneCall },
    { to: '/upload', label: 'Upload Call', icon: UploadCloud },
    { to: '/simulator', label: 'Telephony Simulator', icon: Webhook },
    { to: '/feedback', label: 'Feedback', icon: History },
  ];

  return (
    <aside 
      className={`fixed inset-y-0 left-0 z-40 bg-white border-r border-neutral-200 flex flex-col justify-between transition-all duration-300 ${
        sidebarOpen ? 'w-64' : 'w-16'
      }`}
    >
      <div>
        {/* Logo / Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-neutral-200">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shrink-0 font-bold">
              F
            </div>
            {sidebarOpen && (
              <span className="font-semibold text-neutral-900 tracking-tight whitespace-nowrap">
                FitNova <span className="text-brand-600 font-medium">Intel</span>
              </span>
            )}
          </div>
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100"
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-600'
                      : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
                  }`
                }
              >
                <Icon className="w-5 h-5 shrink-0" />
                {sidebarOpen && <span className="truncate">{link.label}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-neutral-200 space-y-3 bg-neutral-50">
        {/* Environment Indicator */}
        <div className="flex items-center gap-2 text-xs font-medium text-neutral-500">
          <Flame className="w-4 h-4 text-orange-500 shrink-0" />
          {sidebarOpen ? (
            <div className="flex justify-between w-full">
              <span>Environment</span>
              <span className="text-neutral-900 uppercase">Development</span>
            </div>
          ) : (
            <span className="sr-only">DEV</span>
          )}
        </div>

        {/* API Connection Indicator */}
        <div className="flex items-center gap-2 text-xs font-medium text-neutral-500">
          <Activity className={`w-4 h-4 shrink-0 ${apiConnected && !isError ? 'text-emerald-500' : 'text-red-500'}`} />
          {sidebarOpen ? (
            <div className="flex justify-between w-full">
              <span>API Status</span>
              <span className={apiConnected && !isError ? 'text-emerald-600' : 'text-red-600'}>
                {apiConnected && !isError ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          ) : (
            <span className="sr-only">{apiConnected ? 'OK' : 'ERR'}</span>
          )}
        </div>
      </div>
    </aside>
  );
}

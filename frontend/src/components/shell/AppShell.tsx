import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { useAppGlobalContext } from '../../contexts/AppContext';

export default function AppShell() {
  const { sidebarOpen } = useAppGlobalContext();

  return (
    <div className="min-h-screen bg-neutral-50 flex">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Layout Container */}
      <div 
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${
          sidebarOpen ? 'pl-64' : 'pl-16'
        }`}
      >
        {/* Top Header Bar */}
        <TopBar />

        {/* Dynamic Route Content */}
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

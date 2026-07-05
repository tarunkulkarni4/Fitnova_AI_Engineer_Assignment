import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppContextProvider } from './contexts/AppContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import AppShell from './components/shell/AppShell';
import PageLoader from './components/common/PageLoader';
import Modal from './components/common/Modal';
import { HelpCircle } from 'lucide-react';

// Pages (Lazy Loaded)
const Overview = lazy(() => import('./pages/Overview'));
const Teams = lazy(() => import('./pages/Teams'));
const TeamDetail = lazy(() => import('./pages/TeamDetail'));
const Advisors = lazy(() => import('./pages/Advisors'));
const AdvisorDetail = lazy(() => import('./pages/AdvisorDetail'));
const CallList = lazy(() => import('./pages/CallList'));
const CallReview = lazy(() => import('./pages/CallReview'));
const Upload = lazy(() => import('./pages/Upload'));
const FeedbackActivity = lazy(() => import('./pages/FeedbackActivity'));
const NotFound = lazy(() => import('./pages/NotFound'));

const TelephonySimulator = lazy(() => import('./pages/TelephonySimulator'));

// Setup TanStack Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
  },
});

export default function App() {
  const [isWelcomeOpen, setIsWelcomeOpen] = useState(false);

  useEffect(() => {
    const hasSeenWelcome = sessionStorage.getItem('fitnova_seen_welcome');
    if (!hasSeenWelcome) {
      setIsWelcomeOpen(true);
    }
  }, []);

  const handleCloseWelcome = () => {
    sessionStorage.setItem('fitnova_seen_welcome', 'true');
    setIsWelcomeOpen(false);
  };

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContextProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                {/* Main App Layout */}
                <Route path="/" element={<AppShell />}>
                  <Route index element={<Navigate to="/overview" replace />} />
                  <Route path="overview" element={<Overview />} />
                  <Route path="teams" element={<Teams />} />
                  <Route path="teams/:teamId" element={<TeamDetail />} />
                  <Route path="advisors" element={<Advisors />} />
                  <Route path="advisors/:advisorId" element={<AdvisorDetail />} />
                  <Route path="calls" element={<CallList />} />
                  <Route path="calls/:callId" element={<CallReview />} />
                  <Route path="upload" element={<Upload />} />
                  <Route path="simulator" element={<TelephonySimulator />} />
                  <Route path="feedback" element={<FeedbackActivity />} />
                </Route>

                {/* 404 Route */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
            
            {/* Floating Welcome Re-open Button & Tooltip */}
            <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end space-y-2 pointer-events-none">
              <div className="bg-neutral-900 text-white text-[10px] uppercase tracking-wider font-bold px-2.5 py-1 rounded shadow-md border border-neutral-800 animate-bounce">
                Setup & Docs
              </div>
              <button
                onClick={() => setIsWelcomeOpen(true)}
                className="pointer-events-auto flex items-center justify-center w-12 h-12 rounded-full bg-neutral-900 text-white shadow-xl hover:bg-neutral-800 transition-all hover:scale-105 hover:rotate-6 active:scale-95 duration-200"
                title="Show Welcome Info & Links"
              >
                <HelpCircle className="w-6 h-6" />
              </button>
            </div>

            {/* Welcome Popup Modal */}
            <Modal 
              isOpen={isWelcomeOpen} 
              onClose={handleCloseWelcome} 
              title="Welcome to FitNova Sales Intelligence"
            >
              <div className="space-y-4 py-2">
                <p className="text-sm text-neutral-600 leading-relaxed">
                  An end-to-end AI system that ingests sales calls, transcribes and separates speakers, redacts sensitive information, scores call quality, flags evidence-based sales issues, and surfaces insights across the organization.
                </p>
                
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <a 
                    href="https://github.com/tarunkulkarni4/Fitnova_AI_Engineer_Assignment" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center justify-center p-3 rounded-lg border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 font-medium text-neutral-800 hover:text-neutral-900 transition-colors text-center text-sm shadow-sm"
                  >
                    GitHub & Setup
                  </a>
                  <a 
                    href="https://docs.google.com/document/d/19yiXaM4b5JPch-r9iABw9I6LadRu2QS0U-4TokmLesc/edit?tab=t.0#heading=h.ef4hzle1ivmh" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center justify-center p-3 rounded-lg border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 font-medium text-neutral-800 hover:text-neutral-900 transition-colors text-center text-sm shadow-sm"
                  >
                    How the System Works
                  </a>
                </div>

                <button
                  onClick={handleCloseWelcome}
                  className="w-full mt-4 flex items-center justify-center p-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 font-semibold text-white transition-colors text-sm shadow"
                >
                  Continue to Dashboard
                </button>
              </div>
            </Modal>
          </BrowserRouter>
        </AppContextProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

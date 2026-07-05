import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppContextProvider } from './contexts/AppContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import AppShell from './components/shell/AppShell';
import PageLoader from './components/common/PageLoader';

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
          </BrowserRouter>
        </AppContextProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

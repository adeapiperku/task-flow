// src/App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { MonitoringPage } from './pages/MonitoringPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { Navigation } from './components/Navigation';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <Notifications position="top-right" />
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Navigation />
            <main className="py-6">
              <Routes>
                <Route path="/" element={<MonitoringPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
              </Routes>
            </main>
          </div>
        </Router>
      </MantineProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
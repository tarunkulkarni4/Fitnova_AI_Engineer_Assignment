import '@testing-library/jest-dom';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock;

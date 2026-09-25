import '@testing-library/jest-dom/vitest';

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom doesn't
// implement. A minimal no-op stub is enough for tests — we're not
// asserting on actual pixel dimensions.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// @ts-expect-error -- test-environment polyfill, not a real ResizeObserver
global.ResizeObserver = ResizeObserverStub;

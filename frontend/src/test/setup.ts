import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock ResizeObserver which is used by Recharts but not provided by jsdom
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserver);

// Mock fetch for API calls
vi.stubGlobal('fetch', vi.fn());

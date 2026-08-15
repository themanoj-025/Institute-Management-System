import '@testing-library/jest-dom';
import { vi } from 'vitest';

// localStorage polyfill
// jsdom in Vitest sometimes lacks a working localStorage.
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i) => Object.keys(store)[i] ?? null,
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });

# Global fetch polyfill
// Some components (e.g. Settings.jsx PromotionHistory) call raw fetch()
// instead of the api client. Intercept those calls in tests so they
// don't produce unhandled rejections from relative URLs.
const mockedFetch = vi.fn().mockImplementation((url) => {
  // Return a 200 with empty JSON for any API call
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ data: [] }),
    headers: new Headers({ 'content-type': 'application/json' }),
  });
});

if (typeof globalThis.fetch === 'undefined') {
  globalThis.fetch = mockedFetch;
} else {
  // Wrap the existing fetch (e.g. jsdom's) with our mock for API calls
  const originalFetch = globalThis.fetch;
  globalThis.fetch = vi.fn((url, ...args) => {
    // Let relative API URLs be handled by our mock
    if (typeof url === 'string' && url.startsWith('/')) {
      return mockedFetch(url, ...args);
    }
    return originalFetch(url, ...args);
  });
}

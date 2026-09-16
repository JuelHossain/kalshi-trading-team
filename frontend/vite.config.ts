import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Proxy to the engine.
 *
 * There used to be a `configure` hook here that set Content-Length on any
 * response that arrived without one:
 *
 *     proxyRes.headers['content-length'] =
 *       Buffer.byteLength(proxyRes.body || '', 'utf8').toString();
 *
 * `body` does not exist on an IncomingMessage, so that expression was always
 * `Buffer.byteLength('')` -- zero. It therefore stamped `Content-Length: 0`
 * onto precisely the responses that legitimately have no length: the chunked
 * and streaming ones, including /api/stream, the SSE feed the dashboard reads
 * for every live update. A browser told the body is empty stops reading it.
 *
 * TypeScript would have caught it on the first compile, but @types/react was
 * never installed, so the project's type checking had never run at all.
 *
 * http-proxy forwards bodies without help, so the fix is to stop helping.
 */
const engineProxy = {
  '/api': {
    target: 'http://localhost:3002',
    changeOrigin: true,
    secure: false,
  },
};

export default defineConfig({
  server: { port: 3000, host: '0.0.0.0', proxy: engineProxy, fs: { allow: ['..'] } },
  preview: { port: 3000, host: '0.0.0.0', proxy: engineProxy },
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
});

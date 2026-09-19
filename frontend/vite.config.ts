import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Every engine call goes to /api and is proxied to the engine on :3002,
// including the SSE stream. The engine also mounts its routes under /api/,
// so the same paths work without the proxy in production.
const proxy = {
  '/api': {
    target: 'http://localhost:3002',
    changeOrigin: true,
    secure: false,
  },
};

export default defineConfig({
  server: { port: 3000, host: '0.0.0.0', proxy },
  preview: { port: 3000, host: '0.0.0.0', proxy },
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
});

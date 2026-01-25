import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: 'http://localhost:3002',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
      fs: {
        allow: ['..'], // Allow access to shared folder
      },
    },
    preview: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: 'http://localhost:3002',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    plugins: [react()],
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GROQ_API_KEY': JSON.stringify(env.GROQ_API_KEY),
      'process.env.SUPABASE_URL': JSON.stringify(env.SUPABASE_URL),
      'process.env.SUPABASE_KEY': JSON.stringify(env.SUPABASE_KEY),
      'process.env.KALSHI_DEMO_KEY_ID': JSON.stringify(env.KALSHI_DEMO_KEY_ID),
      'process.env.KALSHI_DEMO_PRIVATE_KEY': JSON.stringify(env.KALSHI_DEMO_PRIVATE_KEY),
      'process.env.KALSHI_PROD_KEY_ID': JSON.stringify(env.KALSHI_PROD_KEY_ID),
      'process.env.KALSHI_PROD_PRIVATE_KEY': JSON.stringify(env.KALSHI_PROD_PRIVATE_KEY),
      'process.env.RAPID_API_KEY': JSON.stringify(env.RAPID_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@shared': path.resolve(__dirname, '../shared'),
      },
    },
  };
});

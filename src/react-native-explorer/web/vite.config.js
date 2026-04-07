import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5100',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:5100',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../ui',
    emptyOutDir: true,
  },
});

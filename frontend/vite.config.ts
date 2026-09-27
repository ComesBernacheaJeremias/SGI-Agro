/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

// En Docker la API es "http://api:8000"; corriendo Vite fuera de Docker, localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [
    react(),
    // App instalable y que abre sin conexión (ADR-006). Los datos los guarda la app (IndexedDB).
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png'],
      manifest: {
        name: 'SGI Agro',
        short_name: 'SGI Agro',
        description: 'Sistema de gestión integral',
        lang: 'es-AR',
        start_url: '/',
        display: 'standalone',
        theme_color: '#2F6B3F',
        background_color: '#ffffff',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,svg,woff2}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
      },
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: true,
    port: 5173,
    // Mismo origen para la API: sin CORS y con la cookie de sesión funcionando.
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
    // Detectar cambios en carpetas montadas desde Windows
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
});

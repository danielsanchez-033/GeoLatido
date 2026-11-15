/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // Rutas relativas: el sitio estático funciona servido desde cualquier carpeta.
  base: './',
  optimizeDeps: {
    // MapLibre 6 carga su worker con una URL relativa a su propio módulo
    // (maplibre-gl-worker.mjs). El preempaquetado de Vite rompe esa ruta y el
    // mapa se queda en blanco con "Worker failed to load" (Atlas).
    exclude: ['maplibre-gl'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})

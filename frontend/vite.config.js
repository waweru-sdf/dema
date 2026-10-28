import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Flask backend serves the built site from `dist/`.
// `npm run dev` runs this dev server and forwards data requests to Flask on port 5000.
export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', assetsDir: 'static', sourcemap: false },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/media': 'http://127.0.0.1:5000',
    },
  },
})

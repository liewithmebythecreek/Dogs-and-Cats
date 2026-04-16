import path from "path"
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // Forward all FastAPI routes to the uvicorn backend
      '/health':  { target: 'http://localhost:8000', changeOrigin: true },
      '/current': { target: 'http://localhost:8000', changeOrigin: true },
      '/forecast':{ target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})


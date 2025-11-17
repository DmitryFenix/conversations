import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Для работы в Docker
    port: 5173,
    watch: {
      usePolling: true, // Для работы в Docker/WSL
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/artifacts': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/sessions': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/jobs': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/upload-mr': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})

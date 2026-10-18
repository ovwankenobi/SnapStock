import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // Forward API and upload requests to the backend so other devices on the
    // LAN only need to reach the Vite port.
    proxy: {
      '/api': 'http://127.0.0.1:6767',
      '/uploads': 'http://127.0.0.1:6767',
    },
  },
})

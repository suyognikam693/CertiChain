import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import url from 'url'
import path from 'path'

const __dirname = url.fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})

import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (/[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/.test(id)) return 'vendor-react';
          if (/[\\/]node_modules[\\/](@radix-ui|cmdk|vaul|input-otp)[\\/]/.test(id)) return 'vendor-ui';
          if (/[\\/]node_modules[\\/](framer-motion|lucide-react)[\\/]/.test(id)) return 'vendor-interaction';
          if (/[\\/]node_modules[\\/](@tanstack|recharts|date-fns)[\\/]/.test(id)) return 'vendor-data';
          if (/[\\/]node_modules[\\/](marked|highlight.js)[\\/]/.test(id)) return 'vendor-markdown';
          return undefined;
        }
      }
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});

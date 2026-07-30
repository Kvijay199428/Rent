import path from "path"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

export default defineConfig({
  base: '/rent/landlord/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@shared": path.resolve(__dirname, "../shared"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
            return 'react-vendor';
          }
          if (id.includes('node_modules/react-router')) {
            return 'router';
          }
          if (id.includes('node_modules/recharts')) {
            return 'charts';
          }
          if (id.includes('node_modules/date-fns') || id.includes('node_modules/lucide-react')) {
            return 'utils';
          }
          if (id.includes('node_modules/@radix-ui') ||
              id.includes('node_modules/class-variance-authority') ||
              id.includes('node_modules/clsx') ||
              id.includes('node_modules/tailwind-merge')) {
            return 'ui-primitives';
          }
        },
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
    chunkSizeWarningLimit: 600,
    target: 'es2022',
    cssCodeSplit: true,
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'recharts',
      'lucide-react',
    ],
  },
})

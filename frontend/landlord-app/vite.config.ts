import path from "path"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

export default defineConfig({
  base: '/landlord/',
  envDir: '../',
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    allowedHosts: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@shared": path.resolve(__dirname, "../shared"),
      react: path.resolve(__dirname, "node_modules/react"),
      "react-dom": path.resolve(__dirname, "node_modules/react-dom"),
      "framer-motion": path.resolve(__dirname, "node_modules/framer-motion"),
      "react-router": path.resolve(__dirname, "node_modules/react-router"),
      "react-phone-number-input": path.resolve(__dirname, "node_modules/react-phone-number-input"),
      "country-flag-icons": path.resolve(__dirname, "node_modules/country-flag-icons"),
      "libphonenumber-js": path.resolve(__dirname, "node_modules/libphonenumber-js"),
      "lucide-react": path.resolve(__dirname, "node_modules/lucide-react"),
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
          if (id.includes('node_modules/framer-motion')) {
            return 'motion';
          }
          if (id.includes('node_modules/react-phone-number-input') ||
              id.includes('node_modules/libphonenumber-js') ||
              id.includes('node_modules/country-flag-icons')) {
            return 'phone';
          }
          if (id.includes('node_modules/react-hook-form') ||
              id.includes('node_modules/@hookform') ||
              id.includes('node_modules/zod')) {
            return 'forms';
          }
          if (id.includes('node_modules/cmdk') ||
              id.includes('node_modules/vaul') ||
              id.includes('node_modules/sonner') ||
              id.includes('node_modules/embla-carousel-react') ||
              id.includes('node_modules/react-day-picker') ||
              id.includes('node_modules/@react-oauth')) {
            return 'overlays';
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
      'react-router',
      'recharts',
      'lucide-react',
    ],
  },
})

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/rent/platform-admin/",
  plugins: [react()],
});


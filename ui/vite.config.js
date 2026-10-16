import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" -> the built dist/ works when opened from any folder or static host.
// Recharts alone is ~500 kB; one chunk is fine for a local dashboard.
export default defineConfig({ plugins: [react()], base: "./", build: { chunkSizeWarningLimit: 900 } });

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" -> the built dist/ works when opened from any folder or static host
export default defineConfig({ plugins: [react()], base: "./" });

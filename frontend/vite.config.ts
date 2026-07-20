import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev: el backend corre en :8000; en producción FastAPI sirve este build (mismo origen).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { outDir: "dist", sourcemap: false },
});

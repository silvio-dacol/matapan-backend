import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Requests stay on the frontend origin so the HTTP-only import cookie is retained.
const target = process.env.MATAPAN_API_TARGET || "http://127.0.0.1:8000";
const proxy = {
  "/api": { target, changeOrigin: true },
  "/health": { target, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
  preview: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
});

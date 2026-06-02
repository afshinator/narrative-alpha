import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendPort = process.env.VITE_BACKEND_PORT ?? "8000";
const port = process.env.PORT ? parseInt(process.env.PORT) : undefined;

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port,
    proxy: {
      "/api": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        proxyTimeout: 900_000,
        timeout: 900_000,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});

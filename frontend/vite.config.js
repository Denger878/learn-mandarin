import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  /* The Python server serves this build; it looks for web/dist. */
  build: {
    outDir: "../web/dist",
    emptyOutDir: true,
  },

  /* `npm run dev` gives hot reload and forwards the API to the Python server. */
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});

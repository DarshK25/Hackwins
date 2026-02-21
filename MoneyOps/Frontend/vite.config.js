import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 3000,
        open: true,
        proxy: {
            // Proxy /api/v1 to AI Gateway (port 8000)
            "/api/v1": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
            // Proxy general /api to Java Backend (port 8080)
            "/api": {
                target: "http://localhost:8080",
                changeOrigin: true,
            },
        },
    },
});

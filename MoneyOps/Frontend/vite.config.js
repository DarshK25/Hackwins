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
            // Proxy /api/v1 to AI Gateway (port 8001)
            "/api/v1": {
                target: "http://localhost:8001",
                changeOrigin: true,
            },
            // Proxy general /api to Spring Boot Backend (port 8000)
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
});

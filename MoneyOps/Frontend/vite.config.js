import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, path.resolve(__dirname, "../"), "");
    const backendTarget = env.VITE_BACKEND_PROXY_TARGET || "http://127.0.0.1:8002";
    const gatewayTarget = env.VITE_GATEWAY_PROXY_TARGET || "http://127.0.0.1:8001";

    return {
        envDir: "../",
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
                // Compatibility route for older compliance UI calls.
                "/api/v1/compliance/status": {
                    target: backendTarget,
                    changeOrigin: true,
                    rewrite: (requestPath) =>
                        requestPath.replace("/api/v1/compliance/status", "/api/compliance/status"),
                },
                // Proxy /api/v1 to AI Gateway (port 8001 by default)
                "/api/v1": {
                    target: gatewayTarget,
                    changeOrigin: true,
                },
                // Proxy general /api to Spring Boot Backend (port 8002 by default)
                "/api": {
                    target: backendTarget,
                    changeOrigin: true,
                },
            },
        },
    };
});

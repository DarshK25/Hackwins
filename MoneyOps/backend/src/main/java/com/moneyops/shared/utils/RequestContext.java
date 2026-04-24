// src/main/java/com/moneyops/shared/utils/RequestContext.java
package com.moneyops.shared.utils;

/**
 * Thread-local holder for HTTP request metadata (IP address, User-Agent).
 * Populated by the JwtFilter on every request, consumed by AuditLogService
 * to enrich audit log entries.
 */
public class RequestContext {

    private static final ThreadLocal<String> ipAddress = new ThreadLocal<>();
    private static final ThreadLocal<String> userAgent = new ThreadLocal<>();

    public static void setIpAddress(String ip) {
        ipAddress.set(ip);
    }

    public static String getIpAddress() {
        return ipAddress.get();
    }

    public static void setUserAgent(String ua) {
        userAgent.set(ua);
    }

    public static String getUserAgent() {
        return userAgent.get();
    }

    /**
     * Resolve the real client IP, respecting reverse-proxy headers.
     * Priority: X-Forwarded-For → X-Real-IP → request.getRemoteAddr()
     */
    public static String resolveIp(jakarta.servlet.http.HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip != null && !ip.isBlank()) {
            // X-Forwarded-For may contain a chain: "client, proxy1, proxy2"
            ip = ip.split(",")[0].trim();
        }
        if (ip == null || ip.isBlank()) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isBlank()) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }

    public static void clear() {
        ipAddress.remove();
        userAgent.remove();
    }
}

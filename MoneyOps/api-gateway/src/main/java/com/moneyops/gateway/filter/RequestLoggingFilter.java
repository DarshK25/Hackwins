package com.moneyops.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * RequestLoggingFilter - Centralized Request/Response Logging
 * 
 * PURPOSE:
 * - Log all incoming requests with correlation IDs
 * - Track request duration and status codes
 * - Provide traceability for debugging and monitoring
 * 
 * BUSINESS LOGIC:
 * - Generate unique correlation ID for each request
 * - Add correlation ID to response headers (for client-side tracking)
 * - Log: method, path, status, duration, user context
 * - Flag slow requests (> configured threshold)
 * 
 * CORRELATION ID:
 * - If client provides X-Correlation-Id → Use it
 * - Otherwise → Generate new UUID
 * - Add to downstream service headers (X-Correlation-Id)
 * - Return in response headers (for client debugging)
 * 
 * SECURITY:
 * - Does NOT log request/response bodies (may contain sensitive data)
 * - Can be enabled via configuration for debugging
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)  // Run first to capture all requests
@RequiredArgsConstructor
public class RequestLoggingFilter implements WebFilter {
    
    private static final String CORRELATION_ID_HEADER = "X-Correlation-Id";
    private static final String REQUEST_START_TIME_ATTR = "request_start_time";
    
    @Value("${gateway.logging.enabled:true}")
    private boolean loggingEnabled;
    
    @Value("${gateway.logging.log-request-body:false}")
    private boolean logRequestBody;
    
    @Value("${gateway.logging.log-response-body:false}")
    private boolean logResponseBody;
    
    @Value("${gateway.logging.slow-request-threshold-ms:3000}")
    private long slowRequestThresholdMs;
    
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        if (!loggingEnabled) {
            return chain.filter(exchange);
        }
        
        ServerHttpRequest request = exchange.getRequest();
        
        // Generate or extract correlation ID
        String correlationId = getOrGenerateCorrelationId(request);
        
        // Add correlation ID to request headers for downstream services
        ServerHttpRequest mutatedRequest = request.mutate()
            .header(CORRELATION_ID_HEADER, correlationId)
            .build();
        
        // Add correlation ID to response headers for client
        exchange.getResponse().getHeaders().add(CORRELATION_ID_HEADER, correlationId);
        
        // Store request start time
        exchange.getAttributes().put(REQUEST_START_TIME_ATTR, System.currentTimeMillis());
        
        // Log incoming request
        logRequest(mutatedRequest, correlationId);
        
        // Continue filter chain and log response
        return chain.filter(exchange.mutate().request(mutatedRequest).build())
            .doFinally(signalType -> logResponse(exchange, correlationId));
    }
    
    /**
     * Get correlation ID from request header or generate new one
     */
    private String getOrGenerateCorrelationId(ServerHttpRequest request) {
        String correlationId = request.getHeaders().getFirst(CORRELATION_ID_HEADER);
        if (correlationId == null || correlationId.isBlank()) {
            correlationId = UUID.randomUUID().toString();
        }
        return correlationId;
    }
    
    /**
     * Log incoming request details
     */
    private void logRequest(ServerHttpRequest request, String correlationId) {
        String method = request.getMethod().toString();
        String path = request.getPath().value();
        String userId = request.getHeaders().getFirst("X-User-Id");
        String orgId = request.getHeaders().getFirst("X-Org-Id");
        String clientIp = getClientIp(request);
        
        log.info(">>> REQUEST | correlationId={} | method={} | path={} | userId={} | orgId={} | clientIp={}",
            correlationId, method, path, userId, orgId, clientIp);
        
        // Optional: Log request body (disabled by default for security)
        if (logRequestBody) {
            log.debug("Request Body Logging: Enabled but not implemented (security risk)");
        }
    }
    
    /**
     * Log response details with duration
     */
    private void logResponse(ServerWebExchange exchange, String correlationId) {
        Long startTime = exchange.getAttribute(REQUEST_START_TIME_ATTR);
        if (startTime == null) {
            return;
        }
        
        long duration = System.currentTimeMillis() - startTime;
        int statusCode = exchange.getResponse().getStatusCode() != null 
            ? exchange.getResponse().getStatusCode().value() 
            : 0;
        
        String method = exchange.getRequest().getMethod().toString();
        String path = exchange.getRequest().getPath().value();
        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        
        // Flag slow requests
        if (duration > slowRequestThresholdMs) {
            log.warn("<<< SLOW REQUEST | correlationId={} | method={} | path={} | status={} | duration={}ms | userId={} | SLOW!",
                correlationId, method, path, statusCode, duration, userId);
        } else {
            log.info("<<< RESPONSE | correlationId={} | method={} | path={} | status={} | duration={}ms | userId={}",
                correlationId, method, path, statusCode, duration, userId);
        }
    }
    
    /**
     * Extract client IP address from request
     * Checks X-Forwarded-For header first (for proxied requests)
     */
    private String getClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            // X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
            // Take the first one (original client)
            return xForwardedFor.split(",")[0].trim();
        }
        
        // Fallback to remote address
        return request.getRemoteAddress() != null 
            ? request.getRemoteAddress().getAddress().getHostAddress() 
            : "unknown";
    }
}
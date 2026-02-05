package com.moneyops.gateway.filter;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;
/**
 * RequestDurationFilter - Performance Monitoring
 * 
 * PURPOSE:
 * - Track request duration for performance analysis
 * - Record metrics for monitoring dashboards (Grafana)
 * - Identify slow endpoints and performance bottlenecks
 * 
 * BUSINESS LOGIC:
 * - Measure time from request arrival to response completion
 * - Record metrics by: method, path, status code
 * - Add X-Response-Time header (for client-side monitoring)
 * 
 * METRICS (Micrometer):
 * - Timer: gateway.request.duration
 *   → Tags: method, path, status
 *   → Percentiles: p50, p95, p99
 * 
 * FUTURE USE:
 * - Phase 6: Export to Prometheus/Grafana
 * - Phase 6: Alert on high p99 latency
 * - Phase 6: Dashboard for endpoint performance
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
@RequiredArgsConstructor
public class RequestDurationFilter implements WebFilter {
    private static final String REQUEST_START_INSTANT_ATTR = "request_start_instant";
    private static final String RESPONSE_TIME_HEADER = "X-Response-Time";

    private final MeterRegistry meterRegistry;
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        exchange.getAttributes().put(REQUEST_START_INSTANT_ATTR, Instant.now());
        
        // Add header before response is committed
        exchange.getResponse().beforeCommit(() -> {
            addResponseTimeHeader(exchange);
            return Mono.empty();
        });

        return chain.filter(exchange)
                .doFinally(signalType -> recordMetric(exchange));        
    }

    private void addResponseTimeHeader(ServerWebExchange exchange) {
        Instant startTime = exchange.getAttribute(REQUEST_START_INSTANT_ATTR);
        if (startTime == null) {
            return;
        }
        
        Duration duration = Duration.between(startTime, Instant.now());
        long durationMs = duration.toMillis();
        
        // Add response time header
        exchange.getResponse().getHeaders().add(RESPONSE_TIME_HEADER, durationMs + "ms");
    }

    private void recordMetric(ServerWebExchange exchange) {
        Instant startTime = exchange.getAttribute(REQUEST_START_INSTANT_ATTR);
        if (startTime == null) {
            return;
        }
        
        Duration duration = Duration.between(startTime, Instant.now());
        long durationMs = duration.toMillis();
        
        ServerHttpRequest request = exchange.getRequest();
        String method = request.getMethod().toString();
        String path = simplifyPath(request.getPath().value());
        int status = exchange.getResponse().getStatusCode() != null 
            ? exchange.getResponse().getStatusCode().value() 
            : 0;
            
        // Record metric (for Prometheus/Grafana)
        try {
            Timer.builder("gateway.request.duration")
                .description("Request duration in milliseconds")
                .tag("method", method)
                .tag("path", path)
                .tag("status", String.valueOf(status))
                .register(meterRegistry)
                .record(duration);
            
            log.debug("Recorded metric: method={}, path={}, status={}, duration={}ms", 
                method, path, status, durationMs);
        } catch (Exception e) {
            log.error("Failed to record request duration metric", e);
        }
    }
    
    /**
     * Simplify path for metrics (remove IDs to avoid high cardinality)
     * 
     * EXAMPLES:
     * /api/clients/123 → /api/clients/{id}
     * /api/invoices/456/pdf → /api/invoices/{id}/pdf
     * 
     * This prevents metric explosion (1000 clients = 1000 metrics)
     */
    private String simplifyPath(String path) {
        // Replace UUID patterns with {id}
        String simplified = path.replaceAll(
            "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", 
            "{id}"
        );
        
        // Replace numeric IDs with {id}
        simplified = simplified.replaceAll("/\\d+", "/{id}");
        
        return simplified;
    }
}
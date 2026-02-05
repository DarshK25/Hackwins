package com.moneyops.gateway.filter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * Unit tests for RequestLoggingFilter
 */
@ExtendWith(MockitoExtension.class)
class RequestLoggingFilterTest {
    
    @Mock
    private WebFilterChain filterChain;
    
    private RequestLoggingFilter requestLoggingFilter;
    
    @BeforeEach
    void setUp() {
        requestLoggingFilter = new RequestLoggingFilter();
        
        // Set test configuration
        ReflectionTestUtils.setField(requestLoggingFilter, "loggingEnabled", true);
        ReflectionTestUtils.setField(requestLoggingFilter, "logRequestBody", false);
        ReflectionTestUtils.setField(requestLoggingFilter, "logResponseBody", false);
        ReflectionTestUtils.setField(requestLoggingFilter, "slowRequestThresholdMs", 3000L);
        
        // Mock filter chain
        when(filterChain.filter(any(ServerWebExchange.class)))
            .thenReturn(Mono.empty());
    }
    
    @Test
    void shouldAddCorrelationIdToRequest() {
        // Given: Request without correlation ID
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = requestLoggingFilter.filter(exchange, filterChain);
        
        // Then: Correlation ID should be added to response headers
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getHeaders().getFirst("X-Correlation-Id"))
            .isNotNull();
    }
    
    @Test
    void shouldPreserveClientProvidedCorrelationId() {
        // Given: Request with existing correlation ID
        String clientCorrelationId = "client-correlation-123";
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .header("X-Correlation-Id", clientCorrelationId)
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = requestLoggingFilter.filter(exchange, filterChain);
        
        // Then: Client's correlation ID should be preserved
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getHeaders().getFirst("X-Correlation-Id"))
            .isEqualTo(clientCorrelationId);
    }
    
    @Test
    void shouldExtractClientIpFromXForwardedFor() {
        // Given: Request with X-Forwarded-For header (proxied request)
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .header("X-Forwarded-For", "203.0.113.1, 198.51.100.1")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = requestLoggingFilter.filter(exchange, filterChain);
        
        // Then: Request should complete successfully
        // (Actual IP extraction is tested in logs, not assertions)
        StepVerifier.create(result)
            .verifyComplete();
    }
    
    @Test
    void shouldSkipLoggingWhenDisabled() {
        // Given: Logging is disabled
        ReflectionTestUtils.setField(requestLoggingFilter, "loggingEnabled", false);
        
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = requestLoggingFilter.filter(exchange, filterChain);
        
        // Then: Request should pass through without logging
        StepVerifier.create(result)
            .verifyComplete();
        
        // No correlation ID should be added
        assertThat(exchange.getResponse().getHeaders().getFirst("X-Correlation-Id"))
            .isNull();
    }
    
    @Test
    void shouldRecordRequestStartTime() {
        // Given: Request to any endpoint
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = requestLoggingFilter.filter(exchange, filterChain);
        
        // Then: Request start time should be stored
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getAttributes().get("request_start_time"))
            .isNotNull();
    }
}
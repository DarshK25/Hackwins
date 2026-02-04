package com.moneyops.gateway.filter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.util.Arrays;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * Unit tests for TenantContextFilter
 */
@ExtendWith(MockitoExtension.class)
class TenantContextFilterTest {
    
    @Mock
    private WebFilterChain filterChain;
    
    private TenantContextFilter tenantContextFilter;
    
    @BeforeEach
    void setUp() {
        tenantContextFilter = new TenantContextFilter();
        
        // Set test configuration
        ReflectionTestUtils.setField(tenantContextFilter, "enforceTenantIsolation", true);
        ReflectionTestUtils.setField(tenantContextFilter, "tenantRequiredPaths", 
            Arrays.asList("/api/clients/**", "/api/invoices/**", "/api/transactions/**"));
        
        // Mock filter chain to complete successfully
        lenient().when(filterChain.filter(any(ServerWebExchange.class)))
            .thenReturn(Mono.empty());
    }
    
    @Test
    void shouldAllowRequestWithValidOrgId() {
        // Given: Request to tenant-required path with valid X-Org-Id
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .header("X-Org-Id", "org-123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = tenantContextFilter.filter(exchange, filterChain);
        
        // Then: Request should pass through
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();  // No error
    }
    
    @Test
    void shouldRejectRequestWithMissingOrgId() {
        // Given: Request to tenant-required path WITHOUT X-Org-Id
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = tenantContextFilter.filter(exchange, filterChain);
        
        // Then: Request should be rejected with 403
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
    }
    
    @Test
    void shouldAllowNonTenantPath() {
        // Given: Request to non-tenant path (e.g., user profile)
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/users/profile")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = tenantContextFilter.filter(exchange, filterChain);
        
        // Then: Request should pass through (no org ID required)
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }
    
    @Test
    void shouldAllowWhenTenantIsolationDisabled() {
        // Given: Tenant isolation is disabled
        ReflectionTestUtils.setField(tenantContextFilter, "enforceTenantIsolation", false);
        
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/clients/123")
            .build();  // No X-Org-Id header
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = tenantContextFilter.filter(exchange, filterChain);
        
        // Then: Request should pass through (isolation disabled)
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }
    
    @Test
    void shouldMatchWildcardPaths() {
        // Given: Request to nested tenant path
        MockServerHttpRequest request = MockServerHttpRequest
            .get("/api/invoices/123/pdf")
            .header("X-Org-Id", "org-123")
            .build();
        
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = tenantContextFilter.filter(exchange, filterChain);
        
        // Then: Request should pass through
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }
}
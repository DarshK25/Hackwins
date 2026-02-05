package com.moneyops.gateway.config;

import com.moneyops.gateway.filter.AuthenticationFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.SecurityWebFiltersOrder;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * SecurityConfig - Gateway Security Configuration
 * 
 * PURPOSE:
 * - Configure Spring Security for API Gateway
 * - Enable CORS for frontend access
 * - Integrate custom AuthenticationFilter
 * 
 * SECURITY MODEL:
 * - Public endpoints: /api/auth/login, /api/auth/register, /actuator/health
 * - Protected endpoints: All others (require valid JWT)
 * - JWT validation happens in AuthenticationFilter
 * 
 * CORS:
 * - Allow specific origins (configure for production)
 * - Allow credentials (cookies, auth headers)
 * - Preflight cache: 1 hour
 */
@Configuration
@EnableWebFluxSecurity
@RequiredArgsConstructor
public class SecurityConfig {
    
    private final AuthenticationFilter authenticationFilter;
    
    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            // Disable CSRF (not needed for stateless JWT API)
            .csrf(csrf -> csrf.disable())
            
            // Disable form login (using JWT)
            .formLogin(formLogin -> formLogin.disable())
            
            // Disable HTTP Basic (using JWT)
            .httpBasic(httpBasic -> httpBasic.disable())
            
            // Configure authorization rules
            .authorizeExchange(exchange -> exchange
                // Public endpoints (no authentication required)
                .pathMatchers("/api/auth/login", "/api/auth/register").permitAll()
                .pathMatchers("/actuator/health", "/actuator/ready").permitAll()
                
                // OPTIONS requests for CORS preflight
                .pathMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                
                // All other endpoints require authentication
                .anyExchange().authenticated()
            )
            
            // Add custom authentication filter
            .addFilterAt(authenticationFilter, SecurityWebFiltersOrder.AUTHENTICATION)
            
            // Enhanced security headers
            .headers(headers -> headers
                .frameOptions(frame -> frame.disable())  // Allow embedding if needed
                .xssProtection(xss -> xss.disable())     // Not needed for API
                .contentTypeOptions(cto -> cto.disable())
            )
            
            .build();
    }
    
    /**
     * CORS Configuration
     * 
     * PRODUCTION: Replace "*" with specific frontend URLs
     * Example: "https://app.moneyops.com", "https://admin.moneyops.com"
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        
        // IMPORTANT: For production, replace with actual frontend URLs
        configuration.setAllowedOriginPatterns(List.of("*"));
        // configuration.setAllowedOrigins(Arrays.asList(
        //     "https://app.moneyops.com",
        //     "https://admin.moneyops.com",
        //     "http://localhost:3000"  // Dev frontend
        // ));
        
        configuration.setAllowedMethods(Arrays.asList(
            "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"
        ));
        
        configuration.setAllowedHeaders(List.of("*"));
        
        // Allow credentials (cookies, Authorization header)
        configuration.setAllowCredentials(true);
        
        // Preflight cache duration (1 hour)
        configuration.setMaxAge(3600L);
        
        // Expose custom headers to frontend
        configuration.setExposedHeaders(Arrays.asList(
            "X-Correlation-Id",
            "X-Response-Time",
            "X-Total-Count"  // For pagination
        ));
        
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        
        return source;
    }
}
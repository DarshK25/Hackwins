// src/main/java/com/moneyops/auth/config/SecurityConfig.java
package com.moneyops.auth.config;

import com.moneyops.auth.security.AuthEntryPoint;
import com.moneyops.auth.security.JwtFilter;
import com.moneyops.auth.security.OAuth2SuccessHandler;
import com.moneyops.auth.security.ServiceTokenFilter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.context.annotation.Lazy;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtFilter jwtFilter;
    private final AuthEntryPoint authEntryPoint;
    private final OAuth2SuccessHandler oAuth2SuccessHandler;
    private final ServiceTokenFilter serviceTokenFilter;

    public SecurityConfig(
            JwtFilter jwtFilter,
            AuthEntryPoint authEntryPoint,
            OAuth2SuccessHandler oAuth2SuccessHandler,
            ServiceTokenFilter serviceTokenFilter
    ) {
        this.jwtFilter = jwtFilter;
        this.authEntryPoint = authEntryPoint;
        this.oAuth2SuccessHandler = oAuth2SuccessHandler;
        this.serviceTokenFilter = serviceTokenFilter;
    }



    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable());

        http.exceptionHandling(ex -> 
            ex.authenticationEntryPoint(authEntryPoint)
        );

        http.sessionManagement(session -> 
            session.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
        );

        http.authorizeHttpRequests(auth -> auth
            .requestMatchers(
                "/api/auth/**",
                "/api/onboarding/**",
                "/oauth2/**",
                "/swagger-ui/**",
                "/v3/api-docs/**"
            ).permitAll()
            .anyRequest().authenticated()
        );

        http.oauth2Login(oauth -> 
            oauth.successHandler(oAuth2SuccessHandler)
        );

        // ServiceTokenFilter runs FIRST so internal AI-Gateway calls
        // are authenticated before the JWT filter sees the request.
        http.addFilterBefore(serviceTokenFilter, UsernamePasswordAuthenticationFilter.class);
        http.addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}

// src/main/java/com/ledgertalk/auth/config/SecurityConfig.java
package com.ledgertalk.auth.config;

import com.ledgertalk.auth.security.AuthEntryPoint;
import com.ledgertalk.auth.security.JwtFilter;
import com.ledgertalk.auth.security.OAuth2SuccessHandler;
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

    public SecurityConfig(
            JwtFilter jwtFilter,
            AuthEntryPoint authEntryPoint,
            OAuth2SuccessHandler oAuth2SuccessHandler
    ) {
        this.jwtFilter = jwtFilter;
        this.authEntryPoint = authEntryPoint;
        this.oAuth2SuccessHandler = oAuth2SuccessHandler;
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
                "/oauth2/**",
                "/swagger-ui/**",
                "/v3/api-docs/**"
            ).permitAll()
            .anyRequest().authenticated()
        );

        http.oauth2Login(oauth -> 
            oauth.successHandler(oAuth2SuccessHandler)
        );

        http.addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
// src/main/java/com/moneyops/shared/dto/ErrorResponse.java
package com.moneyops.shared.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ErrorResponse {
    private String error;
    private String message;
    private List<String> details;
    private String timestamp;
    private String path;

    public ErrorResponse(String error, String message, String path) {
        this.error = error;
        this.message = message;
        this.timestamp = java.time.LocalDateTime.now().toString();
        this.path = path;
    }
}
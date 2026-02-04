// src/main/java/com/moneyops/shared/dto/ApiResponse.java
package com.moneyops.shared.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    private boolean success;
    private String message;
    private T data;
    private String timestamp;

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, "Success", data, java.time.LocalDateTime.now().toString());
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(true, message, data, java.time.LocalDateTime.now().toString());
    }

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null, java.time.LocalDateTime.now().toString());
    }

    public static ApiResponse<ErrorResponse> error(ErrorResponse errorResponse) {
        return new ApiResponse<>(false, errorResponse.getMessage(), errorResponse, java.time.LocalDateTime.now().toString());
    }
}
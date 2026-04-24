package com.moneyops.settings.controller;

import com.moneyops.settings.dto.SettingsResponseDto;
import com.moneyops.settings.dto.SettingsUpdateRequestDto;
import com.moneyops.settings.service.SettingsService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/settings")
@RequiredArgsConstructor
public class SettingsController {

    private final SettingsService settingsService;

    @GetMapping
    public ResponseEntity<ApiResponse<SettingsResponseDto>> getSettings(
            @RequestHeader("X-User-Id") String userId,
            @RequestHeader("X-Org-Id") String orgId) {
        SettingsResponseDto settings = settingsService.getSettings();
        return ResponseEntity.ok(ApiResponse.success(settings));
    }

    @PutMapping
    public ResponseEntity<ApiResponse<SettingsResponseDto>> updateSettings(
            @RequestBody SettingsUpdateRequestDto request,
            @RequestHeader("X-User-Id") String userId,
            @RequestHeader("X-Org-Id") String orgId) {
        SettingsResponseDto settings = settingsService.updateSettings(request);
        return ResponseEntity.ok(ApiResponse.success(settings));
    }
}

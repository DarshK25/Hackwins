package com.moneyops.cashflow.controller;

import com.moneyops.cashflow.dto.CashflowForecastDto;
import com.moneyops.cashflow.dto.CashflowSummaryDto;
import com.moneyops.cashflow.service.CashflowService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/cashflow")
@RequiredArgsConstructor
public class CashflowController {

    private final CashflowService cashflowService;

    @GetMapping("/summary")
    public ResponseEntity<CashflowSummaryDto> getSummary(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "6") int months) {
        String resolvedOrgId = OrgContext.getOrgId() != null ? OrgContext.getOrgId() : orgId;
        if (resolvedOrgId == null) return ResponseEntity.status(401).build();

        return ResponseEntity.ok(cashflowService.getSummary(resolvedOrgId, months));
    }

    @GetMapping("/forecast")
    public ResponseEntity<CashflowForecastDto> getForecast(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "3") int months) {
        String resolvedOrgId = OrgContext.getOrgId() != null ? OrgContext.getOrgId() : orgId;
        if (resolvedOrgId == null) return ResponseEntity.status(401).build();

        return ResponseEntity.ok(cashflowService.getForecast(resolvedOrgId, months));
    }
}

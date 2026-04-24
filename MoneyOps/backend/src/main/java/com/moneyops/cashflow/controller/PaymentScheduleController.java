package com.moneyops.cashflow.controller;

import com.moneyops.cashflow.dto.SchedulePaymentDto;
import com.moneyops.cashflow.service.PaymentScheduleService;
import com.moneyops.shared.utils.OrgContext;
import com.moneyops.transactions.dto.TransactionDto;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/payments")
@RequiredArgsConstructor
public class PaymentScheduleController {

    private final PaymentScheduleService paymentScheduleService;

    @PostMapping("/schedule")
    public ResponseEntity<TransactionDto> schedulePayment(@RequestBody SchedulePaymentDto dto) {
        String resolvedOrgId = OrgContext.getOrgId() != null ? OrgContext.getOrgId() : dto.getOrgId();
        String userId = OrgContext.getUserId();
        
        if (resolvedOrgId == null || userId == null) {
            return ResponseEntity.status(401).build();
        }
        
        dto.setOrgId(resolvedOrgId);
        TransactionDto scheduled = paymentScheduleService.schedulePayment(dto, userId);
        return ResponseEntity.ok(scheduled);
    }
}

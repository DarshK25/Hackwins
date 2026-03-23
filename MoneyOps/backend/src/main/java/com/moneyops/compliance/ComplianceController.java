package com.moneyops.compliance;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;

    @GetMapping("/deadlines")
    public ResponseEntity<ComplianceService.DeadlinesResponse> getDeadlines(@RequestParam(required = false) String businessId) {
        return ResponseEntity.ok(complianceService.getDeadlines(businessId));
    }

    @PostMapping("/tds/calc")
    public ResponseEntity<ComplianceService.TdsCalculationResponse> calculateTds(@RequestBody ComplianceService.TdsCalcRequest request) {
        return ResponseEntity.ok(complianceService.calculateTds(request));
    }
}

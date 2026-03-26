package com.moneyops.compliance;

import com.moneyops.shared.utils.OrgContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;

    @GetMapping("/compliance/status")
    public ResponseEntity<ComplianceService.ComplianceStatusResponse> getComplianceStatus(
            @RequestParam(required = false) String businessId,
            @RequestParam(required = false) String userId) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getComplianceStatus(orgId, businessId, userId));
    }

    @GetMapping("/deadlines")
    public ResponseEntity<ComplianceService.DeadlinesResponse> getDeadlines(@RequestParam(required = false) String businessId) {
        return ResponseEntity.ok(complianceService.getDeadlines(businessId));
    }

    @PostMapping("/tds/calc")
    public ResponseEntity<ComplianceService.TdsCalculationResponse> calculateTds(@RequestBody ComplianceService.TdsCalcRequest request) {
        return ResponseEntity.ok(complianceService.calculateTds(request));
    }
}
